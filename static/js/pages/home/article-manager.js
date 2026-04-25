import { endpoints } from "../../core/endpoints.js";
import { apiFetch, parseJson } from "../../core/auth.js?v=20260425b";
import { closeModal, openModal } from "../../ui/modal.js";
import { showToast } from "../../ui/toast.js";

const state = {
    articles: [],
    folders: [],
    refreshHomepage: null,
    openArticleSheet: null,
    editorMode: "edit",
};

let initialized = false;

function escapeHtml(text) {
    if (text === null || text === undefined) {
        return "";
    }
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
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

function groupArticlesByCategory(articles) {
    return articles.reduce((groups, article) => {
        const category = article.category || "未分类";
        if (!groups[category]) {
            groups[category] = [];
        }
        groups[category].push(article);
        return groups;
    }, {});
}

function findArticle(path) {
    return state.articles.find((article) => article.path === path) || null;
}

function setArticleEditorState({ mode, path = "", content = "", title = "" }) {
    const pathInput = document.getElementById("edit-article-path");
    const pathHelp = document.getElementById("edit-article-path-help");
    const contentInput = document.getElementById("edit-article-content");
    const originalPathInput = document.getElementById("edit-article-original-path");
    const modalTitle = document.getElementById("edit-article-modal-title");
    const submitButton = document.getElementById("save-article-btn");
    const deleteButton = document.getElementById("delete-article-btn");

    state.editorMode = mode;
    if (originalPathInput) {
        originalPathInput.value = mode === "edit" ? path : "";
    }
    if (pathInput) {
        pathInput.value = path;
        pathInput.readOnly = mode === "edit";
    }
    if (pathHelp) {
        pathHelp.textContent = mode === "edit"
            ? "当前版本只支持编辑内容，文章路径在这里保持只读。"
            : "支持 notes/weekly/hello 或 notes/weekly/hello.md。";
    }
    if (contentInput) {
        contentInput.value = content;
    }
    if (modalTitle) {
        modalTitle.textContent = mode === "edit" ? (title || "编辑文章") : "新建文章";
    }
    if (submitButton) {
        submitButton.textContent = mode === "edit" ? "保存" : "创建文章";
    }
    if (deleteButton) {
        deleteButton.hidden = mode !== "edit";
    }
}

function renderManageArticles() {
    const container = document.getElementById("manage-article-list");
    if (!container) return;

    if (!state.articles.length) {
        container.innerHTML = '<div class="manage-resource-empty">暂无可管理的文章。</div>';
        return;
    }

    const groups = groupArticlesByCategory(state.articles);
    container.innerHTML = Object.entries(groups).map(([category, items]) => `
        <section class="manage-group">
            <div class="manage-group-title">${escapeHtml(category)}</div>
            <div class="manage-group-list">
                ${items.map((article) => `
                    <article class="manage-resource-card">
                        <div class="manage-resource-main">
                            <div class="manage-resource-title">${escapeHtml(article.title || "未命名文章")}</div>
                            <div class="manage-resource-meta">
                                <span>${escapeHtml(article.path)}</span>
                                <span>${escapeHtml(formatArticleDate(article.created_time) || "--")}</span>
                                <span class="manage-pill">${article.protected ? "私密" : "公开"}</span>
                            </div>
                        </div>
                        <div class="manage-resource-actions">
                            <button type="button" class="btn btn-secondary" data-action="open-article" data-path="${escapeHtml(article.path)}">打开</button>
                            <button type="button" class="btn btn-secondary" data-action="edit-article" data-path="${escapeHtml(article.path)}">编辑</button>
                        </div>
                    </article>
                `).join("")}
            </div>
        </section>
    `).join("");
}

function renderManageFolders() {
    const container = document.getElementById("manage-folder-list");
    if (!container) return;

    if (!state.folders.length) {
        container.innerHTML = '<div class="manage-resource-empty">暂无目录，先创建一个目录。</div>';
        return;
    }

    container.innerHTML = state.folders.map((folder) => `
        <article class="manage-resource-card">
            <div class="manage-resource-main">
                <div class="manage-resource-title">${escapeHtml(folder.name)}</div>
                <div class="manage-resource-meta">
                    <span>${escapeHtml(folder.path || folder.name)}</span>
                    <span>${escapeHtml(String(folder.article_count || 0))} 篇文章</span>
                </div>
            </div>
            <div class="manage-resource-actions">
                <button type="button" class="btn btn-secondary" data-action="edit-folder" data-name="${escapeHtml(folder.name)}">重命名</button>
                <button type="button" class="btn btn-danger" data-action="delete-folder" data-name="${escapeHtml(folder.name)}">删除</button>
            </div>
        </article>
    `).join("");
}

export async function loadManageArticles() {
    const container = document.getElementById("manage-article-list");
    if (container) {
        container.innerHTML = '<div class="manage-resource-empty">正在加载文章...</div>';
    }

    try {
        const response = await apiFetch(endpoints.articles.list());
        const data = await parseJson(response, "加载文章失败");
        state.articles = data.articles || [];
        renderManageArticles();
    } catch (error) {
        if (container) {
            container.innerHTML = `<div class="manage-resource-empty">加载失败：${escapeHtml(error.message)}</div>`;
        }
    }
}

export async function loadManageFolders() {
    const container = document.getElementById("manage-folder-list");
    if (container) {
        container.innerHTML = '<div class="manage-resource-empty">正在加载目录...</div>';
    }

    try {
        const response = await apiFetch(endpoints.folders.list());
        const data = await parseJson(response, "加载目录失败");
        state.folders = data.folders || [];
        renderManageFolders();
    } catch (error) {
        if (container) {
            container.innerHTML = `<div class="manage-resource-empty">加载失败：${escapeHtml(error.message)}</div>`;
        }
    }
}

export async function refreshArticleManagerData() {
    await Promise.all([loadManageArticles(), loadManageFolders()]);
}

async function refreshAfterContentChange() {
    await Promise.all([loadManageArticles(), loadManageFolders()]);
    if (typeof state.refreshHomepage === "function") {
        await state.refreshHomepage();
    }
}

function openCreateArticleModal() {
    setArticleEditorState({
        mode: "create",
        path: "",
        content: "# 标题\n\n",
    });
    openModal("edit-article-modal");
}

async function openEditArticleModal(path) {
    try {
        const response = await apiFetch(endpoints.articles.detail(path));
        const article = await parseJson(response, "加载文章失败");
        const summary = findArticle(path);

        setArticleEditorState({
            mode: "edit",
            path: article.path,
            content: article.content,
            title: summary?.title || article.path,
        });
        openModal("edit-article-modal");
    } catch (error) {
        showToast(`加载失败: ${error.message}`, "error");
    }
}

async function createArticle(path, content) {
    try {
        const response = await apiFetch(endpoints.articles.sync(), {
            method: "POST",
            json: { path, content },
        });
        await parseJson(response, "创建失败");
        closeModal("edit-article-modal");
        await refreshAfterContentChange();
        showToast("文章已创建", "success");
    } catch (error) {
        showToast(`创建失败: ${error.message}`, "error");
    }
}

async function saveArticle(path, content) {
    try {
        const response = await apiFetch(endpoints.articles.update(path), {
            method: "PUT",
            json: { content },
        });
        await parseJson(response, "保存失败");
        closeModal("edit-article-modal");
        await refreshAfterContentChange();
        showToast("文章已保存", "success");
    } catch (error) {
        showToast(`保存失败: ${error.message}`, "error");
    }
}

async function deleteArticle(path) {
    if (!path) {
        showToast("请选择文章", "error");
        return;
    }

    if (!window.confirm("确定要删除这篇文章吗？此操作不可恢复。")) {
        return;
    }

    try {
        const response = await apiFetch(endpoints.articles.remove(path), {
            method: "DELETE",
        });
        await parseJson(response, "删除失败");
        closeModal("edit-article-modal");
        await refreshAfterContentChange();
        showToast("文章已删除", "success");
    } catch (error) {
        showToast(`删除失败: ${error.message}`, "error");
    }
}

async function createFolder(name) {
    try {
        const response = await apiFetch(endpoints.folders.create(name), {
            method: "POST",
        });
        await parseJson(response, "创建目录失败");
        document.getElementById("new-folder-name").value = "";
        await refreshAfterContentChange();
        showToast("目录创建成功", "success");
    } catch (error) {
        showToast(`创建失败: ${error.message}`, "error");
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
        await parseJson(response, "目录重命名失败");
        closeModal("edit-folder-modal");
        await refreshAfterContentChange();
        showToast("目录已重命名", "success");
    } catch (error) {
        showToast(`重命名失败: ${error.message}`, "error");
    }
}

async function deleteFolder(name) {
    if (!window.confirm(`确定要删除目录 "${name}" 及其中所有文章吗？`)) {
        return;
    }

    try {
        const response = await apiFetch(endpoints.folders.remove(name), {
            method: "DELETE",
        });
        await parseJson(response, "删除目录失败");
        closeModal("edit-folder-modal");
        await refreshAfterContentChange();
        showToast("目录已删除", "success");
    } catch (error) {
        showToast(`删除失败: ${error.message}`, "error");
    }
}

function bindArticleManagerEvents() {
    document.getElementById("new-article-btn")?.addEventListener("click", openCreateArticleModal);
    document.getElementById("refresh-articles-btn")?.addEventListener("click", loadManageArticles);
    document.getElementById("refresh-folders-btn")?.addEventListener("click", loadManageFolders);

    document.getElementById("create-folder-form")?.addEventListener("submit", (event) => {
        event.preventDefault();
        const name = document.getElementById("new-folder-name").value.trim();
        if (!name) {
            showToast("请输入目录名称", "error");
            return;
        }
        createFolder(name);
    });

    document.getElementById("manage-article-list")?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-action][data-path]");
        if (!button) return;

        const { action, path } = button.dataset;
        if (action === "open-article") {
            const article = findArticle(path) || { path, title: path };
            closeModal("manage-modal");
            state.openArticleSheet?.(article);
            return;
        }

        if (action === "edit-article") {
            openEditArticleModal(path);
        }
    });

    document.getElementById("manage-folder-list")?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-action][data-name]");
        if (!button) return;

        const { action, name } = button.dataset;
        if (action === "edit-folder") {
            openEditFolderModal(name);
            return;
        }
        if (action === "delete-folder") {
            deleteFolder(name);
        }
    });

    document.getElementById("edit-article-form")?.addEventListener("submit", (event) => {
        event.preventDefault();
        const path = document.getElementById("edit-article-path").value.trim();
        const content = document.getElementById("edit-article-content").value;
        const originalPath = document.getElementById("edit-article-original-path").value;

        if (!path) {
            showToast("请输入文章路径", "error");
            return;
        }

        if (state.editorMode === "create") {
            createArticle(path, content);
            return;
        }

        saveArticle(originalPath || path, content);
    });

    document.getElementById("delete-article-btn")?.addEventListener("click", () => {
        deleteArticle(document.getElementById("edit-article-original-path").value);
    });

    document.getElementById("edit-folder-form")?.addEventListener("submit", (event) => {
        event.preventDefault();
        const oldName = document.getElementById("edit-folder-old-name").value;
        const newName = document.getElementById("edit-folder-name").value.trim();
        if (!newName) {
            showToast("请输入目录名称", "error");
            return;
        }
        renameFolder(oldName, newName);
    });

    document.getElementById("delete-folder-btn")?.addEventListener("click", () => {
        deleteFolder(document.getElementById("edit-folder-old-name").value);
    });
}

export function initArticleManager({ refreshHomepage, openArticleSheet } = {}) {
    state.refreshHomepage = refreshHomepage || null;
    state.openArticleSheet = openArticleSheet || null;

    if (initialized) {
        return;
    }

    bindArticleManagerEvents();
    initialized = true;
}
