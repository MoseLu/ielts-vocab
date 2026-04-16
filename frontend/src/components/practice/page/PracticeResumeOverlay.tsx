import { Button, Modal } from '../../ui'

interface PracticeResumeOverlayProps {
  isOpen: boolean
  message: string
  continueLabel: string
  onContinue: () => void
  onRestart: () => void
}

export function PracticeResumeOverlay({
  isOpen,
  message,
  continueLabel,
  onContinue,
  onRestart,
}: PracticeResumeOverlayProps) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onContinue}
      size="md"
      closeOnOverlay={false}
      showCloseButton={false}
    >
      <div className="practice-resume-overlay">
        <button
          type="button"
          className="practice-resume-overlay__close"
          aria-label="关闭"
          onClick={onContinue}
        >
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <div className="practice-resume-overlay__message-row">
          <div className="practice-resume-overlay__status" aria-hidden="true">
            <svg fill="none" viewBox="0 0 20 20">
              <circle cx="10" cy="10" r="7" stroke="currentColor" strokeWidth="1.6" />
              <path d="M10 9.2v3.1" stroke="currentColor" strokeLinecap="round" strokeWidth="1.6" />
              <circle cx="10" cy="6.4" r="0.9" fill="currentColor" />
            </svg>
          </div>
          <p className="practice-resume-overlay__message">{message}</p>
        </div>
        <div className="practice-resume-overlay__actions">
          <Button
            variant="secondary"
            size="sm"
            className="practice-resume-overlay__button"
            onClick={() => void onRestart()}
          >
            重新开始
          </Button>
          <Button
            size="sm"
            className="practice-resume-overlay__button practice-resume-overlay__button--primary"
            onClick={onContinue}
          >
            {continueLabel}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
