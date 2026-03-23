const toastQueue = [];
let toastIdCounter = 0;

function updateToastPositions() {
    let offset = 80;
    toastQueue.forEach((item) => {
        item.element.style.top = `${offset}px`;
        offset += item.element.offsetHeight + 12;
    });
}

export function showToast(message, type = "info", duration = 3000) {
    const toastId = toastIdCounter++;
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
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
