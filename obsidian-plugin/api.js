const API_PREFIX = "/api/v1";

function normalizePath(path) {
    return path.startsWith("/") ? path : `/${path}`;
}

function buildApiUrl(baseUrl, path) {
    const normalizedPath = normalizePath(path);
    const trimmedBase = (baseUrl || "").replace(/\/+$/, "");
    if (trimmedBase.endsWith(API_PREFIX)) {
        const suffix = normalizedPath.startsWith(API_PREFIX)
            ? normalizedPath.slice(API_PREFIX.length)
            : normalizedPath;
        return `${trimmedBase}${suffix}`;
    }
    return `${trimmedBase}${normalizedPath}`;
}

function buildHeaders(token, extraHeaders = {}) {
    return {
        ...extraHeaders,
        Authorization: `Bearer ${token}`,
    };
}

function authMePath() {
    return `${API_PREFIX}/auth/me`;
}

function syncArticlePath() {
    return `${API_PREFIX}/articles/sync`;
}

async function requestApi({ requestUrl, baseUrl, token, path, method = "GET", body = null, headers = {} }) {
    return requestUrl({
        url: buildApiUrl(baseUrl, path),
        method,
        headers: buildHeaders(token, headers),
        body: body ? JSON.stringify(body) : undefined,
    });
}

async function checkMe({ requestUrl, baseUrl, token }) {
    return requestApi({
        requestUrl,
        baseUrl,
        token,
        path: authMePath(),
        method: "GET",
    });
}

async function syncArticle({ requestUrl, baseUrl, token, payload }) {
    return requestApi({
        requestUrl,
        baseUrl,
        token,
        path: syncArticlePath(),
        method: "POST",
        body: payload,
        headers: { "Content-Type": "application/json" },
    });
}

module.exports = {
    API_PREFIX,
    authMePath,
    buildApiUrl,
    buildHeaders,
    checkMe,
    requestApi,
    syncArticle,
    syncArticlePath,
};
