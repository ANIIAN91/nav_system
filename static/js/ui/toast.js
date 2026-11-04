const toastQueue = [];
let toastIdCounter = 0;

function updateToastPositions() {
    let offset = 80;
    toastQueue.forEach((item) => {
        item.element.style.top = `${offset}px`;
        offset += item.element.offsetHeight + 12;
    });
}

export function showToast(message, type = "info", duration = 3000, action = null) {
    const toastId = toastIdCounter++;
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    if (action) {
        // 可选操作按钮，例如删除后的“撤销”
        const actionBtn = document.createElement("button");
        actionBtn.type = "button";
        actionBtn.className = "toast-action";
        actionBtn.textContent = action.label;
        actionBtn.addEventListener("click", () => {
            actionBtn.disabled = true;
            toast.classList.remove("show");
            action.onClick();
        }, { once: true });
        toast.appendChild(actionBtn);
        toast.classList.add("has-action");
    }
    toast.dataset.toastId = String(toastId);
    toast.setAttribute("role", "status");
    toast.setAttribute("aria-live", "polite");
    toast.setAttribute("aria-atomic", "true");

    document.body.appendChild(toast);
    toastQueue.push({ id: toastId, element: toast });
    updateToastPositions();

    window.setTimeout(() => toast.classList.add("show"), 10);

    window.setTimeout(() => {
        toast.classList.remove("show");
        window.setTimeout(() => {
            toast.remove();
            const index = toastQueue.findIndex((item) => item.id === toastId);
            if (index !== -1) {
                toastQueue.splice(index, 1);
                updateToastPositions();
            }
        }, 300);
    }, duration);
}
