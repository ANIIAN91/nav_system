import { getToken, getUsername } from "./auth.js";

export const homePageState = {
    token: getToken(),
    username: getUsername(),
    links: { categories: [] },
    articles: [],
    settings: { link_size: "medium", protected_article_paths: [] },
    currentCategory: null,
    currentView: "navigation",
    searchTerm: "",
};
