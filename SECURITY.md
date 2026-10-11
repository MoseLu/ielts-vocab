# Security Policy

## Reporting

Report security-sensitive issues through the private operator channel for this workspace. Do not open public issues containing credentials, API tokens, private keys, server addresses with secrets, or customer data.

For sensitive disclosure, contact the repository owner via the private channel documented in this workspace's governance hub.

## Supported Versions

| Version | Supported |
| ------- | --------- |
| latest `main` branch  | yes |
| latest tagged release | yes |
| older releases        | no  |

Security fixes are backported only to the current `main` branch and the most recent tagged release. Older releases are not patched unless the owner explicitly extends coverage.

## Disclosure Timeline

- **T+0** — Report acknowledged in the private channel within 2 business days.
- **T+5** — Triage completed; severity assigned (Critical / High / Medium / Low) and reproduced.
- **T+30** — Patch released on `main` and the latest tagged release, unless actively exploited issues trigger an emergency patch within 72 hours of triage.
- **T+90** — Public disclosure after the patch is widely available. Coordinated disclosure may extend this window if a downstream consumer requires more time.

## Prohibited Content in Commits / Issues / Logs

Never include in commits, issues, or logs:

- API tokens / API 令牌
- Private keys / 私钥
- Database connection strings with credentials / 带凭证的数据库连接字符串
- Environment variables containing secrets / 包含密钥的环境变量
- Server addresses with embedded secrets / 嵌入密钥的服务器地址
- Customer PII or sensitive data / 客户个人信息或敏感数据

Credential material must be referenced through secret refs only. Known local credential files, including Cloudflare credentials, must not be read by CI or printed in logs.

## Contact

如有关安全问题，请通过工作区的私有操作员渠道联系。
For security concerns, contact the workspace owner through the private channel.
