/* ─────────────────────────────────────────────
   MESSAGE API DASHBOARD — Application Logic
   ───────────────────────────────────────────── */

(function () {
    "use strict";

    // ── Constants ─────────────────────────────────
    const API_BASE = window.location.origin;
    const HEALTH_POLL_MS = 15_000;
    const TOAST_DURATION_MS = 4_000;

    // ── DOM References ────────────────────────────
    const $ = (sel) => document.querySelector(sel);
    const form            = $("#message-form");
    const textarea        = $("#message-input");
    const charCount       = $("#char-count");
    const sendBtn         = $("#send-btn");
    const sendBtnText     = $("#send-btn-text");
    const sendBtnContent  = $(".send-btn-content");
    const sendBtnLoader   = $(".send-btn-loader");
    const healthBadge     = $("#health-badge");
    const healthText      = $(".health-text");
    const historyList     = $("#history-list");
    const emptyState      = $("#empty-state");
    const clearBtn        = $("#clear-history");
    const toastContainer  = $("#toast-container");
    const telegramCount   = $("#telegram-count");
    const whatsappCount   = $("#whatsapp-count");
    const totalCount      = $("#total-count");
    const platformBtns    = document.querySelectorAll(".platform-btn");

    // Recipient fields
    const telegramRecipientGroup = $("#telegram-recipient-group");
    const whatsappRecipientGroup = $("#whatsapp-recipient-group");
    const telegramRecipient      = $("#telegram-recipient");
    const whatsappRecipient      = $("#whatsapp-recipient");

    // ── State ─────────────────────────────────────
    let selectedPlatform = "telegram";
    let history = JSON.parse(localStorage.getItem("msg_history") || "[]");
    let stats = JSON.parse(localStorage.getItem("msg_stats") || '{"telegram":0,"whatsapp":0}');
    let isSending = false;

    // ── Initialisation ────────────────────────────
    function init() {
        renderHistory();
        renderStats();
        checkHealth();
        setInterval(checkHealth, HEALTH_POLL_MS);

        // Event listeners
        platformBtns.forEach((btn) => {
            btn.addEventListener("click", () => selectPlatform(btn.dataset.platform));
        });

        textarea.addEventListener("input", updateCharCount);
        form.addEventListener("submit", handleSubmit);
        clearBtn.addEventListener("click", clearHistory);

        // Set initial button style and recipient visibility
        updateSendBtnStyle();
        updateRecipientVisibility();
    }

    // ── Platform Selection ────────────────────────
    function selectPlatform(platform) {
        selectedPlatform = platform;
        platformBtns.forEach((btn) => {
            const isActive = btn.dataset.platform === platform;
            btn.classList.toggle("active", isActive);
            btn.setAttribute("aria-pressed", isActive);
        });
        updateSendBtnStyle();
        updateRecipientVisibility();
    }

    function updateRecipientVisibility() {
        // Show/hide recipient fields based on selected platform
        const showTelegram = selectedPlatform === "telegram" || selectedPlatform === "both";
        const showWhatsapp = selectedPlatform === "whatsapp" || selectedPlatform === "both";

        telegramRecipientGroup.classList.toggle("visible", showTelegram);
        whatsappRecipientGroup.classList.toggle("visible", showWhatsapp);

        // Animate the container
        telegramRecipientGroup.style.maxHeight = showTelegram ? "120px" : "0";
        telegramRecipientGroup.style.opacity = showTelegram ? "1" : "0";
        telegramRecipientGroup.style.marginBottom = showTelegram ? "16px" : "0";

        whatsappRecipientGroup.style.maxHeight = showWhatsapp ? "120px" : "0";
        whatsappRecipientGroup.style.opacity = showWhatsapp ? "1" : "0";
        whatsappRecipientGroup.style.marginBottom = showWhatsapp ? "16px" : "0";
    }

    function updateSendBtnStyle() {
        sendBtn.classList.remove("telegram-active", "whatsapp-active", "both-active");
        sendBtn.classList.add(`${selectedPlatform}-active`);

        // Update button label
        const labels = {
            telegram: "Send via Telegram",
            whatsapp: "Send via WhatsApp",
            both: "Send to Both",
        };
        sendBtnText.textContent = labels[selectedPlatform] || "Send Message";
    }

    // ── Character Counter ─────────────────────────
    function updateCharCount() {
        const len = textarea.value.length;
        charCount.textContent = len;
        if (len > 3900) {
            charCount.parentElement.style.color = "#f87171";
        } else {
            charCount.parentElement.style.color = "";
        }
    }

    // ── Health Check ──────────────────────────────
    async function checkHealth() {
        try {
            const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(5000) });
            if (res.ok) {
                healthBadge.classList.remove("offline");
                healthBadge.classList.add("online");
                healthText.textContent = "Online";
            } else {
                throw new Error("Not OK");
            }
        } catch {
            healthBadge.classList.remove("online");
            healthBadge.classList.add("offline");
            healthText.textContent = "Offline";
        }
    }

    // ── Send Message ──────────────────────────────
    async function handleSubmit(e) {
        e.preventDefault();

        const message = textarea.value.trim();
        if (!message || isSending) return;

        isSending = true;
        setLoading(true);

        // Build request body
        const body = {
            platform: selectedPlatform,
            message: message,
        };

        // Determine the recipient based on the selected platform
        const tgRecipient = telegramRecipient.value.trim();
        const waRecipient = whatsappRecipient.value.trim();

        if (selectedPlatform === "telegram" && tgRecipient) {
            body.recipient = tgRecipient;
        } else if (selectedPlatform === "whatsapp" && waRecipient) {
            body.recipient = waRecipient;
        } else if (selectedPlatform === "both") {
            // For "both", pass whatsapp number as recipient (used by WhatsApp)
            // and telegram_chat_id for Telegram
            if (tgRecipient) body.telegram_chat_id = tgRecipient;
            if (waRecipient) body.whatsapp_recipient = waRecipient;
        }

        // Build display string for the recipient info in history
        const recipientDisplay = buildRecipientDisplay(tgRecipient, waRecipient);

        try {
            const res = await fetch(`${API_BASE}/send`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });

            const data = await res.json();

            if (res.ok && data.success) {
                // Success — track stats for both platforms when "both"
                if (selectedPlatform === "both") {
                    addHistoryItem("both", message, true, null, recipientDisplay);
                    stats.telegram++;
                    stats.whatsapp++;
                } else {
                    addHistoryItem(selectedPlatform, message, true, null, recipientDisplay);
                    stats[selectedPlatform]++;
                }
                saveStats();
                renderStats();
                textarea.value = "";
                updateCharCount();

                const platformLabel = selectedPlatform === "both"
                    ? "Telegram & WhatsApp"
                    : capitalize(selectedPlatform);
                showToast("success", `Message sent via ${platformLabel}!`);
            } else {
                // API error
                const errorMsg = data.detail || data.error || "Unknown error";
                addHistoryItem(selectedPlatform, message, false, errorMsg, recipientDisplay);
                showToast("error", `Failed: ${errorMsg}`);
            }
        } catch (err) {
            addHistoryItem(selectedPlatform, message, false, err.message, recipientDisplay);
            showToast("error", `Network error: ${err.message}`);
        } finally {
            isSending = false;
            setLoading(false);
        }
    }

    function buildRecipientDisplay(tg, wa) {
        const parts = [];
        if (selectedPlatform === "telegram" || selectedPlatform === "both") {
            parts.push(tg ? `TG: ${tg}` : "TG: default");
        }
        if (selectedPlatform === "whatsapp" || selectedPlatform === "both") {
            parts.push(wa ? `WA: ${wa}` : "WA: default");
        }
        return parts.join(" · ");
    }

    function setLoading(loading) {
        sendBtn.disabled = loading;
        if (loading) {
            sendBtnContent.hidden = true;
            sendBtnLoader.hidden = false;
        } else {
            sendBtnContent.hidden = false;
            sendBtnLoader.hidden = true;
        }
    }

    // ── History Management ────────────────────────
    function addHistoryItem(platform, message, success, error, recipientInfo) {
        const item = {
            id: Date.now(),
            platform,
            message,
            success,
            error: error || null,
            recipientInfo: recipientInfo || null,
            timestamp: new Date().toISOString(),
        };
        history.unshift(item);
        if (history.length > 50) history.pop();
        saveHistory();
        renderHistory();
    }

    function renderHistory() {
        if (history.length === 0) {
            emptyState.hidden = false;
            // Remove all history items but keep empty state
            historyList.querySelectorAll(".history-item").forEach((el) => el.remove());
            return;
        }

        emptyState.hidden = true;
        const fragment = document.createDocumentFragment();

        history.forEach((item, i) => {
            const el = createHistoryElement(item);
            el.style.animationDelay = `${i * 0.04}s`;
            fragment.appendChild(el);
        });

        // Clear existing items
        historyList.querySelectorAll(".history-item").forEach((el) => el.remove());
        historyList.prepend(fragment);
    }

    function createHistoryElement(item) {
        const div = document.createElement("div");
        div.className = "history-item";

        const telegramSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M11.944 0A12 12 0 1 0 24 12.056A12.014 12.014 0 0 0 11.944 0ZM16.906 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472c-.18 1.898-.962 6.502-1.36 8.627c-.168.9-.499 1.201-.82 1.23c-.696.065-1.225-.46-1.9-.902c-1.056-.693-1.653-1.124-2.678-1.8c-1.185-.78-.417-1.21.258-1.91c.177-.184 3.247-2.977 3.307-3.23c.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345c-.48.33-.913.492-1.302.48c-.428-.008-1.252-.241-1.865-.44c-.752-.245-1.349-.374-1.297-.789c.027-.216.325-.437.893-.663c3.498-1.524 5.83-2.529 6.998-3.014c3.332-1.386 4.025-1.627 4.476-1.635Z"/></svg>';
        const whatsappSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967c-.273-.099-.471-.148-.67.15c-.197.297-.767.966-.94 1.164c-.173.199-.347.223-.644.075c-.297-.15-1.255-.463-2.39-1.475c-.883-.788-1.48-1.761-1.653-2.059c-.173-.297-.018-.458.13-.606c.134-.133.298-.347.446-.52c.149-.174.198-.298.298-.497c.099-.198.05-.371-.025-.52c-.075-.149-.669-1.612-.916-2.207c-.242-.579-.487-.5-.669-.51c-.173-.008-.371-.01-.57-.01c-.198 0-.52.074-.792.372c-.272.297-1.04 1.016-1.04 2.479c0 1.462 1.065 2.875 1.213 3.074c.149.198 2.096 3.2 5.077 4.487c.709.306 1.262.489 1.694.625c.712.227 1.36.195 1.871.118c.571-.085 1.758-.719 2.006-1.413c.248-.694.248-1.289.173-1.413c-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214l-3.741.982l.998-3.648l-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884c2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413Z"/></svg>';
        const bothSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>';

        let iconSvg, iconClass, platformLabel;
        if (item.platform === "both") {
            iconSvg = bothSvg;
            iconClass = "both";
            platformLabel = "Both";
        } else if (item.platform === "telegram") {
            iconSvg = telegramSvg;
            iconClass = "telegram";
            platformLabel = "Telegram";
        } else {
            iconSvg = whatsappSvg;
            iconClass = "whatsapp";
            platformLabel = "WhatsApp";
        }

        const statusClass = item.success ? "success" : "error";
        const statusText = item.success ? "✓ Delivered" : `✗ ${item.error || "Failed"}`;

        // Show recipient info if available
        const recipientHtml = item.recipientInfo
            ? `<span class="history-item-recipient" title="${escapeHtml(item.recipientInfo)}">
                 <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                 ${escapeHtml(item.recipientInfo)}
               </span>`
            : "";

        div.innerHTML = `
            <div class="history-item-icon ${iconClass}">${iconSvg}</div>
            <div class="history-item-body">
                <div class="history-item-header">
                    <span class="history-item-platform">${platformLabel}</span>
                    <span class="history-item-time">${formatTime(item.timestamp)}</span>
                </div>
                ${recipientHtml}
                <div class="history-item-message" title="${escapeHtml(item.message)}">${escapeHtml(item.message)}</div>
                <span class="history-item-status ${statusClass}">${statusText}</span>
            </div>
        `;
        return div;
    }

    function clearHistory() {
        history = [];
        stats = { telegram: 0, whatsapp: 0 };
        saveHistory();
        saveStats();
        renderHistory();
        renderStats();
        showToast("info", "History cleared");
    }

    // ── Stats ─────────────────────────────────────
    function renderStats() {
        animateCounter(telegramCount, stats.telegram);
        animateCounter(whatsappCount, stats.whatsapp);
        animateCounter(totalCount, stats.telegram + stats.whatsapp);
    }

    function animateCounter(el, target) {
        const current = parseInt(el.textContent, 10) || 0;
        if (current === target) return;

        const duration = 400;
        const start = performance.now();

        function step(now) {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
            el.textContent = Math.round(current + (target - current) * eased);
            if (progress < 1) requestAnimationFrame(step);
        }

        requestAnimationFrame(step);
    }

    // ── Toast Notifications ───────────────────────
    function showToast(type, message) {
        const icons = {
            success: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
            error: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
            info: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
        };

        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.innerHTML = `<span class="toast-icon">${icons[type]}</span><span>${escapeHtml(message)}</span>`;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.classList.add("toast-exit");
            toast.addEventListener("animationend", () => toast.remove());
        }, TOAST_DURATION_MS);
    }

    // ── Persistence ───────────────────────────────
    function saveHistory() {
        localStorage.setItem("msg_history", JSON.stringify(history));
    }

    function saveStats() {
        localStorage.setItem("msg_stats", JSON.stringify(stats));
    }

    // ── Utilities ─────────────────────────────────
    function capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    function formatTime(iso) {
        const d = new Date(iso);
        const now = new Date();
        const diffMs = now - d;

        if (diffMs < 60_000) return "Just now";
        if (diffMs < 3_600_000) return `${Math.floor(diffMs / 60_000)}m ago`;
        if (diffMs < 86_400_000) return `${Math.floor(diffMs / 3_600_000)}h ago`;

        return d.toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    // ── Boot ──────────────────────────────────────
    document.addEventListener("DOMContentLoaded", init);
})();
