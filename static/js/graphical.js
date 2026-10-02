let sequence = [];

function selectImage(button) {
    const key = button.dataset.key;
    const existingIndex = sequence.indexOf(key);

    if (existingIndex !== -1) {
        sequence.splice(existingIndex, 1);
        button.classList.remove("selected");
        const badge = button.querySelector(".selection-number");
        if (badge) badge.remove();
        refreshSelectionBadges();
    } else {
        sequence.push(key);
        button.classList.add("selected");
    }

    updateGraphicalPassword();
}

function refreshSelectionBadges() {
    document.querySelectorAll(".image-card").forEach((button) => {
        const key = button.dataset.key;
        const index = sequence.indexOf(key);
        let badge = button.querySelector(".selection-number");

        if (index === -1) {
            if (badge) badge.remove();
            return;
        }

        if (!badge) {
            badge = document.createElement("span");
            badge.className = "selection-number";
            button.appendChild(badge);
        }
        badge.textContent = index + 1;
    });
}

function updateGraphicalPassword() {
    const hidden = document.getElementById("graphical_password");
    const display = document.getElementById("selected-sequence");
    if (hidden) hidden.value = sequence.join(",");
    if (display) display.textContent = sequence.length ? sequence.map((x, i) => i + 1).join(" → ") : "None";
}

function togglePassword(inputId, button) {
    const input = document.getElementById(inputId);
    if (input.type === "password") {
        input.type = "text";
        button.textContent = "Hide";
        button.setAttribute("aria-label", "Hide password");
    } else {
        input.type = "password";
        button.textContent = "Show";
        button.setAttribute("aria-label", "Show password");
    }
}
