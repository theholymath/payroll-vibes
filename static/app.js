let sessionId = null;
let isProcessing = false;

const fileInput = document.getElementById("file-input");
const dropArea = document.getElementById("drop-area");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");

// --- File upload handlers ---

fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
        uploadFile(e.target.files[0]);
    }
});

dropArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropArea.classList.add("dragover");
});

dropArea.addEventListener("dragleave", () => {
    dropArea.classList.remove("dragover");
});

dropArea.addEventListener("drop", (e) => {
    e.preventDefault();
    dropArea.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
        uploadFile(e.dataTransfer.files[0]);
    }
});

chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
    }
});

// --- Upload logic ---

async function uploadFile(file) {
    const name = file.name.toLowerCase();
    if (!name.endsWith(".xls") && !name.endsWith(".xlsx")) {
        alert("Please upload a .xls or .xlsx file.");
        return;
    }

    dropArea.innerHTML = '<div class="spinner"></div><p>Uploading...</p>';

    const formData = new FormData();
    formData.append("file", file);

    try {
        const resp = await fetch("/api/upload", { method: "POST", body: formData });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || "Upload failed");
        }

        const data = await resp.json();
        sessionId = data.session_id;

        // Switch to chat view
        document.getElementById("upload-zone").style.display = "none";
        document.getElementById("chat-area").style.display = "flex";
        document.getElementById("file-badge").textContent = "Analyzing: " + data.filename;

        // Auto-trigger initial analysis
        await sendMessage("Please analyze this payroll spreadsheet for errors and produce a full audit report.");
    } catch (err) {
        dropArea.innerHTML =
            '<div class="drop-icon">&#128196;</div><p>Upload failed: ' +
            escapeHtml(err.message) +
            '</p><p class="drop-hint">Click to try again</p>';
    }
}

// --- Chat logic ---

function handleSend() {
    const text = chatInput.value.trim();
    if (!text || isProcessing) return;
    chatInput.value = "";
    sendMessage(text);
}

async function sendMessage(text) {
    isProcessing = true;
    chatInput.disabled = true;
    sendBtn.disabled = true;

    appendMessage("user", text);
    const loadingEl = showLoading();

    try {
        const resp = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId, message: text }),
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || "Request failed");
        }

        const data = await resp.json();
        loadingEl.remove();
        appendMessage("assistant", data.reply);
    } catch (err) {
        loadingEl.remove();
        appendMessage("assistant", "**Error:** " + escapeHtml(err.message));
    } finally {
        isProcessing = false;
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }
}

// --- UI helpers ---

function appendMessage(role, content) {
    const msgs = document.getElementById("messages");
    const div = document.createElement("div");
    div.className = "message " + role;

    if (role === "assistant") {
        div.innerHTML = marked.parse(content);
    } else {
        div.textContent = content;
    }

    msgs.appendChild(div);
    div.scrollIntoView({ behavior: "smooth" });
}

function showLoading() {
    const msgs = document.getElementById("messages");
    const div = document.createElement("div");
    div.className = "message loading";
    div.innerHTML = '<div class="spinner"></div><span>Analyzing spreadsheet... this may take up to a minute.</span>';
    msgs.appendChild(div);
    div.scrollIntoView({ behavior: "smooth" });
    return div;
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}
