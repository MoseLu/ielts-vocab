const { execSync } = require('node:child_process')

function resolveWifiHost() {
  const explicitHost = process.env.IELTS_MOBILE_DEV_HOST?.trim()
  if (explicitHost) return explicitHost

  for (const iface of ['en0', 'en1', 'en2']) {
    try {
      const host = execSync(`ipconfig getifaddr ${iface}`, {
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'ignore'],
      }).trim()
      if (host) return host
    } catch {
      // Try the next interface.
    }
  }

  return '127.0.0.1'
}

if (process.env.IELTS_MOBILE_ENV === 'dev') {
  const host = resolveWifiHost()
  if (!process.env.IELTS_MOBILE_DEV_HOST) process.env.IELTS_MOBILE_DEV_HOST = host
  if (!process.env.IELTS_MOBILE_API_BASE_URL) process.env.IELTS_MOBILE_API_BASE_URL = `http://${host}:8000`
  if (!process.env.IELTS_MOBILE_SPEECH_BASE_URL) process.env.IELTS_MOBILE_SPEECH_BASE_URL = `http://${host}:5001`
}

module.exports = {
  plugins: [
    [
      'transform-inline-environment-variables',
      {
        include: [
          'IELTS_MOBILE_ENV',
          'IELTS_MOBILE_DEV_HOST',
          'IELTS_MOBILE_API_BASE_URL',
          'IELTS_MOBILE_SPEECH_BASE_URL',
          'IELTS_MOBILE_WECHAT_UNIVERSAL_LINK',
        ],
      },
    ],
    '@babel/plugin-transform-export-namespace-from',
  ],
  presets: ['module:@react-native/babel-preset'],
}
