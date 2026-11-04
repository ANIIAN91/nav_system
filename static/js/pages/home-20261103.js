import {
    apiFetch,
    clearRememberedUsername,
    cleanupLegacyCredentialStorage,
    fetchSessionUser,
    loadSavedUsername,
    revokeSession,
    setRememberedUsername,
    setUnauthorizedHandler,
} from "../core/auth-session-20261103.js";
import { endpoints } from "../core/endpoints.js?v=20261103";
import {
    initArticleManager,
    loadManageArticles,
    loadManageFolders,
    refreshArticleManagerData,
} from "./home/article-manager-20261103.js";
import { initArticleSheet, maybeOpenArticleFromLocation, openArticleSheet } from "./home/article-sheet-20261103.js";
import { closeModal, initModalSystem, openModal } from "../ui/modal.js";
import { initTheme, toggleTheme } from "../ui/theme.js";
import { showToast } from "../ui/toast.js?v=20261103";

// 搜索无匹配时回车使用的搜索引擎
const SEARCH_ENGINE_URL = "https://www.bing.com/search?q=";

const state = {
    authenticated: false,
    username: null,
    editMode: false,
    pendingAdd: null,
    pendingAddFromBookmarklet: false,
    links: { categories: [] },
    articles: [],
    settings: { link_size: "medium", protected_article_paths: [] },
    currentCategory: null,
    currentView: "navigation",
    searchTerm: "",
};

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

async function refreshSession() {
    const username = await fetchSessionUser();
    state.authenticated = Boolean(username);
    state.username = username;
}

function setStatusTone(element, tone = "muted") {
    if (!element) {
        return;
    }
    element.classList.remove("is-muted", "is-success", "is-error");
    element.classList.add(`is-${tone}`);
}

let unauthorizedLogoutPromise = null;

function getSearchTerm() {
    return (state.searchTerm || "").trim().toLowerCase();
}

function articleMatchesSearch(article, searchTerm = getSearchTerm()) {
    if (!searchTerm) return true;
    return [article.title, article.category, article.path]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(searchTerm));
}

function linkMatchesSearch(link, categoryName, searchTerm = getSearchTerm()) {
    if (!searchTerm) return true;
    return [link.title, link.url, categoryName]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(searchTerm));
}

function getFilteredArticles() {
    const searchTerm = getSearchTerm();
    return state.articles.filter((article) => articleMatchesSearch(article, searchTerm));
}

function hasValidToken() {
    return state.authenticated;
}

function getVisibleCategories() {
    return state.links.categories.filter((cat) => !cat.auth_required || hasValidToken());
}

function getRenderableCategories() {
    const searchTerm = getSearchTerm();
    const visibleCategories = getVisibleCategories();

    if (searchTerm) {
        return visibleCategories
            .map((category) => ({
                ...category,
                links: category.links.filter((link) => linkMatchesSearch(link, category.name, searchTerm)),
            }))
            .filter((category) => category.links.length > 0);
    }

    return visibleCategories.filter((cat) => cat.name === state.currentCategory);
}

function formatDisplayUrl(url) {
    if (!url) return "";
    try {
        const normalized = /^[a-zA-Z][a-zA-Z\d+\-.]*:/.test(url) ? url : `https://${url}`;
        const parsed = new URL(normalized);
        const tail = parsed.pathname && parsed.pathname !== "/" ? parsed.pathname.replace(/\/$/, "") : "";
        return `${parsed.host}${tail}`;
    } catch {
        return String(url).replace(/^https?:\/\//, "");
    }
}

function formatArticleDate(timestamp) {
    if (!timestamp) return "";
    const date = new Date(timestamp * 1000);
    if (Number.isNaN(date.getTime())) return "";
    return new Intl.DateTimeFormat("zh-CN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
    }).format(date);
}

function setHomeView(view) {
    state.currentView = view === "navigation" ? "navigation" : "articles";

    const viewMap = {
        articles: document.getElementById("home-articles"),
        navigation: document.getElementById("home-navigation"),
    };

    Object.entries(viewMap).forEach(([key, element]) => {
        if (!element) return;
        element.classList.toggle("hidden", key !== state.currentView);
    });

    document.querySelectorAll("[data-home-view]").forEach((tab) => {
        tab.classList.toggle("active", tab.dataset.homeView === state.currentView);
    });
}

async function api(url, options = {}) {
    const response = await apiFetch(url, options);
    if (response.status === 401) {
        throw new Error('登录已过期');
    }
    return response;
}


