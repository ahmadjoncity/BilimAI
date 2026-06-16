// BilimAI - frontend logikasi

const chat = document.getElementById("chat");
const form = document.getElementById("form");
const input = document.getElementById("input");
const fileInput = document.getElementById("file");
const sendBtn = document.getElementById("send");
const statusEl = document.getElementById("status");
const preview = document.getElementById("preview");
const previewImg = document.getElementById("preview-img");
const previewRemove = document.getElementById("preview-remove");

let selectedFile = null;

// --- Server holatini tekshirish ---
async function checkHealth() {
    try {
        const res = await fetch("/api/health");
        const data = await res.json();
        if (data.configured) {
            statusEl.textContent = "Tayyor · " + (data.provider || "");
            statusEl.className = "status status--ok";
        } else {
            statusEl.textContent = "AI kaliti yo'q";
            statusEl.className = "status status--off";
        }
    } catch (e) {
        statusEl.textContent = "Server offline";
        statusEl.className = "status status--off";
    }
}
checkHealth();

// --- Textarea avtomatik balandlik ---
input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 140) + "px";
});

// Enter = yuborish, Shift+Enter = yangi qator
input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        form.requestSubmit();
    }
});

// --- Prezentatsiya yaratish ---
const pptxBtn = document.getElementById("pptx-btn");
pptxBtn.addEventListener("click", async () => {
    const topic = (input.value.trim()) || prompt("Prezentatsiya mavzusini kiriting:");
    if (!topic) return;

    addMessage("user", `<p>📊 Prezentatsiya: <b>${escapeHtml(topic)}</b></p>`);
    input.value = "";
    input.style.height = "auto";
    const typing = addTyping();
    pptxBtn.disabled = true;

    try {
        const fd = new FormData();
        fd.append("topic", topic);
        fd.append("slides", "8");
        const res = await fetch("/api/presentation", { method: "POST", body: fd });
        typing.remove();
        if (!res.ok) {
            const data = await res.json();
            addMessage("bot", `<p>⚠️ ${escapeHtml(data.error || "Xatolik")}</p>`);
            return;
        }
        // .pptx faylni yuklab olish
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = topic.replace(/[^\w\s-]/g, "").trim().replace(/\s+/g, "_") + ".pptx";
        a.click();
        URL.revokeObjectURL(url);
        addMessage("bot",
            `<p>✅ <b>"${escapeHtml(topic)}"</b> mavzusida prezentatsiya tayyor!</p>
             <p>Fayl yuklab olindi (.pptx). PowerPoint, Google Slides yoki Canva'da ochishingiz mumkin. 📥</p>`);
    } catch (err) {
        typing.remove();
        addMessage("bot", `<p>⚠️ Xatolik: ${escapeHtml(err.message)}</p>`);
    } finally {
        pptxBtn.disabled = false;
    }
});

// --- Rasm tanlash ---
fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (!file) return;
    selectedFile = file;
    previewImg.src = URL.createObjectURL(file);
    preview.classList.remove("hidden");
});
previewRemove.addEventListener("click", () => {
    selectedFile = null;
    fileInput.value = "";
    preview.classList.add("hidden");
});

// --- Xabar elementlarini yaratish ---
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

// Oddiy markdown -> HTML (kod bloklari, qalin, kod, sarlavhalar)
function formatMarkdown(text) {
    let html = escapeHtml(text);
    // kod bloklari ```...```
    html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
        `<pre><code>${code.replace(/\n$/, "")}</code></pre>`);
    // inline kod `...`
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    // qalin **...**
    html = html.replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
    // qatorlarni paragraflarga
    return html
        .split(/\n{2,}/)
        .map((p) => `<p>${p.replace(/\n/g, "<br>")}</p>`)
        .join("");
}

function addMessage(role, contentHtml, imageUrl) {
    const msg = document.createElement("div");
    msg.className = `message message--${role}`;
    const avatar = role === "bot" ? "🎓" : "🧑";
    let bubbleInner = contentHtml;
    if (imageUrl) bubbleInner += `<img src="${imageUrl}" alt="rasm">`;
    msg.innerHTML = `
        <div class="avatar">${avatar}</div>
        <div class="bubble">${bubbleInner}</div>`;
    chat.appendChild(msg);
    chat.scrollTop = chat.scrollHeight;
    return msg;
}

function addTyping() {
    const msg = document.createElement("div");
    msg.className = "message message--bot";
    msg.innerHTML = `
        <div class="avatar">🎓</div>
        <div class="bubble"><span class="typing"><span></span><span></span><span></span></span></div>`;
    chat.appendChild(msg);
    chat.scrollTop = chat.scrollHeight;
    return msg;
}

// --- Yuborish ---
form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text && !selectedFile) return;

    const imageUrl = selectedFile ? URL.createObjectURL(selectedFile) : null;
    addMessage("user", text ? `<p>${escapeHtml(text)}</p>` : "<p>📷 Rasm</p>", imageUrl);

    // tozalash
    input.value = "";
    input.style.height = "auto";
    sendBtn.disabled = true;
    const fileToSend = selectedFile;
    selectedFile = null;
    fileInput.value = "";
    preview.classList.add("hidden");

    const typing = addTyping();

    try {
        let res;
        if (fileToSend) {
            const fd = new FormData();
            fd.append("image", fileToSend);
            fd.append("message", text);
            res = await fetch("/api/chat-image", { method: "POST", body: fd });
        } else {
            const fd = new FormData();
            fd.append("message", text);
            res = await fetch("/api/chat", { method: "POST", body: fd });
        }
        const data = await res.json();
        typing.remove();
        if (res.ok) {
            addMessage("bot", formatMarkdown(data.answer));
        } else {
            addMessage("bot", `<p>⚠️ ${escapeHtml(data.error || "Xatolik yuz berdi")}</p>`);
        }
    } catch (err) {
        typing.remove();
        addMessage("bot", `<p>⚠️ Tarmoq xatosi: ${escapeHtml(err.message)}</p>`);
    } finally {
        sendBtn.disabled = false;
        input.focus();
    }
});
