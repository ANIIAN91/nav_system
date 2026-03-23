import { getToken } from "./auth.js";

let unauthorizedHandler = null;

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
