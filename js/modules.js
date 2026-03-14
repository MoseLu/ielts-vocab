/**
 * HTML Module Loader
 * 动态加载html文件夹中的各个模块
 */

const ModuleLoader = {
    // 模块配置
    modules: [
        { id: 'header-container', file: 'html/header.html' },
        { id: 'auth-container', file: 'html/auth.html' },
        { id: 'home-container', file: 'html/home.html' },
        { id: 'practice-container', file: 'html/practice.html' },
        { id: 'complete-container', file: 'html/complete.html' },
        { id: 'settings-container', file: 'html/settings.html' },
        { id: 'help-container', file: 'html/help.html' },
        { id: 'toast-container', file: 'html/toast.html' }
    ],

    // 加载单个模块
    async loadModule(containerId, filePath) {
        try {
            console.log(`[ModuleLoader] Loading ${filePath} into ${containerId}...`);
            const response = await fetch(filePath);
            if (!response.ok) {
                throw new Error(`Failed to load ${filePath}: ${response.status}`);
            }
            const html = await response.text();
            const container = document.getElementById(containerId);
            if (container) {
                container.innerHTML = html;
                console.log(`[ModuleLoader] ✅ Successfully loaded ${filePath}`);
                return true;
            } else {
                console.error(`[ModuleLoader] ❌ Container ${containerId} not found`);
                return false;
            }
        } catch (error) {
            console.error(`[ModuleLoader] ❌ Error loading module ${filePath}:`, error);
        }
        return false;
    },

    // 加载所有模块
    async loadAllModules() {
        console.log('[ModuleLoader] Starting to load modules...');
        const promises = this.modules.map(module =>
            this.loadModule(module.id, module.file)
        );

        const results = await Promise.all(promises);
        const loadedCount = results.filter(r => r).length;

        console.log(`[ModuleLoader] Loaded ${loadedCount}/${this.modules.length} modules`);

        // 检查是否有模块加载失败（可能是 file:// 协议导致的）
        if (loadedCount < this.modules.length) {
            const failedModules = this.modules.filter((m, i) => !results[i]);
            console.warn('[ModuleLoader] Failed to load modules:', failedModules.map(m => m.file));

            // 检测是否在 file:// 协议下运行
            if (window.location.protocol === 'file:') {
                console.error('[ModuleLoader] 检测到您正在通过 file:// 协议直接打开文件。这会导致模块加载失败。');
                console.error('[ModuleLoader] 解决方法：请使用 HTTP 服务器访问本应用，例如：');
                console.error('  python -m http.server 8080');
                console.error('  npx serve .');
                console.error('  或使用 VS Code Live Server 插件');

                // 显示用户友好的错误提示
                this.showFileProtocolError();
            }
        }

        // 即使部分模块加载失败，也触发事件让应用继续初始化
        // 这样至少能看到错误提示，而不是完全卡住
        window.modulesInitialized = true;
        console.log('[ModuleLoader] Dispatching modulesLoaded event');
        window.dispatchEvent(new CustomEvent('modulesLoaded'));

        return loadedCount === this.modules.length;
    },

    // 显示 file:// 协议错误提示
    showFileProtocolError() {
        const style = document.createElement('style');
        style.textContent = `
            .file-protocol-error {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0,0,0,0.8);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 9999;
                padding: 20px;
            }
            .file-protocol-error-content {
                background: white;
                border-radius: 12px;
                padding: 32px;
                max-width: 500px;
                text-align: center;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            .file-protocol-error h2 {
                color: #dc2626;
                margin: 0 0 16px 0;
                font-size: 20px;
            }
            .file-protocol-error p {
                color: #4b5563;
                margin: 0 0 20px 0;
                line-height: 1.6;
            }
            .file-protocol-error code {
                background: #f3f4f6;
                padding: 2px 8px;
                border-radius: 4px;
                font-family: monospace;
                font-size: 14px;
            }
            .file-protocol-error .hint {
                background: #fef3c7;
                border-left: 4px solid #f59e0b;
                padding: 12px 16px;
                margin-top: 16px;
                text-align: left;
                border-radius: 4px;
                font-size: 14px;
            }
        `;
        document.head.appendChild(style);

        const errorDiv = document.createElement('div');
        errorDiv.className = 'file-protocol-error';
        errorDiv.innerHTML = `
            <div class="file-protocol-error-content">
                <h2>⚠️ 启动方式不正确</h2>
                <p>您正在通过 <code>file://</code> 协议直接打开文件，这会导致应用功能无法正常使用。</p>
                <div class="hint">
                    <strong>解决方法：</strong>请使用 HTTP 服务器访问本应用：<br><br>
                    1. <strong>Python:</strong> <code>python -m http.server 8080</code><br>
                    2. <strong>Node.js:</strong> <code>npx serve .</code><br>
                    3. <strong>VS Code:</strong> 安装 Live Server 插件<br><br>
                    然后访问 <code>http://localhost:8080</code>
                </div>
            </div>
        `;
        document.body.appendChild(errorDiv);
    },

    // 重新加载特定模块
    async reloadModule(containerId) {
        const module = this.modules.find(m => m.id === containerId);
        if (module) {
            return await this.loadModule(module.id, module.file);
        }
        return false;
    }
};

// 页面加载完成后自动加载所有模块
// 立即执行，不等待 DOMContentLoaded，因为脚本在 body 末尾
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        ModuleLoader.loadAllModules();
    });
} else {
    // DOM 已经加载完成
    ModuleLoader.loadAllModules();
}
