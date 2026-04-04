import { useMemo } from 'react'
import { Link } from 'react-router-dom'

const termsSections = [
  {
    id: 'overview',
    title: '1. 协议适用范围',
    paragraphs: [
      '本协议适用于“雅思冲刺 IELTS Vocabulary”网站、前端应用、后端服务及其附属功能，包括词书学习、章节训练、听音训练、听写训练、随身听、学习统计、学习日志、AI 问答与账户服务。',
      '当您访问、注册、登录、使用本项目提供的任何功能时，即表示您已经阅读、理解并同意接受本协议全部内容。若您不同意本协议任一条款，请停止注册或使用本服务。 ',
    ],
  },
  {
    id: 'account',
    title: '2. 账户注册与使用',
    paragraphs: [
      '您在注册时应提供真实、准确、完整且可更新的账户信息，并妥善保管您的登录凭证。因您保管不当导致的账户被盗用、数据丢失或异常操作风险，由您自行承担相应后果。',
      '您不得以任何方式冒用他人身份、批量注册、恶意试探接口、利用自动化脚本破坏学习数据，或将本项目用于任何违法违规用途。',
    ],
    bullets: [
      '您应对账户项下发生的全部操作负责。',
      '如发现账户存在异常登录、数据异常或安全风险，应及时联系平台处理。',
      '平台有权对涉嫌滥用、攻击、刷量或异常调用的账户采取限制、暂停或注销措施。',
    ],
  },
  {
    id: 'service',
    title: '3. 服务内容与可用性',
    paragraphs: [
      '本项目定位为雅思词汇学习工具，当前提供的服务包括词书浏览、章节练习、训练模式切换、语音播放、学习统计、错词回顾、学习日志和 AI 辅助答疑等。',
      '我们会持续对功能、接口、题库、音频、推荐逻辑和页面体验进行调整、升级、修复或下线。为保证系统安全与稳定，平台有权在必要时进行维护、中断、限流或重构。',
    ],
    bullets: [
      '平台不承诺所有功能在任意时间、任意设备、任意网络环境下持续可用。',
      '语音识别、语音播放、AI 问答等功能可能受第三方能力、网络环境和浏览器兼容性影响。',
      '对于测试期、灰度期或内部能力，平台有权调整使用范围和可用策略。',
    ],
  },
  {
    id: 'behavior',
    title: '4. 用户行为规范',
    paragraphs: [
      '您在使用本项目时，应遵守法律法规、公序良俗以及互联网使用规范，不得实施影响平台稳定、侵害他人权益或绕过平台限制的行为。',
    ],
    bullets: [
      '不得反向工程、抓取、镜像、批量导出题库、音频、页面资源或接口数据。',
      '不得传播违法、侵权、侮辱、骚扰、虚假或其他不适当内容。',
      '不得利用系统漏洞、未公开接口、脚本程序或自动化方式干扰正常学习秩序。',
      '不得将 AI 问答、日志总结等功能用于生成违法违规内容。',
    ],
  },
  {
    id: 'data',
    title: '5. 学习数据与内容说明',
    paragraphs: [
      '为提供学习进度同步、训练统计、错词回顾、日志汇总和个性化建议，本项目会处理与您使用行为相关的数据，包括账户信息、词书进度、学习时长、训练记录、答题结果、AI 问答内容等。',
      '平台会尽力保证数据记录的准确性，但学习统计、音频、识别结果、AI 总结和推荐建议仍可能存在延迟、误差或不完整情况，相关内容仅作为学习辅助，不构成专业考试、教学或升学保证。',
    ],
  },
  {
    id: 'ai',
    title: '6. AI 与语音能力说明',
    paragraphs: [
      '本项目部分功能依赖 AI 服务、语音合成、语音识别或其他第三方技术能力。相关输出可能基于模型推断生成，不保证绝对准确、完整、及时或适用于所有学习场景。',
      '您应结合自身判断使用 AI 回答、每日总结、听写结果和语音反馈，不应将其视为唯一依据。对于因第三方服务异常、网络波动、浏览器限制造成的功能不可用，平台将在合理范围内持续优化，但不承担超出法定范围的责任。',
    ],
  },
  {
    id: 'ip',
    title: '7. 知识产权',
    paragraphs: [
      '本项目中的页面设计、代码实现、接口结构、训练逻辑、统计逻辑、视觉样式及平台自有内容，除依法属于用户或第三方的部分外，相关知识产权归平台或权利人所有。',
      '未经明确许可，您不得复制、转载、传播、改编、公开展示、商业化使用或以其他方式利用本项目资源。 ',
    ],
  },
  {
    id: 'liability',
    title: '8. 责任限制',
    paragraphs: [
      '在法律允许的范围内，平台对因系统维护、网络故障、第三方能力异常、设备兼容性、数据同步延迟、用户误操作、账号泄露、不可抗力等原因造成的服务中断、学习记录异常或使用损失，不承担超出法定范围的赔偿责任。',
      '如果您违反本协议，给平台或第三方造成损失，您应依法承担相应责任。',
    ],
  },
  {
    id: 'change',
    title: '9. 协议更新与生效',
    paragraphs: [
      '平台有权根据业务调整、法律法规变化或产品升级需要对本协议进行修订。更新后的协议将在相关页面公布，并自公布之日起生效。',
      '如您在协议更新后继续使用本服务，视为您接受更新后的协议内容；如您不同意更新内容，应立即停止使用相关服务。',
    ],
  },
]

