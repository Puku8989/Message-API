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
    const sendBtnContent  = $(".send-btn-content");
    const sendBtnLoader   = $(".send-btn-loader");
    const healthBadge     = $("#health-badge");
    const healthText      = $(".health-text");
    const historyList     = $("#history-list");
    const emptyState      = $("#empty-state");
    const clearBtn        = $("#clear-history");
    const toastContainer  = $("#toast-container");
    const telegramCount   = $("#telegram-count");
    const successCount    = $("#success-count");
    const failedCount     = $("#failed-count");
    const recipientInput  = $("#telegram-recipient");

    // ── State ─────────────────────────────────────
    let history = JSON.parse(localStorage.getItem("msg_history") || "[]");
    
    function loadStats() {
        try {
            const raw = JSON.parse(localStorage.getItem("msg_stats"));
            return {
                sent: Number(raw?.sent) || 0,
                success: Number(raw?.success) || 0,
                failed: Number(raw?.failed) || 0,
            };
        } catch {
            return { sent: 0, success: 0, failed: 0 };
        }
    }
    let stats = loadStats();
    let isSending = false;

    // ── Initialisation ────────────────────────────
    function init() {
        renderHistory();
        renderStats();
        checkHealth();
        setInterval(checkHealth, HEALTH_POLL_MS);

        textarea.addEventListener("input", updateCharCount);
        form.addEventListener("submit", handleSubmit);
        clearBtn.addEventListener("click", clearHistory);
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

        const body = {
            platform: "telegram",
            message: message,
        };

        const recipient = recipientInput.value.trim();
        if (recipient) {
            body.recipient = recipient;
        }

        const recipientDisplay = recipient || "default";

        try {
            const res = await fetch(`${API_BASE}/send`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });

            const data = await res.json();

            if (res.ok && data.success) {
                addHistoryItem(message, true, null, recipientDisplay);
                stats.sent++;
                stats.success++;
                saveStats();
                renderStats();
                textarea.value = "";
                updateCharCount();
                showToast("success", "Message sent via Telegram!");
            } else {
                const errorMsg = data.detail || data.error || "Unknown error";
                addHistoryItem(message, false, errorMsg, recipientDisplay);
                stats.sent++;
                stats.failed++;
                saveStats();
                renderStats();
                showToast("error", `Failed: ${errorMsg}`);
            }
        } catch (err) {
            addHistoryItem(message, false, err.message, recipientDisplay);
            stats.sent++;
            stats.failed++;
            saveStats();
            renderStats();
            showToast("error", `Network error: ${err.message}`);
        } finally {
            isSending = false;
            setLoading(false);
        }
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
    function addHistoryItem(message, success, error, recipientInfo) {
        const item = {
            id: Date.now(),
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

        historyList.querySelectorAll(".history-item").forEach((el) => el.remove());
        historyList.prepend(fragment);
    }

    function createHistoryElement(item) {
        const div = document.createElement("div");
        div.className = "history-item";

        const telegramSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M11.944 0A12 12 0 1 0 24 12.056A12.014 12.014 0 0 0 11.944 0ZM16.906 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472c-.18 1.898-.962 6.502-1.36 8.627c-.168.9-.499 1.201-.82 1.23c-.696.065-1.225-.46-1.9-.902c-1.056-.693-1.653-1.124-2.678-1.8c-1.185-.78-.417-1.21.258-1.91c.177-.184 3.247-2.977 3.307-3.23c.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345c-.48.33-.913.492-1.302.48c-.428-.008-1.252-.241-1.865-.44c-.752-.245-1.349-.374-1.297-.789c.027-.216.325-.437.893-.663c3.498-1.524 5.83-2.529 6.998-3.014c3.332-1.386 4.025-1.627 4.476-1.635Z"/></svg>';

        const statusClass = item.success ? "success" : "error";
        const statusText = item.success ? "✓ Delivered" : `✗ ${item.error || "Failed"}`;

        const recipientHtml = item.recipientInfo
            ? `<span class="history-item-recipient" title="${escapeHtml(item.recipientInfo)}">
                 <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                 ${escapeHtml(item.recipientInfo)}
               </span>`
            : "";

        div.innerHTML = `
            <div class="history-item-icon telegram">${telegramSvg}</div>
            <div class="history-item-body">
                <div class="history-item-header">
                    <span class="history-item-platform">Telegram</span>
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
        stats = { sent: 0, success: 0, failed: 0 };
        saveHistory();
        saveStats();
        renderHistory();
        renderStats();
        showToast("info", "History cleared");
    }

    // ── Stats ─────────────────────────────────────
    function renderStats() {
        animateCounter(telegramCount, stats.sent);
        animateCounter(successCount, stats.success);
        animateCounter(failedCount, stats.failed);
    }

    function animateCounter(el, target) {
        if (!el) return;
        const targetNum = Number(target) || 0;
        const current = parseInt(el.textContent, 10) || 0;
        if (current === targetNum) {
            el.textContent = targetNum;
            return;
        }

        const duration = 400;
        const start = performance.now();

        function step(now) {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const val = Math.round(current + (targetNum - current) * eased);
            el.textContent = Number.isNaN(val) ? 0 : val;
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
    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    function formatTime(iso) {
        const d = new Date(iso);
        if (Number.isNaN(d.getTime())) return "Recently";
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
