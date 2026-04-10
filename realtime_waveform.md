# 实时音频波形 UI — 技术实现文档

> Web Audio API + Canvas 2D · TypeScript / React 实现细节

---

## 目录

1. [总体架构](#1-总体架构)
2. [类型定义](#2-类型定义)
3. [权限申请与 AudioContext 初始化](#3-权限申请与-audiocontext-初始化)
4. [AnalyserNode 参数配置](#4-analysernode-参数配置)
5. [历史数组与滚动逻辑](#5-历史数组与滚动逻辑)
6. [Canvas 渲染](#6-canvas-渲染)
7. [自定义 Hook：useAudioWaveform](#7-自定义-hookUseaudiowaveform)
8. [React 组件：AudioWaveform.tsx](#8-react-组件-audiowaveformtsx)
9. [停止与资源清理](#9-停止与资源清理)
10. [常见问题与注意事项](#10-常见问题与注意事项)
11. [纯 TypeScript 参考实现](#11-纯-typescript-参考实现)
12. [参数速查表](#12-参数速查表)

---

## 1. 总体架构

整个方案由三个层次组成，彼此解耦，可以独立替换：

```
┌─────────────────────────────────────────────────────┐
│                   音频采集层                          │
│   getUserMedia → MediaStream → AudioContext          │
│   MediaStreamSourceNode → AnalyserNode               │
└─────────────────┬───────────────────────────────────┘
                  │ 每帧 getByteTimeDomainData()
┌─────────────────▼───────────────────────────────────┐
│                   数据处理层                          │
│   计算 RMS 振幅 → 写入 history[] → 降采样控制         │
└─────────────────┬───────────────────────────────────┘
                  │ requestAnimationFrame
┌─────────────────▼───────────────────────────────────┐
│                   渲染层                             │
│   Canvas 2D → 滚动竖条 → DPR 适配 → 颜色状态          │
└─────────────────────────────────────────────────────┘
```

**关键原则：** 采样与绘制分离。数据层只管写入 `history[]`，渲染层只管读取并绘制，互不干扰。

---

## 2. 类型定义

统一的类型定义放在 `types/waveform.ts`：

```typescript
// types/waveform.ts

export interface WaveformConfig {
  /** 竖条宽度（px），推荐 2~4 */
  barWidth: number;
  /** 竖条间距（px），推荐 1~3 */
  gap: number;
  /** 历史振幅数组最大长度 */
  maxBars: number;
  /** 静音时竖条最小高度比例（相对 canvas 高度），推荐 0.04~0.1 */
  minHeightRatio: number;
  /** 振幅线性放大系数，低音量设备建议 2~4 */
  amplify: number;
  /** 降采样：每 N 帧采样一次，1 = 每帧都采 */
  sampleEvery: number;
  /** 录音中的颜色 */
  activeColor: string;
  /** 停止后的颜色 */
  idleColor: string;
}

export interface WaveformState {
  isRecording: boolean;
  elapsedSeconds: number;
  /** 当前帧振幅，0~1 */
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

## 3. 权限申请与 AudioContext 初始化

### 3.1 getUserMedia

必须在用户手势（点击按钮）的回调中调用，否则部分浏览器会静默拒绝：

```typescript
// utils/audio.ts

/**
 * 申请麦克风权限并返回 MediaStream
 * 必须在用户手势回调中调用
 */
export async function requestMicrophoneAccess(): Promise<MediaStream> {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error('当前浏览器不支持 getUserMedia');
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        // 关闭回声消除和降噪，保留原始信号（可按需开启）
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
        // 采样率（部分浏览器支持）
        // sampleRate: 44100,
      },
    });
    return stream;
  } catch (err) {
    if (err instanceof DOMException) {
      switch (err.name) {
        case 'NotAllowedError':
          throw new Error('用户拒绝了麦克风权限');
        case 'NotFoundError':
          throw new Error('未检测到麦克风设备');
        case 'NotReadableError':
          throw new Error('麦克风被其他应用占用');
        default:
          throw new Error(`麦克风访问失败：${err.message}`);
      }
    }
    throw err;
  }
}
```

### 3.2 初始化 AudioContext 与 AnalyserNode

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

  // Safari 创建后默认 suspended，必须在手势上下文中 resume
  if (audioCtx.state === 'suspended') {
    await audioCtx.resume();
  }

  const analyser = audioCtx.createAnalyser();
  analyser.fftSize = config.fftSize ?? 256;
  analyser.smoothingTimeConstant = config.smoothingTimeConstant ?? 0.4;

  const source = audioCtx.createMediaStreamSource(stream);
  // ⚠️ 不要 connect 到 destination，否则麦克风声音会从扬声器播出
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

## 4. AnalyserNode 参数配置

### 4.1 核心参数说明

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `fftSize` | `256` | 时域缓冲区大小（必须是 2 的幂）。256 已足够波形 UI，更大值延迟更高 |
| `smoothingTimeConstant` | `0.4` | 平滑系数 0~1。0 = 完全不平滑（跳动剧烈），1 = 完全不响应 |
| `minDecibels` | 默认 | 仅影响 `getByteFrequencyData`，时域数据不受影响 |
| `maxDecibels` | 默认 | 同上 |

### 4.2 振幅计算：均值 vs RMS

```typescript
// utils/amplitude.ts

/**
 * 方式 A：简单均值（快，CPU 极低）
 * 对爆音不够敏感，适合视觉展示
 */
export function calcAmplitudeMean(data: Uint8Array): number {
  let sum = 0;
  for (let i = 0; i < data.length; i++) {
    sum += Math.abs(data[i] - 128); // 128 是静音基准
  }
  return sum / data.length / 128; // 归一化到 0~1
}

/**
 * 方式 B：RMS 均方根（更准确，更接近主观响度）
 * 推荐用于需要精确响应的场景
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
 * 对振幅做非线性放大，低音量区间拉伸更明显
 * 适合麦克风增益低的设备
 */
export function amplifyLog(amp: number, factor = 9): number {
  return Math.log1p(amp * factor) / Math.log(1 + factor);
}

/**
 * 线性放大 + clamp
 */
export function amplifyLinear(amp: number, factor = 3): number {
  return Math.min(1, amp * factor);
}
```

> **参考振幅范围：**
> - 静音（环境噪声）：`0.01 ~ 0.03`
> - 正常说话：`0.1 ~ 0.4`
> - 大声说话：`0.4 ~ 0.7`
> - 接近麦克风大喊：`0.7 ~ 1.0`

---

## 5. 历史数组与滚动逻辑

### 5.1 数据结构

```typescript
// 使用普通数组，push/shift 即可
// 对于超高性能场景可改用 Float32Array + 环形缓冲，但波形 UI 不需要
const history: number[] = [];
const MAX_BARS = 300;

function pushAmplitude(amp: number): void {
  history.push(amp);
  if (history.length > MAX_BARS) {
    history.shift(); // 最旧的数据从左侧移出
  }
}
```

### 5.2 降采样控制（避免波形过密）

`requestAnimationFrame` 约 60fps，每帧都采样会让竖条滚动很快，视觉上像噪声。

```typescript
let frameCount = 0;
const SAMPLE_EVERY = 2; // 每 2 帧采一次，等效 30fps

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

> **经验值：** `barWidth=3, gap=2`（每格 5px），canvas 宽 400px 约显示 80 格。`MAX_BARS` 建议设为显示格数的 2~3 倍，避免边缘出现空白列。

---

## 6. Canvas 渲染

### 6.1 DPR 适配（Retina 屏必须处理）

```typescript
// utils/canvas.ts

/**
 * 设置 canvas 的物理分辨率，解决高清屏模糊问题
 * 返回已缩放的 ctx，后续用 CSS 尺寸坐标绘制即可
 */
export function setupHiDPICanvas(
  canvas: HTMLCanvasElement
): CanvasRenderingContext2D {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();

  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;

  const ctx = canvas.getContext('2d')!;
  ctx.scale(dpr, dpr); // 坐标系还原为 CSS 尺寸

  return ctx;
}
```

### 6.2 绘制函数

```typescript
// utils/canvas.ts

export interface DrawOptions {
  history: number[];
  barWidth?: number;      // 默认 3
  gap?: number;           // 默认 2
  minHeightRatio?: number; // 默认 0.06
  color?: string;         // 默认 '#E24B4A'
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

  // 使用 CSS 尺寸（ctx 已 scale）
  const W = canvas.offsetWidth;
  const H = canvas.offsetHeight;

  ctx.clearRect(0, 0, W, H);

  const stride = barWidth + gap;
  const count = Math.floor(W / stride); // 当前宽度能放几根

  ctx.fillStyle = color;

  for (let i = 0; i < count; i++) {
    // 最新数据在最右侧：从 history 末尾往前取
    const histIdx = history.length - count + i;
    const amp = histIdx >= 0 ? history[histIdx] : 0;

    const minH = H * minHeightRatio;
    const barH = Math.max(minH, amp * H * 0.9);
    const x = i * stride;
    const y = (H - barH) / 2; // 垂直居中

    ctx.beginPath();
    // roundRect 需判断兼容性（Safari 15.4+, Chrome 99+）
    if (ctx.roundRect) {
      ctx.roundRect(x, y, barWidth, barH, 1);
    } else {
      ctx.rect(x, y, barWidth, barH);
    }
    ctx.fill();
  }
}
```

### 6.3 响应式宽度（ResizeObserver）

```typescript
// canvas 宽度变化时需重新绘制
const ro = new ResizeObserver(() => {
  const ctx = setupHiDPICanvas(canvas); // 重新设置物理分辨率
  drawWaveform(canvas, ctx, { history, color: isRecording ? activeColor : idleColor });
});
ro.observe(canvas);

// 组件卸载时断开
ro.disconnect();
```

---

## 7. 自定义 Hook：useAudioWaveform

将所有逻辑封装为可复用的 Hook：

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

  // Canvas ref（由使用方传入）
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const ctxRef = useRef<CanvasRenderingContext2D | null>(null);

  // 音频资源 refs（不触发重渲染）
  const audioRefs = useRef<AudioRefs>({
    stream: null,
    audioCtx: null,
    analyser: null,
    animFrame: null,
    dataArray: null,
  });

  // 历史振幅（不触发重渲染，避免每帧 setState）
  const historyRef = useRef<number[]>([]);
  const frameCountRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 对外暴露的状态（只在状态真正变化时更新）
  const [state, setState] = useState<WaveformState>({
    isRecording: false,
    elapsedSeconds: 0,
    currentAmplitude: 0,
    error: null,
  });

  // ─── 绘制 ────────────────────────────────────────────────────────
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

  // ─── 动画循环 ─────────────────────────────────────────────────────
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

      // 每次采样更新一次 amplitude（不是每帧，避免过度渲染）
      setState(prev => ({ ...prev, currentAmplitude: amp }));
    }

    draw(true);
    refs.animFrame = requestAnimationFrame(tick);
  }, [cfg, draw]);

  // ─── 开始录音 ─────────────────────────────────────────────────────
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

      // 初始化 canvas ctx（如果还没初始化或 canvas 换了）
      if (canvasRef.current) {
        ctxRef.current = setupHiDPICanvas(canvasRef.current);
      }

      setState({ isRecording: true, elapsedSeconds: 0, currentAmplitude: 0, error: null });

      // 计时器
      timerRef.current = setInterval(() => {
        setState(prev => ({ ...prev, elapsedSeconds: prev.elapsedSeconds + 1 }));
      }, 1000);

      tick();
    } catch (err) {
      setState(prev => ({
        ...prev,
        error: err instanceof Error ? err.message : '未知错误',
      }));
    }
  }, [state.isRecording, tick]);

  // ─── 停止录音 ─────────────────────────────────────────────────────
  const stop = useCallback(async () => {
    if (!state.isRecording) return;

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    await destroyAudioPipeline(audioRefs.current);

    setState(prev => ({ ...prev, isRecording: false }));
    draw(false); // 最后绘制一次，变为灰色
  }, [state.isRecording, draw]);

  // ─── 切换 ─────────────────────────────────────────────────────────
  const toggle = useCallback(async () => {
    if (state.isRecording) await stop();
    else await start();
  }, [state.isRecording, start, stop]);

  // ─── 卸载清理 ─────────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      destroyAudioPipeline(audioRefs.current);
    };
  }, []);

  // ─── 页面后台暂停 ────────────────────────────────────────────────
  useEffect(() => {
    const handleVisibility = () => {
      const refs = audioRefs.current;
      if (document.hidden) {
        if (refs.animFrame !== null) {
          cancelAnimationFrame(refs.animFrame);
          refs.animFrame = null;
        }
      } else if (state.isRecording) {
        tick(); // 重新启动
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

## 8. React 组件：AudioWaveform.tsx

### 8.1 完整组件

```tsx
// components/AudioWaveform.tsx
import React, { useEffect, useRef } from 'react';
import { useAudioWaveform } from '../hooks/useAudioWaveform';
import { setupHiDPICanvas } from '../utils/canvas';
import type { WaveformConfig } from '../types/waveform';

interface AudioWaveformProps {
  /** 组件配置，可覆盖默认值 */
  config?: Partial<WaveformConfig>;
  /** canvas 高度（px），默认 56 */
  height?: number;
  /** 停止录音时的回调，返回录音时长（秒） */
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

  // 通知父组件
  const prevRecordingRef = useRef(false);
  useEffect(() => {
    if (prevRecordingRef.current && !state.isRecording) {
      onStop?.(state.elapsedSeconds);
    }
    prevRecordingRef.current = state.isRecording;
  }, [state.isRecording, state.elapsedSeconds, onStop]);

  // ResizeObserver：宽度变化时重绘
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ro = new ResizeObserver(() => {
      setupHiDPICanvas(canvas);
    });
    ro.observe(canvas);
    return () => ro.disconnect();
  }, [canvasRef]);

  // 格式化时间
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
      {/* 波形 Canvas */}
      <canvas
        ref={canvasRef}
        style={{
          display: 'block',
          width: '100%',
          height,
          borderRadius: 4,
        }}
      />

      {/* 控制栏 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 10 }}>
        {/* 计时 */}
        <span style={{ fontSize: 13, color: '#888', minWidth: 36 }}>
          {formatTime(state.elapsedSeconds)}
        </span>

        {/* 录音按钮 */}
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
          aria-label={state.isRecording ? '停止录音' : '开始录音'}
        >
          {state.isRecording ? (
            // 停止图标（方形）
            <div style={{ width: 10, height: 10, borderRadius: 2, background: '#fff' }} />
          ) : (
            // 录音图标（圆形）
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#888' }} />
          )}
        </button>

        {/* 状态文字 / 错误提示 */}
        <span style={{ fontSize: 12, color: state.error ? '#E24B4A' : '#999' }}>
          {state.error ?? (state.isRecording ? '录音中...' : '点击开始录音')}
        </span>
      </div>
    </div>
  );
};

export default AudioWaveform;
```

### 8.2 使用示例

```tsx
// App.tsx
import React from 'react';
import { AudioWaveform } from './components/AudioWaveform';

export default function App() {
  const handleStop = (seconds: number) => {
    console.log(`录音结束，时长 ${seconds} 秒`);
    // 可在此处理音频数据、上传等
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

### 8.3 同时录音 + 实时获取 Blob（可选）

如果需要在停止时拿到音频文件：

```tsx
// hooks/useAudioRecorder.ts
// 在 useAudioWaveform 基础上叠加 MediaRecorder

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
    recorder.start(100); // 每 100ms 触发一次 ondataavailable
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

## 9. 停止与资源清理

**必须按顺序清理，否则麦克风指示灯不会熄灭或产生内存泄漏：**

```typescript
async function stopRecording(refs: AudioRefs): Promise<void> {
  // 1. 停止动画循环（否则 tick 继续访问已关闭的 analyser）
  if (refs.animFrame !== null) {
    cancelAnimationFrame(refs.animFrame);
    refs.animFrame = null;
  }

  // 2. 停止所有音轨（让浏览器麦克风图标消失）
  refs.stream?.getTracks().forEach(track => track.stop());

  // 3. 关闭 AudioContext（释放系统音频资源）
  if (refs.audioCtx?.state !== 'closed') {
    await refs.audioCtx?.close();
  }

  // 4. 置空引用（帮助 GC）
  refs.stream = null;
  refs.audioCtx = null;
  refs.analyser = null;
  refs.dataArray = null;
}
```

> `stream.getTracks().forEach(t => t.stop())` 是让浏览器麦克风图标消失的关键，不调用则图标一直显示，用户会以为还在录音。

---

## 10. 常见问题与注意事项

### 10.1 Safari 兼容

```typescript
// Safari 需要 webkitAudioContext 前缀
const AudioContextClass =
  window.AudioContext ?? (window as any).webkitAudioContext as typeof AudioContext;

// Safari iOS：页面必须是 HTTPS（localhost 可以）
// Safari：AudioContext 创建后 state 为 suspended，需显式 resume
if (audioCtx.state === 'suspended') {
  await audioCtx.resume(); // 必须在用户手势上下文中
}
```

### 10.2 TypeScript 的 roundRect 类型缺失

部分 TypeScript 版本中 `CanvasRenderingContext2D` 不包含 `roundRect`，需要手动扩展：

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

### 10.3 振幅放大（低音量场景）

```typescript
// 线性放大，简单直接
const amp = Math.min(1, rawAmp * 3);

// 对数放大：低振幅区间拉伸更明显，高振幅不会爆表
const amp = Math.log1p(rawAmp * 9) / Math.log(10);

// 动态增益（根据近期最大值自动调整）
const recentMax = Math.max(...historyRef.current.slice(-30), 0.1);
const amp = Math.min(1, rawAmp / recentMax);
```

### 10.4 canvas 首次渲染宽度为 0

`canvas.offsetWidth` 在首次渲染前可能为 0（SSR 或隐藏容器中），使用 `ResizeObserver` 替代直接读取：

```typescript
useEffect(() => {
  const canvas = canvasRef.current;
  if (!canvas) return;

  const ro = new ResizeObserver(entries => {
    for (const entry of entries) {
      // 使用 contentRect 而非 offsetWidth，更精确
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

### 10.5 页面后台暂停恢复

```typescript
useEffect(() => {
  const handleVisibility = () => {
    if (document.hidden) {
      // 页面进入后台：暂停 rAF（浏览器也会自动降频，但显式取消更安全）
      if (audioRefs.current.animFrame !== null) {
        cancelAnimationFrame(audioRefs.current.animFrame);
        audioRefs.current.animFrame = null;
      }
    } else if (isRecording) {
      // 页面恢复前台：重新启动循环
      tick();
    }
  };

  document.addEventListener('visibilitychange', handleVisibility);
  return () => document.removeEventListener('visibilitychange', handleVisibility);
}, [isRecording, tick]);
```

### 10.6 Next.js / SSR 环境

Web Audio API 只能在浏览器中运行，SSR 时需要 guard：

```typescript
// 在 hook 或工具函数中
const isBrowser = typeof window !== 'undefined';

if (!isBrowser || !window.AudioContext) {
  throw new Error('当前环境不支持 Web Audio API');
}

// 或在 Next.js 组件中
import dynamic from 'next/dynamic';
const AudioWaveform = dynamic(() => import('./AudioWaveform'), { ssr: false });
```

---

## 11. 纯 TypeScript 参考实现

适用于非 React 场景（原生 DOM / Vue / Svelte 等）：

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

  // 事件回调
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

**使用示例（原生 DOM）：**

```typescript
const canvas = document.getElementById('waveform') as HTMLCanvasElement;
const recorder = new WaveformRecorder(canvas, { amplify: 4 });

recorder.onStop = (sec) => console.log(`录音 ${sec}s`);
recorder.onError = (err) => console.error(err.message);

document.getElementById('btn')!.addEventListener('click', () => recorder.toggle());
```

---

## 12. 参数速查表

| 参数 | 推荐值 | 范围 | 说明 |
|------|--------|------|------|
| `fftSize` | `256` | 32 ~ 32768（2的幂） | 时域缓冲区大小，256 已足够波形 UI |
| `smoothingTimeConstant` | `0.4` | 0 ~ 1 | 0 = 不平滑（跳动剧烈），1 = 不响应 |
| `barWidth` | `3` | 2 ~ 6 px | 竖条宽度 |
| `gap` | `2` | 1 ~ 4 px | 竖条间距 |
| `minHeightRatio` | `0.06` | 0.02 ~ 0.15 | 静音时最小竖条高度占比 |
| `amplify` | `3` | 1 ~ 8 | 振幅线性放大系数 |
| `sampleEvery` | `2` | 1 ~ 4 | 每 N 帧采样一次（降采样） |
| `maxBars` | `300` | 显示格数 × 2 | 历史数组上限 |

---

*文档版本 1.0 · Web Audio API + Canvas 2D · TypeScript / React*
