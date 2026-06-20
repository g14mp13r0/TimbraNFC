(() => {
    const badgeInput = document.getElementById("badge_uid");
    const statusEl = document.getElementById("enroll-status");
    const btnEnroll = document.getElementById("btn-enroll");
    const btnSubmit = document.getElementById("btn-submit");
    let sessionId = null;
    let pollTimer = null;

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
                    setStatus("Badge già registrato nel sistema — usa un altro badge.", "error");
                    badgeInput.value = "";
                    enableSubmit();
                    await startEnrollment();
                    return;
                }
                setStatus("Badge registrato: " + data.badge_uid, "success");
                clearInterval(pollTimer);
                pollTimer = null;
            } else if (data.status === "expired" || data.status === "invalid") {
                setStatus("Sessione scaduta — clicca «Rileggi badge».", "error");
                clearInterval(pollTimer);
                pollTimer = null;
            }
        } catch (_) {
            setStatus("Errore di connessione al server.", "error");
        }
    }

    async function startEnrollment() {
        await stopEnrollment();
        badgeInput.value = "";
        enableSubmit();
        setStatus("Avvicina il badge vergine al lettore NFC del Raspberry Pi.", "waiting");
        try {
            const res = await fetch("/api/v1/enrollment/start", { method: "POST" });
            if (!res.ok) throw new Error("start failed");
            const data = await res.json();
            sessionId = data.session_id;
            pollTimer = setInterval(pollSession, 500);
        } catch (_) {
            setStatus("Impossibile avviare la registrazione badge.", "error");
        }
    }

    btnEnroll.addEventListener("click", startEnrollment);
    window.addEventListener("beforeunload", stopEnrollment);

    startEnrollment();
})();
