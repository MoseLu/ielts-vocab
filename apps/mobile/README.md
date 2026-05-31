# IELTS Vocab Mobile

React Native learner app for Android and iOS. This app does not embed the Web UI in a WebView. It reuses backend contracts and pure TypeScript logic from `@ielts-vocab/app-core`, while microphone capture and playback are owned by native modules.

## Runtime Contracts

- API base URL defaults to `https://axiomaticworld.com`.
- `android:dev` resolves the Mac's active Wi-Fi IP at build time and points the dev app to `http://<ip>:8000` plus `http://<ip>:5001`; set `IELTS_MOBILE_DEV_HOST` to override it.
- Authentication uses `/api/auth/mobile/login`, `/api/auth/mobile/refresh`, and `/api/auth/mobile/logout`.
- Browser cookie auth remains a Web-only contract.
- Speech uses Socket.IO namespace `/speech` plus mobile Bearer token auth.
- Native audio modules must emit `16kHz` mono `PCM16` frames for realtime ASR.

## Commands

```bash
pnpm --dir apps/mobile typecheck
pnpm --dir apps/mobile test
pnpm --dir apps/mobile android
pnpm --dir apps/mobile android:dev
pnpm --dir apps/mobile android:prod
pnpm --dir apps/mobile ios
```

The Android debug build includes the RN Gradle wrapper and debug signing key so a connected adb device can run the first smoke pass without relying on a global Gradle install. Store signing, polished launcher assets, and CI device builds should be added after the first real-device smoke pass.
