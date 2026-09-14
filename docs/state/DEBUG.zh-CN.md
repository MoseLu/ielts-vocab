# DEBUG
最后更新：2026-06-03

> **脱敏说明**：本文是英文源文件的简体中文镜像。
> 源文件中保留了一处历史微信 AppID 字面值（以 wx 开头的 18 位字符串）作为「硬编码凭据示例」出现于
> 第 20 节「微信 AppID 硬编码」问题描述中。该 AppID 属历史凭据示例，请读者切勿直接复用、复制或部署。
> 本镜像为保持与源文件的内联反引号 token 多重集严格一致，**未替换**该字面值。

> `apps/mobile/`（含 `@ielts-vocab/app-core` 共享层与 Android 工程）已知代码质量问题跟踪，按优先级排列。
> 审查基线：React Native 0.81 + React 19.1，模块结构已确认分层清晰、无循环依赖。

## 模块结构（已核对）

- 分层清晰、无循环依赖：`screens` → `components`/`api`/`speech` → `state`/`storage`/`native` → `config`
- `apps/mobile/src/api/mobileApi.ts` 是单例壳，复用 `@ielts-vocab/app-core` 的 `MobileApiClient` / `MobileAuthClient`
- 导航走纯 `ScreenKey` 字符串，避免 `react-navigation` 耦合
- 未发现：循环依赖、`setInterval`/`setTimeout` 未清理、AsyncStorage 句柄泄漏、React `key` 重复、非空断言 `!` 滥用

---

## 🔴 严重（生产前必修）

### 1. Token 用 AsyncStorage 明文存储
- 状态：[待修复]
- 文件：`apps/mobile/src/storage/mobileStorage.ts:1-30`
- 描述：接口名是 `SecureTokenStorage`，底层却直接用 `@react-native-async-storage/async-storage`（明文、未加密、root/越狱设备可读）
- 建议：iOS 改 `react-native-keychain`，Android 改 EncryptedSharedPreferences，或统一 `expo-secure-store`

### 2. Release 复用 debug 签名 + 硬编码密码
- 状态：[待修复]
- 文件：`apps/mobile/android/app/build.gradle:29-44`
- 描述：整个项目只有 `signingConfigs.debug`（`storePassword 'android'`），release 的 `signingConfig signingConfigs.debug` 复用同一份 → 任何人可重签 APK
- 建议：建独立 release keystore，密码走 Gradle properties / 环境变量

### 3. Release 未启用 R8 / Proguard
- 状态：[待修复]
- 文件：`apps/mobile/android/app/build.gradle:9, 45-46` + `apps/mobile/android/app/proguard-rules.pro:1`
- 描述：`enableProguardInReleaseBuilds = false`，proguard 规则文件首行注释明确"暂关"。包体大、无混淆、JS bundle 调用栈暴露
- 建议：开启 `minifyEnabled true`，补 RN / Hermes / Socket.IO / `wechat-lib` 的 keep 规则

### 4. `usesCleartextTraffic` 在 prod 可能仍为 `true`
- 状态：[待修复]
- 文件：`apps/mobile/android/app/build.gradle:26-27, 42-43`
- 描述：`defaultConfig` 里 `manifestPlaceholders` 与 `resValue` 写死 `"true"`，`buildTypes.release` 用变量覆盖。同名 `resValue` 在 Gradle 合并时存在冲突 / 覆盖风险，prod 仍可能为 `true`（明文 HTTP 通行）
- 建议：prod 端只放 `buildTypes`，`defaultConfig` 不设

### 5. 登录页硬编码默认账号密码
- 状态：[待修复]
- 文件：`apps/mobile/src/screens/LoginScreen.tsx:34, 36`
- 描述：`useState('admin')` / `useState('admin123456')`，会随版本发布到商店
- 建议：默认值改空串，或仅 `__DEV__` 时填充

### 6. 录音事件订阅泄漏
- 状态：[待修复]
- 文件：`apps/mobile/src/speech/useMobileSpeechRecognition.ts:116-155`
- 描述：`levelSubscription` / `pcmSubscription` 是 `start()` 内部的局部变量，仅在 `start` 返回的 cleanup（第 152-155 行）里 `.remove()`。hook 的 unmount cleanup（第 65-68 行）只 `stopNativePcmCapture` + `disconnectSocket`，不清理这两个订阅 → 录音中切屏后订阅常驻、内存堆积、重启后重复回调
- 建议：把两个 subscription 提到 `useRef`，在 unmount cleanup 里也调 `.remove()`

---

## 🟡 中等（影响可观测性 / 离线鲁棒性）

### 7. `MobileApiClient.doRefresh` 整段 catch 吞错
- 状态：[待修复]
- 文件：`packages/app-core/src/apiClient.ts`（`doRefresh` 内的 `catch {}`）
- 描述：401 与网络错误都映射为 `'temporarily_unavailable'`，运维侧零可见性
- 建议：保留 reason，至少 `console.warn` 或上报

### 8. `socket.on('connect_error')` 只 dispatch、不关 socket
- 状态：[待修复]
- 文件：`apps/mobile/src/speech/useMobileSpeechRecognition.ts:106-108`
- 描述：socket.io 仍会按 `reconnectionAttempts: 3` 重连；用户已看到错误却仍可能再触发回调，UI 状态不一致
- 建议：dispatch 后 `socket.disconnect()` + 清 ref

### 9. PracticeScreen 多处静默吞错
- 状态：[待修复]
- 文件：`apps/mobile/src/screens/PracticeScreen.tsx`（`submit` 中 `syncWrongWord` / `syncQuickMemory` / `savePracticeProgress` / `logPracticeSession`）
- 描述：均以 `.catch(() => undefined)` 静默吞错，进度同步失败用户毫无感知，离线场景误差累计
- 建议：至少 `console.warn` + 攒到下次重试队列

