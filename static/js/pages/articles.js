import { isAuthenticated } from "../core/auth.js";
import { endpoints } from "../core/endpoints.js";
import { apiFetch, parseJson } from "../core/http.js";
import { articlePageState as state } from "../core/state.js";
import { closeModal, initModalSystem, openModal } from "../ui/modal.js";
import { initTheme, toggleTheme } from "../ui/theme.js";
import { showToast } from "../ui/toast.js";

function escapeHtml(text) {
    if (text === null || text === undefined) {
        return "";
    }
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function updateUI() {
    if (isAuthenticated()) {
        const manageButton = document.getElementById("manage-folders-btn");
        if (manageButton) {
            manageButton.style.display = "block";
        }
    }
}

async function loadSettings() {
    try {
        const response = await apiFetch(endpoints.settings.get(), { auth: false });
        const settings = await parseJson(response, "加载设置失败");
        state.settings = settings;

        const titleEl = document.getElementById("page-title");
        if (titleEl && settings.article_page_title) {
            titleEl.textContent = settings.article_page_title;
            document.title = `${settings.article_page_title} - 个人主页`;
        }

        const icpEl = document.getElementById("icp-info");
        if (icpEl) {
            let footerText = "";
            if (settings.copyright) {
                footerText += settings.copyright;
            }
            if (settings.icp) {
                footerText += footerText ? ` | ${settings.icp}` : settings.icp;
            }
            icpEl.textContent = footerText;
        }
    } catch (error) {
        console.error("加载设置失败:", error);
    }
}

async function loadArticles() {
    try {
        const response = await apiFetch(endpoints.articles.list());
        const data = await parseJson(response, "加载文章列表失败");
        state.articles = data.articles || [];
        renderArticleTree(state.articles);
    } catch (error) {
        console.error("加载文章列表失败:", error);
    }
}

function renderArticleTree(articles) {
    const tree = document.getElementById("articles-tree");
    const categories = {};
    for (const article of articles) {
        const category = article.category || "未分类";
        if (!categories[category]) {
            categories[category] = [];
        }
        categories[category].push(article);
    }

    const collapsedState = JSON.parse(localStorage.getItem("articleCollapsed") || "{}");
    let html = "";
    for (const [category, items] of Object.entries(categories)) {
        const isCollapsed = collapsedState[category] === true;
        html += `<div class="article-category ${isCollapsed ? "collapsed" : ""}" data-category="${escapeHtml(category)}">
            <div class="article-category-header">
                <h4><span class="collapse-icon">&#9660;</span> ${escapeHtml(category)}</h4>
            </div>
            <ul>`;
        for (const item of items) {
            html += `<li><a href="#" data-path="${escapeHtml(item.path)}">${escapeHtml(item.title)}</a></li>`;
        }
        html += "</ul></div>";
    }

    tree.innerHTML = html || '<p class="no-articles">暂无文章</p>';

    tree.querySelectorAll(".article-category-header").forEach((header) => {
        header.addEventListener("click", () => {
            const category = header.closest(".article-category");
            category.classList.toggle("collapsed");
            const categoryName = category.dataset.category;
            const nextState = JSON.parse(localStorage.getItem("articleCollapsed") || "{}");
            nextState[categoryName] = category.classList.contains("collapsed");
            localStorage.setItem("articleCollapsed", JSON.stringify(nextState));
        });
    });

    tree.querySelectorAll("a[data-path]").forEach((link) => {
        link.addEventListener("click", async (event) => {
            event.preventDefault();
            await loadArticle(link.dataset.path);
            tree.querySelectorAll("a").forEach((item) => item.classList.remove("active"));
            link.classList.add("active");
        });
    });
}

async function loadArticle(path) {
    try {
        const response = await apiFetch(endpoints.articles.detail(path));
        const data = await parseJson(response, "文章不存在");
        const sanitizedHtml = window.DOMPurify ? window.DOMPurify.sanitize(data.html) : data.html;
        document.getElementById("article-body").innerHTML = sanitizedHtml;
        state.currentArticlePath = path;
        state.currentArticleContent = data.content;
        if (isAuthenticated()) {
            document.getElementById("article-toolbar").style.display = "block";
        }
    } catch (error) {
        document.getElementById("article-body").innerHTML = `<p class="error">加载失败: ${escapeHtml(error.message)}</p>`;
        state.currentArticlePath = null;
        state.currentArticleContent = null;
        document.getElementById("article-toolbar").style.display = "none";
    }
}

function openEditArticleModal() {
    if (!state.currentArticlePath || !state.currentArticleContent) {
        showToast("请先选择一篇文章");
        return;
    }
    document.getElementById("edit-article-path").value = state.currentArticlePath;
    document.getElementById("edit-article-content").value = state.currentArticleContent;
    openModal("edit-article-modal");
}

async function saveArticle(path, content) {
    try {
        const response = await apiFetch(endpoints.articles.update(path), {
            method: "PUT",
            json: { content },
        });
        await parseJson(response, "保存失败");
        closeModal("edit-article-modal");
        await loadArticle(path);
        showToast("文章已保存");
    } catch (error) {
        showToast(`保存失败: ${error.message}`);
    }
}

async function deleteArticle() {
    if (!state.currentArticlePath) {
        showToast("请先选择一篇文章");
        return;
    }
    if (!window.confirm("确定要删除这篇文章吗？此操作不可恢复。")) {
        return;
    }

    try {
        const response = await apiFetch(endpoints.articles.remove(state.currentArticlePath), {
            method: "DELETE",
        });
        await parseJson(response, "删除失败");
        state.currentArticlePath = null;
        state.currentArticleContent = null;
        document.getElementById("article-body").innerHTML = '<p class="placeholder">文章已删除</p>';
        document.getElementById("article-toolbar").style.display = "none";
        await loadArticles();
        showToast("文章已删除");
    } catch (error) {
        showToast(`删除失败: ${error.message}`);
    }
}

async function loadFolders() {
    try {
        const response = await apiFetch(endpoints.folders.list());
        const data = await parseJson(response, "加载失败");
        renderFolders(data.folders || []);
    } catch (error) {
        document.getElementById("folder-list").innerHTML = '<p style="color: var(--danger-color);">加载失败</p>';
    }
}

function renderFolders(folders) {
    const container = document.getElementById("folder-list");
    if (!folders.length) {
        container.innerHTML = '<p style="color: var(--text-muted);">暂无目录</p>';
        return;
    }

    container.innerHTML = folders
        .map(
            (folder) => `<div style="display:flex;justify-content:space-between;align-items:center;padding:10px;border-bottom:1px solid var(--border-color);">
                <span>${escapeHtml(folder.name)} <small style="color: var(--text-muted);">(${folder.article_count} 篇)</small></span>
                <button class="btn btn-secondary edit-folder-btn" data-name="${escapeHtml(folder.name)}" style="padding:5px 10px;font-size:12px;">编辑</button>
            </div>`
        )
        .join("");

    container.querySelectorAll(".edit-folder-btn").forEach((button) => {
        button.addEventListener("click", () => openEditFolderModal(button.dataset.name));
    });
}

async function createFolder(name) {
    try {
        const response = await apiFetch(endpoints.folders.create(name), { method: "POST" });
        await parseJson(response, "创建失败");
        document.getElementById("new-folder-name").value = "";
        await Promise.all([loadFolders(), loadArticles()]);
        showToast("目录创建成功");
    } catch (error) {
        showToast(`创建失败: ${error.message}`);
    }
}

function openEditFolderModal(name) {
    document.getElementById("edit-folder-old-name").value = name;
    document.getElementById("edit-folder-name").value = name;
    openModal("edit-folder-modal");
}

async function renameFolder(oldName, newName) {
    try {
        const response = await apiFetch(endpoints.folders.rename(oldName), {
            method: "PUT",
            json: { new_name: newName },
        });
        await parseJson(response, "重命名失败");
        closeModal("edit-folder-modal");
        await Promise.all([loadFolders(), loadArticles()]);
        showToast("目录重命名成功");
    } catch (error) {
        showToast(`重命名失败: ${error.message}`);
    }
}

async function deleteFolder(name) {
    if (!window.confirm(`确定要删除目录 "${name}" 及其中的所有文章吗？此操作不可恢复。`)) {
        return;
    }

    try {
        const response = await apiFetch(endpoints.folders.remove(name), { method: "DELETE" });
        await parseJson(response, "删除失败");
        closeModal("edit-folder-modal");
        await Promise.all([loadFolders(), loadArticles()]);
        showToast("目录已删除");
    } catch (error) {
        showToast(`删除失败: ${error.message}`);
    }
}

function checkUrlPath() {
    const path = window.location.pathname.replace("/articles/", "").replace("/articles", "");
    if (path && path !== "/") {
        loadArticle(path);
    }
}

function initBackToTop() {
    const backToTopButton = document.getElementById("back-to-top");
    if (!backToTopButton) {
        return;
    }
    window.addEventListener("scroll", () => {
        backToTopButton.classList.toggle("visible", window.scrollY > 300);
    });
    backToTopButton.addEventListener("click", () => {
        window.scrollTo({ top: 0, behavior: "smooth" });
    });
}

function bindEvents() {
    document.getElementById("theme-toggle")?.addEventListener("click", toggleTheme);
    document.getElementById("edit-article-btn")?.addEventListener("click", openEditArticleModal);
    document.getElementById("delete-article-btn")?.addEventListener("click", deleteArticle);
    document.getElementById("manage-folders-btn")?.addEventListener("click", async () => {
        await loadFolders();
        openModal("folder-modal");
    });
    document.getElementById("create-folder-btn")?.addEventListener("click", () => {
        const name = document.getElementById("new-folder-name").value.trim();
        if (!name) {
            showToast("请输入目录名称");
            return;
        }
        createFolder(name);
    });
    document.getElementById("edit-article-form")?.addEventListener("submit", (event) => {
        event.preventDefault();
        saveArticle(
            document.getElementById("edit-article-path").value,
            document.getElementById("edit-article-content").value
        );
    });
    document.getElementById("edit-folder-form")?.addEventListener("submit", (event) => {
        event.preventDefault();
        const oldName = document.getElementById("edit-folder-old-name").value;
        const newName = document.getElementById("edit-folder-name").value.trim();
        if (!newName) {
            showToast("请输入目录名称");
            return;
        }
        renameFolder(oldName, newName);
    });
    document.getElementById("delete-folder-btn")?.addEventListener("click", () => {
        deleteFolder(document.getElementById("edit-folder-old-name").value);
    });
}

document.addEventListener("DOMContentLoaded", async () => {
    initTheme();
    initModalSystem();
    updateUI();
    bindEvents();
    initBackToTop();
    await Promise.all([loadSettings(), loadArticles()]);
    checkUrlPath();
});
