import { AppProviders } from './AppProviders'
import { AppRoutes } from './AppRoutes'
import { usePracticeRuntimeState } from './usePracticeRuntimeState'

export default function AppShell() {
  const { mode, currentDay, handleModeChange, handleDayChange } = usePracticeRuntimeState()

  return (
    <AppProviders>
      <AppRoutes
        mode={mode}
        currentDay={currentDay}
        onModeChange={handleModeChange}
        onDayChange={handleDayChange}
      />
    </AppProviders>
  )
}