const docNavSections = [
  {
    title: '协议与条款',
    items: [
      { label: '用户服务协议', href: '/terms', active: true },
    ],
  },
]

export default function TermsPage() {
  const updatedAt = useMemo(() => '2026-03-30', [])

  return (
    <div className="special-page terms-page">
      <article className="terms-shell" aria-labelledby="terms-title">
        <div className="terms-layout">
          <aside className="terms-sidebar" aria-label="文档列表">
            {docNavSections.map((section) => (
              <section key={section.title} className="terms-sidebar-group">
                <h2 className="terms-sidebar-title">{section.title}</h2>
                <ul className="terms-sidebar-list">
                  {section.items.map((item) => (
                    <li key={item.label}>
                      <Link
                        to={item.href}
                        className={`terms-sidebar-link ${item.active ? 'is-active' : ''}`}
                        aria-current={item.active ? 'page' : undefined}
                      >
                        {item.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </aside>

          <div className="terms-content-shell">
            <div className="terms-content markdown-body">
              <header className="terms-header">
                <h1 id="terms-title" className="terms-title">用户服务协议</h1>
                <p className="terms-summary">
                  本协议用于说明您在使用雅思冲刺 IELTS Vocabulary 学习平台时的账户规则、功能边界、数据处理原则与双方责任。
                  请在注册前完整阅读，并在确认同意后继续使用本项目提供的学习服务。
                </p>
              </header>

              {termsSections.map((section) => (
                <section key={section.id} id={section.id} className="terms-section">
                  <h2>{section.title}</h2>
                  {section.paragraphs.map((paragraph) => (
                    <p key={paragraph}>{paragraph}</p>
                  ))}
                  {section.bullets && (
                    <ul>
                      {section.bullets.map((bullet) => (
                        <li key={bullet}>{bullet}</li>
                      ))}
                    </ul>
                  )}
                </section>
              ))}

              <section id="contact" className="terms-section">
                <h2>10. 联系与反馈</h2>
                <p>
                  如果您对本协议、账户安全、数据处理、功能可用性或内容纠错有疑问，可通过平台后续提供的反馈入口与我们联系。
                  对于协议相关的解释、修订与执行，以本页面最新公示内容为准。
                </p>

                <table>
                  <thead>
                    <tr>
                      <th>事项</th>
                      <th>说明</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>适用对象</td>
                      <td>所有访问、注册、登录或使用本项目服务的用户</td>
                    </tr>
                    <tr>
                      <td>生效方式</td>
                      <td>注册、登录或继续使用服务即视为同意本协议</td>
                    </tr>
                    <tr>
                      <td>版本更新</td>
                      <td>平台可根据功能、法律或运营需要进行修订并在页面公示</td>
                    </tr>
                  </tbody>
                </table>

                <blockquote>
                  请仅在您完全理解并接受本协议的前提下继续注册或使用服务。
                </blockquote>
              </section>
            </div>
          </div>

          <nav className="terms-outline" aria-label="本页目录">
            <h2 className="terms-outline-title">本页</h2>
            <ol className="terms-outline-list">
              {termsSections.map((section) => (
                <li key={section.id}>
                  <a href={`#${section.id}`} className="terms-outline-link">{section.title}</a>
                </li>
              ))}
              <li>
                <a href="#contact" className="terms-outline-link">10. 联系与反馈</a>
              </li>
            </ol>

            <div className="terms-outline-info" aria-label="文档信息">
              <span className="terms-eyebrow">User Agreement</span>
              <span className="terms-updated">最后更新：{updatedAt}</span>
            </div>
          </nav>
        </div>
      </article>
    </div>
  )
}
