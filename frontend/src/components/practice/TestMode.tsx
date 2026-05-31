import QuickMemoryMode from './QuickMemoryMode'
import type { QuickMemoryModeProps } from './types'

export default function TestMode(props: QuickMemoryModeProps) {
  return <QuickMemoryMode {...props} modeVariant="test" />
}
