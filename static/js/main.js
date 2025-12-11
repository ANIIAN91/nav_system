/**
 * 个人主页导航系统 - 前端逻辑
 */

// 状态管理
const state = {
    token: localStorage.getItem('token') || sessionStorage.getItem('token'),
    username: localStorage.getItem('username') || sessionStorage.getItem('username'),
    links: { categories: [] },
    isManageMode: false,
    theme: localStorage.getItem('theme') || 'dark',
    settings: { link_size: 'medium', protected_article_paths: [] }
};

// 主题切换
function initTheme() {
    document.documentElement.setAttribute('data-theme', state.theme);
    updateThemeIcon(state.theme);
}

function toggleTheme() {
    state.theme = state.theme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', state.theme);
    localStorage.setItem('theme', state.theme);
    updateThemeIcon(state.theme);
}

function updateThemeIcon(theme) {
    const btn = document.getElementById('theme-toggle');
    if (btn) {
        btn.innerHTML = theme === 'light' ? '&#9728;' : '&#9790;';
    }
}

// API 请求封装
async function api(url, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }

    const response = await fetch(url, { ...options, headers });

    if (response.status === 401) {
        logout();
        throw new Error('登录已过期');
    }

    return response;
}

// 时钟
function updateClock() {
    const clock = document.getElementById('clock');
    if (!clock) return;

    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    clock.textContent = `${hours}:${minutes}:${seconds}`;
}

// 初始化时钟
setInterval(updateClock, 1000);
updateClock();

// 更新 UI 状态
function updateUI() {
    const loginBtn = document.getElementById('login-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const manageBtn = document.getElementById('manage-btn');
    const usernameDisplay = document.getElementById('username-display');

    if (state.token) {
        loginBtn.style.display = 'none';
        logoutBtn.style.display = 'block';
        manageBtn.style.display = 'block';
        usernameDisplay.style.display = 'inline';
        usernameDisplay.textContent = state.username;
    } else {
        loginBtn.style.display = 'block';
        logoutBtn.style.display = 'none';
        manageBtn.style.display = 'none';
        usernameDisplay.style.display = 'none';
    }
}

// 加载导航链接
async function loadLinks() {
    try {
        const response = await api('/api/links');
        state.links = await response.json();
        renderLinks();
    } catch (error) {
        console.error('加载链接失败:', error);
    }
}

// HTML 转义函数 - 防止 XSS 攻击
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 安全地设置元素文本内容
function setTextContent(element, text) {
    element.textContent = text || '';
}

// 渲染导航链接
function renderLinks() {
    const container = document.getElementById('links-container');
    if (!container) return;

    container.innerHTML = '';

    // 获取链接大小设置
    const linkSize = state.settings.link_size || 'medium';

    state.links.categories.forEach(category => {
        const categoryEl = document.createElement('div');
        categoryEl.className = 'category';

        // 创建分类头部
        const headerDiv = document.createElement('div');
        headerDiv.className = 'category-header';

        const titleH2 = document.createElement('h2');
        titleH2.className = 'category-title';
        setTextContent(titleH2, category.name);

        if (category.auth_required) {
            const authBadge = document.createElement('span');
            authBadge.className = 'auth-badge';
            authBadge.textContent = '私密';
            titleH2.appendChild(authBadge);
        }

        headerDiv.appendChild(titleH2);

        if (state.token) {
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'category-actions';

            const upBtn = document.createElement('button');
            upBtn.className = 'btn-icon reorder-category-btn';
            upBtn.dataset.name = category.name;
            upBtn.dataset.direction = 'up';
            upBtn.title = '上移';
            upBtn.innerHTML = '&#9650;';

            const downBtn = document.createElement('button');
            downBtn.className = 'btn-icon reorder-category-btn';
            downBtn.dataset.name = category.name;
            downBtn.dataset.direction = 'down';
            downBtn.title = '下移';
            downBtn.innerHTML = '&#9660;';

            const editBtn = document.createElement('button');
            editBtn.className = 'btn btn-secondary edit-category-btn';
            editBtn.dataset.name = category.name;
            editBtn.dataset.auth = category.auth_required;
            editBtn.textContent = '编辑分类';

            actionsDiv.appendChild(upBtn);
            actionsDiv.appendChild(downBtn);
            actionsDiv.appendChild(editBtn);
            headerDiv.appendChild(actionsDiv);
        }

        categoryEl.appendChild(headerDiv);

        // 创建链接网格，应用大小设置
        const linksGrid = document.createElement('div');
        linksGrid.className = `links-grid size-${linkSize}`;

        category.links.forEach(link => {
            const linkEl = document.createElement('a');
            linkEl.href = link.url;
            linkEl.target = '_blank';
            linkEl.className = 'link-item';
            linkEl.dataset.id = link.id || '';

            const iconDiv = document.createElement('div');
            iconDiv.className = 'link-icon';

            if (link.icon) {
                const img = document.createElement('img');
                img.src = '/static/icons/' + escapeHtml(link.icon);
                img.alt = link.title || '';
                img.onerror = function() {
                    this.parentElement.textContent = (link.title || '?').charAt(0);
                };
                iconDiv.appendChild(img);
            } else {
                iconDiv.textContent = (link.title || '?').charAt(0);
            }

            const titleSpan = document.createElement('span');
            titleSpan.className = 'link-title';
            setTextContent(titleSpan, link.title);

            linkEl.appendChild(iconDiv);
            linkEl.appendChild(titleSpan);

            if (state.token) {
                const editLinkBtn = document.createElement('button');
                editLinkBtn.className = 'edit-btn';
                editLinkBtn.dataset.id = link.id || '';
                editLinkBtn.dataset.title = link.title || '';
                editLinkBtn.dataset.url = link.url || '';
                editLinkBtn.dataset.icon = link.icon || '';
                editLinkBtn.innerHTML = '&#9998;';
                linkEl.appendChild(editLinkBtn);
            }

            linksGrid.appendChild(linkEl);
        });

        categoryEl.appendChild(linksGrid);
        container.appendChild(categoryEl);
    });

    // 绑定编辑按钮事件
    if (state.token) {
        document.querySelectorAll('.edit-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                openEditModal(btn.dataset);
            });
        });

        document.querySelectorAll('.edit-category-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                openEditCategoryModal(btn.dataset.name, btn.dataset.auth === 'true');
            });
        });

        document.querySelectorAll('.reorder-category-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                reorderCategory(btn.dataset.name, btn.dataset.direction);
            });
        });
    }

    // 更新分类下拉框
    updateCategorySelect();
}

