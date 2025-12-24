/**
 * Nav System Sync - Obsidian Plugin
 * 将 Obsidian 笔记同步到 Nav System
 */

const { Plugin, PluginSettingTab, Setting, Notice, requestUrl } = require('obsidian');

const DEFAULT_SETTINGS = {
    apiUrl: 'http://localhost:8001',
    jwtToken: '',
    defaultPath: 'notes',
    syncOnSave: false
};

class NavSystemSyncPlugin extends Plugin {
    async onload() {
        await this.loadSettings();

        // 添加命令：上传当前文件
        this.addCommand({
            id: 'upload-current-file',
            name: '上传当前文件到 Nav System',
            callback: () => this.uploadCurrentFile()
        });

        // 添加命令：上传并指定路径
        this.addCommand({
            id: 'upload-with-path',
            name: '上传当前文件（指定路径）',
            callback: () => this.uploadWithCustomPath()
        });

        // 添加文件菜单项
        this.registerEvent(
            this.app.workspace.on('file-menu', (menu, file) => {
                // 检查是文件还是文件夹
                if (file.children !== undefined) {
                    // 是文件夹
                    menu.addItem((item) => {
                        item
                            .setTitle('上传文件夹到 Nav System')
                            .setIcon('upload')
                            .onClick(() => this.uploadFolder(file));
                    });
                } else if (file.extension === 'md') {
                    // 是 Markdown 文件
                    menu.addItem((item) => {
                        item
                            .setTitle('上传到 Nav System')
                            .setIcon('upload')
                            .onClick(() => this.uploadFile(file));
                    });
                }
            })
        );

        // 添加编辑器菜单项
        this.registerEvent(
            this.app.workspace.on('editor-menu', (menu, editor, view) => {
                menu.addItem((item) => {
                    item
                        .setTitle('上传到 Nav System')
                        .setIcon('upload')
                        .onClick(() => this.uploadCurrentFile());
                });
            })
        );

        // 自动保存时同步（可选）
        if (this.settings.syncOnSave) {
            this.registerEvent(
                this.app.vault.on('modify', (file) => {
                    if (file.extension === 'md') {
                        this.uploadFile(file, true);
                    }
                })
            );
        }

        // 添加设置选项卡
        this.addSettingTab(new NavSystemSyncSettingTab(this.app, this));

        // 添加状态栏图标
        this.statusBarItem = this.addStatusBarItem();
        this.statusBarItem.setText('Nav Sync');
    }

    onunload() {
        // 清理
    }

    async loadSettings() {
        this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
    }

    async saveSettings() {
        await this.saveData(this.settings);
    }

    // 上传当前打开的文件
    async uploadCurrentFile() {
        const activeFile = this.app.workspace.getActiveFile();
        if (!activeFile) {
            new Notice('没有打开的文件');
            return;
        }
        if (activeFile.extension !== 'md') {
            new Notice('只能上传 Markdown 文件');
            return;
        }
        await this.uploadFile(activeFile);
    }

    // 上传并指定自定义路径
    async uploadWithCustomPath() {
        const activeFile = this.app.workspace.getActiveFile();
        if (!activeFile) {
            new Notice('没有打开的文件');
            return;
        }

        // 简单的路径输入（实际可以用 Modal）
        const customPath = prompt('输入保存路径（如 notes/my-article）:',
            this.settings.defaultPath + '/' + activeFile.basename);

        if (customPath) {
            await this.uploadFile(activeFile, false, customPath);
        }
    }

    // 上传文件夹（递归上传所有 .md 文件）
    async uploadFolder(folder) {
        if (!this.settings.jwtToken) {
            new Notice('请先在设置中配置 JWT Token');
            return;
        }

        const files = this.getAllMarkdownFiles(folder);
        if (files.length === 0) {
            new Notice('文件夹中没有 Markdown 文件');
            return;
        }

        new Notice(`开始上传 ${files.length} 个文件...`);

        let successCount = 0;
        let failCount = 0;

        for (const file of files) {
            try {
                await this.uploadFile(file, true);
                successCount++;
            } catch (error) {
                failCount++;
                console.error(`上传失败: ${file.path}`, error);
            }
        }

        new Notice(`上传完成: ${successCount} 成功, ${failCount} 失败`);
    }

    // 递归获取文件夹下所有 Markdown 文件
    getAllMarkdownFiles(folder) {
        const files = [];

        const traverse = (item) => {
            if (item.children !== undefined) {
                // 是文件夹，递归遍历
                for (const child of item.children) {
                    traverse(child);
                }
            } else if (item.extension === 'md') {
                // 是 Markdown 文件
                files.push(item);
            }
        };

        traverse(folder);
        return files;
    }

