/**
 * 个人主页导航系统 - 前端逻辑
 */

// Toast 队列管理
const toastQueue = [];
let toastIdCounter = 0;

// Toast 提示函数（支持队列）
function showToast(message, type = 'info') {
    const toastId = toastIdCounter++;

    // 创建新 toast
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    toast.dataset.toastId = toastId;

    // ARIA 可访问性属性
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    toast.setAttribute('aria-atomic', 'true');

    document.body.appendChild(toast);

    // 添加到队列
    toastQueue.push({ id: toastId, element: toast });

    // 更新所有 toast 的位置
    updateToastPositions();

    // 显示动画
    setTimeout(() => toast.classList.add('show'), 10);

    // 3秒后自动隐藏
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            toast.remove();
            // 从队列中移除
            const index = toastQueue.findIndex(t => t.id === toastId);
            if (index !== -1) {
                toastQueue.splice(index, 1);
                updateToastPositions();
            }
        }, 300);
    }, 3000);
}

// 更新 Toast 位置（垂直堆叠）
function updateToastPositions() {
    let offset = 80; // 初始顶部偏移
    toastQueue.forEach((item, index) => {
        item.element.style.top = `${offset}px`;
        offset += item.element.offsetHeight + 12; // 12px 间距
    });
}

// URL protocol validation to prevent XSS via javascript: protocol
function isSafeUrl(url) {
    if (!url) return false;
    try {
        const parsed = new URL(url);
        return ['http:', 'https:', 'mailto:'].includes(parsed.protocol);
    } catch {
        return false;
    }
}

// 状态管理
const state = {
    token: localStorage.getItem('token') || sessionStorage.getItem('token') || null,
    username: localStorage.getItem('username') || sessionStorage.getItem('username') || null,
    links: { categories: [] },
    isManageMode: false,
    theme: localStorage.getItem('theme') || 'dark',
    settings: { link_size: 'medium', protected_article_paths: [] },
    currentCategory: null  // 当前选中的分类，null 表示默认选中第一个
};

// 确保 token 是有效字符串或 null（防止空字符串）
if (state.token && state.token.trim() === '') {
    state.token = null;
    localStorage.removeItem('token');
    sessionStorage.removeItem('token');
}
if (state.username && state.username.trim() === '') {
    state.username = null;
    localStorage.removeItem('username');
    sessionStorage.removeItem('username');
}

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

    // 获取时区设置，默认为北京时间 (Asia/Shanghai)
    const timezone = state.settings?.timezone || 'Asia/Shanghai';

    try {
        const now = new Date();
        const formatter = new Intl.DateTimeFormat('zh-CN', {
            timeZone: timezone,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
        clock.textContent = formatter.format(now);
    } catch (error) {
        // 如果时区无效，回退到本地时间
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        clock.textContent = `${hours}:${minutes}:${seconds}`;
    }
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
        document.body.classList.add('logged-in');
    } else {
        loginBtn.style.display = 'block';
        logoutBtn.style.display = 'none';
        manageBtn.style.display = 'none';
        usernameDisplay.style.display = 'none';
        document.body.classList.remove('logged-in');
    }
}