setUnauthorizedHandler(async () => {
    if (unauthorizedLogoutPromise) {
        await unauthorizedLogoutPromise;
        return;
    }
    if (!state.authenticated) {
        return;
    }

    unauthorizedLogoutPromise = (async () => {
        clearAuthState();
        updateUI();
        await refreshHomeData({ auth: false });
    })();

    try {
        await unauthorizedLogoutPromise;
    } finally {
        unauthorizedLogoutPromise = null;
    }
});

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
    const editModeBtn = document.getElementById('edit-mode-btn');
    const usernameDisplay = document.getElementById('username-display');

    editModeBtn.hidden = !state.authenticated;
    if (state.authenticated) {
        loginBtn.hidden = true;
        logoutBtn.hidden = false;
        manageBtn.hidden = false;
        usernameDisplay.hidden = false;
        usernameDisplay.textContent = state.username;
        document.body.classList.add('logged-in');
    } else {
        loginBtn.hidden = false;
        logoutBtn.hidden = true;
        manageBtn.hidden = true;
        usernameDisplay.hidden = true;
        usernameDisplay.textContent = '';
        document.body.classList.remove('logged-in');
    }
}

// 加载导航链接
async function loadLinks(options = {}) {
    try {
        const response = await api(endpoints.links.list(), options);
        state.links = await response.json();
        renderCategoryNav();
        renderLinks();
    } catch (error) {
        console.error('加载链接失败:', error);
    }
}

async function loadArticles(options = {}) {
    try {
        const response = await api(endpoints.articles.list(), options);
        const data = await response.json();
        state.articles = data.articles || [];
        renderArticleCards();
        await maybeOpenArticleFromLocation(state.articles);
    } catch (error) {
        console.error("加载文章失败:", error);
        state.articles = [];
        renderArticleCards();
    }
}

async function refreshHomeData(options = {}) {
    await Promise.all([loadLinks(options), loadArticles(options), loadSettings(options)]);
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

    const visibleCategories = getVisibleCategories();

    // 没有可见分类时隐藏分类栏，由链接区给出唯一的空状态提示
    const categoryNav = document.getElementById('category-nav');
    if (categoryNav) {
        categoryNav.hidden = visibleCategories.length === 0;
    }
    if (visibleCategories.length === 0) {
        state.currentCategory = null;
        return;
    }

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

        // 分类默认私有，只标记公开分类
        if (!category.auth_required) {
            const badge = document.createElement('span');
            badge.className = 'auth-badge';
            badge.textContent = '公开';
            btn.appendChild(badge);
        }

        // 添加编辑按钮（仅编辑模式且为当前分类）
        if (state.editMode && state.currentCategory === category.name) {
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

    // 编辑模式下初始化分类导航栏的拖拽排序
    if (state.editMode) {
        initCategoryNavDragAndDrop();
    } else if (navContainer.sortableInstance) {
        navContainer.sortableInstance.destroy();
        navContainer.sortableInstance = null;
    }

}

function renderArticleCards() {
    const container = document.getElementById("article-grid");
    if (!container) return;

    container.innerHTML = "";

    const filteredArticles = getFilteredArticles();

    if (filteredArticles.length === 0) {
        container.innerHTML = `
            <div class="empty-state article-empty">
                <div class="empty-title">暂无可展示的文章</div>
                <div class="empty-copy">当前筛选条件下没有文章，或者文章目录还是空的。</div>
            </div>
        `;
        return;
    }

    filteredArticles.forEach((article) => {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "article-card";
        card.addEventListener("click", () => {
            openArticleSheet(article);
        });

        const category = article.category ? article.category.split("/").filter(Boolean).pop() : "文章";
        const dateLabel = formatArticleDate(article.created_time);
        const metaLabel = article.protected ? "私密" : "公开";

        card.innerHTML = `
            <div class="card-cat">${escapeHtml(category || "文章")}</div>
            <div class="card-title">${escapeHtml(article.title || "未命名文章")}</div>
            <div class="card-foot">
                <div class="card-date">${escapeHtml(dateLabel)}</div>
                <div class="card-read">${escapeHtml(metaLabel)}</div>
            </div>
        `;

        container.appendChild(card);
    });
}

// 渲染导航链接
function renderLinks() {
    const container = document.getElementById('links-container');
    if (!container) return;

    const skeletonLinks = document.querySelector('.skeleton-links');
    if (skeletonLinks) {
        skeletonLinks.classList.add('hidden');
    }

    container.innerHTML = '';

    const linkSize = state.settings.link_size || 'medium';
    const searchTerm = getSearchTerm();
    const categoriesToShow = getRenderableCategories();

    if (categoriesToShow.length === 0) {
        container.appendChild(createLinksEmptyState(searchTerm));
        updateCategorySelect();
        return;
    }

    categoriesToShow.forEach((category) => {
        const categoryEl = document.createElement('div');
        categoryEl.className = 'category';

        if (searchTerm) {
            const label = document.createElement("div");
            label.className = "category-search-label";
            label.textContent = category.name;
            categoryEl.appendChild(label);
        }

        const linksGrid = document.createElement('div');
        linksGrid.className = `links-grid size-${linkSize}`;

        category.links.forEach(link => {
            const linkEl = document.createElement('a');
            linkEl.href = isSafeUrl(link.url) ? link.url : '#';
            linkEl.target = '_blank';
            linkEl.rel = 'noopener noreferrer';
            linkEl.className = 'link-item';
            linkEl.dataset.id = link.id || '';
            linkEl.addEventListener('click', (e) => {
                // 编辑模式下点击卡片不跳转，避免拖拽时误打开
                if (state.editMode) e.preventDefault();
            });

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

            const copyDiv = document.createElement("div");
            copyDiv.className = "link-card-copy";

            const titleSpan = document.createElement('span');
            titleSpan.className = 'link-title';
            setTextContent(titleSpan, link.title);

            const urlSpan = document.createElement("span");
            urlSpan.className = "link-url-preview";
            setTextContent(urlSpan, formatDisplayUrl(link.url));

            copyDiv.appendChild(titleSpan);
            copyDiv.appendChild(urlSpan);

            linkEl.appendChild(iconDiv);
            linkEl.appendChild(copyDiv);

            if (state.editMode) {
                const deleteLinkBtn = document.createElement('button');
                deleteLinkBtn.className = 'delete-btn';
                deleteLinkBtn.title = '删除';
                deleteLinkBtn.innerHTML = '&times;';
                deleteLinkBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    deleteLinkWithUndo(link.id, category.name);
                });
                linkEl.appendChild(deleteLinkBtn);

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

        if (state.authenticated && !searchTerm) {
            linksGrid.appendChild(createQuickAddElement(category.name));
        }

        categoryEl.appendChild(linksGrid);
        container.appendChild(categoryEl);
    });

    if (state.editMode) {
        container.querySelectorAll('.edit-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                openEditModal(btn.dataset);
            });
        });

        // 搜索结果跨分类，不支持排序
        if (!searchTerm) {
            initDragAndDrop();
        }
    }

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
async function login(username, password, rememberUsername, keepLoggedIn) {
    try {
        const response = await api(endpoints.auth.login(), {
            method: 'POST',
            body: JSON.stringify({ username, password, remember: keepLoggedIn }),
            auth: false
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || '登录失败');
        }

        // 会话由服务端写入 HttpOnly Cookie，前端不保存 Token
        state.authenticated = true;
        state.username = username;

        // 安全改进：只记住用户名，不存储密码
        // 密码应由浏览器密码管理器处理
        if (rememberUsername) {
            setRememberedUsername(username);
        } else {
            clearRememberedUsername();
        }

        // 清理旧版本可能存储的密码（安全迁移）
        cleanupLegacyCredentialStorage();

        updateUI();
        closeModal('login-modal');
        await refreshHomeData();
        openPendingAdd();
    } catch (error) {
        document.getElementById('login-error').textContent = error.message;
    }
}

