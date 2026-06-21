(() => {
    const badgeInput = document.getElementById("badge_uid");
    const statusEl = document.getElementById("enroll-status");
    const btnEnroll = document.getElementById("btn-enroll");
    const btnSubmit = document.getElementById("btn-submit");
    if (!badgeInput || !statusEl || !btnEnroll || !btnSubmit) return;

    const I18N = window.TIMBRANFC_I18N || {};
    const txt = (key, fallback) => I18N[key] || fallback;

    let sessionId = null;
    let pollTimer = null;
    const targetDipendenteId = window.TIMBRANFC_ENROLL_DIPENDENTE_ID || null;

    function setStatus(text, kind) {
        statusEl.textContent = text;
        statusEl.className = "enroll-status " + (kind || "waiting");
    }

    function enableSubmit() {
        btnSubmit.disabled = !badgeInput.value.trim();
    }

    async function stopEnrollment() {
        if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
        sessionId = null;
        try {
            await fetch("/api/v1/enrollment/stop", { method: "POST" });
        } catch (_) {
            /* ignore */
        }
    }

    async function pollSession() {
        if (!sessionId) return;
        try {
            const res = await fetch("/api/v1/enrollment/poll?session_id=" + encodeURIComponent(sessionId));
            const data = await res.json();
            if (data.status === "captured") {
                badgeInput.value = data.badge_uid || "";
                enableSubmit();
                if (data.duplicate) {
                    setStatus(txt("enroll_duplicate_js", "Badge already in use."), "error");
                    badgeInput.value = "";
                    enableSubmit();
                    await startEnrollment();
                    return;
                }
                const captured = txt("enroll_captured", "Badge registered: {uid}").replace("{uid}", data.badge_uid || "");
                setStatus(captured, "ok");
                clearInterval(pollTimer);
                pollTimer = null;
            } else if (data.status === "expired" || data.status === "invalid") {
                setStatus(txt("enroll_expired", "Session expired."), "error");
                clearInterval(pollTimer);
                pollTimer = null;
            }
        } catch (_) {
            setStatus(txt("enroll_conn_error", "Connection error."), "error");
        }
    }

    async function startEnrollment() {
        await stopEnrollment();
        badgeInput.value = "";
        enableSubmit();
        setStatus(txt("enroll_near_reader", "Hold badge to reader."), "waiting");
        try {
            let url = "/api/v1/enrollment/start";
            if (targetDipendenteId) {
                url += "?dipendente_id=" + encodeURIComponent(targetDipendenteId);
            }
            const res = await fetch(url, { method: "POST" });
            if (!res.ok) throw new Error("start failed");
            const data = await res.json();
            sessionId = data.session_id;
            pollTimer = setInterval(pollSession, 500);
        } catch (_) {
            setStatus(txt("enroll_start_error", "Cannot start enrollment."), "error");
        }
    }

    btnEnroll.addEventListener("click", startEnrollment);
    window.addEventListener("beforeunload", stopEnrollment);
    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "hidden") stopEnrollment();
    });

    setStatus(txt("enroll_click_wait", "Click rescan and hold badge to reader."), "waiting");
})();