// 更新分类下拉框
function updateCategorySelect() {
    const select = document.getElementById('link-category');
    if (!select) return;

    select.innerHTML = '';
    state.links.categories.forEach(cat => {
        const option = document.createElement('option');
        option.value = cat.name;
        option.textContent = cat.name;
        select.appendChild(option);
    });
}

// 登录
async function login(username, password, rememberUsername, stayLoggedIn) {
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || '登录失败');
        }

        const data = await response.json();
        state.token = data.access_token;
        state.username = username;

        // 根据选项决定存储方式
        if (stayLoggedIn) {
            localStorage.setItem('token', state.token);
            localStorage.setItem('username', username);
        } else {
            sessionStorage.setItem('token', state.token);
            sessionStorage.setItem('username', username);
        }

        // 安全改进：只记住用户名，不存储密码
        // 密码应由浏览器密码管理器处理
        if (rememberUsername) {
            localStorage.setItem('savedUsername', username);
            localStorage.setItem('rememberUsername', 'true');
        } else {
            localStorage.removeItem('savedUsername');
            localStorage.removeItem('rememberUsername');
        }

        // 清理旧版本可能存储的密码（安全迁移）
        localStorage.removeItem('savedPassword');
        localStorage.removeItem('rememberCredentials');

        updateUI();
        loadLinks();
        loadSettings();
        closeModal('login-modal');
    } catch (error) {
        document.getElementById('login-error').textContent = error.message;
    }
}

// 加载保存的用户名（不再加载密码）
function loadSavedCredentials() {
    // 清理旧版本可能存储的密码（安全迁移）
    if (localStorage.getItem('savedPassword')) {
        localStorage.removeItem('savedPassword');
        localStorage.removeItem('rememberCredentials');
    }

    // 只加载用户名
    if (localStorage.getItem('rememberUsername') === 'true') {
        const savedUsername = localStorage.getItem('savedUsername');
        if (savedUsername) {
            document.getElementById('username').value = savedUsername;
            document.getElementById('remember-credentials').checked = true;
        }
    }
}

// 登出
function logout() {
    state.token = null;
    state.username = null;
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('username');
    updateUI();
    loadLinks();
    loadSettings();
}

// 添加链接
async function addLink(category, title, url, icon) {
    try {
        const response = await api(`/api/links?category_name=${encodeURIComponent(category)}`, {
            method: 'POST',
            body: JSON.stringify({ title, url, icon: icon || null })
        });

        if (!response.ok) {
            throw new Error('添加失败');
        }

        loadLinks();
        closeModal('manage-modal');
        document.getElementById('add-link-form').reset();
    } catch (error) {
        alert(error.message);
    }
}

