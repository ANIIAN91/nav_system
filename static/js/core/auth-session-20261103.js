import { endpoints } from "./endpoints.js";

let unauthorizedHandler = null;

function normalizeStoredValue(value) {
    if (typeof value !== "string") {
        return null;
    }
    const trimmed = value.trim();
    return trimmed ? trimmed : null;
}

export function setUnauthorizedHandler(handler) {
    unauthorizedHandler = handler;
}

// 登录态保存在服务端设置的 HttpOnly Cookie 中，前端不接触 Token
export async function apiFetch(
    url,
    { method = "GET", json, body, headers = {}, auth = true } = {}
) {
    // 配合服务端 Cookie 会话的 CSRF 校验
    const requestHeaders = { "X-Nav-Request": "1", ...headers };
    if (json !== undefined) {
        requestHeaders["Content-Type"] = "application/json";
    } else if (body !== undefined && !requestHeaders["Content-Type"]) {
        requestHeaders["Content-Type"] = "application/json";
    }

    const response = await fetch(url, {
        method,
        headers: requestHeaders,
        body: json !== undefined ? JSON.stringify(json) : body,
    });

    if (auth && response.status === 401 && unauthorizedHandler) {
        await unauthorizedHandler(response);
    }

    return response;
}

export async function parseJson(response, fallbackMessage) {
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.detail || fallbackMessage);
    }
    return data;
}

export function cleanupLegacyCredentialStorage() {
    localStorage.removeItem("savedPassword");
    localStorage.removeItem("rememberCredentials");
    // 旧版本把 JWT 存在浏览器存储中
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("username");
}

export function loadSavedUsername() {
    cleanupLegacyCredentialStorage();
    if (localStorage.getItem("rememberUsername") !== "true") {
        return null;
    }
    return normalizeStoredValue(localStorage.getItem("savedUsername"));
}

export function setRememberedUsername(username) {
    localStorage.setItem("savedUsername", username);
    localStorage.setItem("rememberUsername", "true");
}

export function clearRememberedUsername() {
    localStorage.removeItem("savedUsername");
    localStorage.removeItem("rememberUsername");
}

export async function revokeSession() {
    await fetch(endpoints.auth.logout(), { method: "POST" });
}

// 通过 /auth/me 查询 Cookie 会话对应的用户，未登录或会话失效时返回 null
export async function fetchSessionUser() {
    try {
        const response = await fetch(endpoints.auth.me());
        if (!response.ok) {
            return null;
        }
        const data = await response.json().catch(() => ({}));
        return normalizeStoredValue(data.username);
    } catch {
        return null;
    }
}
