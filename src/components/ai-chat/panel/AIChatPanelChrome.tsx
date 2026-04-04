import React from 'react'

import { renderJournalMarkdown } from '../../../lib/journalMarkdown'

export const AIRobotSVG = () => (
  <svg viewBox="0 0 1024 1024" width="22" height="22" fill="currentColor" className="ai-robot-icon">
    <path d="M512 32c91.818667 0 166.272 214.912 166.272 480l-0.085333 15.829333C675.285333 785.621333 602.026667 992 512 992c-90.88 0-164.778667-210.645333-166.272-472.064V512C345.728 246.912 420.181333 32 512 32z m0 112.213333l-1.066667 1.706667c-8.618667 14.506667-17.493333 34.133333-25.813333 58.112-27.221333 78.592-43.392 189.013333-43.392 307.968 0 118.912 16.213333 229.376 43.392 307.968 8.277333 23.936 17.194667 43.562667 25.813333 58.069333l1.066667 1.706667 1.066667-1.706667c7.893333-13.312 16.042667-30.890667 23.722666-52.181333l2.090667-5.888c27.221333-78.592 43.392-189.013333 43.392-307.968 0-118.912-16.213333-229.376-43.392-307.968a322.346667 322.346667 0 0 0-25.813333-58.069333L512 144.213333z" />
    <path d="M927.701333 272c45.909333 79.530667-102.997333 251.477333-332.544 384l-13.781333 7.850667C356.693333 790.229333 141.312 829.952 96.298667 752c-45.44-78.72 100.010667-248.021333 325.717333-380.032l6.826667-3.968c229.589333-132.565333 452.949333-175.530667 498.858666-96zM830.506667 328.106667h-2.048a322.346667 322.346667 0 0 0-63.146667 6.613333c-81.706667 15.744-185.472 56.96-288.426667 116.394667-103.04 59.477333-190.592 128.725333-245.034666 191.573333-16.597333 19.2-29.141333 36.693333-37.376 51.413333l-0.981334 1.749334 2.048 0.085333c15.445333 0.213333 34.773333-1.536 57.045334-5.546667l6.144-1.109333c81.664-15.744 185.429333-56.96 288.426666-116.394667 102.997333-59.477333 190.549333-128.725333 244.992-191.573333 16.597333-19.2 29.141333-36.693333 37.376-51.413333l0.981334-1.792z" />
    <path d="M927.701333 752c-45.909333 79.530667-269.226667 36.565333-498.858666-96l-13.653334-7.978667c-221.781333-131.413333-363.861333-298.069333-318.890666-376.021333 45.482667-78.72 264.832-37.418667 491.946666 92.032l6.912 3.968c229.546667 132.522667 378.453333 304.469333 332.544 384z m-97.194666-56.106667l-0.981334-1.792a322.346667 322.346667 0 0 0-37.376-51.370666c-54.442667-62.890667-141.994667-132.138667-244.992-191.573334-102.997333-59.477333-206.762667-100.693333-288.426666-116.437333a322.346667 322.346667 0 0 0-63.189334-6.656l-2.005333 0.042667 0.938667 1.792c7.552 13.482667 18.730667 29.354667 33.28 46.634666l4.096 4.736c54.442667 62.890667 141.994667 132.138667 244.992 191.573334 102.997333 59.477333 206.762667 100.693333 288.426666 116.437333a322.346667 322.346667 0 0 0 63.189334 6.656l2.048-0.04267z" />
  </svg>
)

export const SendIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="22" y1="2" x2="11" y2="13" />
    <polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
)

export const MicIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3Z" />
    <path d="M19 11a7 7 0 0 1-14 0" />
    <path d="M12 18v3" />
    <path d="M8 21h8" />
  </svg>
)

export const StopIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <rect x="6" y="6" width="12" height="12" rx="2.5" />
  </svg>
)

export const CloseIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
)