// 加载保存的用户名（不再加载密码）
function loadSavedCredentials() {
    const savedUsername = loadSavedUsername();
    if (savedUsername) {
        document.getElementById('username').value = savedUsername;
        document.getElementById('remember-credentials').checked = true;
    }
}

function clearAuthState() {
    state.authenticated = false;
    state.username = null;
    setEditMode(false);

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
}

// 登出
async function logout({ revoke = true, silent = false } = {}) {
    if (revoke) {
        try {
            await revokeSession();
        } catch (error) {
            console.warn('调用登出接口失败:', error);
        }
    }

    clearAuthState();
    updateUI();
    await refreshHomeData({ auth: false });
    if (!silent) {
        showToast('已登出', 'success');
    }
}

// 添加链接
async function addLink(category, title, url, icon) {
    try {
        const response = await api(endpoints.links.create(category), {
            method: 'POST',
            body: JSON.stringify({ title: title || null, url: normalizeUrlInput(url), icon: icon || null })
        });

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || '添加失败');
        }

        loadLinks();
        closeModal('manage-modal');
        document.getElementById('add-link-form').reset();
        showToast('链接添加成功', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// 补全省略协议的网址，例如 github.com
function normalizeUrlInput(url) {
    const trimmed = (url || '').trim();
    if (!trimmed || /^[a-z][a-z0-9+.-]*:/i.test(trimmed)) {
        return trimmed;
    }
    return 'https://' + trimmed;
}

function openLoginModal() {
    loadSavedCredentials();
    openModal('login-modal');
}

// 链接区的空状态：区分私有模式、尚无分类和搜索无结果
function createLinksEmptyState(searchTerm) {
    const emptyEl = document.createElement('div');
    emptyEl.className = 'empty-state';

    let title = '没有匹配的导航项';
    let copy = '试试切换分类，或者换一个搜索词；按回车可用 Bing 搜索。';
    let withLogin = false;
    if (!searchTerm && getVisibleCategories().length === 0) {
        if (state.authenticated) {
            title = '还没有分类';
            copy = '点击右上角「管理」添加分类，或导入浏览器书签。';
        } else if (state.settings.private_mode !== false) {
            title = '私有模式已开启';
            copy = '登录后查看导航。';
            withLogin = true;
        } else {
            title = '暂无公开链接';
            copy = '登录后可查看全部导航。';
            withLogin = true;
        }
    }

    const titleEl = document.createElement('div');
    titleEl.className = 'empty-title';
    titleEl.textContent = title;
    const copyEl = document.createElement('div');
    copyEl.className = 'empty-copy';
    copyEl.textContent = copy;
    emptyEl.appendChild(titleEl);
    emptyEl.appendChild(copyEl);

    if (withLogin) {
        const loginBtn = document.createElement('button');
        loginBtn.type = 'button';
        loginBtn.className = 'btn btn-secondary empty-action';
        loginBtn.textContent = '登录';
        loginBtn.addEventListener('click', openLoginModal);
        emptyEl.appendChild(loginBtn);
    }
    return emptyEl;
}

// 分类末尾的“快速添加”卡片
function createQuickAddElement(categoryName) {
    const addEl = document.createElement('button');
    addEl.type = 'button';
    addEl.className = 'link-item link-add';
    addEl.title = `添加链接到「${categoryName}」`;

    const iconDiv = document.createElement('div');
    iconDiv.className = 'link-icon';
    iconDiv.textContent = '+';

    const copyDiv = document.createElement('div');
    copyDiv.className = 'link-card-copy';
    const titleSpan = document.createElement('span');
    titleSpan.className = 'link-title';
    titleSpan.textContent = '添加链接';
    const hintSpan = document.createElement('span');
    hintSpan.className = 'link-url-preview';
    hintSpan.textContent = '粘贴网址即可';
    copyDiv.appendChild(titleSpan);
    copyDiv.appendChild(hintSpan);

    addEl.appendChild(iconDiv);
    addEl.appendChild(copyDiv);
    addEl.addEventListener('click', () => openQuickAddModal(categoryName));
    return addEl;
}

function openQuickAddModal(categoryName, prefill = {}) {
    document.getElementById('quick-add-form').reset();
    const categorySelect = document.getElementById('quick-add-category');
    categorySelect.innerHTML = '';
    state.links.categories.forEach(cat => {
        const option = document.createElement('option');
        option.value = cat.name;
        option.textContent = cat.name;
        categorySelect.appendChild(option);
    });
    if (categoryName) categorySelect.value = categoryName;
    document.getElementById('quick-add-url').value = prefill.url || '';
    document.getElementById('quick-add-title').value = prefill.title || '';
    openModal('quick-add-modal');
    document.getElementById('quick-add-url').focus();
}

// 快速添加：只需网址，标题和图标由服务端自动获取
async function quickAddLink(category, url, title) {
    const submitBtn = document.getElementById('quick-add-submit');
    submitBtn.disabled = true;
    submitBtn.textContent = title ? '添加中...' : '正在获取标题和图标...';
    try {
        const response = await api(endpoints.links.create(category), {
            method: 'POST',
            body: JSON.stringify({ title: title || null, url: normalizeUrlInput(url), icon: null, fetch_icon: true })
        });
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || '添加失败');
        }
        const data = await response.json();
        closeModal('quick-add-modal');
        state.currentCategory = category;
        await loadLinks();
        showToast(`已添加「${data.link.title}」`, 'success');
        // 由书签小工具打开的小窗口，添加完成后自动关闭
        if (state.pendingAddFromBookmarklet && window.opener) {
            window.setTimeout(() => window.close(), 800);
        }
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '添加';
    }
}

