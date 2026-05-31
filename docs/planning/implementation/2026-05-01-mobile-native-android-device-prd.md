# IELTS Vocab Mobile Native Android Device PRD

Last updated: 2026-05-01

## Summary

The mobile v1 goal is to turn the existing React/Vite learning product into a native Android and iOS app without wrapping the Web UI in a WebView. The current implementation already has the first mobile slice: `apps/mobile`, `packages/app-core`, mobile token auth, and mobile ASR Socket.IO support. This PRD records the Android-first real-device milestone.

The first device target is `M2012K10C`, Android 13, SDK 33, connected through adb. The delivery target for this milestone is a debug Android build that installs on that device and can complete the learner smoke path: login, basic API reads, practice screen entry, microphone permission, native PCM capture, and speech Socket.IO connection with mobile access-token auth.

## Product Requirements

- Mobile v1 is a learner app only. Admin pages, desktop content editing, and complex management flows are out of scope.
- The app must be native React Native UI, not a WebView shell.
- The first screen after login must expose the learner tabs: plan, books, practice, stats, AI, and profile.
- The Android debug build must install on the connected device using local Gradle wrapper commands.
- The test account for the first smoke pass is `admin / admin123456`.
- The app must be able to target both local split runtime and production gateway. Production defaults to `https://axiomaticworld.com`; dev targets the Mac's Wi-Fi IP on ports `8000` and `5001`, with `adb reverse` reserved only as a temporary fallback for isolated debugging.
- Speech capture must request microphone permission, emit `16kHz` mono `PCM16` frames, show recording level, and forward frames to the existing ASR Socket.IO contract.
- API and speech errors must be visible in the UI without native crashes, white screens, or stuck loading states.

## Native And API Contracts

- Web cookie auth remains unchanged for the browser app.
- Mobile auth uses:
  - `POST /api/auth/mobile/login`
  - `POST /api/auth/mobile/refresh`
  - `POST /api/auth/mobile/logout`
- Mobile auth responses contain `access_token`, `refresh_token`, `access_expires_in`, and `user`.
- Mobile API requests send `Authorization: Bearer <access_token>`.
- Refresh token storage uses the platform secure store; non-sensitive cache uses the mobile storage adapter.
- Speech uses Socket.IO namespace `/speech`, path `/socket.io`, and mobile token auth from `auth.token`.
- Mobile audio frames use `base64Pcm`, `sampleRate=16000`, `channels=1`, and `encoding=pcm16`.

## Android Implementation Plan

- Complete the Android React Native project from the RN 0.85 template: Gradle wrapper, RN settings plugin, root/app Gradle files, debug signing, ProGuard placeholder, and standard activity/application entrypoints.
- Keep `applicationId` and namespace as `com.axiomaticworld.ieltsvocab`.
- Keep `minSdkVersion=26`, `compileSdkVersion=35`, and `targetSdkVersion=35` for this milestone.
- Keep required permissions: `INTERNET`, `RECORD_AUDIO`, and `MODIFY_AUDIO_SETTINGS`.
- Allow cleartext only for debug/dev so local split runtime can be tested from a physical device.
- Keep Android orientation portrait for the first learner smoke flow.
- Add script aliases for Android dev/prod runs without changing the Web app.

## Real-Device Smoke Plan

1. Confirm device: `adb devices -l`.
2. For local API smoke, use the Mac Wi-Fi IP for `:8000` and `:5001`; if Wi-Fi routing is unavailable, use `adb reverse` only as a temporary fallback.
3. Build/install debug APK through `apps/mobile/android/gradlew :app:installDebug`.
4. Launch `com.axiomaticworld.ieltsvocab/.MainActivity`.
5. Verify no native crash through `adb logcat -b crash`.
6. Login with `admin / admin123456`.
7. Open plan/books/stats and confirm at least one API-backed screen returns data or an explicit service error.
8. Open practice, request microphone permission, start recording, and confirm the level changes from native audio input.
9. Confirm speech Socket.IO uses mobile Bearer auth and either returns ASR events or a clear service error.
10. Capture adb logs and note blockers in this PRD or a follow-up smoke report.

## Test Plan

