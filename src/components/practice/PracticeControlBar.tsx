// ── Practice Control Bar Component ──────────────────────────────────────────────

import React from 'react'
import Popover from '../ui/Popover'
import type { PracticeControlBarProps, PracticeMode, RadioQuickSettings } from './types'

const modeNames: Record<PracticeMode, string> = {
  'smart': '智能模式',
  'listening': '听音选义',
  'meaning': '看词选义',
  'dictation': '听写模式',
  'radio': '随身听',
  'quickmemory': '快速记忆',
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
      trigger={
        <button className="radio-quick-btn">{label}</button>
      }
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
  radioQuickSettings,
  onRadioSettingChange,
}: PracticeControlBarProps) {
  return (
    <div className="practice-ctrl-bar">
      {/* Context label for error mode */}
      {errorMode ? (
        <div className="practice-ctx-label">
          错词复习
          <span className="practice-ctrl-count">{vocabularyLength}词</span>
        </div>
      ) : null}

      <div className="practice-ctrl-right">
        {/* ── Chapter/day selector — Popover with auto-flip ── */}
        {!errorMode && (
          <Popover
            placement="bottom"
            offset={10}
            panelClassName="popover-ctx-panel"
            trigger={
              <button className="practice-ctrl-icon-btn practice-mode-btn" title="切换章节">
                <span className="practice-mode-label">
                  {bookId ? (currentChapterTitle || '选择章节') : `Day ${currentDay}`}
                </span>
                <svg className="practice-ctx-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </button>
            }
          >
            <div className="popover-ctx-scroll">
              {bookId ? (
                bookChapters.length > 0 ? bookChapters.map(ch => (
                  <button
                    key={ch.id}
                    className={`popover-option ${String(chapterId) === String(ch.id) ? 'active' : ''}`}
                    onClick={() => onNavigate(`/practice?book=${bookId}&chapter=${ch.id}`)}
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
            </div>
          </Popover>
        )}

        {/* ── Radio mode quick controls ── */}
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
              label={radioQuickSettings.loopMode ? '连听' : '单次'}
              value={radioQuickSettings.loopMode}
              options={[
                { value: true, label: '连听' },
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

        {/* ── Mode switcher — Popover with auto-flip ── */}
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

        {/* ── Word list toggle ── */}
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

        {/* ── Settings ── */}
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

        {/* ── Home ── */}
        <button
          className="practice-ctrl-icon-btn"
          onClick={() => onNavigate('/')}
          title="主页"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
            <polyline points="9 22 9 12 15 12 15 22" />
          </svg>
        </button>
      </div>
    </div>
  )
}
