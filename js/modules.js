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
            const response = await fetch(filePath);
            if (!response.ok) {
                throw new Error(`Failed to load ${filePath}: ${response.status}`);
            }
            const html = await response.text();
            const container = document.getElementById(containerId);
            if (container) {
                container.innerHTML = html;
                return true;
            }
        } catch (error) {
            console.error(`Error loading module ${filePath}:`, error);
        }
        return false;
    },

    // 加载所有模块
    async loadAllModules() {
        const promises = this.modules.map(module =>
            this.loadModule(module.id, module.file)
        );

        const results = await Promise.all(promises);
        const loadedCount = results.filter(r => r).length;

        console.log(`[ModuleLoader] Loaded ${loadedCount}/${this.modules.length} modules`);

        // 触发自定义事件，通知所有模块已加载完成
        if (loadedCount === this.modules.length) {
            window.dispatchEvent(new CustomEvent('modulesLoaded'));
        }

        return loadedCount === this.modules.length;
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
document.addEventListener('DOMContentLoaded', () => {
    ModuleLoader.loadAllModules();
});
