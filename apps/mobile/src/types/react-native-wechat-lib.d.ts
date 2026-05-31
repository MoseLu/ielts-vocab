declare module 'react-native-wechat-lib' {
  export interface WeChatAuthResponse {
    code?: string
    errCode?: number
    errStr?: string
    state?: string
  }

  export function registerApp(appId: string, universalLink?: string): Promise<boolean>
  export function isWXAppInstalled(): Promise<boolean>
  export function isWXAppSupportApi(): Promise<boolean>
  export function getApiVersion(): Promise<string>
  export function openWXApp(): Promise<boolean>
  export function sendAuthRequest(scope: string | string[], state?: string): Promise<WeChatAuthResponse>
}