    // 上传文件
    async uploadFile(file, silent = false, customPath = null) {
        if (!this.settings.jwtToken) {
            new Notice('请先在设置中配置 JWT Token');
            return;
        }

        try {
            // 读取文件内容
            const content = await this.app.vault.read(file);

            // 解析 frontmatter
            const { frontmatter, body } = this.parseFrontmatter(content);

            // 确定保存路径
            const savePath = customPath || this.getDefaultPath(file);

            // 提取标签
            const tags = this.extractTags(content, frontmatter);

            // 构建请求数据
            const requestData = {
                path: savePath,
                content: body,
                title: frontmatter?.title || file.basename,
                tags: tags,
                frontmatter: frontmatter
            };

            // 发送请求
            const response = await requestUrl({
                url: `${this.settings.apiUrl}/api/v1/articles/sync`,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.settings.jwtToken}`
                },
                body: JSON.stringify(requestData)
            });

            if (response.status === 200 || response.status === 201) {
                if (!silent) {
                    new Notice(`文章已同步: ${savePath}`);
                }
                this.statusBarItem.setText('Nav Sync ✓');
                setTimeout(() => this.statusBarItem.setText('Nav Sync'), 3000);
            } else {
                throw new Error(response.json?.detail || '同步失败');
            }
        } catch (error) {
            console.error('Nav System Sync Error:', error);
            new Notice(`同步失败: ${error.message}`);
            this.statusBarItem.setText('Nav Sync ✗');
            setTimeout(() => this.statusBarItem.setText('Nav Sync'), 3000);
        }
    }

    // 解析 frontmatter
    parseFrontmatter(content) {
        const frontmatterRegex = /^---\n([\s\S]*?)\n---\n/;
        const match = content.match(frontmatterRegex);

        if (match) {
            try {
                // 简单的 YAML 解析
                const yamlContent = match[1];
                const frontmatter = {};

                yamlContent.split('\n').forEach(line => {
                    const colonIndex = line.indexOf(':');
                    if (colonIndex > 0) {
                        const key = line.substring(0, colonIndex).trim();
                        let value = line.substring(colonIndex + 1).trim();

                        // 处理数组
                        if (value.startsWith('[') && value.endsWith(']')) {
                            value = value.slice(1, -1).split(',').map(v => v.trim().replace(/['"]/g, ''));
                        } else {
                            value = value.replace(/['"]/g, '');
                        }

                        frontmatter[key] = value;
                    }
                });

                return {
                    frontmatter,
                    body: content.substring(match[0].length)
                };
            } catch (e) {
                return { frontmatter: null, body: content };
            }
        }

        return { frontmatter: null, body: content };
    }

    // 提取标签
    extractTags(content, frontmatter) {
        const tags = [];

        // 从 frontmatter 提取
        if (frontmatter?.tags) {
            if (Array.isArray(frontmatter.tags)) {
                tags.push(...frontmatter.tags);
            } else if (typeof frontmatter.tags === 'string') {
                tags.push(...frontmatter.tags.split(',').map(t => t.trim()));
            }
        }

        // 从内容中提取 #tag 格式的标签
        const tagMatches = content.match(/#[\w\u4e00-\u9fa5]+/g);
        if (tagMatches) {
            tagMatches.forEach(tag => {
                const cleanTag = tag.substring(1);
                if (!tags.includes(cleanTag)) {
                    tags.push(cleanTag);
                }
            });
        }

        return tags;
    }

    // 获取默认保存路径
    getDefaultPath(file) {
        // 使用文件在 vault 中的相对路径，或者默认路径 + 文件名
        const relativePath = file.path.replace(/\.md$/, '');
        if (this.settings.defaultPath) {
            return `${this.settings.defaultPath}/${file.basename}`;
        }
        return relativePath;
    }
}

// 设置选项卡
class NavSystemSyncSettingTab extends PluginSettingTab {
    constructor(app, plugin) {
        super(app, plugin);
        this.plugin = plugin;
    }

    display() {
        const { containerEl } = this;
        containerEl.empty();

        containerEl.createEl('h2', { text: 'Nav System Sync 设置' });

        new Setting(containerEl)
            .setName('API 地址')
            .setDesc('Nav System 后端 API 地址')
            .addText(text => text
                .setPlaceholder('http://localhost:8000')
                .setValue(this.plugin.settings.apiUrl)
                .onChange(async (value) => {
                    this.plugin.settings.apiUrl = value;
                    await this.plugin.saveSettings();
                }));

        new Setting(containerEl)
            .setName('JWT Token')
            .setDesc('登录后获取的 JWT Token')
            .addText(text => text
                .setPlaceholder('输入 JWT Token')
                .setValue(this.plugin.settings.jwtToken)
                .onChange(async (value) => {
                    this.plugin.settings.jwtToken = value;
                    await this.plugin.saveSettings();
                }));

        new Setting(containerEl)
            .setName('默认保存路径')
            .setDesc('文章默认保存的目录路径')
            .addText(text => text
                .setPlaceholder('notes')
                .setValue(this.plugin.settings.defaultPath)
                .onChange(async (value) => {
                    this.plugin.settings.defaultPath = value;
                    await this.plugin.saveSettings();
                }));

        new Setting(containerEl)
            .setName('保存时自动同步')
            .setDesc('文件保存时自动同步到 Nav System')
            .addToggle(toggle => toggle
                .setValue(this.plugin.settings.syncOnSave)
                .onChange(async (value) => {
                    this.plugin.settings.syncOnSave = value;
                    await this.plugin.saveSettings();
                }));

        // 测试连接按钮
        new Setting(containerEl)
            .setName('测试连接')
            .setDesc('测试与 Nav System 的连接')
            .addButton(button => button
                .setButtonText('测试')
                .onClick(async () => {
                    try {
                        const response = await requestUrl({
                            url: `${this.plugin.settings.apiUrl}/api/v1/auth/me`,
                            method: 'GET',
                            headers: {
                                'Authorization': `Bearer ${this.plugin.settings.jwtToken}`
                            }
                        });

                        if (response.status === 200) {
                            new Notice(`连接成功！用户: ${response.json.username}`);
                        } else {
                            new Notice('连接失败：Token 无效');
                        }
                    } catch (error) {
                        new Notice(`连接失败: ${error.message}`);
                    }
                }));

        // 使用说明
        containerEl.createEl('h3', { text: '使用说明' });
        containerEl.createEl('p', { text: '1. 在 Nav System 登录后，从浏览器开发者工具获取 JWT Token' });
        containerEl.createEl('p', { text: '2. 使用命令面板（Ctrl/Cmd + P）搜索 "Nav System" 相关命令' });
        containerEl.createEl('p', { text: '3. 或右键文件/编辑器选择 "上传到 Nav System"' });
    }
}

module.exports = NavSystemSyncPlugin;
