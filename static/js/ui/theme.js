const STORAGE_KEY = "theme";

function updateThemeIcon(theme) {
    const button = document.getElementById("theme-toggle");
    if (button) {
        button.innerHTML = theme === "light" ? "&#9728;" : "&#9790;";
    }
}

export function initTheme() {
    const savedTheme = localStorage.getItem(STORAGE_KEY) || "dark";
    document.documentElement.setAttribute("data-theme", savedTheme);
    updateThemeIcon(savedTheme);
}

export function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute("data-theme");
    const newTheme = currentTheme === "light" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem(STORAGE_KEY, newTheme);
    updateThemeIcon(newTheme);
}
