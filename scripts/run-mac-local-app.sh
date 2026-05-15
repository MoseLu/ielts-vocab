#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "${script_dir}/.." && pwd)"
mode="${1:-dev}"
runtime_prefix="${IELTS_MAC_RUNTIME_PREFIX:-$HOME/.local/share/micromamba/envs/ielts-mac-runtime}"

case "${mode}" in
  dev|preview)
    ;;
  *)
    printf '[ERROR] Expected mode "dev" or "preview", got: %s\n' "${mode}" >&2
    exit 64
    ;;
esac

vite_bin="${root}/frontend/node_modules/vite/bin/vite.js"

log() {
  printf '[mac-local-app] %s\n' "$1"
}

mode_label() {
  case "${mode}" in
    dev) printf '开发版' ;;
    preview) printf '预览版' ;;
  esac
}

mode_url() {
  case "${mode}" in
    dev) printf 'http://127.0.0.1:3020' ;;
    preview) printf 'http://127.0.0.1:3002' ;;
  esac
}

run_direct() {
  [[ -f "${vite_bin}" ]] || {
    printf '[ERROR] Missing Vite binary. Run pnpm install first: %s\n' "${vite_bin}" >&2
    exit 1
  }

  cd "${root}/frontend"
  case "${mode}" in
    dev)
      exec node "${vite_bin}"
      ;;
    preview)
      exec node "${vite_bin}" preview
      ;;
  esac
}

write_app_icon() {
  local resources_dir="$1"
  local icon_source="${root}/frontend/assets/images/logo.png"
  local iconset="${resources_dir}/IELTSVocab.iconset"
  local icon_file="${resources_dir}/IELTSVocab.icns"

  [[ -f "${icon_source}" ]] || return 0
  command -v sips >/dev/null 2>&1 || return 0
  command -v iconutil >/dev/null 2>&1 || return 0

  rm -rf "${iconset}"
  mkdir -p "${iconset}"

  local spec size scale pixels suffix output
  for spec in 16:1 16:2 32:1 32:2 128:1 128:2 256:1 256:2 512:1 512:2; do
    IFS=':' read -r size scale <<<"${spec}"
    pixels=$((size * scale))
    suffix=""
    if [[ "${scale}" == "2" ]]; then
      suffix="@2x"
    fi
    output="${iconset}/icon_${size}x${size}${suffix}.png"
    sips -s format png -z "${pixels}" "${pixels}" "${icon_source}" --out "${output}" >/dev/null
  done

  iconutil -c icns "${iconset}" -o "${icon_file}" >/dev/null
  rm -rf "${iconset}"
}

