# Real-Time Audio Waveform UI — Technical Implementation

> Web Audio API + Canvas 2D · TypeScript / React implementation details

---

## Table of Contents

1. [Overall Architecture](#1-overall-architecture)
2. [Type Definitions](#2-type-definitions)
3. [Permission Request and AudioContext Initialization](#3-permission-request-and-audiocontext-initialization)
4. [AnalyserNode Parameter Configuration](#4-analysernode-parameter-configuration)
5. [History Array and Scrolling Logic](#5-history-array-and-scrolling-logic)
6. [Canvas Rendering](#6-canvas-rendering)
7. [Custom Hook: useAudioWaveform](#7-custom-hook-useaudiowaveform)
8. [React Component: AudioWaveform.tsx](#8-react-component-audiowaveformtsx)
9. [Stop and Resource Cleanup](#9-stop-and-resource-cleanup)
10. [Common Issues and Notes](#10-common-issues-and-notes)
11. [Pure TypeScript Reference Implementation](#11-pure-typescript-reference-implementation)
12. [Parameter Quick Reference](#12-parameter-quick-reference)

---

## 1. Overall Architecture

The solution is composed of three layers, decoupled from each other and independently replaceable:

```
┌─────────────────────────────────────────────────────┐
│                  Audio Capture Layer                  │
│   getUserMedia → MediaStream → AudioContext          │
│   MediaStreamSourceNode → AnalyserNode               │
└─────────────────┬───────────────────────────────────┘
                  │ getByteTimeDomainData() per frame
┌─────────────────▼───────────────────────────────────┐
│                  Data Processing Layer                │
│   Compute RMS amplitude → write to history[] → downsampling control │
└─────────────────┬───────────────────────────────────┘
                  │ requestAnimationFrame
┌─────────────────▼───────────────────────────────────┐
│                  Rendering Layer                     │
│   Canvas 2D → scrolling bars → DPR adaptation → color state │
└─────────────────────────────────────────────────────┘
```

**Key principle:** Sampling and drawing are separated. The data layer only writes to `history[]`; the rendering layer only reads and draws. They do not interfere with each other.

---

## 2. Type Definitions

The unified type definitions live in `types/waveform.ts`:

```typescript
// types/waveform.ts

export interface WaveformConfig {
  /** Bar width (px), recommended 2~4 */
  barWidth: number;
  /** Gap between bars (px), recommended 1~3 */
  gap: number;
  /** Maximum length of the historical amplitude array */
  maxBars: number;
  /** Minimum bar height ratio when silent (relative to canvas height), recommended 0.04~0.1 */
  minHeightRatio: number;
  /** Linear amplification factor for amplitude; 2~4 is recommended for low-volume devices */
  amplify: number;
  /** Downsampling: sample every N frames; 1 = sample every frame */
  sampleEvery: number;
  /** Color when recording */
  activeColor: string;
  /** Color after stopping */
  idleColor: string;
}

export interface WaveformState {
  isRecording: boolean;
  elapsedSeconds: number;
  /** Current frame amplitude, 0~1 */
  currentAmplitude: number;
  error: string | null;
}

export interface AudioRefs {
  stream: MediaStream | null;
  audioCtx: AudioContext | null;
  analyser: AnalyserNode | null;
  animFrame: number | null;
  dataArray: Uint8Array | null;
}
```

---

## 3. Permission Request and AudioContext Initialization

### 3.1 getUserMedia

Must be called inside a user-gesture callback (such as a button click); otherwise some browsers silently reject:

```typescript
// utils/audio.ts

/**
 * Request microphone permission and return a MediaStream
 * Must be called inside a user-gesture callback
 */
export async function requestMicrophoneAccess(): Promise<MediaStream> {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error('The current browser does not support getUserMedia');
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        // Disable echo cancellation and noise suppression to keep the raw signal (toggle as needed)
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
        // Sample rate (supported by some browsers)
        // sampleRate: 44100,
      },
    });
    return stream;
  } catch (err) {
    if (err instanceof DOMException) {
      switch (err.name) {
        case 'NotAllowedError':
          throw new Error('User denied microphone permission');
        case 'NotFoundError':
          throw new Error('No microphone device detected');
        case 'NotReadableError':
          throw new Error('Microphone is in use by another application');
        default:
          throw new Error(`麦克风访问失败：${err.message}`);
        }
    }
    throw err;
  }
}
```

### 3.2 Initialize AudioContext and AnalyserNode

```typescript
// utils/audio.ts

const AudioContextClass =
  window.AudioContext ?? (window as any).webkitAudioContext as typeof AudioContext;

export interface AudioPipeline {
  audioCtx: AudioContext;
  analyser: AnalyserNode;
  dataArray: Uint8Array;
}

export async function createAudioPipeline(
  stream: MediaStream,
  config: Pick<WaveformConfig, never> & {
    fftSize?: number;
    smoothingTimeConstant?: number;
  } = {}
): Promise<AudioPipeline> {
  const audioCtx = new AudioContextClass();

  // Safari creates the context as suspended by default; must resume within a user gesture
  if (audioCtx.state === 'suspended') {
    await audioCtx.resume();
  }

  const analyser = audioCtx.createAnalyser();
  analyser.fftSize = config.fftSize ?? 256;
  analyser.smoothingTimeConstant = config.smoothingTimeConstant ?? 0.4;

  const source = audioCtx.createMediaStreamSource(stream);
  // ⚠️ Do not connect to destination, or the microphone audio will be played through the speaker
  source.connect(analyser);

  const dataArray = new Uint8Array(analyser.fftSize);

  return { audioCtx, analyser, dataArray };
}

export async function destroyAudioPipeline(refs: AudioRefs): Promise<void> {
  if (refs.animFrame !== null) {
    cancelAnimationFrame(refs.animFrame);
    refs.animFrame = null;
  }
  refs.stream?.getTracks().forEach(track => track.stop());
  await refs.audioCtx?.close();
  refs.stream = null;
  refs.audioCtx = null;
  refs.analyser = null;
  refs.dataArray = null;
}
```

---

## 4. AnalyserNode Parameter Configuration

### 4.1 Core Parameter Description

| Parameter | Recommended | Description |
|-----------|-------------|-------------|
| `fftSize` | `256` | Time-domain buffer size (must be a power of 2). 256 is enough for a waveform UI; larger values add latency |
| `smoothingTimeConstant` | `0.4` | Smoothing factor 0~1. 0 = no smoothing (jittery), 1 = no response |
| `minDecibels` | default | Only affects `getByteFrequencyData`; time-domain data is not affected |
| `maxDecibels` | default | Same as above |

### 4.2 Amplitude Calculation: Mean vs RMS

```typescript
// utils/amplitude.ts

/**
 * Method A: Simple mean (fast, very low CPU)
 * Less sensitive to peaks; suitable for visual display
 */
export function calcAmplitudeMean(data: Uint8Array): number {
  let sum = 0;
  for (let i = 0; i < data.length; i++) {
    sum += Math.abs(data[i] - 128); // 128 is the silence baseline
  }
  return sum / data.length / 128; // Normalize to 0~1
}

/**
 * Method B: RMS root-mean-square (more accurate, closer to perceived loudness)
 * Recommended when precise response is needed
 */
export function calcAmplitudeRMS(data: Uint8Array): number {
  let sum = 0;
  for (let i = 0; i < data.length; i++) {
    const v = (data[i] - 128) / 128;
    sum += v * v;
  }
  return Math.sqrt(sum / data.length);
}

/**
 * Apply non-linear amplification to the amplitude, stretching the low-volume range more
 * Suitable for devices with low microphone gain
 */
export function amplifyLog(amp: number, factor = 9): number {
  return Math.log1p(amp * factor) / Math.log(1 + factor);
}

/**
 * Linear amplification + clamp
 */
export function amplifyLinear(amp: number, factor = 3): number {
  return Math.min(1, amp * factor);
}
```

> **Reference amplitude range:**
> - Silence (ambient noise): `0.01 ~ 0.03`
> - Normal speech: `0.1 ~ 0.4`
> - Loud speech: `0.4 ~ 0.7`
> - Shouting near the microphone: `0.7 ~ 1.0`

---

## 5. History Array and Scrolling Logic

### 5.1 Data Structure

```typescript
// Use a plain array; push/shift is enough
// For ultra-high-performance scenarios, switch to Float32Array + a ring buffer, but a waveform UI does not need it
const history: number[] = [];
const MAX_BARS = 300;

function pushAmplitude(amp: number): void {
  history.push(amp);
  if (history.length > MAX_BARS) {
    history.shift(); // The oldest data is shifted out from the left
  }
}
```

### 5.2 Downsampling Control (Avoid Over-Dense Waveforms)

`requestAnimationFrame` runs at roughly 60fps; sampling every frame makes the bars scroll so fast that the visual becomes noise.

```typescript
let frameCount = 0;
const SAMPLE_EVERY = 2; // Sample every 2 frames, equivalent to 30fps

function tick(): void {
  frameCount++;

  if (frameCount % SAMPLE_EVERY === 0) {
    analyser.getByteTimeDomainData(dataArray);
    const amp = calcAmplitudeMean(dataArray);
    pushAmplitude(amplifyLinear(amp));
  }

  draw();
  animFrame = requestAnimationFrame(tick);
}
```

> **Empirical value:** `barWidth=3, gap=2` (5px per slot), a 400px-wide canvas shows roughly 80 slots. `MAX_BARS` is recommended at 2~3x the visible slots to avoid empty columns at the edge.

---

## 6. Canvas Rendering

### 6.1 DPR Adaptation (Required for Retina Screens)

```typescript
// utils/canvas.ts

/**
 * Set the physical resolution of the canvas to fix blur on Retina screens
 * Returns a scaled ctx; subsequent drawing can use CSS-pixel coordinates
 */
export function setupHiDPICanvas(
  canvas: HTMLCanvasElement
): CanvasRenderingContext2D {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();

  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;

  const ctx = canvas.getContext('2d')!;
  ctx.scale(dpr, dpr); // Scale the coordinate system back to CSS pixels

  return ctx;
}
```

### 6.2 Draw Function

```typescript
// utils/canvas.ts

export interface DrawOptions {
  history: number[];
  barWidth?: number;      // Default 3
  gap?: number;           // Default 2
  minHeightRatio?: number; // Default 0.06
  color?: string;         // Default '#E24B4A'
}

export function drawWaveform(
  canvas: HTMLCanvasElement,
  ctx: CanvasRenderingContext2D,
  options: DrawOptions
): void {
  const {
    history,
    barWidth = 3,
    gap = 2,
    minHeightRatio = 0.06,
    color = '#E24B4A',
  } = options;

  // Use CSS dimensions (ctx is already scaled)
  const W = canvas.offsetWidth;
  const H = canvas.offsetHeight;

  ctx.clearRect(0, 0, W, H);

  const stride = barWidth + gap;
  const count = Math.floor(W / stride); // How many bars fit in the current width

  ctx.fillStyle = color;

  for (let i = 0; i < count; i++) {
    // The newest data is on the right: read backwards from the end of history
    const histIdx = history.length - count + i;
    const amp = histIdx >= 0 ? history[histIdx] : 0;

    const minH = H * minHeightRatio;
    const barH = Math.max(minH, amp * H * 0.9);
    const x = i * stride;
    const y = (H - barH) / 2; // Vertically centered

    ctx.beginPath();
    // roundRect availability check (Safari 15.4+, Chrome 99+)
    if (ctx.roundRect) {
      ctx.roundRect(x, y, barWidth, barH, 1);
    } else {
      ctx.rect(x, y, barWidth, barH);
    }
    ctx.fill();
  }
}
```

### 6.3 Responsive Width (ResizeObserver)

```typescript
// Redraw when canvas width changes
const ro = new ResizeObserver(() => {
  const ctx = setupHiDPICanvas(canvas); // Re-set the physical resolution
  drawWaveform(canvas, ctx, { history, color: isRecording ? activeColor : idleColor });
});
ro.observe(canvas);

// Disconnect on component unmount
ro.disconnect();
```

---

## 7. Custom Hook: useAudioWaveform

Encapsulate all logic into a reusable hook:

```typescript
// hooks/useAudioWaveform.ts
import { useRef, useState, useCallback, useEffect } from 'react';
import type { WaveformConfig, WaveformState, AudioRefs } from '../types/waveform';
import {
  requestMicrophoneAccess,
  createAudioPipeline,
  destroyAudioPipeline,
} from '../utils/audio';
import { calcAmplitudeMean, amplifyLinear } from '../utils/amplitude';
import { setupHiDPICanvas, drawWaveform } from '../utils/canvas';

const DEFAULT_CONFIG: WaveformConfig = {
  barWidth: 3,
  gap: 2,
  maxBars: 300,
  minHeightRatio: 0.06,
  amplify: 3,
  sampleEvery: 2,
  activeColor: '#E24B4A',
  idleColor: '#B4B2A9',
};

export function useAudioWaveform(config: Partial<WaveformConfig> = {}) {
  const cfg = { ...DEFAULT_CONFIG, ...config };

  // Canvas ref (provided by the consumer)
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const ctxRef = useRef<CanvasRenderingContext2D | null>(null);

  // Audio resource refs (do not trigger re-renders)
  const audioRefs = useRef<AudioRefs>({
    stream: null,
    audioCtx: null,
    analyser: null,
    animFrame: null,
    dataArray: null,
  });

  // Historical amplitude (does not trigger re-renders; avoids per-frame setState)
  const historyRef = useRef<number[]>([]);
  const frameCountRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Externally exposed state (only updates when the value actually changes)
  const [state, setState] = useState<WaveformState>({
    isRecording: false,
    elapsedSeconds: 0,
    currentAmplitude: 0,
    error: null,
  });

  // ─── Draw ────────────────────────────────────────────────────────
  const draw = useCallback((isRecording: boolean) => {
    const canvas = canvasRef.current;
    const ctx = ctxRef.current;
    if (!canvas || !ctx) return;

    drawWaveform(canvas, ctx, {
      history: historyRef.current,
      barWidth: cfg.barWidth,
      gap: cfg.gap,
      minHeightRatio: cfg.minHeightRatio,
      color: isRecording ? cfg.activeColor : cfg.idleColor,
    });
  }, [cfg]);

  // ─── Animation Loop ───────────────────────────────────────────────
  const tick = useCallback(() => {
    const refs = audioRefs.current;
    if (!refs.analyser || !refs.dataArray) return;

    frameCountRef.current++;

    if (frameCountRef.current % cfg.sampleEvery === 0) {
      refs.analyser.getByteTimeDomainData(refs.dataArray);
      const raw = calcAmplitudeMean(refs.dataArray);
      const amp = amplifyLinear(raw, cfg.amplify);

      historyRef.current.push(amp);
      if (historyRef.current.length > cfg.maxBars) {
        historyRef.current.shift();
      }

      // Update amplitude once per sample (not every frame, to avoid over-rendering)
      setState(prev => ({ ...prev, currentAmplitude: amp }));
    }

    draw(true);
    refs.animFrame = requestAnimationFrame(tick);
  }, [cfg, draw]);

  // ─── Start Recording ──────────────────────────────────────────────
  const start = useCallback(async () => {
    if (state.isRecording) return;

    try {
      setState(prev => ({ ...prev, error: null }));

      const stream = await requestMicrophoneAccess();
      const { audioCtx, analyser, dataArray } = await createAudioPipeline(stream);

      audioRefs.current = {
        stream,
        audioCtx,
        analyser,
        dataArray,
        animFrame: null,
      };

      historyRef.current = [];
      frameCountRef.current = 0;

      // Initialize the canvas ctx (if not yet initialized or the canvas was swapped)
      if (canvasRef.current) {
        ctxRef.current = setupHiDPICanvas(canvasRef.current);
      }

      setState({ isRecording: true, elapsedSeconds: 0, currentAmplitude: 0, error: null });

      // Timer
      timerRef.current = setInterval(() => {
        setState(prev => ({ ...prev, elapsedSeconds: prev.elapsedSeconds + 1 }));
      }, 1000);

      tick();
    } catch (err) {
      setState(prev => ({
        ...prev,
        error: err instanceof Error ? err.message : 'Unknown error',
      }));
    }
  }, [state.isRecording, tick]);

  // ─── Stop Recording ───────────────────────────────────────────────
  const stop = useCallback(async () => {
    if (!state.isRecording) return;

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    await destroyAudioPipeline(audioRefs.current);

    setState(prev => ({ ...prev, isRecording: false }));
    draw(false); // Draw one final frame in the idle color
  }, [state.isRecording, draw]);

  // ─── Toggle ───────────────────────────────────────────────────────
  const toggle = useCallback(async () => {
    if (state.isRecording) await stop();
    else await start();
  }, [state.isRecording, start, stop]);

  // ─── Unmount Cleanup ──────────────────────────────────────────────
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      destroyAudioPipeline(audioRefs.current);
    };
  }, []);

  // ─── Page Background Pause ────────────────────────────────────────
  useEffect(() => {
    const handleVisibility = () => {
      const refs = audioRefs.current;
      if (document.hidden) {
        if (refs.animFrame !== null) {
          cancelAnimationFrame(refs.animFrame);
          refs.animFrame = null;
        }
      } else if (state.isRecording) {
        tick(); // Restart
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, [state.isRecording, tick]);

  return {
    canvasRef,
    state,
    start,
    stop,
    toggle,
  };
}
```

---

## 8. React Component: AudioWaveform.tsx

### 8.1 Full Component

```tsx
// components/AudioWaveform.tsx
import React, { useEffect, useRef } from 'react';
import { useAudioWaveform } from '../hooks/useAudioWaveform';
import { setupHiDPICanvas } from '../utils/canvas';
import type { WaveformConfig } from '../types/waveform';

interface AudioWaveformProps {
  /** Component config; overrides defaults */
  config?: Partial<WaveformConfig>;
  /** Canvas height (px), default 56 */
  height?: number;
  /** Callback fired when recording stops, returning the elapsed seconds */
  onStop?: (elapsedSeconds: number) => void;
  className?: string;
}

export const AudioWaveform: React.FC<AudioWaveformProps> = ({
  config,
  height = 56,
  onStop,
  className,
}) => {
  const { canvasRef, state, toggle } = useAudioWaveform(config);

  // Notify the parent component
  const prevRecordingRef = useRef(false);
  useEffect(() => {
    if (prevRecordingRef.current && !state.isRecording) {
      onStop?.(state.elapsedSeconds);
    }
    prevRecordingRef.current = state.isRecording;
  }, [state.isRecording, state.elapsedSeconds, onStop]);

  // ResizeObserver: redraw when width changes
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ro = new ResizeObserver(() => {
      setupHiDPICanvas(canvas);
    });
    ro.observe(canvas);
    return () => ro.disconnect();
  }, [canvasRef]);

  // Format time
  const formatTime = (sec: number): string => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${String(s).padStart(2, '0')}`;
  };

  return (
    <div
      className={className}
      style={{
        background: 'var(--color-background-primary, #fff)',
        borderRadius: 12,
        border: '0.5px solid var(--color-border-tertiary, #e0e0e0)',
        padding: '12px 16px',
      }}
    >
      {/* Waveform canvas */}
      <canvas
        ref={canvasRef}
        style={{
          display: 'block',
          width: '100%',
          height,
          borderRadius: 4,
        }}
      />

      {/* Control bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 10 }}>
        {/* Timer */}
        <span style={{ fontSize: 13, color: '#888', minWidth: 36 }}>
          {formatTime(state.elapsedSeconds)}
        </span>

        {/* Record button */}
        <button
          onClick={toggle}
          style={{
            width: 36,
            height: 36,
            borderRadius: '50%',
            border: state.isRecording ? 'none' : '0.5px solid #ccc',
            background: state.isRecording ? '#E24B4A' : '#f0f0f0',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            transition: 'background 0.2s',
          }}
          aria-label={state.isRecording ? 'Stop recording' : 'Start recording'}
        >
          {state.isRecording ? (
            // Stop icon (square)
            <div style={{ width: 10, height: 10, borderRadius: 2, background: '#fff' }} />
          ) : (
            // Record icon (circle)
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#888' }} />
          )}
        </button>

        {/* Status text / error message */}
        <span style={{ fontSize: 12, color: state.error ? '#E24B4A' : '#999' }}>
          {state.error ?? (state.isRecording ? 'Recording...' : 'Tap to start recording')}
        </span>
      </div>
    </div>
  );
};

export default AudioWaveform;
```

### 8.2 Usage Example

```tsx
// App.tsx
import React from 'react';
import { AudioWaveform } from './components/AudioWaveform';

export default function App() {
  const handleStop = (seconds: number) => {
    console.log(`录音结束，时长 ${seconds} 秒`);
    // Handle audio data, upload, etc. here
  };

  return (
    <div style={{ padding: 24, maxWidth: 480 }}>
      <AudioWaveform
        height={56}
        config={{
          barWidth: 3,
          gap: 2,
          amplify: 3,
          activeColor: '#E24B4A',
          idleColor: '#B4B2A9',
        }}
        onStop={handleStop}
      />
    </div>
  );
}
```

### 8.3 Recording + Capturing Blob in Real Time (Optional)

If you need the audio file when stopping:

```tsx
// hooks/useAudioRecorder.ts
// Layer MediaRecorder on top of useAudioWaveform

export function useAudioRecorder() {
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);

  const startRecording = (stream: MediaStream) => {
    chunksRef.current = [];
    const recorder = new MediaRecorder(stream, {
      mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/ogg;codecs=opus',
    });
    recorder.ondataavailable = e => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };
    recorder.start(100); // Trigger ondataavailable every 100ms
    mediaRecorderRef.current = recorder;
  };

  const stopRecording = (): Promise<Blob> => {
    return new Promise(resolve => {
      const recorder = mediaRecorderRef.current;
      if (!recorder) return;
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
        resolve(blob);
      };
      recorder.stop();
    });
  };

  return { startRecording, stopRecording };
}
```

---

## 9. Stop and Resource Cleanup

**Must be cleaned up in order, otherwise the microphone indicator will not turn off or memory will leak:**

```typescript
async function stopRecording(refs: AudioRefs): Promise<void> {
  // 1. Stop the animation loop (otherwise tick keeps accessing the closed analyser)
  if (refs.animFrame !== null) {
    cancelAnimationFrame(refs.animFrame);
    refs.animFrame = null;
  }

  // 2. Stop all tracks (so the browser microphone icon disappears)
  refs.stream?.getTracks().forEach(track => track.stop());

  // 3. Close the AudioContext (release system audio resources)
  if (refs.audioCtx?.state !== 'closed') {
    await refs.audioCtx?.close();
  }

  // 4. Null out references (help GC)
  refs.stream = null;
  refs.audioCtx = null;
  refs.analyser = null;
  refs.dataArray = null;
}
```

> `stream.getTracks().forEach(t => t.stop())` is the key to making the browser microphone icon disappear; if you skip it, the icon stays on and the user thinks recording is still active.

---

## 10. Common Issues and Notes

### 10.1 Safari Compatibility

```typescript
// Safari requires the webkitAudioContext prefix
const AudioContextClass =
  window.AudioContext ?? (window as any).webkitAudioContext as typeof AudioContext;

// Safari iOS: the page must be served over HTTPS (localhost is allowed)
// Safari: AudioContext starts in 'suspended' state and must be explicitly resumed
if (audioCtx.state === 'suspended') {
  await audioCtx.resume(); // Must be inside a user gesture
}
```

### 10.2 TypeScript Missing roundRect Type

Some TypeScript versions do not include `roundRect` on `CanvasRenderingContext2D`; you need to extend it manually:

```typescript
// types/canvas.d.ts
interface CanvasRenderingContext2D {
  roundRect(
    x: number, y: number,
    width: number, height: number,
    radii?: number | DOMPointInit | (number | DOMPointInit)[]
  ): void;
}
```

### 10.3 Amplification (Low-Volume Scenarios)

```typescript
// Linear amplification, simple and direct
const amp = Math.min(1, rawAmp * 3);

// Logarithmic amplification: low-amplitude range stretches more, high amplitude does not clip
const amp = Math.log1p(rawAmp * 9) / Math.log(10);

// Dynamic gain (auto-adjusts based on the recent maximum)
const recentMax = Math.max(...historyRef.current.slice(-30), 0.1);
const amp = Math.min(1, rawAmp / recentMax);
```

### 10.4 Canvas Initial Render Width Is 0

`canvas.offsetWidth` can be 0 before the first render (SSR or hidden container). Use `ResizeObserver` instead of reading it directly:

```typescript
useEffect(() => {
  const canvas = canvasRef.current;
  if (!canvas) return;

  const ro = new ResizeObserver(entries => {
    for (const entry of entries) {
      // Use contentRect instead of offsetWidth for better accuracy
      const { width } = entry.contentRect;
      if (width > 0) {
        setupHiDPICanvas(canvas);
      }
    }
  });

  ro.observe(canvas);
  return () => ro.disconnect();
}, []);
```

### 10.5 Page Background Pause / Resume

```typescript
useEffect(() => {
  const handleVisibility = () => {
    if (document.hidden) {
      // Page goes to background: pause rAF (browsers throttle automatically, but explicit cancel is safer)
      if (audioRefs.current.animFrame !== null) {
        cancelAnimationFrame(audioRefs.current.animFrame);
        audioRefs.current.animFrame = null;
      }
    } else if (isRecording) {
      // Page returns to foreground: restart the loop
      tick();
    }
  };

  document.addEventListener('visibilitychange', handleVisibility);
  return () => document.removeEventListener('visibilitychange', handleVisibility);
}, [isRecording, tick]);
```

### 10.6 Next.js / SSR Environment

The Web Audio API only runs in the browser; guard for SSR:

```typescript
// Inside a hook or utility
const isBrowser = typeof window !== 'undefined';

if (!isBrowser || !window.AudioContext) {
  throw new Error('The current environment does not support the Web Audio API');
}

// Or inside a Next.js component
import dynamic from 'next/dynamic';
const AudioWaveform = dynamic(() => import('./AudioWaveform'), { ssr: false });
```

---

## 11. Pure TypeScript Reference Implementation

For non-React scenarios (vanilla DOM / Vue / Svelte, etc.):

```typescript
// WaveformRecorder.ts

import type { WaveformConfig } from './types/waveform';

const DEFAULT_CONFIG: WaveformConfig = {
  barWidth: 3,
  gap: 2,
  maxBars: 300,
  minHeightRatio: 0.06,
  amplify: 3,
  sampleEvery: 2,
  activeColor: '#E24B4A',
  idleColor: '#B4B2A9',
};

export class WaveformRecorder {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private cfg: WaveformConfig;

  private stream: MediaStream | null = null;
  private audioCtx: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private dataArray: Uint8Array | null = null;
  private animFrame: number | null = null;
  private timer: ReturnType<typeof setInterval> | null = null;

  private history: number[] = [];
  private frameCount = 0;
  private _isRecording = false;
  private _elapsedSeconds = 0;

  // Event callbacks
  public onStart?: () => void;
  public onStop?: (elapsedSeconds: number) => void;
  public onError?: (error: Error) => void;
  public onTick?: (amplitude: number) => void;

  constructor(canvas: HTMLCanvasElement, config: Partial<WaveformConfig> = {}) {
    this.canvas = canvas;
    this.cfg = { ...DEFAULT_CONFIG, ...config };
    this.ctx = this.setupCanvas();
    this.observeResize();
  }

  get isRecording(): boolean { return this._isRecording; }
  get elapsedSeconds(): number { return this._elapsedSeconds; }

  private setupCanvas(): CanvasRenderingContext2D {
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = (rect.width || this.canvas.offsetWidth) * dpr;
    this.canvas.height = (rect.height || this.canvas.offsetHeight) * dpr;
    const ctx = this.canvas.getContext('2d')!;
    ctx.scale(dpr, dpr);
    return ctx;
  }

  private observeResize(): void {
    const ro = new ResizeObserver(() => {
      this.ctx = this.setupCanvas();
      this.draw();
    });
    ro.observe(this.canvas);
  }

  private draw(): void {
    const W = this.canvas.offsetWidth;
    const H = this.canvas.offsetHeight;
    const { barWidth, gap, minHeightRatio, activeColor, idleColor } = this.cfg;

    this.ctx.clearRect(0, 0, W, H);

    const stride = barWidth + gap;
    const count = Math.floor(W / stride);
    this.ctx.fillStyle = this._isRecording ? activeColor : idleColor;

    for (let i = 0; i < count; i++) {
      const idx = this.history.length - count + i;
      const amp = idx >= 0 ? this.history[idx] : 0;
      const minH = H * minHeightRatio;
      const barH = Math.max(minH, amp * H * 0.9);
      const x = i * stride;
      const y = (H - barH) / 2;

      this.ctx.beginPath();
      if (this.ctx.roundRect) {
        this.ctx.roundRect(x, y, barWidth, barH, 1);
      } else {
        this.ctx.rect(x, y, barWidth, barH);
      }
      this.ctx.fill();
    }
  }

  private tick = (): void => {
    if (!this.analyser || !this.dataArray) return;

    this.frameCount++;
    if (this.frameCount % this.cfg.sampleEvery === 0) {
      this.analyser.getByteTimeDomainData(this.dataArray);

      let sum = 0;
      for (let i = 0; i < this.dataArray.length; i++) {
        sum += Math.abs(this.dataArray[i] - 128);
      }
      const amp = Math.min(1, (sum / this.dataArray.length / 128) * this.cfg.amplify);

      this.history.push(amp);
      if (this.history.length > this.cfg.maxBars) this.history.shift();

      this.onTick?.(amp);
    }

    this.draw();
    this.animFrame = requestAnimationFrame(this.tick);
  };

  async start(): Promise<void> {
    if (this._isRecording) return;

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const AudioCtx = window.AudioContext ?? (window as any).webkitAudioContext;
      this.audioCtx = new AudioCtx();
      if (this.audioCtx.state === 'suspended') await this.audioCtx.resume();

      this.analyser = this.audioCtx.createAnalyser();
      this.analyser.fftSize = 256;
      this.analyser.smoothingTimeConstant = 0.4;
      this.audioCtx.createMediaStreamSource(this.stream).connect(this.analyser);
      this.dataArray = new Uint8Array(this.analyser.fftSize);

      this.history = [];
      this.frameCount = 0;
      this._elapsedSeconds = 0;
      this._isRecording = true;

      this.timer = setInterval(() => { this._elapsedSeconds++; }, 1000);
      this.tick();
      this.onStart?.();
    } catch (err) {
      this.onError?.(err instanceof Error ? err : new Error(String(err)));
    }
  }

  async stop(): Promise<void> {
    if (!this._isRecording) return;

    if (this.animFrame !== null) cancelAnimationFrame(this.animFrame);
    if (this.timer !== null) clearInterval(this.timer);
    this.stream?.getTracks().forEach(t => t.stop());
    if (this.audioCtx?.state !== 'closed') await this.audioCtx?.close();

    this.animFrame = null;
    this.timer = null;
    this.stream = null;
    this.audioCtx = null;
    this.analyser = null;
    this.dataArray = null;
    this._isRecording = false;

    this.draw();
    this.onStop?.(this._elapsedSeconds);
  }

  async toggle(): Promise<void> {
    if (this._isRecording) await this.stop();
    else await this.start();
  }
}
```

**Usage example (vanilla DOM):**

```typescript
const canvas = document.getElementById('waveform') as HTMLCanvasElement;
const recorder = new WaveformRecorder(canvas, { amplify: 4 });

recorder.onStop = (sec) => console.log(`录音 ${sec}s`);
recorder.onError = (err) => console.error(err.message);

document.getElementById('btn')!.addEventListener('click', () => recorder.toggle());
```

---

## 12. Parameter Quick Reference

| Parameter | Recommended | Range | Description |
|-----------|-------------|-------|-------------|
| `fftSize` | `256` | 32 ~ 32768 (power of 2) | Time-domain buffer size; 256 is enough for a waveform UI |
| `smoothingTimeConstant` | `0.4` | 0 ~ 1 | 0 = no smoothing (jittery), 1 = no response |
| `barWidth` | `3` | 2 ~ 6 px | Bar width |
| `gap` | `2` | 1 ~ 4 px | Gap between bars |
| `minHeightRatio` | `0.06` | 0.02 ~ 0.15 | Minimum bar height ratio when silent |
| `amplify` | `3` | 1 ~ 8 | Linear amplification factor for amplitude |
| `sampleEvery` | `2` | 1 ~ 4 | Sample every N frames (downsampling) |
| `maxBars` | `300` | visible slots × 2 | Upper bound for the history array |

---

*Document version 1.0 · Web Audio API + Canvas 2D · TypeScript / React*