// 加载导航链接
async function loadLinks() {
    try {
        const response = await api('/api/v1/links');
        state.links = await response.json();
        renderCategoryNav();
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

// 渲染分类导航栏
function renderCategoryNav() {
    const navContainer = document.querySelector('.category-nav-container');
    if (!navContainer) return;

    // 隐藏骨架屏
    const skeletonNav = document.querySelector('.skeleton-nav');
    if (skeletonNav) {
        skeletonNav.classList.add('hidden');
    }

    navContainer.innerHTML = '';

    // 过滤可见分类（确保 token 是有效字符串）
    const hasValidToken = state.token && state.token.trim().length > 0;
    const visibleCategories = state.links.categories.filter(cat => {
        return !cat.auth_required || hasValidToken;
    });

    // 如果当前分类不可见，选择第一个可见分类
    const currentCategoryVisible = visibleCategories.some(cat => cat.name === state.currentCategory);
    if (!currentCategoryVisible && visibleCategories.length > 0) {
        state.currentCategory = visibleCategories[0].name;
    }

    // 添加各分类按钮
    visibleCategories.forEach((category) => {
        const btn = document.createElement('button');
        btn.className = 'category-nav-item';
        btn.dataset.category = category.name;
        btn.dataset.auth = category.auth_required;

        const textSpan = document.createElement('span');
        textSpan.textContent = category.name;
        btn.appendChild(textSpan);

        if (category.auth_required) {
            const badge = document.createElement('span');
            badge.className = 'auth-badge';
            badge.textContent = '私密';
            btn.appendChild(badge);
        }

        // 添加编辑按钮（仅登录状态且为当前分类）
        if (hasValidToken && state.currentCategory === category.name) {
            const editBtn = document.createElement('button');
            editBtn.className = 'category-edit-icon';
            editBtn.innerHTML = '&#9998;';
            editBtn.title = '编辑分类';
            editBtn.onclick = (e) => {
                e.stopPropagation();
                openEditCategoryModal(category.name, category.auth_required);
            };
            btn.appendChild(editBtn);
        }

        if (state.currentCategory === category.name) {
            btn.classList.add('active');
        }

        navContainer.appendChild(btn);
    });

    // 绑定点击事件
    navContainer.querySelectorAll('.category-nav-item').forEach(btn => {
        btn.addEventListener('click', (e) => {
            // 如果点击的是编辑按钮，不切换分类
            if (e.target.classList.contains('category-edit-icon')) {
                return;
            }
            state.currentCategory = btn.dataset.category;
            renderCategoryNav();
            renderLinks();
        });
    });

    // 如果已登录，初始化分类导航栏的拖拽排序
    if (hasValidToken) {
        initCategoryNavDragAndDrop();
    }
}

// 渲染导航链接
function renderLinks() {
    const container = document.getElementById('links-container');
    if (!container) return;

    // 隐藏骨架屏
    const skeletonLinks = document.querySelector('.skeleton-links');
    if (skeletonLinks) {
        skeletonLinks.classList.add('hidden');
    }

    container.innerHTML = '';

    // 获取链接大小设置
    const linkSize = state.settings.link_size || 'medium';

    // 过滤要显示的分类
    const categoriesToShow = state.links.categories.filter(cat => cat.name === state.currentCategory);

    categoriesToShow.forEach(category => {
        const categoryEl = document.createElement('div');
        categoryEl.className = 'category';

        // 直接创建链接网格，不再显示分类标题
        const linksGrid = document.createElement('div');
        linksGrid.className = `links-grid size-${linkSize}`;

        category.links.forEach(link => {
            const linkEl = document.createElement('a');
            linkEl.href = isSafeUrl(link.url) ? link.url : '#';
            linkEl.target = '_blank';
            linkEl.rel = 'noopener noreferrer';
            linkEl.className = 'link-item';
            linkEl.dataset.id = link.id || '';

            const iconDiv = document.createElement('div');
            iconDiv.className = 'link-icon';

            if (link.icon) {
                const img = document.createElement('img');
                img.src = '/static/icons/' + escapeHtml(link.icon);
                img.alt = link.title || '';
                img.loading = 'lazy';
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
                editLinkBtn.dataset.category = category.name || '';
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

        // 初始化拖拽排序
        initDragAndDrop();
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
async function login(username, password, rememberUsername) {
    try {
        const response = await fetch('/api/v1/auth/login', {
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

        // 始终使用 localStorage 以支持跨标签页登录状态共享
        // Token 有效期为 30 天，由后端控制
        localStorage.setItem('token', state.token);
        localStorage.setItem('username', username);

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

    // 如果当前在私密分类，退出后切换到第一个非私密分类
    const currentCat = state.links.categories.find(cat => cat.name === state.currentCategory);
    if (currentCat && currentCat.auth_required) {
        // 查找第一个不需要认证的分类
        const publicCategory = state.links.categories.find(cat => !cat.auth_required);
        if (publicCategory) {
            state.currentCategory = publicCategory.name;
        } else {
            // 如果所有分类都需要认证，切换到第一个分类
            state.currentCategory = state.links.categories.length > 0 ? state.links.categories[0].name : null;
        }
    }

    updateUI();
    loadLinks();
    loadSettings();
}

// 添加链接
async function addLink(category, title, url, icon) {
    try {
        const response = await api(`/api/v1/links?category_name=${encodeURIComponent(category)}`, {
            method: 'POST',
            body: JSON.stringify({ title, url, icon: icon || null })
        });

        if (!response.ok) {
            throw new Error('添加失败');
        }

        loadLinks();
        closeModal('manage-modal');
        document.getElementById('add-link-form').reset();
        showToast('链接添加成功', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// 更新链接
async function updateLink(id, title, url, icon, category) {
    try {
        const response = await api(`/api/v1/links/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ title, url, icon: icon || null, category: category || null })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const errorMessage = errorData.detail || `更新失败 (HTTP ${response.status})`;
            throw new Error(errorMessage);
        }

        loadLinks();
        closeModal('edit-modal');
        showToast('链接更新成功', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// 删除链接
async function deleteLink(id) {
    if (!confirm('确定要删除这个链接吗？')) return;

    try {
        const response = await api(`/api/v1/links/${id}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('删除失败');
        }

        loadLinks();
        closeModal('edit-modal');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// 添加分类
async function addCategory(name, authRequired) {
    try {
        const response = await api('/api/v1/categories', {
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
        showToast('分类添加成功', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// 删除分类
async function deleteCategory(name) {
    if (!confirm(`确定要删除分类 "${name}" 及其所有链接吗？`)) return;

    try {
        const response = await api(`/api/v1/categories/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('删除失败');
        }

        // 重新加载链接
        await loadLinks();

        // 如果删除的是当前分类，切换到第一个分类
        if (state.currentCategory === name) {
            if (state.links.categories.length > 0) {
                state.currentCategory = state.links.categories[0].name;
            } else {
                state.currentCategory = null;
            }
        }

        renderCategoryNav();
        renderLinks();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// 弹窗控制
function openModal(id) {
    document.getElementById(id).classList.add('active');
    document.body.classList.add('modal-open');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
    document.body.classList.remove('modal-open');
}

function openEditModal(data) {
    document.getElementById('edit-link-id').value = data.id;
    document.getElementById('edit-link-title').value = data.title;
    document.getElementById('edit-link-url').value = data.url;
    document.getElementById('edit-link-icon').value = data.icon;

    // 填充分类选择器
    const categorySelect = document.getElementById('edit-link-category');
    categorySelect.innerHTML = '';
    state.links.categories.forEach(cat => {
        const option = document.createElement('option');
        option.value = cat.name;
        option.textContent = cat.name;
        if (cat.name === data.category) {
            option.selected = true;
        }
        categorySelect.appendChild(option);
    });

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

        const response = await api('/api/v1/favicon/fetch', {
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
        const response = await api(`/api/v1/categories/${encodeURIComponent(oldName)}`, {
            method: 'PUT',
            body: JSON.stringify({ name: newName, auth_required: authRequired })
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || '更新失败');
        }

        // 重新加载链接
        await loadLinks();

        // 自动切换到修改后的分类
        state.currentCategory = newName;
        renderCategoryNav();
        renderLinks();

        closeModal('edit-category-modal');
        showToast('分类更新成功', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// 打开编辑分类弹窗
function openEditCategoryModal(name, authRequired) {
    document.getElementById('edit-category-old-name').value = name;
    document.getElementById('edit-category-name').value = name;
    document.getElementById('edit-category-auth').checked = authRequired;
    openModal('edit-category-modal');
}

// 调整链接顺序
async function reorderLink(id, direction) {
    try {
        const response = await api(`/api/v1/links/${id}/reorder`, {
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
        const response = await fetch('/api/v1/settings');
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

        // 更新 GitHub 链接显示
        const githubEl = document.getElementById('github-link');
        if (githubEl && settings.github_url) {
            githubEl.innerHTML = '';
            const githubLink = document.createElement('a');
            githubLink.href = isSafeUrl(settings.github_url) ? settings.github_url : '#';
            githubLink.target = '_blank';
            githubLink.rel = 'noopener noreferrer';
            githubLink.style.color = 'var(--text-muted)';
            githubLink.style.textDecoration = 'none';

            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.setAttribute('width', '16');
            svg.setAttribute('height', '16');
            svg.setAttribute('viewBox', '0 0 16 16');
            svg.setAttribute('fill', 'currentColor');
            svg.style.verticalAlign = 'text-bottom';

            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('d', 'M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z');

            svg.appendChild(path);
            githubLink.appendChild(svg);
            githubLink.appendChild(document.createTextNode(' GitHub'));
            githubEl.appendChild(githubLink);
        }

        // 重新渲染链接以应用大小设置
        if (state.links.categories.length > 0) {
            renderLinks();
        }

        // 更新时钟以应用时区设置
        updateClock();

        return settings;
    } catch (error) {
        console.error('加载设置失败:', error);
        return {};
    }
}

// 保存站点设置
async function saveSettings(icp, copyright, articlePageTitle, siteTitle, linkSize, protectedPaths, analyticsCode, githubUrl, timezone) {
    try {
        const response = await api('/api/v1/settings', {
            method: 'PUT',
            body: JSON.stringify({
                icp,
                copyright,
                article_page_title: articlePageTitle,
                site_title: siteTitle,
                link_size: linkSize,
                protected_article_paths: protectedPaths,
                analytics_code: analyticsCode,
                github_url: githubUrl,
                timezone: timezone
            })
        });

        if (!response.ok) {
            throw new Error('保存失败');
        }

        loadSettings();
        showToast('站点设置已保存', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// 事件绑定
document.addEventListener('DOMContentLoaded', () => {
    // 初始化
    initTheme();
    updateUI();
    loadLinks();
    loadSettings();

    // 键盘支持：ESC 关闭模态框
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const activeModal = document.querySelector('.modal.active');
            if (activeModal) {
                activeModal.classList.remove('active');
                document.body.classList.remove('modal-open');
            }
        }
    });

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
        const githubUrlInput = document.getElementById('github-url');
        const linkSizeSelect = document.getElementById('link-size');
        const timezoneSelect = document.getElementById('timezone');
        const protectedPathsInput = document.getElementById('protected-paths');
        const analyticsCodeInput = document.getElementById('analytics-code');
        const jwtTokenDisplay = document.getElementById('jwt-token-display');
        if (siteTitleInput) siteTitleInput.value = settings.site_title || '个人主页导航';
        if (articleTitleInput) articleTitleInput.value = settings.article_page_title || '文章';
        if (icpInput) icpInput.value = settings.icp || '';
        if (copyrightInput) copyrightInput.value = settings.copyright || '';
        if (githubUrlInput) githubUrlInput.value = settings.github_url || 'https://github.com/ANIIAN91/nav_system';
        if (linkSizeSelect) linkSizeSelect.value = settings.link_size || 'medium';
        if (timezoneSelect) timezoneSelect.value = settings.timezone || 'Asia/Shanghai';
        if (protectedPathsInput) protectedPathsInput.value = (settings.protected_article_paths || []).join(',');
        if (analyticsCodeInput) analyticsCodeInput.value = settings.analytics_code || '';

        // Security: Hide JWT token by default
        if (jwtTokenDisplay) {
            jwtTokenDisplay.value = '••••••••••••••••••••';
            jwtTokenDisplay.dataset.actualToken = state.token || '';
            jwtTokenDisplay.dataset.revealed = 'false';
        }

        openModal('manage-modal');
    });

    // 复制 Token 按钮
    document.getElementById('copy-token-btn')?.addEventListener('click', () => {
        const tokenInput = document.getElementById('jwt-token-display');
        if (tokenInput) {
            // Copy the actual token, not the masked value
            const actualToken = tokenInput.dataset.actualToken || tokenInput.value;
            if (actualToken && actualToken !== '••••••••••••••••••••') {
                navigator.clipboard.writeText(actualToken).then(() => {
                    showToast('Token 已复制到剪贴板', 'success');
                }).catch(() => {
                    // Fallback for older browsers
                    const tempInput = document.createElement('input');
                    tempInput.value = actualToken;
                    document.body.appendChild(tempInput);
                    tempInput.select();
                    document.execCommand('copy');
                    document.body.removeChild(tempInput);
                    showToast('Token 已复制到剪贴板', 'success');
                });
            }
        }
    });

    // Toggle Token visibility button
    document.getElementById('toggle-token-btn')?.addEventListener('click', () => {
        const tokenInput = document.getElementById('jwt-token-display');
        const toggleBtn = document.getElementById('toggle-token-btn');
        if (tokenInput && toggleBtn) {
            const isRevealed = tokenInput.dataset.revealed === 'true';
            if (isRevealed) {
                // Hide token
                tokenInput.value = '••••••••••••••••••••';
                tokenInput.dataset.revealed = 'false';
                toggleBtn.textContent = '显示 Token';
            } else {
                // Show token
                tokenInput.value = tokenInput.dataset.actualToken || '';
                tokenInput.dataset.revealed = 'true';
                toggleBtn.textContent = '隐藏 Token';
            }
        }
    });

    // 关闭弹窗
    document.querySelectorAll('.modal .close').forEach(btn => {
        btn.addEventListener('click', () => {
            const modal = btn.closest('.modal');
            modal.classList.remove('active');
            document.body.classList.remove('modal-open');
        });
    });

    // 点击弹窗外部关闭
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
                document.body.classList.remove('modal-open');
            }
        });
    });

    // 登录表单
    document.getElementById('login-form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const rememberCredentials = document.getElementById('remember-credentials').checked;
        login(username, password, rememberCredentials);
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
        const category = document.getElementById('edit-link-category').value;
        updateLink(id, title, url, icon, category);
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
        const githubUrl = document.getElementById('github-url').value || 'https://github.com/ANIIAN91/nav_system';
        const linkSize = document.getElementById('link-size').value || 'medium';
        const timezone = document.getElementById('timezone').value || 'Asia/Shanghai';
        const protectedPathsStr = document.getElementById('protected-paths').value || '';
        const protectedPaths = protectedPathsStr.split(',').map(p => p.trim()).filter(p => p);
        const analyticsCode = document.getElementById('analytics-code').value || '';
        saveSettings(icp, copyright, articleTitle, siteTitle, linkSize, protectedPaths, analyticsCode, githubUrl, timezone);
    });

    // 导出导航数据
    document.getElementById('export-links-btn')?.addEventListener('click', async () => {
        try {
            const response = await api('/api/v1/links/export');
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
            showToast('导出失败: ' + error.message, 'error');
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

    // 访问记录相关
    document.getElementById('refresh-visits-btn')?.addEventListener('click', loadVisits);
    document.getElementById('clear-visits-btn')?.addEventListener('click', clearVisits);

    // 更新记录相关
    document.getElementById('refresh-updates-btn')?.addEventListener('click', loadUpdates);
    document.getElementById('clear-updates-btn')?.addEventListener('click', clearUpdates);

    // 标签页切换时加载记录
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.dataset.tab === 'visit-log') {
                loadVisits();
            } else if (btn.dataset.tab === 'update-log') {
                loadUpdates();
            }
        });
    });
});

// 加载访问记录
async function loadVisits() {
    try {
        const response = await api('/api/v1/logs/visits?limit=200');
        if (!response.ok) {
            throw new Error('加载失败');
        }
        const data = await response.json();
        renderVisits(data.visits, data.total);
    } catch (error) {
        console.error('加载访问记录失败:', error);
        document.getElementById('visit-table-body').innerHTML =
            '<tr><td colspan="3" style="padding: 20px; text-align: center; color: var(--danger-color);">加载失败</td></tr>';
    }
}

// 渲染访问记录
function renderVisits(visits, total) {
    document.getElementById('visit-total').textContent = total;
    const tbody = document.getElementById('visit-table-body');

    if (!visits || visits.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" style="padding: 20px; text-align: center; color: var(--text-muted);">暂无访问记录</td></tr>';
        return;
    }

    let html = '';
    visits.forEach(visit => {
        html += `<tr>
            <td style="padding: 8px 10px; border-bottom: 1px solid var(--border-color);">${escapeHtml(visit.time)}</td>
            <td style="padding: 8px 10px; border-bottom: 1px solid var(--border-color);">${escapeHtml(visit.ip)}</td>
            <td style="padding: 8px 10px; border-bottom: 1px solid var(--border-color);">${escapeHtml(visit.path)}</td>
        </tr>`;
    });
    tbody.innerHTML = html;
}

// 清空访问记录
async function clearVisits() {
    if (!confirm('确定要清空所有访问记录吗？')) return;

    try {
        const response = await api('/api/v1/logs/visits', { method: 'DELETE' });
        if (!response.ok) {
            throw new Error('清空失败');
        }
        loadVisits();
        showToast('访问记录已清空', 'success');
    } catch (error) {
        showToast('清空失败: ' + error.message, 'error');
    }
}

// 加载更新记录
async function loadUpdates() {
    try {
        const response = await api('/api/v1/logs/updates?limit=200');
        if (!response.ok) {
            throw new Error('加载失败');
        }
        const data = await response.json();
        renderUpdates(data.updates, data.total);
    } catch (error) {
        console.error('加载更新记录失败:', error);
        document.getElementById('update-table-body').innerHTML =
            '<tr><td colspan="5" style="padding: 20px; text-align: center; color: var(--danger-color);">加载失败</td></tr>';
    }
}

// 渲染更新记录
function renderUpdates(updates, total) {
    document.getElementById('update-total').textContent = total;
    const tbody = document.getElementById('update-table-body');

    if (!updates || updates.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="padding: 20px; text-align: center; color: var(--text-muted);">暂无更新记录</td></tr>';
        return;
    }

    const actionMap = { add: '添加', update: '修改', delete: '删除', move: '移动' };
    const typeMap = { link: '链接', category: '分类', article: '文章', folder: '目录', settings: '设置' };

    let html = '';
    updates.forEach(update => {
        html += `<tr>
            <td style="padding: 8px 10px; border-bottom: 1px solid var(--border-color);">${escapeHtml(update.time)}</td>
            <td style="padding: 8px 10px; border-bottom: 1px solid var(--border-color);">${escapeHtml(actionMap[update.action] || update.action)}</td>
            <td style="padding: 8px 10px; border-bottom: 1px solid var(--border-color);">${escapeHtml(typeMap[update.target_type] || update.target_type)}</td>
            <td style="padding: 8px 10px; border-bottom: 1px solid var(--border-color);">${escapeHtml(update.target_name)}</td>
            <td style="padding: 8px 10px; border-bottom: 1px solid var(--border-color); font-size: 12px; color: var(--text-muted);">${escapeHtml(update.details || '')}</td>
        </tr>`;
    });
    tbody.innerHTML = html;
}

// 清空更新记录
async function clearUpdates() {
    if (!confirm('确定要清空所有更新记录吗？')) return;

    try {
        const response = await api('/api/v1/logs/updates', { method: 'DELETE' });
        if (!response.ok) {
            throw new Error('清空失败');
        }
        loadUpdates();
        showToast('更新记录已清空', 'success');
    } catch (error) {
        showToast('清空失败: ' + error.message, 'error');
    }
}

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

    // Security: Validate file size (max 10MB)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
        statusEl.textContent = '文件过大，最大支持 10MB';
        statusEl.style.color = 'var(--danger-color)';
        showToast('文件过大，最大支持 10MB', 'error');
        return;
    }

    // Security: Validate MIME type
    if (file.type !== 'application/json' && !file.name.endsWith('.json')) {
        statusEl.textContent = '请选择有效的 JSON 文件';
        statusEl.style.color = 'var(--danger-color)';
        showToast('请选择有效的 JSON 文件', 'error');
        return;
    }

    try {
        statusEl.textContent = '正在导入...';
        statusEl.style.color = 'var(--text-muted)';

        const text = await file.text();
        const data = JSON.parse(text);

        const response = await api('/api/v1/links/import', {
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
        showToast('导入成功', 'success');
    } catch (error) {
        statusEl.textContent = '导入失败: ' + error.message;
        statusEl.style.color = 'var(--danger-color)';
        showToast('导入失败: ' + error.message, 'error');
    }
}

// 初始化分类导航栏的拖拽排序
function initCategoryNavDragAndDrop() {
    if (typeof Sortable === 'undefined') {
        console.warn('Sortable.js not loaded');
        return;
    }

    const navContainer = document.querySelector('.category-nav-container');
    if (navContainer) {
        // 销毁旧的 Sortable 实例（如果存在）
        if (navContainer.sortableInstance) {
            navContainer.sortableInstance.destroy();
        }

        // 创建新的 Sortable 实例
        navContainer.sortableInstance = new Sortable(navContainer, {
            animation: 150,
            ghostClass: 'sortable-ghost',
            chosenClass: 'sortable-chosen',
            dragClass: 'sortable-drag',
            handle: '.category-nav-item',
            filter: '.category-edit-icon',
            preventOnFilter: false,
            onEnd: async function(evt) {
                // 获取新的分类排序
                const categoryNames = Array.from(evt.to.children)
                    .map(el => el.dataset.category)
                    .filter(name => name);

                // 调用批量排序 API
                await batchReorderCategories(categoryNames);
            }
        });
    }
}

// 初始化拖拽排序
function initDragAndDrop() {
    if (typeof Sortable === 'undefined') {
        console.warn('Sortable.js not loaded');
        return;
    }

    // 为每个链接网格启用拖拽排序
    document.querySelectorAll('.links-grid').forEach(grid => {
        new Sortable(grid, {
            animation: 150,
            ghostClass: 'sortable-ghost',
            chosenClass: 'sortable-chosen',
            dragClass: 'sortable-drag',
            handle: '.link-item',
            filter: '.edit-btn',
            preventOnFilter: false,
            onEnd: async function(evt) {
                // 获取新的排序
                const linkIds = Array.from(evt.to.children)
                    .map(el => el.dataset.id)
                    .filter(id => id);

                // 调用批量排序 API
                await batchReorderLinks(linkIds);
            }
        });
    });
}

// 批量排序链接
async function batchReorderLinks(linkIds) {
    try {
        const response = await api('/api/v1/links/reorder/batch', {
            method: 'POST',
            body: JSON.stringify({ ids: linkIds })
        });

        if (!response.ok) {
            throw new Error('排序失败');
        }

        // 刷新链接列表
        await loadLinks();
    } catch (error) {
        console.error('批量排序链接失败:', error);
        showToast('排序失败: ' + error.message, 'error');
    }
}

// 批量排序分类
async function batchReorderCategories(categoryNames) {
    try {
        const response = await api('/api/v1/categories/reorder/batch', {
            method: 'POST',
            body: JSON.stringify({ ids: categoryNames })
        });

        if (!response.ok) {
            throw new Error('排序失败');
        }

        // 刷新链接列表
        await loadLinks();
    } catch (error) {
        console.error('批量排序分类失败:', error);
        showToast('排序失败: ' + error.message, 'error');
    }
}