write_app_bundle() {
  local label="$1"
  local app_title="雅思词汇${label}"
  local node_path=""
  local app_root="${IELTS_MAC_LOCAL_APP_DIR:-${root}/logs/runtime/mac-apps}"
  local app_bundle="${app_root}/雅思词汇${label}.app"
  local contents_dir="${app_bundle}/Contents"
  local macos_dir="${contents_dir}/MacOS"
  local resources_dir="${contents_dir}/Resources"
  local executable="${macos_dir}/ielts-vocab-local"
  local plist="${contents_dir}/Info.plist"
  local config_file="${resources_dir}/run.conf"
  local swift_source="${resources_dir}/MacLocalWebApp.swift"

  mkdir -p "${macos_dir}" "${resources_dir}"
  write_app_icon "${resources_dir}"
  node_path="$([[ -x "${runtime_prefix}/bin/node" ]] && printf '%s' "${runtime_prefix}/bin/node" || command -v node 2>/dev/null || true)"

  cat > "${plist}" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>ielts-vocab-local</string>
  <key>CFBundleIconFile</key>
  <string>IELTSVocab</string>
  <key>CFBundleIdentifier</key>
  <string>local.ielts-vocab.${mode}</string>
  <key>CFBundleName</key>
  <string>${app_title}</string>
  <key>CFBundleDisplayName</key>
  <string>${app_title}</string>
  <key>CFBundleDevelopmentRegion</key>
  <string>zh-Hans</string>
  <key>CFBundleLocalizations</key>
  <array><string>zh-Hans</string><string>zh_CN</string></array>
  <key>CFBundleAllowMixedLocalizations</key>
  <true/>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>1.0</string>
  <key>LSMinimumSystemVersion</key>
  <string>10.15</string>
  <key>NSAppTransportSecurity</key>
  <dict>
    <key>NSAllowsLocalNetworking</key>
    <true/>
  </dict>
  <key>NSAppSleepDisabled</key>
  <true/>
  <key>NSMicrophoneUsageDescription</key>
  <string>雅思词汇需要使用麦克风进行口语和听力练习。</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
PLIST

  cat > "${swift_source}" <<'SWIFT'
import Cocoa
import Foundation
import WebKit

UserDefaults.standard.set(["zh-Hans", "zh_CN"], forKey: "AppleLanguages")
UserDefaults.standard.set("zh_CN", forKey: "AppleLocale")

func appConfig() -> [String: String] {
    guard let url = Bundle.main.resourceURL?.appendingPathComponent("run.conf"),
          let text = try? String(contentsOf: url, encoding: .utf8) else {
        return [:]
    }
    var values: [String: String] = [:]
    for line in text.split(separator: "\n", omittingEmptySubsequences: true) {
        guard let separator = line.firstIndex(of: "=") else { continue }
        let key = String(line[..<separator])
        let value = String(line[line.index(after: separator)...])
        values[key] = value
    }
    return values
}

func htmlEscape(_ value: String) -> String {
    value
        .replacingOccurrences(of: "&", with: "&amp;")
        .replacingOccurrences(of: "<", with: "&lt;")
        .replacingOccurrences(of: ">", with: "&gt;")
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    private let config = appConfig()
    private var window: NSWindow!
    private var webView: WKWebView!
    private var backendLauncher: Process?
    private var frontendServer: Process?
    private var readyTimer: Timer?
    private var stdoutHandle: FileHandle?
    private var stderrHandle: FileHandle?
    private var didLoadApp = false
    private var startedAt = Date()

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        createWindow()
        guard prepareLogs() else { return }
        startBackend()
        startFrontend()
        waitForServices()
        NSApp.activate(ignoringOtherApps: true)
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }

    func applicationWillTerminate(_ notification: Notification) {
        readyTimer?.invalidate()
        if let frontendServer, frontendServer.isRunning {
            frontendServer.terminate()
        }
        if let backendLauncher, backendLauncher.isRunning {
            backendLauncher.terminate()
        }
        stdoutHandle?.closeFile()
        stderrHandle?.closeFile()
    }

    private func createWindow() {
        let webConfig = WKWebViewConfiguration()
        webConfig.websiteDataStore = .default()
        webConfig.preferences.javaScriptCanOpenWindowsAutomatically = true
        webConfig.userContentController.addUserScript(WKUserScript(
            source: """
            window.__IELTS_LOCAL_APP__ = { defaultLogin: { identifier: "admin", password: "admin123456" } };
            """,
            injectionTime: .atDocumentStart,
            forMainFrameOnly: true
        ))
        webView = WKWebView(frame: .zero, configuration: webConfig)

        let visibleFrame = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1280, height: 860)
        let width = min(1280, visibleFrame.width * 0.94)
        let height = min(900, visibleFrame.height * 0.94)
        let frame = NSRect(
            x: visibleFrame.midX - width / 2,
            y: visibleFrame.midY - height / 2,
            width: width,
            height: height
        )
        let title = config["IELTS_LOCAL_APP_TITLE"] ?? "雅思词汇"
        window = NSWindow(
            contentRect: frame,
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = title
        window.contentView = webView
        window.makeKeyAndOrderFront(nil)
        showMessage(title, "正在启动本地后端和前端...")
    }

    private func prepareLogs() -> Bool {
        let mode = config["IELTS_LOCAL_APP_MODE"] ?? "preview"
        let root = config["IELTS_LOCAL_APP_ROOT"] ?? ""
        let logDir = "\(root)/logs/runtime/mac-app"
        let stdoutPath = "\(logDir)/\(mode).out.log"
        let stderrPath = "\(logDir)/\(mode).err.log"

        do {
            try FileManager.default.createDirectory(atPath: logDir, withIntermediateDirectories: true)
            FileManager.default.createFile(atPath: stdoutPath, contents: nil)
            FileManager.default.createFile(atPath: stderrPath, contents: nil)
            stdoutHandle = try FileHandle(forWritingTo: URL(fileURLWithPath: stdoutPath))
            stderrHandle = try FileHandle(forWritingTo: URL(fileURLWithPath: stderrPath))
        } catch {
            showMessage("日志初始化失败", error.localizedDescription)
            return false
        }

        writeLog("mode=\(mode) root=\(root)")
        writeLog("started_at=\(Date())")
        return true
    }

    private func processEnvironment() -> [String: String] {
        let runtimePrefix = config["IELTS_MAC_RUNTIME_PREFIX"] ?? "\(NSHomeDirectory())/.local/share/micromamba/envs/ielts-mac-runtime"
        var environment = ProcessInfo.processInfo.environment
        let existingPath = environment["PATH"] ?? ""
        environment["PATH"] = "\(runtimePrefix)/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:\(existingPath)"
        for key in ["VITE_API_PROXY_TARGET", "VITE_SPEECH_PROXY_TARGET", "VITE_ASSET_BASE_URL", "FRONTEND_ASSET_BASE_URL", "CI"] {
            if let value = config[key], !value.isEmpty {
                environment[key] = value
            }
        }
        return environment
    }

    private func startBackend() {
        let root = config["IELTS_LOCAL_APP_ROOT"] ?? ""
        let script = "\(root)/start-microservices.sh"

        guard FileManager.default.fileExists(atPath: script) else {
            showMessage("缺少后端启动脚本", "找不到 start-microservices.sh。")
            return
        }

        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/bin/bash")
        task.arguments = [script, "--project-root", root, "--skip-frontend-checks"]
        task.currentDirectoryURL = URL(fileURLWithPath: root)
        task.environment = processEnvironment()
        task.standardOutput = stdoutHandle
        task.standardError = stderrHandle
        task.terminationHandler = { [weak self] process in
            self?.writeLog("backend_launcher_exited status=\(process.terminationStatus)")
        }

        do {
            try task.run()
            backendLauncher = task
        } catch {
            showMessage("后端启动失败", error.localizedDescription)
        }
    }

    private func startFrontend() {
        let mode = config["IELTS_LOCAL_APP_MODE"] ?? "preview"
        let root = config["IELTS_LOCAL_APP_ROOT"] ?? ""
        let nodeCommand = config["IELTS_LOCAL_APP_NODE"].flatMap { $0.isEmpty ? nil : $0 } ?? "node"
        let viteBin = "\(root)/frontend/node_modules/vite/bin/vite.js"

        guard FileManager.default.fileExists(atPath: viteBin) else {
            showMessage("缺少前端启动文件", "请先在项目根目录执行 pnpm install。")
            return
        }

        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        task.arguments = mode == "preview" ? [nodeCommand, viteBin, "preview"] : [nodeCommand, viteBin]
        task.currentDirectoryURL = URL(fileURLWithPath: "\(root)/frontend")
        task.environment = processEnvironment()
        task.standardOutput = stdoutHandle
        task.standardError = stderrHandle
        task.terminationHandler = { [weak self] process in
            self?.writeLog("frontend_exited status=\(process.terminationStatus)")
        }

        do {
            try task.run()
            frontendServer = task
        } catch {
            showMessage("前端启动失败", error.localizedDescription)
        }
    }

    private func waitForServices() {
        startedAt = Date()
        readyTimer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] _ in
            self?.checkServices()
        }
    }

    private func checkServices() {
        guard !didLoadApp,
              let appURL = config["IELTS_LOCAL_APP_URL"],
              let frontendURL = URL(string: appURL),
              let apiHealthURL = config["IELTS_LOCAL_APP_API_HEALTH_URL"] else {
            return
        }

        probeStatus(apiHealthURL) { [weak self] backendStatus in
            self?.probeStatus(appURL) { [weak self] frontendStatus in
                DispatchQueue.main.async {
                    guard let self, !self.didLoadApp else { return }
                    let backendReady = (200..<300).contains(backendStatus)
                    let frontendReady = (200..<500).contains(frontendStatus)
                    if backendReady && frontendReady {
                        self.ensureLocalAdminUser()
                        self.didLoadApp = true
                        self.readyTimer?.invalidate()
                        self.writeLog("ready api=\(apiHealthURL) app=\(appURL)")
                        self.webView.load(URLRequest(url: frontendURL))
                    } else if Date().timeIntervalSince(self.startedAt) > 90 {
                        self.readyTimer?.invalidate()
                        self.showMessage("本地服务启动超时", "无法同时连通后端 \(htmlEscape(apiHealthURL)) 和前端 \(htmlEscape(appURL))。请查看 logs/runtime/mac-app。")
                    }
                }
            }
        }
    }

    private func probeStatus(_ urlString: String, completion: @escaping (Int) -> Void) {
        guard let url = URL(string: urlString) else {
            completion(0)
            return
        }
        var request = URLRequest(url: url)
        request.timeoutInterval = 2
        URLSession.shared.dataTask(with: request) { _, response, _ in
            completion((response as? HTTPURLResponse)?.statusCode ?? 0)
        }.resume()
    }

    private func ensureLocalAdminUser() {
        let root = config["IELTS_LOCAL_APP_ROOT"] ?? ""
        let script = "\(root)/scripts/ensure-local-admin-user.py"
        guard FileManager.default.fileExists(atPath: script) else { return }
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        task.arguments = ["python", script]
        task.currentDirectoryURL = URL(fileURLWithPath: root)
        task.environment = processEnvironment()
        task.standardOutput = stdoutHandle
        task.standardError = stderrHandle
        try? task.run()
        task.waitUntilExit()
    }

    private func showMessage(_ title: String, _ body: String) {
        let html = """
        <!doctype html><meta name="viewport" content="width=device-width, initial-scale=1">
        <body style="margin:0;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif;background:#f7faf5;color:#1f2937;display:grid;place-items:center;height:100vh">
        <main style="text-align:center;max-width:520px;padding:32px">
        <h1 style="font-size:24px;margin:0 0 12px">\(htmlEscape(title))</h1>
        <p style="font-size:15px;line-height:1.7;color:#64748b;margin:0">\(htmlEscape(body))</p>
        </main></body>
        """
        webView.loadHTMLString(html, baseURL: nil)
    }

    private func writeLog(_ line: String) {
        guard let data = "[mac-local-app] \(line)\n".data(using: .utf8) else { return }
        stdoutHandle?.write(data)
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
SWIFT

  command -v swiftc >/dev/null 2>&1 || {
    printf '[ERROR] Missing swiftc. Install Xcode Command Line Tools to build the local Mac app shell.\n' >&2
    exit 1
  }
  swiftc -framework Cocoa -framework WebKit "${swift_source}" -o "${executable}"
  chmod +x "${executable}"

  {
    printf 'IELTS_LOCAL_APP_MODE=%s\n' "${mode}"
    printf 'IELTS_LOCAL_APP_TITLE=%s\n' "${app_title}"
    printf 'IELTS_LOCAL_APP_ROOT=%s\n' "${root}"
    printf 'IELTS_LOCAL_APP_URL=%s\n' "$(mode_url)"
    printf 'IELTS_LOCAL_APP_API_HEALTH_URL=http://127.0.0.1:5001/ready\n'
    printf 'IELTS_MAC_RUNTIME_PREFIX=%s\n' "${runtime_prefix}"
    if [[ -n "${node_path}" ]]; then
      printf 'IELTS_LOCAL_APP_NODE=%s\n' "${node_path}"
    fi
    for env_name in VITE_API_PROXY_TARGET VITE_SPEECH_PROXY_TARGET VITE_ASSET_BASE_URL FRONTEND_ASSET_BASE_URL CI; do
      if [[ -n "${!env_name:-}" ]]; then
        printf '%s=%s\n' "${env_name}" "${!env_name}"
      fi
    done
  } > "${config_file}"

  printf '%s\n' "${app_bundle}"
}

