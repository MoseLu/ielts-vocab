import React from 'react'
import Popover from '../ui/Popover'
import { Scrollbar } from '../ui/Scrollbar'
import type { PracticeControlBarProps, PracticeMode } from './types'

const modeNames: Record<PracticeMode, string> = {
  smart: '智能模式',
  listening: '听音选义',
  meaning: '看词选义',
  dictation: '听写模式',
  radio: '随身听',
  quickmemory: '快速记忆',
}

const modeList: PracticeMode[] = ['smart', 'quickmemory', 'listening', 'meaning', 'dictation', 'radio']

const SPEED_OPTIONS = ['0.6', '0.8', '1.0', '1.2'] as const
const COUNT_OPTIONS = ['1', '2', '3'] as const
const INTERVAL_OPTIONS = ['1', '2', '3', '5'] as const

function RadioQuickControl<T extends string | boolean>({
  label,
  options,
  value,
  onChange,
}: {
  label: string
  options: { value: T; label: string }[]
  value: T
  onChange: (v: T) => void
}) {
  return (
    <Popover
      placement="bottom"
      offset={10}
      panelClassName="popover-radio-panel"
      trigger={<button className="radio-quick-btn">{label}</button>}
    >
      {options.map(opt => (
        <button
          key={String(opt.value)}
          className={`popover-option ${value === opt.value ? 'active' : ''}`}
          onClick={() => onChange(opt.value)}
        >
          <span className={`ctx-radio ${value === opt.value ? 'checked' : ''}`} />
          {opt.label}
        </button>
      ))}
    </Popover>
  )
}

