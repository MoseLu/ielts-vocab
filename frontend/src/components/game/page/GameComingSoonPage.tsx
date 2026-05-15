import { useNavigate } from 'react-router-dom'
import { staticAssetUrl } from '../../../lib/staticAssetUrl'

export default function GameComingSoonPage() {
  const navigate = useNavigate()

  return (
    <div className="special-page not-found-page" role="status" aria-label="五维模式敬请期待">
      <div className="special-page-brand">
        <img src={staticAssetUrl('/images/logo.png')} alt="IELTS Vocab" className="special-page-brand-logo" />
        <div className="special-page-brand-text">
          <span className="special-page-brand-title">雅思冲刺</span>
          <span className="special-page-brand-subtitle">IELTS Vocabulary</span>
        </div>
      </div>

      <div className="special-page-card not-found-card">
        <span className="not-found-code">敬请期待</span>
        <h1 className="not-found-title">五维模式正在打磨中</h1>
        <p className="not-found-description">当前请先使用词书学习、到期复习和错词清理完成基础训练。</p>
        <div className="not-found-actions">
          <button type="button" className="not-found-btn not-found-btn--primary" onClick={() => navigate('/plan')}>
            返回学习中心
          </button>
          <button type="button" className="not-found-btn" onClick={() => navigate('/practice')}>
            去基础练习
          </button>
        </div>
      </div>
    </div>
  )
}
