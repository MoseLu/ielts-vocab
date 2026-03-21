// ── Practice Control Bar Component ──────────────────────────────────────────────

import React from 'react'
import Popover from '../ui/Popover'
import type { PracticeControlBarProps, PracticeMode } from './types'

const modeNames: Record<PracticeMode, string> = {
  'smart': '智能模式',
  'listening': '听音选义',
  'meaning': '看词选义',
  'dictation': '听写模式',
  'radio': '随身听'
}

const modeList: PracticeMode[] = ['smart', 'listening', 'meaning', 'dictation', 'radio']

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
              <button className="practice-ctx-btn">
                <span className="practice-ctx-text">
                  {bookId ? (currentChapterTitle || '选择章节') : `Day ${currentDay}`}
                </span>
                <span className="practice-ctrl-count">{vocabularyLength}词</span>
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
                    <span className="ctx-opt-label">{ch.title}</span>
                    <span className="ctx-opt-count">{ch.word_count}词</span>
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