export default function PracticeControlBar({
  mode,
  currentDay,
  bookId,
  chapterId,
  errorMode,
  vocabularyLength,
  currentChapterTitle,
  bookChapters,
  showWordList,
  showPracticeSettings,
  onWordListToggle,
  onSettingsToggle,
  onModeChange,
  onDayChange,
  onNavigate,
  buildChapterPath,
  onPause,
  radioQuickSettings,
  onRadioSettingChange,
}: PracticeControlBarProps) {
  const hasStaticContextLabel = !bookId && currentDay == null && Boolean(currentChapterTitle)
  const contextLabel = bookId
    ? (currentChapterTitle || '选择章节')
    : hasStaticContextLabel
      ? currentChapterTitle
      : currentDay != null
        ? `Day ${currentDay}`
        : '选择单元'

  return (
    <div className="practice-ctrl-bar">
      <button
        type="button"
        className="practice-ctrl-brand"
        onClick={() => onNavigate('/plan')}
        title="返回学习中心"
      >
        <img
          src="/images/logo.png"
          alt="Logo"
          className="practice-ctrl-brand-logo"
          onError={(e) => { e.currentTarget.style.display = 'none' }}
        />
        <span className="practice-ctrl-brand-text">雅思冲刺</span>
      </button>

      <div className="practice-ctrl-right">
        {errorMode ? (
          <div className="practice-ctx-label">
            错词复习
            <span className="practice-ctrl-count">{vocabularyLength}词</span>
          </div>
        ) : null}

        {!errorMode && (
          hasStaticContextLabel ? (
            <button
              type="button"
              className="practice-ctrl-icon-btn practice-mode-btn"
              title={contextLabel}
              disabled
            >
              <span className="practice-mode-label">{contextLabel}</span>
            </button>
          ) : (
            <Popover
              placement="bottom"
              offset={10}
              panelClassName="popover-ctx-panel"
              trigger={
                <button className="practice-ctrl-icon-btn practice-mode-btn" title="切换章节">
                  <span className="practice-mode-label">{contextLabel}</span>
                  <svg className="practice-ctx-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </button>
              }
            >
              <Scrollbar className="popover-ctx-scroll" maxHeight={320}>
                {bookId ? (
                  bookChapters.length > 0 ? bookChapters.map(ch => (
                    <button
                      key={ch.id}
                      className={`popover-option ${String(chapterId) === String(ch.id) ? 'active' : ''}`}
                      onClick={() => onNavigate(
                        buildChapterPath?.(ch.id) ?? `/practice?book=${bookId}&chapter=${ch.id}`,
                      )}
                    >
                      <span className={`ctx-radio ${String(chapterId) === String(ch.id) ? 'checked' : ''}`} />
                      {ch.title}
                    </button>
                  )) : (
                    <div className="popover-loading">加载章节...</div>
                  )
                ) : (
                  Array.from({ length: 30 }, (_, i) => (
                    <button
                      key={i + 1}
                      className={`popover-option ${currentDay === i + 1 ? 'active' : ''}`}
                      onClick={() => onDayChange(i + 1)}
                    >
                      <span className={`ctx-radio ${currentDay === i + 1 ? 'checked' : ''}`} />
                      <span className="ctx-opt-label">Day {i + 1}</span>
                    </button>
                  ))
                )}
              </Scrollbar>
            </Popover>
          )
        )}

        {mode === 'radio' && radioQuickSettings && onRadioSettingChange && (
          <>
            <RadioQuickControl<string>
              label={`x${radioQuickSettings.playbackSpeed}倍`}
              value={radioQuickSettings.playbackSpeed}
              options={SPEED_OPTIONS.map(v => ({ value: v, label: `x${v}倍` }))}
              onChange={v => onRadioSettingChange('playbackSpeed', v)}
            />
            <RadioQuickControl<string>
              label={`${radioQuickSettings.playbackCount}遍`}
              value={radioQuickSettings.playbackCount}
              options={COUNT_OPTIONS.map(v => ({ value: v, label: `${v}遍` }))}
              onChange={v => onRadioSettingChange('playbackCount', v)}
            />
            <RadioQuickControl<boolean>
              label={radioQuickSettings.loopMode ? '循环' : '单次'}
              value={radioQuickSettings.loopMode}
              options={[
                { value: true, label: '循环' },
                { value: false, label: '单次' },
              ]}
              onChange={v => onRadioSettingChange('loopMode', v)}
            />
            <RadioQuickControl<string>
              label={`${radioQuickSettings.interval}秒`}
              value={radioQuickSettings.interval}
              options={INTERVAL_OPTIONS.map(v => ({ value: v, label: `${v}秒` }))}
              onChange={v => onRadioSettingChange('interval', v)}
            />
          </>
        )}

        <Popover
          placement="bottom-end"
          offset={10}
          panelClassName="popover-mode-panel"
          trigger={
            <button className="practice-ctrl-icon-btn practice-mode-btn" title="切换模式">
              <span className="practice-mode-label">{modeNames[mode as PracticeMode] || mode}</span>
              <svg className="practice-ctx-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </button>
          }
        >
          {modeList.map(m => (
            <button
              key={m}
              className={`popover-option ${mode === m ? 'active' : ''}`}
              onClick={() => onModeChange(m)}
            >
              <span className={`ctx-radio ${mode === m ? 'checked' : ''}`} />
              {modeNames[m]}
            </button>
          ))}
        </Popover>

        <button
          className={`practice-ctrl-icon-btn ${showWordList ? 'active' : ''}`}
          onClick={onWordListToggle}
          title="单词列表"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="3" y="4" width="18" height="4" rx="1" />
            <rect x="3" y="10" width="18" height="4" rx="1" />
            <rect x="3" y="16" width="12" height="4" rx="1" />
          </svg>
        </button>

        <button
          className={`practice-ctrl-icon-btn ${showPracticeSettings ? 'active' : ''}`}
          onClick={onSettingsToggle}
          title="设置"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
        </button>

        <button
          className="practice-ctrl-icon-btn"
          onClick={() => onPause?.()}
          title="暂停"
        >
          <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
            <rect x="5" y="3" width="4" height="18" rx="1.5" />
            <rect x="15" y="3" width="4" height="18" rx="1.5" />
          </svg>
        </button>
      </div>
    </div>
  )
}
