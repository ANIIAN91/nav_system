const API_PREFIX = "/api/v1";

function encodePathSegments(path = "") {
    return String(path)
        .split("/")
        .filter(Boolean)
        .map((segment) => encodeURIComponent(segment))
        .join("/");
}

function withQuery(path, params = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
            query.set(key, String(value));
        }
    });
    const suffix = query.toString();
    return suffix ? `${path}?${suffix}` : path;
}

export const endpoints = {
    auth: {
        login: () => `${API_PREFIX}/auth/login`,
        logout: () => `${API_PREFIX}/auth/logout`,
        me: () => `${API_PREFIX}/auth/me`,
        cleanupTokens: () => `${API_PREFIX}/auth/cleanup-tokens`,
    },
    settings: {
        get: () => `${API_PREFIX}/settings`,
        admin: () => `${API_PREFIX}/settings/admin`,
        update: () => `${API_PREFIX}/settings`,
    },
    links: {
        list: () => `${API_PREFIX}/links`,
        create: (categoryName) => withQuery(`${API_PREFIX}/links`, { category_name: categoryName }),
        detail: (id) => `${API_PREFIX}/links/${encodeURIComponent(id)}`,
        reorder: (id) => `${API_PREFIX}/links/${encodeURIComponent(id)}/reorder`,
        batchReorder: () => `${API_PREFIX}/links/reorder/batch`,
        exportData: () => `${API_PREFIX}/links/export`,
        importData: () => `${API_PREFIX}/links/import`,
    },
    categories: {
        create: () => `${API_PREFIX}/categories`,
        detail: (name) => `${API_PREFIX}/categories/${encodePathSegments(name)}`,
        batchReorder: () => `${API_PREFIX}/categories/reorder/batch`,
    },
    articles: {
        list: () => `${API_PREFIX}/articles`,
        sync: () => `${API_PREFIX}/articles/sync`,
        detail: (path) => `${API_PREFIX}/articles/${encodePathSegments(path)}`,
        update: (path) => `${API_PREFIX}/articles/${encodePathSegments(path)}`,
        remove: (path) => `${API_PREFIX}/articles/${encodePathSegments(path)}`,
    },
    folders: {
        list: () => `${API_PREFIX}/folders`,
        create: (name) => `${API_PREFIX}/folders?name=${encodeURIComponent(name)}`,
        rename: (name) => `${API_PREFIX}/folders/${encodePathSegments(name)}`,
        remove: (name) => `${API_PREFIX}/folders/${encodePathSegments(name)}`,
    },
    favicon: {
        fetch: () => `${API_PREFIX}/favicon/fetch`,
    },
    logs: {
        visits: (limit = 100) => withQuery(`${API_PREFIX}/logs/visits`, { limit }),
        clearVisits: () => `${API_PREFIX}/logs/visits`,
        updates: (limit = 100) => withQuery(`${API_PREFIX}/logs/updates`, { limit }),
        clearUpdates: () => `${API_PREFIX}/logs/updates`,
    },
};
