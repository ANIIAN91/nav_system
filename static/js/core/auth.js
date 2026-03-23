import { endpoints } from "./endpoints.js";

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

export function storeSession(token, username) {
    clearSession();
    if (token) {
        localStorage.setItem("token", token);
    }
    if (username) {
        localStorage.setItem("username", username);
    }
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
