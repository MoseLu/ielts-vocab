# IELTS Vocab Mobile

面向 Android 与 iOS 的 React Native 学习者 App。本 App 并非把 Web UI 塞进 WebView，而是复用后端契约与 `@ielts-vocab/app-core` 中的纯 TypeScript 逻辑；麦克风采集与音频播放由原生模块负责。

## Runtime Contracts

- API base URL 默认为 `https://axiomaticworld.com`.
- `android:dev` 在构建时解析 Mac 当前活跃的 Wi-Fi IP，把 dev 应用的请求指向 `http://<ip>:8000` 与 `http://<ip>:5001`；可通过 `IELTS_MOBILE_DEV_HOST` 显式覆盖。
- 鉴权使用 `/api/auth/mobile/login`、`/api/auth/mobile/refresh` 与 `/api/auth/mobile/logout`。
- 浏览器 Cookie 鉴权仍是 Web 专属契约，App 不复用。
- 语音使用 Socket.IO 命名空间 `/speech`，并配 mobile Bearer token 鉴权。
- 原生音频模块必须为 realtime ASR 输出 `16kHz` 单声道 `PCM16` 帧。

## Commands

```bash
pnpm --dir apps/mobile typecheck
pnpm --dir apps/mobile test
pnpm --dir apps/mobile metro
pnpm --dir apps/mobile android
pnpm --dir apps/mobile android:dev
pnpm --dir apps/mobile android:dev:one-shot
pnpm --dir apps/mobile android:prod
pnpm --dir apps/mobile ios
```

手动调试 Android 时，请把 Metro 留在前台终端，再用第二个终端安装/启动 App：

```bash
# terminal 1: interactive Metro, Fast Refresh, RN DevTools entry
pnpm mobile:metro

# terminal 2: install / launch only, without spawning another Metro process
pnpm mobile:android:dev
```

`android`、`android:dev`、`android:prod` 三个脚本都传了
`--no-packager`，因此它们仍然借助 adb 完成原生 install/launch，但不再
独占 Metro。仅在需要一条命令同时拉起 Metro 和 adb 时，才使用
`android:dev:one-shot` 或 `android:prod:one-shot`。

Android debug 构建已自带 RN Gradle wrapper 与 debug 签名 key，让已连接的 adb 设备在第一次冒烟验证中不依赖全局 Gradle 安装即可运行。签名保管、上线用 launcher 资源以及 CI 设备构建，应在第一次实机冒烟通过之后再补齐。