// 书签小工具：/?add=<url>&title=<title>
function readPendingAdd() {
    const params = new URLSearchParams(window.location.search);
    const url = params.get('add');
    if (!url) return null;
    const title = (params.get('title') || '').slice(0, 200);
    // 只移除书签小工具的参数，保留 ?article= 等其他参数
    params.delete('add');
    params.delete('title');
    const query = params.toString();
    window.history.replaceState(null, '', window.location.pathname + (query ? `?${query}` : ''));
    return { url, title };
}

function openPendingAdd() {
    if (!state.pendingAdd) return;
    const prefill = state.pendingAdd;
    state.pendingAdd = null;
    if (state.links.categories.length === 0) {
        showToast('请先在「管理」中添加一个分类', 'error');
        return;
    }
    openQuickAddModal(state.currentCategory, prefill);
}

function initBookmarklet() {
    const bookmarklet = document.getElementById('bookmarklet-link');
    if (!bookmarklet) return;
    const addUrl = `${window.location.origin}/?add=`;
    bookmarklet.href = `javascript:(()=>{window.open('${addUrl}'+encodeURIComponent(location.href)+'&title='+encodeURIComponent(document.title),'nav_add','width=520,height=640')})()`;
    bookmarklet.addEventListener('click', (e) => {
        e.preventDefault();
        showToast('请把按钮拖到浏览器书签栏后再使用', 'info');
    });
}

