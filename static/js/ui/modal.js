function resolveModal(target) {
    if (!target) {
        return null;
    }
    if (typeof target === "string") {
        return document.getElementById(target);
    }
    return target;
}

export function openModal(target) {
    const modal = resolveModal(target);
    if (!modal) {
        return;
    }
    modal.classList.add("active");
    document.body.classList.add("modal-open");
    document.body.style.overflow = "hidden";
    modal.dispatchEvent(new CustomEvent("modal:open"));
}

export function closeModal(target) {
    const modal = resolveModal(target);
    if (!modal) {
        return;
    }
    modal.classList.remove("active");
    modal.dispatchEvent(new CustomEvent("modal:close"));
    if (!document.querySelector(".modal.active")) {
        document.body.classList.remove("modal-open");
        document.body.style.overflow = "";
    }
}

export function initModalSystem() {
    document.querySelectorAll(".modal").forEach((modal) => {
        modal.addEventListener("click", (event) => {
            if (event.target === modal) {
                closeModal(modal);
            }
        });
    });

    document.querySelectorAll(".modal .close, [data-modal-close]").forEach((button) => {
        button.addEventListener("click", () => {
            closeModal(button.closest(".modal"));
        });
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            document.querySelectorAll(".modal.active").forEach((modal) => closeModal(modal));
        }
    });
}
