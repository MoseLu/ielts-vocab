import { useNavigate } from 'react-router-dom'

export default function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <div className="special-page not-found-page">
      <div className="special-page-brand">
        <img src="/images/logo.png" alt="IELTS Vocab" className="special-page-brand-logo" />
        <div className="special-page-brand-text">
          <span className="special-page-brand-title">雅思冲刺</span>
          <span className="special-page-brand-subtitle">IELTS Vocabulary</span>
        </div>
      </div>

      <div className="special-page-card not-found-card">
        <span className="not-found-code">404</span>
        <h1 className="not-found-title">页面不存在</h1>
        <p className="not-found-description">你访问的页面不存在，或者链接已经失效。</p>
        <div className="not-found-actions">
          <button type="button" className="not-found-btn not-found-btn--primary" onClick={() => navigate('/plan')}>
            返回首页
          </button>
          <button type="button" className="not-found-btn" onClick={() => navigate('/login')}>
            去登录
          </button>
        </div>
      </div>
    </div>
  )
}