### 10. PracticeScreen 主 useEffect 跳过 eslint deps
- 状态：[待修复]
- 文件：`apps/mobile/src/screens/PracticeScreen.tsx`
- 描述：使用 `// eslint-disable-next-line react-hooks/exhaustive-deps`，`startPractice` 在 effect 内调用但未列入依赖；options 变更时可能用到过期闭包
- 建议：把 `startPractice` 用 `useCallback` 包装并加入依赖

### 11. Android 14+ 缺前台服务权限
- 状态：[待修复]
- 文件：`apps/mobile/android/app/src/main/AndroidManifest.xml:1-6`
- 描述：仅声明 `INTERNET` / `RECORD_AUDIO` / `MODIFY_AUDIO_SETTINGS` / `POST_NOTIFICATIONS`。Android 14 切后台 mic 录制会被系统中断
- 建议：加 `FOREGROUND_SERVICE` + `FOREGROUND_SERVICE_MICROPHONE`，并配合 `startForeground` 通知

### 12. 微信 Universal Link 缺省为空
- 状态：[待修复]
- 文件：`apps/mobile/src/auth/wechatAuth.ts:5`
- 描述：`process.env.IELTS_MOBILE_WECHAT_UNIVERSAL_LINK || ''` — iOS 注册 SDK 会失败
- 建议：缺失时直接抛错并禁用微信入口按钮

### 13. `logout()` 不通知后端撤销 refresh_token
- 状态：[待修复]
- 文件：`apps/mobile/src/state/SessionContext.tsx:53-61` → `MobileAuthClient.logout`
- 描述：只清本地 token，被盗 refresh_token 在服务端仍可续命
- 建议：先 `POST /api/auth/logout`，失败也清本地

### 14. 原生 PCM 契约 TS 侧无 schema 校验
- 状态：[待修复]
- 文件：`apps/mobile/src/speech/useMobileSpeechRecognition.ts:128-133`
- 描述：`frame.sampleRate || 16000` / `frame.channels || 1` — 仅类型层假设 16kHz 单声道；原生某次升级若输出 22.05kHz / stereo，服务端转写会全错
- 建议：emit 前 zod 校验，不一致上报错误

### 15. HomePlanScreen 重复调 `useHomeState`
- 状态：[待修复]
- 文件：`apps/mobile/src/screens/HomeScreen.tsx`（`HomePlanScreen` 与 `HomeScreen` 各持一份）
- 描述：两次相同的 `/api/ai/home-todos` + `/api/ai/learning-stats` 请求
- 建议：提到 Context 或 SWR 风格缓存

---

## 🟢 建议（可维护性）

### 16. 测试假数据写死在 UI
- 状态：[待修复]
- 文件：`apps/mobile/src/components/StudyRoomScene.tsx:65-68`
- 描述：`sideEntryTestBadges: { 'todo-list': '128', 'wrong-kit': '1288' }` 直接覆盖真实计数
- 建议：替换为 props 或真实数据

### 17. `style?: StyleProp<any>` 过宽 + 任意 `as`
- 状态：[待修复]
- 文件：`apps/mobile/src/components/primitives.tsx:120`、`apps/mobile/src/components/LoginRunnerVideo.tsx:27`（`source={runnerVideo as any}`）
- 建议：改 `StyleProp<ViewStyle | TextStyle>`，或具体类型

### 18. `NativeModules.X as Module | undefined` 仅类型伪装
- 状态：[待修复]
- 文件：`apps/mobile/src/native/NativeAudioBridge.ts:11`、`apps/mobile/src/native/NativeAudioPlayer.ts:9`
- 描述：方法缺失时仍会 runtime 崩
- 建议：封一个 `requireNativeModule` 工具做存在性校验

### 19. `learnerApi.ts` 多处 `as ProgressSnapshot`
- 状态：[待修复]
- 文件：`apps/mobile/src/api/learnerApi.ts:62, 68, 75`
- 描述：已有 zod schema，聚合时绕过
- 建议：一并 `parse`

### 20. 微信 AppID 硬编码
- 状态：[待修复]
- 文件：`apps/mobile/src/auth/wechatAuth.ts:3`
- 描述：`wx30125ac6333945cb` 写死
- 建议：移到 `config.ts` / 环境变量

### 21. `config.ts` 默认 dev host = `127.0.0.1`
- 状态：[待修复]
- 文件：`apps/mobile/src/config.ts:15`
- 描述：Android 模拟器需 `10.0.2.2`
- 建议：按 `Platform.OS` 自动切换

### 22. `App.tsx` 微信注册失败 warn 吞掉
- 状态：[待修复]
- 文件：`apps/mobile/App.tsx:10`
- 描述：与 #12 同根
- 建议：升级到 #12 一并处理

---

## 建议修复顺序

1. **#2 / #3 / #5** — 阻塞上架，必须先做
2. **#1** — 改 SecureStore 抽象即可，影响面中等
3. **#4** — gradle 合并问题，需验证 prod APK 实际值
4. **#6** — 真机录音场景的内存 / 回调 bug
5. **#7 - #15** — 一次性 batch 改完
6. **#16 - #22** — 维护性改进，按节奏穿插

---

## 审查方法

- 用 CodeGraph（`codegraph_explore`）一次性拉取相关源文件完整段落作为主要来源
- 关键问题（#1 / #2 / #4 / #5 / #6 / 涉及 `build.gradle` 与 `wechatAuth.ts`）已逐一 `Read` 核对源文件，未做猜测
- 审查范围：模块结构、错误处理、类型与资源泄漏、安全与可维护性