wait_until_ready() {
  local url="$1"
  local stdout_log="${root}/logs/runtime/mac-app/${mode}.out.log"
  local stderr_log="${root}/logs/runtime/mac-app/${mode}.err.log"
  local deadline=$((SECONDS + 90))

  while (( SECONDS < deadline )); do
    local status
    status="$(curl -s -o /dev/null -w '%{http_code}' "${url}" || true)"
    if [[ "${status}" =~ ^[234][0-9][0-9]$ ]]; then
      log "Ready: ${url}"
      return 0
    fi
    sleep 1
  done

  printf '[ERROR] Timed out waiting for %s\n' "${url}" >&2
  printf '        stdout: %s\n' "${stdout_log}" >&2
  printf '        stderr: %s\n' "${stderr_log}" >&2
  exit 1
}

if [[ "$(uname -s)" != "Darwin" || "${IELTS_DISABLE_MAC_APP:-0}" == "1" ]]; then
  run_direct
fi

label="$(mode_label)"
url="$(mode_url)"
api_url="http://127.0.0.1:5001/ready"
app_bundle="$(write_app_bundle "${label}")"

if [[ "${IELTS_MAC_LOCAL_APP_DRY_RUN:-0}" == "1" ]]; then
  log "Prepared ${app_bundle}"
  exit 0
fi

log "Launching ${app_bundle}"
open "${app_bundle}"
wait_until_ready "${url}"
wait_until_ready "${api_url}"
log "Logs: ${root}/logs/runtime/mac-app/${mode}.out.log"
