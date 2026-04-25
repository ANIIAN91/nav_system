import { endpoints } from "../../core/endpoints.js";
import { apiFetch, parseJson } from "../../core/auth.js?v=20260425b";
import { openModal } from "../../ui/modal.js";

let currentArticlePath = null;

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

function setSheetMeta(article = {}) {
    const categoryEl = document.getElementById("article-sheet-category");
    const titleEl = document.getElementById("article-sheet-title");
    const dateEl = document.getElementById("article-sheet-date");
    const visibilityEl = document.getElementById("article-sheet-visibility");

    if (categoryEl) {
        const category = article.category ? article.category.split("/").filter(Boolean).pop() : "Article";
        categoryEl.textContent = category || "Article";
    }
    if (titleEl) {
        titleEl.textContent = article.title || "文章";
    }
    if (dateEl) {
        dateEl.textContent = formatArticleDate(article.created_time) || "--";
    }
    if (visibilityEl) {
        visibilityEl.textContent = article.protected ? "私密" : "公开";
    }
}

function setSheetBody(html) {
    const contentEl = document.getElementById("article-sheet-content");
    if (!contentEl) return;
    contentEl.innerHTML = html;
}

function setSheetLoading(article) {
    setSheetMeta(article);
    setSheetBody('<div class="article-sheet-loading">文章加载中...</div>');
}

function setSheetError(message) {
    setSheetBody(`
        <div class="article-sheet-error">
            <div class="empty-title">加载失败</div>
            <div class="empty-copy">${escapeHtml(message)}</div>
        </div>
    `);
}

function updateArticleQuery(path) {
    const url = new URL(window.location.href);
    if (path) {
        url.searchParams.set("article", path);
    } else {
        url.searchParams.delete("article");
    }
    window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
}

export function initArticleSheet() {
    const bodyEl = document.getElementById("article-sheet-body");
    const modal = document.getElementById("article-sheet-modal");

    document.getElementById("article-sheet-top")?.addEventListener("click", () => {
        bodyEl?.scrollTo({ top: 0, behavior: "smooth" });
    });

    document.getElementById("article-sheet-down")?.addEventListener("click", () => {
        if (!bodyEl) return;
        bodyEl.scrollTo({ top: bodyEl.scrollHeight, behavior: "smooth" });
    });

    modal?.addEventListener("modal:close", () => {
        currentArticlePath = null;
        updateArticleQuery(null);
    });
}

export async function openArticleSheet(article, { updateUrl = true } = {}) {
    if (!article?.path) {
        return;
    }

    currentArticlePath = article.path;
    openModal("article-sheet-modal");
    setSheetLoading(article);
    if (updateUrl) {
        updateArticleQuery(article.path);
    }

    try {
        const response = await apiFetch(endpoints.articles.detail(article.path));
        const data = await parseJson(response, "加载文章失败");
        const sanitizedHtml = window.DOMPurify ? window.DOMPurify.sanitize(data.html) : data.html;
        setSheetMeta(article);
        setSheetBody(sanitizedHtml || '<p class="placeholder">文章内容为空</p>');
        document.getElementById("article-sheet-body")?.scrollTo({ top: 0, behavior: "auto" });
    } catch (error) {
        setSheetMeta(article);
        setSheetError(error.message || "加载文章失败");
    }
}

export async function maybeOpenArticleFromLocation(articles = []) {
    const requestedPath = new URLSearchParams(window.location.search).get("article");
    if (!requestedPath || requestedPath === currentArticlePath) {
        return;
    }

    const article = articles.find((item) => item.path === requestedPath) || {
        path: requestedPath,
        title: requestedPath.split("/").pop() || "文章",
        category: requestedPath.includes("/") ? requestedPath.split("/").slice(0, -1).join("/") : null,
        protected: false,
        created_time: null,
    };

    await openArticleSheet(article, { updateUrl: false });
}
