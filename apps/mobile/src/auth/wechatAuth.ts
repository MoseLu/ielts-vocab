import * as WeChat from 'react-native-wechat-lib'

const WECHAT_APP_ID = 'wx30125ac6333945cb'
const WECHAT_SCOPE = 'snsapi_userinfo'
const WECHAT_UNIVERSAL_LINK = process.env.IELTS_MOBILE_WECHAT_UNIVERSAL_LINK || ''

let registerPromise: Promise<boolean> | undefined

type WeChatError = Error & { code?: number }

function createWechatState() {
  return `ielts_mobile_${Date.now().toString(36)}`
}

function describeWechatError(error: unknown): Error {
  const code = (error as WeChatError | undefined)?.code
  if (code === -2) return new Error('已取消微信授权')
  if (code === -4) return new Error('微信授权被拒绝')
  if (code === -5) return new Error('当前微信版本不支持授权登录')
  if (code === -6) {
    return new Error('微信授权被拒绝：请确认开放平台 Android 包名和签名已配置为当前安装包')
  }
  return error instanceof Error ? error : new Error('微信登录失败')
}

export function ensureWechatSdkRegistered(): Promise<boolean> {
  if (!registerPromise) {
    registerPromise = WeChat.registerApp(WECHAT_APP_ID, WECHAT_UNIVERSAL_LINK).catch(error => {
      registerPromise = undefined
      throw error
    })
  }
  return registerPromise
}

export async function requestWechatAuthCode(): Promise<{ code: string; state?: string }> {
  await ensureWechatSdkRegistered()
  const isInstalled = await WeChat.isWXAppInstalled()
  if (!isInstalled) {
    throw new Error('请先安装微信客户端')
  }
  const state = createWechatState()
  const response = await WeChat.sendAuthRequest(WECHAT_SCOPE, state).catch(error => {
    throw describeWechatError(error)
  })
  const code = response?.code?.trim()
  if (!code) {
    throw new Error('微信授权失败，请重试')
  }
  return { code, state: response?.state ?? state }
}
