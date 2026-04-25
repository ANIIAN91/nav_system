import { endpoints } from "./endpoints.js";

let unauthorizedHandler = null;

function normalizeStoredValue(value) {
    if (typeof value !== "string") {
        return null;
    }
    const trimmed = value.trim();
    return trimmed ? trimmed : null;
}

function readStorage(key) {
    return normalizeStoredValue(localStorage.getItem(key))
        || normalizeStoredValue(sessionStorage.getItem(key));
}

export function getToken() {
    return readStorage("token");
}

export function getUsername() {
    return readStorage("username");
}

export function isAuthenticated() {
    return Boolean(getToken());
}

export function setUnauthorizedHandler(handler) {
    unauthorizedHandler = handler;
}

export async function apiFetch(
    url,
    { method = "GET", json, body, headers = {}, auth = true } = {}
) {
    const requestHeaders = { ...headers };
    if (json !== undefined) {
        requestHeaders["Content-Type"] = "application/json";
    } else if (body !== undefined && !requestHeaders["Content-Type"]) {
        requestHeaders["Content-Type"] = "application/json";
    }

    const token = auth ? getToken() : null;
    if (token) {
        requestHeaders.Authorization = `Bearer ${token}`;
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

export function storeSession(token, username) {
    clearSession();
    if (token) {
        localStorage.setItem("token", token);
    }
    if (username) {
        localStorage.setItem("username", username);
    }
}

function writeUsernameForCurrentToken(username) {
    const normalizedUsername = normalizeStoredValue(username);
    if (!normalizedUsername) {
        return;
    }

    const tokenInSession = normalizeStoredValue(sessionStorage.getItem("token"));
    const storage = tokenInSession ? sessionStorage : localStorage;
    storage.setItem("username", normalizedUsername);
}

export function clearSession() {
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("username");
}

export function cleanupLegacyCredentialStorage() {
    localStorage.removeItem("savedPassword");
    localStorage.removeItem("rememberCredentials");
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

export async function revokeSession(token = getToken()) {
    if (!token) {
        return;
    }
    await fetch(endpoints.auth.logout(), {
        method: "POST",
        headers: {
            Authorization: `Bearer ${token}`,
        },
    });
}

export async function validateStoredSession(token = getToken()) {
    if (!token) {
        return null;
    }

    try {
        const response = await fetch(endpoints.auth.me(), {
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });

        if (!response.ok) {
            clearSession();
            return null;
        }

        const data = await response.json().catch(() => ({}));
        writeUsernameForCurrentToken(data.username);
        return {
            token,
            username: normalizeStoredValue(data.username) || getUsername(),
        };
    } catch {
        clearSession();
        return null;
    }
}