- `pnpm --dir packages/app-core typecheck && pnpm --dir packages/app-core test`
- `pnpm --dir apps/mobile typecheck && pnpm --dir apps/mobile test`
- `pnpm --dir frontend verify:repo-guards`
- `pnpm check:file-lines`
- `pytest backend/tests/test_auth_core.py::TestMobileAuth backend/tests/test_speech_socketio.py backend/tests/test_source_text_integrity.py -q`
- `apps/mobile/android/gradlew :app:assembleDebug`
- `apps/mobile/android/gradlew :app:installDebug`

## 2026-05-01 Execution Notes

- Device confirmed through adb: `m7lru45xu4mjcq7x`, model `M2012K10C`, Android `13`, SDK `33`.
- Completed Android project scaffold work: RN Gradle wrapper, RN settings plugin, root/app Gradle files, debug signing, release placeholder, standard RN activity/application entrypoints, manifest permissions, and package name.
- Passed: `pnpm --dir packages/app-core typecheck && pnpm --dir packages/app-core test`.
- Passed: `pnpm --dir apps/mobile typecheck && pnpm --dir apps/mobile test`.
- Passed: `pnpm --dir frontend verify:repo-guards`.
- Passed: `pnpm check:file-lines`.
- Passed: `pytest backend/tests/test_auth_core.py::TestMobileAuth backend/tests/test_speech_socketio.py backend/tests/test_source_text_integrity.py -q`.
- Blocked before APK build: this Mac currently exposes only `/usr/bin/java` and `/usr/bin/javac` stubs, both returning `Unable to locate a Java Runtime`; `ANDROID_HOME` and `ANDROID_SDK_ROOT` are also unset.
- Attempted local user-space JDK install from Oracle/Temurin sources, but network throughput stayed around `100KB/s` and was not practical within this run.
- Next unblock step: install JDK 21 plus Android SDK command-line tools locally, then rerun `apps/mobile/android/gradlew -p apps/mobile/android :app:assembleDebug --console=plain` and continue with `:app:installDebug`.

## 2026-05-02 Execution Notes

- Installed local user-space JDKs: JDK 21 for SDK tooling bootstrap and JDK 17 for the Android Gradle/RN build.
- Installed Android SDK command-line tools, platform-tools, `build-tools;35.0.0`, and `platforms;android-35` under `~/.local/opt/android-sdk`.
- Cached Gradle `9.3.1` wrapper under `~/.gradle/wrapper/dists/gradle-9.3.1-bin` after verifying the wrapper zip checksum.
- Added explicit mobile dev dependency `@react-native/gradle-plugin@0.85.2` so the local `apps/mobile/node_modules/@react-native/gradle-plugin` includeBuild path resolves.
- Fixed the RN 0.85 Android application entrypoint to use `SoLoader.init(..., OpenSourceMergedSoMapping)` and `DefaultNewArchitectureEntryPoint.load()`.
- Added Android runtime microphone permission handling before starting native recording.
- Extended native and JS audio frame payloads to include `channels=1` and `encoding=pcm16`, matching the mobile speech frame contract.
- Re-ran and passed: `pnpm --dir apps/mobile typecheck`, `pnpm --dir apps/mobile test`, `pnpm --dir packages/app-core typecheck`, and `pnpm --dir packages/app-core test`.
- Re-ran and passed earlier in this device-prep pass: `pnpm --dir frontend verify:repo-guards`, `pnpm check:file-lines`, and `PATH=/Users/mose/.local/share/micromamba/envs/ielts-mac-runtime/bin:$PATH pytest backend/tests/test_auth_core.py::TestMobileAuth backend/tests/test_speech_socketio.py backend/tests/test_source_text_integrity.py -q`.
- Current Android build blocker moved from missing JDK/SDK to NDK installation: RN 0.85 enables the new architecture by default and AGP requires `ndk;27.1.12297006`.
- `adb devices -l` currently shows no attached device, so install and real-device smoke are pending until `M2012K10C` is reconnected or re-authorized.
- Next unblock step: finish installing `ndk;27.1.12297006`, rerun `apps/mobile/android/gradlew -p apps/mobile/android :app:assembleDebug --console=plain --no-daemon`, then reconnect the device and run `:app:installDebug`.

## Assumptions

- Android real-device validation comes before iOS TestFlight work.
- iOS native project completion remains a separate follow-up milestone.
- The first Android smoke can use production API if local split runtime is not running, but destructive or admin actions are not part of this pass.
- Existing unrelated Web wrong-word page changes are not part of this milestone and must not be reverted or mixed into mobile edits.
