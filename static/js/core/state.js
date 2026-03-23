import { getToken, getUsername } from "./auth.js";

export const homePageState = {
    token: getToken(),
    username: getUsername(),
    links: { categories: [] },
    isManageMode: false,
    settings: { link_size: "medium", protected_article_paths: [] },
    currentCategory: null,
};

export const articlePageState = {
    token: getToken(),
    currentArticlePath: null,
    currentArticleContent: null,
    articles: [],
    settings: {},
};