// 编辑模式：显示编辑/删除按钮并启用拖拽排序
function setEditMode(enabled) {
    state.editMode = enabled;
    document.body.classList.toggle('edit-mode', enabled);
    const editModeBtn = document.getElementById('edit-mode-btn');
    if (editModeBtn) {
        editModeBtn.textContent = enabled ? '完成' : '编辑';
        editModeBtn.classList.toggle('is-active', enabled);
    }
}

// 删除链接，并在提示中提供撤销
async function deleteLinkWithUndo(linkId, categoryName) {
    const category = state.links.categories.find(cat => cat.name === categoryName);
    const link = category?.links.find(item => item.id === linkId);
    if (!link) return;
    const orderBefore = category.links.map(item => item.id);

    try {
        const response = await api(endpoints.links.detail(linkId), { method: 'DELETE' });
        if (!response.ok) {
            throw new Error('删除失败');
        }
        await loadLinks();
        showToast(`已删除「${link.title}」`, 'info', 6000, {
            label: '撤销',
            onClick: () => restoreDeletedLink(link, categoryName, orderBefore),
        });
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// 撤销删除：重新创建链接并恢复原来的位置
async function restoreDeletedLink(link, categoryName, orderBefore) {
    try {
        const response = await api(endpoints.links.create(categoryName), {
            method: 'POST',
            body: JSON.stringify({ title: link.title, url: link.url, icon: link.icon || null })
        });
        if (!response.ok) {
            throw new Error('撤销失败');
        }
        const data = await response.json();
        await loadLinks();

        const category = state.links.categories.find(cat => cat.name === categoryName);
        const currentIds = category ? category.links.map(item => item.id) : [];
        const restoredOrder = orderBefore
            .map(id => (id === link.id ? data.link.id : id))
            .filter(id => currentIds.includes(id));
        currentIds.forEach(id => {
            if (!restoredOrder.includes(id)) restoredOrder.push(id);
        });
        if (restoredOrder.length > 1) {
            await batchReorderLinks(restoredOrder);
        }
        showToast(`已恢复「${link.title}」`, 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// 解析浏览器导出的书签 HTML（Netscape Bookmark 格式），按所在文件夹分类
function parseBookmarksHtml(html) {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const categories = new Map();
    doc.querySelectorAll('a[href]').forEach(anchor => {
        const url = (anchor.getAttribute('href') || '').trim();
        if (!/^https?:\/\//i.test(url)) return;
        const folder = anchor.closest('dl')?.parentElement?.querySelector(':scope > h3');
        const rawName = (folder?.textContent || '').trim().replace(/[\/\\]/g, '-');
        const name = rawName.slice(0, 100) || '书签';
        if (!categories.has(name)) categories.set(name, []);
        categories.get(name).push({
            title: (anchor.textContent || '').trim().slice(0, 200) || url,
            url,
        });
    });
    return {
        categories: [...categories].map(([name, links]) => ({ name, auth_required: true, links })),
    };
}

// 搜索框回车：打开第一个结果；导航视图无匹配时使用搜索引擎
function openFirstSearchResult() {
    const term = (state.searchTerm || '').trim();
    if (!term) return;
    if (state.currentView === 'articles') {
        const [article] = getFilteredArticles();
        if (article) openArticleSheet(article);
        return;
    }
    const [category] = getRenderableCategories();
    const link = category?.links[0];
    if (link) {
        if (isSafeUrl(link.url)) window.open(link.url, '_blank', 'noopener');
        return;
    }
    window.open(SEARCH_ENGINE_URL + encodeURIComponent(term), '_blank', 'noopener');
}

// 更新链接
async function updateLink(id, title, url, icon, category) {
    try {
        const response = await api(endpoints.links.detail(id), {
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
        const response = await api(endpoints.links.detail(id), {
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
        const response = await api(endpoints.categories.create(), {
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
        const response = await api(endpoints.categories.detail(name), {
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

function handleManageTabChange(tabId) {
    switchTab(tabId);
    if (tabId === 'visit-log') {
        loadVisits();
    } else if (tabId === 'article-library') {
        loadManageArticles();
    } else if (tabId === 'folder-library') {
        loadManageFolders();
    } else if (tabId === 'update-log') {
        loadUpdates();
    }
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
        setStatusTone(statusEl, 'muted');

        const response = await api(endpoints.favicon.fetch(), {
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
            setStatusTone(statusEl, 'success');
        } else {
            statusEl.textContent = data.message || '未找到图标';
            setStatusTone(statusEl, 'error');
        }
    } catch (error) {
        statusEl.textContent = '获取失败: ' + error.message;
        setStatusTone(statusEl, 'error');
    }
}

// 更新分类
async function updateCategory(oldName, newName, authRequired) {
    try {
        const response = await api(endpoints.categories.detail(oldName), {
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
        const response = await api(endpoints.links.reorder(id), {
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
async function loadSettings(options = {}) {
    try {
        const response = await api(endpoints.settings.get(), options);
        const settings = await response.json();

        // 保存到状态
        state.settings = settings;

        // 更新网站标题
        if (settings.site_title) {
            document.title = settings.site_title;
        }

        const siteBrandEl = document.getElementById("site-brand");
        if (siteBrandEl) {
            siteBrandEl.textContent = settings.site_title || "ANIAN";
        }

        const articlesViewLabel = document.getElementById("articles-view-label");
        if (articlesViewLabel) {
            articlesViewLabel.textContent = settings.article_page_title || "文章";
        }

        const homeArticlesTitle = document.getElementById("home-articles-title");
        if (homeArticlesTitle) {
            homeArticlesTitle.textContent = settings.article_page_title || "文章";
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
            githubLink.className = 'footer-link';
            githubLink.href = isSafeUrl(settings.github_url) ? settings.github_url : '#';
            githubLink.target = '_blank';
            githubLink.rel = 'noopener noreferrer';

            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.setAttribute('width', '16');
            svg.setAttribute('height', '16');
            svg.setAttribute('viewBox', '0 0 16 16');
            svg.setAttribute('fill', 'currentColor');
            svg.classList.add('footer-link-icon');

            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('d', 'M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z');

            svg.appendChild(path);
            githubLink.appendChild(svg);
            githubLink.appendChild(document.createTextNode(' GitHub'));
            githubEl.appendChild(githubLink);
        }

        // 重新渲染链接以应用大小设置和私有模式提示
        renderLinks();

        // 更新时钟以应用时区设置
        updateClock();

        return settings;
    } catch (error) {
        console.error('加载设置失败:', error);
        return {};
    }
}

async function loadAdminSettings() {
    try {
        const response = await api(endpoints.settings.admin());
        const settings = await response.json();
        state.settings = { ...state.settings, ...settings };
        return settings;
    } catch (error) {
        console.error('加载管理设置失败:', error);
        showToast('加载管理设置失败: ' + error.message, 'error');
        return null;
    }
}

// 保存站点设置
async function saveSettings(icp, copyright, articlePageTitle, siteTitle, linkSize, protectedPaths, githubUrl, timezone, privateMode) {
    try {
        const response = await api(endpoints.settings.update(), {
            method: 'PUT',
            body: JSON.stringify({
                icp,
                copyright,
                article_page_title: articlePageTitle,
                site_title: siteTitle,
                link_size: linkSize,
                protected_article_paths: protectedPaths,
                github_url: githubUrl,
                timezone: timezone,
                private_mode: privateMode
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
document.addEventListener('DOMContentLoaded', async () => {
    // 初始化
    initTheme();
    initModalSystem();
    initArticleSheet();
    initArticleManager({
        refreshHomepage: loadArticles,
        openArticleSheet,
    });
    setHomeView(state.currentView);
    // 清理旧版本存储在浏览器中的 Token 和密码
    cleanupLegacyCredentialStorage();
    state.pendingAdd = readPendingAdd();
    state.pendingAddFromBookmarklet = Boolean(state.pendingAdd);
    initBookmarklet();
    await refreshSession();
    updateUI();
    await refreshHomeData();
    if (state.pendingAdd) {
        if (state.authenticated) {
            openPendingAdd();
        } else {
            openLoginModal();
        }
    }

    // 编辑模式按钮
    document.getElementById('edit-mode-btn')?.addEventListener('click', () => {
        setEditMode(!state.editMode);
        renderCategoryNav();
        renderLinks();
    });

    document.querySelectorAll("[data-home-view]").forEach((tab) => {
        tab.addEventListener("click", () => {
            setHomeView(tab.dataset.homeView);
        });
    });

    const searchInput = document.getElementById("home-search-input");
    if (searchInput) {
        searchInput.addEventListener("input", (event) => {
            state.searchTerm = event.target.value || "";
            renderArticleCards();
            renderLinks();
        });
        searchInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                openFirstSearchResult();
            } else if (event.key === "Escape") {
                searchInput.value = "";
                state.searchTerm = "";
                renderArticleCards();
                renderLinks();
                searchInput.blur();
            }
        });
    }

    document.addEventListener("keydown", (event) => {
        const activeTag = document.activeElement?.tagName;
        const isTypingContext = ["INPUT", "TEXTAREA", "SELECT"].includes(activeTag);

        if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
            event.preventDefault();
            searchInput?.focus();
            searchInput?.select();
            return;
        }

        if (!isTypingContext && event.key === "/") {
            event.preventDefault();
            searchInput?.focus();
        }
    });

    // 登录按钮
    document.getElementById('login-btn')?.addEventListener('click', openLoginModal);

    // 登出按钮
    document.getElementById('logout-btn')?.addEventListener('click', () => logout());

    // 管理按钮
    document.getElementById('manage-btn')?.addEventListener('click', async () => {
        // 加载站点设置到表单
        const settings = await loadAdminSettings();
        if (!settings) {
            return;
        }
        await refreshArticleManagerData();
        const siteTitleInput = document.getElementById('site-title');
        const articleTitleInput = document.getElementById('footer-article-title');
        const icpInput = document.getElementById('footer-icp');
        const copyrightInput = document.getElementById('footer-copyright');
        const githubUrlInput = document.getElementById('github-url');
        const linkSizeSelect = document.getElementById('link-size');
        const timezoneSelect = document.getElementById('timezone');
        const protectedPathsInput = document.getElementById('protected-paths');
        const privateModeInput = document.getElementById('private-mode');
        const apiTokenDisplay = document.getElementById('api-token-display');
        if (siteTitleInput) siteTitleInput.value = settings.site_title || '个人主页导航';
        if (articleTitleInput) articleTitleInput.value = settings.article_page_title || '文章';
        if (icpInput) icpInput.value = settings.icp || '';
        if (copyrightInput) copyrightInput.value = settings.copyright || '';
        if (githubUrlInput) githubUrlInput.value = settings.github_url || 'https://github.com/ANIIAN91/nav_system';
        if (linkSizeSelect) linkSizeSelect.value = settings.link_size || 'medium';
        if (timezoneSelect) timezoneSelect.value = settings.timezone || 'Asia/Shanghai';
        if (protectedPathsInput) protectedPathsInput.value = (settings.protected_article_paths || []).join(',');
        if (privateModeInput) privateModeInput.checked = settings.private_mode !== false;
        if (apiTokenDisplay) apiTokenDisplay.value = '';

        openModal('manage-modal');
    });

    // 生成 API Token（用于 Obsidian 插件或脚本）
    document.getElementById('generate-token-btn')?.addEventListener('click', async () => {
        try {
            const response = await api(endpoints.auth.apiToken(), { method: 'POST' });
            if (!response.ok) throw new Error('生成失败');
            const data = await response.json();
            document.getElementById('api-token-display').value = data.access_token;
            showToast('已生成新的 API Token', 'success');
        } catch (error) {
            showToast(error.message, 'error');
        }
    });

    // 复制 Token 按钮
    document.getElementById('copy-token-btn')?.addEventListener('click', () => {
        const token = document.getElementById('api-token-display')?.value;
        if (!token) {
            showToast('请先生成 Token', 'error');
            return;
        }
        navigator.clipboard.writeText(token).then(() => {
            showToast('Token 已复制到剪贴板', 'success');
        }).catch(() => {
            showToast('复制失败，请手动选择复制', 'error');
        });
    });

    // 登录表单
    document.getElementById('login-form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const rememberCredentials = document.getElementById('remember-credentials').checked;
        const keepLoggedIn = document.getElementById('keep-logged-in').checked;
        login(username, password, rememberCredentials, keepLoggedIn);
    });

    // 快速添加表单
    document.getElementById('quick-add-form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        const category = document.getElementById('quick-add-category').value;
        const url = document.getElementById('quick-add-url').value;
        const title = document.getElementById('quick-add-title').value.trim();
        quickAddLink(category, url, title);
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
            handleManageTabChange(btn.dataset.tab);
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
        const privateMode = document.getElementById('private-mode').checked;
        saveSettings(icp, copyright, articleTitle, siteTitle, linkSize, protectedPaths, githubUrl, timezone, privateMode);
    });

    // 导出导航数据
    document.getElementById('export-links-btn')?.addEventListener('click', async () => {
        try {
            const response = await api(endpoints.links.exportData());
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

    // 导入浏览器书签（HTML 格式）
    document.getElementById('import-bookmarks-btn')?.addEventListener('click', () => {
        importLinks('bookmarks');
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

});

// 加载访问记录
async function loadVisits() {
    try {
        const response = await api(endpoints.logs.visits(200));
        if (!response.ok) {
            throw new Error('加载失败');
        }
        const data = await response.json();
        renderVisits(data.visits, data.total);
    } catch (error) {
        console.error('加载访问记录失败:', error);
        document.getElementById('visit-table-body').innerHTML =
            '<tr class="log-error-row"><td colspan="3">加载失败</td></tr>';
    }
}

// 渲染访问记录
function renderVisits(visits, total) {
    document.getElementById('visit-total').textContent = total;
    const tbody = document.getElementById('visit-table-body');

    if (!visits || visits.length === 0) {
        tbody.innerHTML = '<tr class="log-empty-row"><td colspan="3">暂无访问记录</td></tr>';
        return;
    }

    tbody.innerHTML = visits.map((visit) => `
        <tr>
            <td>${escapeHtml(visit.time)}</td>
            <td>${escapeHtml(visit.ip)}</td>
            <td>${escapeHtml(visit.path)}</td>
        </tr>
    `).join('');
}

// 清空访问记录
async function clearVisits() {
    if (!confirm('确定要清空所有访问记录吗？')) return;

    try {
        const response = await api(endpoints.logs.clearVisits(), { method: 'DELETE' });
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
        const response = await api(endpoints.logs.updates(200));
        if (!response.ok) {
            throw new Error('加载失败');
        }
        const data = await response.json();
        renderUpdates(data.updates, data.total);
    } catch (error) {
        console.error('加载更新记录失败:', error);
        document.getElementById('update-table-body').innerHTML =
            '<tr class="log-error-row"><td colspan="5">加载失败</td></tr>';
    }
}

// 渲染更新记录
function renderUpdates(updates, total) {
    document.getElementById('update-total').textContent = total;
    const tbody = document.getElementById('update-table-body');

    if (!updates || updates.length === 0) {
        tbody.innerHTML = '<tr class="log-empty-row"><td colspan="5">暂无更新记录</td></tr>';
        return;
    }

    const actionMap = { add: '添加', update: '修改', delete: '删除', move: '移动' };
    const typeMap = { link: '链接', category: '分类', article: '文章', folder: '目录', settings: '设置' };

    tbody.innerHTML = updates.map((update) => `
        <tr>
            <td>${escapeHtml(update.time)}</td>
            <td>${escapeHtml(actionMap[update.action] || update.action)}</td>
            <td>${escapeHtml(typeMap[update.target_type] || update.target_type)}</td>
            <td>${escapeHtml(update.target_name)}</td>
            <td class="detail-cell">${escapeHtml(update.details || '')}</td>
        </tr>
    `).join('');
}

// 清空更新记录
async function clearUpdates() {
    if (!confirm('确定要清空所有更新记录吗？')) return;

    try {
        const response = await api(endpoints.logs.clearUpdates(), { method: 'DELETE' });
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
        setStatusTone(statusEl, 'error');
        return;
    }

    const file = fileInput.files[0];

    // Security: Validate file size (max 10MB)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
        statusEl.textContent = '文件过大，最大支持 10MB';
        setStatusTone(statusEl, 'error');
        showToast('文件过大，最大支持 10MB', 'error');
        return;
    }

    // Security: Validate file type
    const isBookmarks = format === 'bookmarks';
    const validType = isBookmarks
        ? /\.html?$/i.test(file.name)
        : file.type === 'application/json' || file.name.endsWith('.json');
    if (!validType) {
        const message = isBookmarks ? '请选择浏览器导出的书签 HTML 文件' : '请选择有效的 JSON 文件';
        statusEl.textContent = message;
        setStatusTone(statusEl, 'error');
        showToast(message, 'error');
        return;
    }

    try {
        statusEl.textContent = '正在导入...';
        setStatusTone(statusEl, 'muted');

        const text = await file.text();
        const data = isBookmarks ? parseBookmarksHtml(text) : JSON.parse(text);
        if (isBookmarks && data.categories.length === 0) {
            throw new Error('文件中没有找到 http/https 书签');
        }

        const response = await api(endpoints.links.importData(), {
            method: 'POST',
            // 书签转换为原生格式导入，分类默认私有
            body: JSON.stringify({ data, format: isBookmarks ? 'native' : format })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || '导入失败');
        }

        const result = await response.json();
        statusEl.textContent = result.message;
        setStatusTone(statusEl, 'success');
        loadLinks();
        fileInput.value = '';
        showToast('导入成功', 'success');
    } catch (error) {
        statusEl.textContent = '导入失败: ' + error.message;
        setStatusTone(statusEl, 'error');
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
            draggable: '.link-item:not(.link-add)',
            filter: '.edit-btn, .delete-btn',
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
        const response = await api(endpoints.links.batchReorder(), {
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
        const response = await api(endpoints.categories.batchReorder(), {
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