export const FullscreenIcon = () => (
  <svg width="18" height="18" viewBox="0 0 1024 1024" fill="currentColor" aria-hidden="true">
    <path d="M896 478.72C878.336 478.72 864 464.384 864 446.72L864 200.192 594.624 469.504C582.656 481.472 563.264 481.472 551.296 469.504 539.328 457.536 539.328 438.144 551.296 426.176L818.752 158.72 576 158.72C558.336 158.72 544 144.384 544 126.72 544 109.056 558.336 94.72 576 94.72L893.056 94.72C897.728 94.016 901.568 95.232 906.112 96.768 907.584 97.28 908.992 97.792 910.336 98.496 913.152 99.904 916.48 99.648 918.784 102.016 920.448 103.68 920.064 106.112 921.28 108.032 924.288 112.064 926.208 116.736 927.04 121.856 927.104 122.752 927.552 123.456 927.488 124.288 927.552 125.12 928 125.888 928 126.72L928 446.72C928 464.384 913.664 478.72 896 478.72ZM205.248 862.72 448 862.72C465.664 862.72 480 877.056 480 894.72 480 912.384 465.664 926.72 448 926.72L130.944 926.72C126.272 927.424 122.432 926.208 117.888 924.672 116.416 924.16 115.008 923.648 113.664 922.944 110.848 921.536 107.52 921.792 105.216 919.424 103.552 917.76 103.936 915.328 102.72 913.408 99.712 909.376 97.792 904.704 96.96 899.584 96.896 898.688 96.448 897.984 96.512 897.152 96.448 896.32 96 895.552 96 894.72L96 574.72C96 557.056 110.336 542.72 128 542.72 145.664 542.72 160 557.056 160 574.72L160 821.248 429.376 551.936C441.344 539.968 460.736 539.968 472.704 551.936 484.672 563.904 484.672 583.296 472.704 595.264L205.248 862.72Z" />
  </svg>
)

export const RestoreIcon = () => (
  <svg width="18" height="18" viewBox="0 0 1024 1024" fill="currentColor" aria-hidden="true">
    <path d="M108.8 561.52v101.39h181.56L64 889.26 134.74 960 361.1 733.64V915.2h101.39V561.52H108.8zM889.26 64L662.91 290.36V108.8H561.52v353.68H915.2V361.09H733.64L960 134.74 889.26 64z" />
  </svg>
)

const CopyIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  </svg>
)

const CheckIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    <polyline points="20 6 9 17 4 12" />
  </svg>
)

export function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = React.useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    }
  }

  return (
    <button
      className={`ai-copy-btn ${copied ? 'copied' : ''}`}
      onClick={handleCopy}
      title={copied ? '已复制' : '复制内容'}
      aria-label={copied ? '已复制' : '复制内容'}
      type="button"
    >
      {copied ? <CheckIcon /> : <CopyIcon />}
    </button>
  )
}

export function PlainTextBubble({ content }: { content: string }) {
  return (
    <div className="ai-msg-bubble">
      {content.split('\n').map((line, index) => (
        <p key={`${index}-${line.slice(0, 12)}`}>{line || <br />}</p>
      ))}
    </div>
  )
}

function MarkdownBubble({ content, className = '' }: { content: string; className?: string }) {
  return (
    <div
      className={`ai-msg-bubble ai-markdown-content markdown-content ${className}`.trim()}
      dangerouslySetInnerHTML={{ __html: renderJournalMarkdown(content) }}
    />
  )
}

export function AssistantBubble({ content, isStreaming = false }: { content: string; isStreaming?: boolean }) {
  return (
    <div className={`ai-assistant-bubble ${isStreaming ? 'ai-assistant-bubble--streaming' : ''}`.trim()}>
      <MarkdownBubble
        content={content}
        className={`ai-assistant-bubble__content ${isStreaming ? 'ai-assistant-bubble__content--streaming' : ''}`.trim()}
      />
      <CopyButton text={content} />
    </div>
  )
}
