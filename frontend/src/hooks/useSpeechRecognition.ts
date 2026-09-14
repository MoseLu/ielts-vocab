// Cross-feature hook barrel for the legacy single-import surface.
//
// This file exists to keep the old `from '@/hooks/useSpeechRecognition'`
// import path working for callers and tests that predate the R1
// consolidation. Real implementation lives in `features/speech/hooks/`.
export { useSpeechRecognition } from '../features/speech/hooks/useSpeechRecognition'
export type {
  SpeechRecognitionOptions,
  UseSpeechRecognitionReturn,
} from '../features/speech/hooks/speechRecognitionTypes'