// 更新链接
async function updateLink(id, title, url, icon) {
    try {
        const response = await api(`/api/links/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ title, url, icon: icon || null })
        });

        if (!response.ok) {
            throw new Error('更新失败');
        }

        loadLinks();
        closeModal('edit-modal');
    } catch (error) {
        alert(error.message);
    }
}

// 删除链接
async function deleteLink(id) {
    if (!confirm('确定要删除这个链接吗？')) return;

    try {
        const response = await api(`/api/links/${id}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('删除失败');
        }

        loadLinks();
        closeModal('edit-modal');
    } catch (error) {
        alert(error.message);
    }
}

// 添加分类
async function addCategory(name, authRequired) {
    try {
        const response = await api('/api/categories', {
            method: 'POST',
            body: JSON.stringify({ name, auth_required: authRequired, links: [] })
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || '添加失败');
        }

        loadLinks();
        closeModal('manage-modal');
        document.getElementById('add-category-form').reset();
    } catch (error) {
        alert(error.message);
    }
}

// 删除分类
async function deleteCategory(name) {
    if (!confirm(`确定要删除分类 "${name}" 及其所有链接吗？`)) return;

    try {
        const response = await api(`/api/categories/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('删除失败');
        }

        loadLinks();
    } catch (error) {
        alert(error.message);
    }
}

// 弹窗控制
function openModal(id) {
    document.getElementById(id).classList.add('active');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
}

function openEditModal(data) {
    document.getElementById('edit-link-id').value = data.id;
    document.getElementById('edit-link-title').value = data.title;
    document.getElementById('edit-link-url').value = data.url;
    document.getElementById('edit-link-icon').value = data.icon;
    openModal('edit-modal');
}

// 标签页切换
function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabId);
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === tabId);
    });
}

// 从网页获取图标（通用函数）
async function fetchFaviconGeneric(url, iconInputId, statusElId) {
    const statusEl = document.getElementById(statusElId);
    const iconInput = document.getElementById(iconInputId);

    if (!url) {
        statusEl.textContent = '请先输入 URL';
        return;
    }

    try {
        statusEl.textContent = '正在获取图标...';
        statusEl.style.color = 'var(--text-muted)';

        const response = await api('/api/fetch-favicon', {
            method: 'POST',
            body: JSON.stringify({ url })
        });

        if (!response.ok) {
            throw new Error('获取失败');
        }

        const data = await response.json();
        if (data.icon) {
            iconInput.value = data.icon;
            statusEl.textContent = '图标获取成功: ' + data.icon;
            statusEl.style.color = 'var(--success-color)';
        } else {
            statusEl.textContent = '未找到图标';
            statusEl.style.color = 'var(--danger-color)';
        }
    } catch (error) {
        statusEl.textContent = '获取失败: ' + error.message;
        statusEl.style.color = 'var(--danger-color)';
    }
}

// 更新分类
async function updateCategory(oldName, newName, authRequired) {
    try {
        const response = await api(`/api/categories/${encodeURIComponent(oldName)}`, {
            method: 'PUT',
            body: JSON.stringify({ name: newName, auth_required: authRequired })
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || '更新失败');
        }

        loadLinks();
        closeModal('edit-category-modal');
    } catch (error) {
        alert(error.message);
    }
}

// 打开编辑分类弹窗
function openEditCategoryModal(name, authRequired) {
    document.getElementById('edit-category-old-name').value = name;
    document.getElementById('edit-category-name').value = name;
    document.getElementById('edit-category-auth').checked = authRequired;
    openModal('edit-category-modal');
}

// 调整分类顺序
async function reorderCategory(name, direction) {
    try {
        const response = await api(`/api/categories/${encodeURIComponent(name)}/reorder`, {
            method: 'POST',
            body: JSON.stringify({ direction })
        });
        if (!response.ok) throw new Error('移动失败');
        loadLinks();
    } catch (error) {
        console.error('移动分类失败:', error);
    }
}

// 调整链接顺序
async function reorderLink(id, direction) {
    try {
        const response = await api(`/api/links/${id}/reorder`, {
            method: 'POST',
            body: JSON.stringify({ direction })
        });
        if (!response.ok) throw new Error('移动失败');
        loadLinks();
    } catch (error) {
        console.error('移动链接失败:', error);
    }
}

// 加载站点设置
async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const settings = await response.json();

        // 保存到状态
        state.settings = settings;

        // 更新网站标题
        if (settings.site_title) {
            document.title = settings.site_title;
        }

        // 更新备案信息显示
        const icpEl = document.getElementById('icp-info');
        if (icpEl) {
            let footerText = '';
            if (settings.copyright) footerText += settings.copyright;
            if (settings.icp) footerText += (footerText ? ' | ' : '') + settings.icp;
            icpEl.textContent = footerText || '';
        }

        // 重新渲染链接以应用大小设置
        if (state.links.categories.length > 0) {
            renderLinks();
        }

        return settings;
    } catch (error) {
        console.error('加载设置失败:', error);
        return {};
    }
}

// 保存站点设置
async function saveSettings(icp, copyright, articlePageTitle, siteTitle, linkSize, protectedPaths) {
    try {
        const response = await api('/api/settings', {
            method: 'PUT',
            body: JSON.stringify({
                icp,
                copyright,
                article_page_title: articlePageTitle,
                site_title: siteTitle,
                link_size: linkSize,
                protected_article_paths: protectedPaths
            })
        });

        if (!response.ok) {
            throw new Error('保存失败');
        }

        loadSettings();
        alert('站点设置已保存');
    } catch (error) {
        alert(error.message);
    }
}

// 事件绑定
document.addEventListener('DOMContentLoaded', () => {
    // 初始化
    initTheme();
    updateUI();
    loadLinks();
    loadSettings();

    // 登录按钮
    document.getElementById('login-btn')?.addEventListener('click', () => {
        loadSavedCredentials();
        openModal('login-modal');
    });

    // 登出按钮
    document.getElementById('logout-btn')?.addEventListener('click', logout);

    // 管理按钮
    document.getElementById('manage-btn')?.addEventListener('click', async () => {
        // 加载站点设置到表单
        const settings = await loadSettings();
        const siteTitleInput = document.getElementById('site-title');
        const articleTitleInput = document.getElementById('footer-article-title');
        const icpInput = document.getElementById('footer-icp');
        const copyrightInput = document.getElementById('footer-copyright');
        const linkSizeSelect = document.getElementById('link-size');
        const protectedPathsInput = document.getElementById('protected-paths');
        const jwtTokenDisplay = document.getElementById('jwt-token-display');
        if (siteTitleInput) siteTitleInput.value = settings.site_title || '个人主页导航';
        if (articleTitleInput) articleTitleInput.value = settings.article_page_title || '文章';
        if (icpInput) icpInput.value = settings.icp || '';
        if (copyrightInput) copyrightInput.value = settings.copyright || '';
        if (linkSizeSelect) linkSizeSelect.value = settings.link_size || 'medium';
        if (protectedPathsInput) protectedPathsInput.value = (settings.protected_article_paths || []).join(',');
        if (jwtTokenDisplay) jwtTokenDisplay.value = state.token || '';
        openModal('manage-modal');
    });

    // 复制 Token 按钮
    document.getElementById('copy-token-btn')?.addEventListener('click', () => {
        const tokenInput = document.getElementById('jwt-token-display');
        if (tokenInput && tokenInput.value) {
            navigator.clipboard.writeText(tokenInput.value).then(() => {
                alert('Token 已复制到剪贴板');
            }).catch(() => {
                tokenInput.select();
                document.execCommand('copy');
                alert('Token 已复制到剪贴板');
            });
        }
    });

    // 关闭弹窗
    document.querySelectorAll('.modal .close').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.modal').classList.remove('active');
        });
    });

    // 点击弹窗外部关闭
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });

    // 登录表单
    document.getElementById('login-form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const rememberCredentials = document.getElementById('remember-credentials').checked;
        const stayLoggedIn = document.getElementById('stay-logged-in').checked;
        login(username, password, rememberCredentials, stayLoggedIn);
    });

    // 添加链接表单
    document.getElementById('add-link-form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        const category = document.getElementById('link-category').value;
        const title = document.getElementById('link-title').value;
        const url = document.getElementById('link-url').value;
        const icon = document.getElementById('link-icon').value;
        addLink(category, title, url, icon);
    });

    // 添加分类表单
    document.getElementById('add-category-form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        const name = document.getElementById('category-name').value;
        const authRequired = document.getElementById('category-auth').checked;
        addCategory(name, authRequired);
    });

    // 编辑链接表单
    document.getElementById('edit-link-form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        const id = document.getElementById('edit-link-id').value;
        const title = document.getElementById('edit-link-title').value;
        const url = document.getElementById('edit-link-url').value;
        const icon = document.getElementById('edit-link-icon').value;
        updateLink(id, title, url, icon);
    });

    // 删除链接按钮
    document.getElementById('delete-link-btn')?.addEventListener('click', () => {
        const id = document.getElementById('edit-link-id').value;
        deleteLink(id);
    });

    // 链接上移按钮
    document.getElementById('link-move-up-btn')?.addEventListener('click', async () => {
        const id = document.getElementById('edit-link-id').value;
        await reorderLink(id, 'up');
        closeModal('edit-modal');
    });

    // 链接下移按钮
    document.getElementById('link-move-down-btn')?.addEventListener('click', async () => {
        const id = document.getElementById('edit-link-id').value;
        await reorderLink(id, 'down');
        closeModal('edit-modal');
    });

    // 标签页切换
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            switchTab(btn.dataset.tab);
        });
    });

    // 主题切换
    document.getElementById('theme-toggle')?.addEventListener('click', toggleTheme);

    // 获取图标按钮（添加链接）
    document.getElementById('fetch-icon-btn')?.addEventListener('click', () => {
        const url = document.getElementById('link-url').value;
        fetchFaviconGeneric(url, 'link-icon', 'fetch-icon-status');
    });

    // 获取图标按钮（编辑链接）
    document.getElementById('edit-fetch-icon-btn')?.addEventListener('click', () => {
        const url = document.getElementById('edit-link-url').value;
        fetchFaviconGeneric(url, 'edit-link-icon', 'edit-fetch-icon-status');
    });

    // 编辑分类表单
    document.getElementById('edit-category-form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        const oldName = document.getElementById('edit-category-old-name').value;
        const newName = document.getElementById('edit-category-name').value;
        const authRequired = document.getElementById('edit-category-auth').checked;
        updateCategory(oldName, newName, authRequired);
    });

    // 删除分类按钮（在编辑弹窗中）
    document.getElementById('delete-category-modal-btn')?.addEventListener('click', () => {
        const name = document.getElementById('edit-category-old-name').value;
        if (confirm(`确定要删除分类 "${name}" 及其所有链接吗？`)) {
            deleteCategory(name);
            closeModal('edit-category-modal');
        }
    });

    // 保存站点设置表单
    document.getElementById('edit-footer-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const siteTitle = document.getElementById('site-title').value || '个人主页导航';
        const articleTitle = document.getElementById('footer-article-title').value || '文章';
        const icp = document.getElementById('footer-icp').value;
        const copyright = document.getElementById('footer-copyright').value;
        const linkSize = document.getElementById('link-size').value || 'medium';
        const protectedPathsStr = document.getElementById('protected-paths').value || '';
        const protectedPaths = protectedPathsStr.split(',').map(p => p.trim()).filter(p => p);
        saveSettings(icp, copyright, articleTitle, siteTitle, linkSize, protectedPaths);
    });

    // 导出导航数据
    document.getElementById('export-links-btn')?.addEventListener('click', async () => {
        try {
            const response = await api('/api/links/export');
            if (!response.ok) throw new Error('导出失败');
            const data = await response.json();
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `homepage-links-${new Date().toISOString().slice(0, 10)}.json`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (error) {
            alert('导出失败: ' + error.message);
        }
    });

    // 导入导航数据（原生格式）
    document.getElementById('import-native-btn')?.addEventListener('click', () => {
        importLinks('native');
    });

    // 导入导航数据（SunPanel 格式）
    document.getElementById('import-sunpanel-btn')?.addEventListener('click', () => {
        importLinks('sunpanel');
    });
});

// 导入导航数据
async function importLinks(format) {
    const fileInput = document.getElementById('import-file');
    const statusEl = document.getElementById('import-status');

    if (!fileInput.files || fileInput.files.length === 0) {
        statusEl.textContent = '请先选择文件';
        statusEl.style.color = 'var(--danger-color)';
        return;
    }

    const file = fileInput.files[0];
    try {
        statusEl.textContent = '正在导入...';
        statusEl.style.color = 'var(--text-muted)';

        const text = await file.text();
        const data = JSON.parse(text);

        const response = await api('/api/links/import', {
            method: 'POST',
            body: JSON.stringify({ data, format })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || '导入失败');
        }

        const result = await response.json();
        statusEl.textContent = result.message;
        statusEl.style.color = 'var(--success-color)';
        loadLinks();
        fileInput.value = '';
    } catch (error) {
        statusEl.textContent = '导入失败: ' + error.message;
        statusEl.style.color = 'var(--danger-color)';
    }
}
