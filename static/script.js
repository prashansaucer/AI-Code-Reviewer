let latestMarkdown = "";
let latestOptimizedCode = "";
let latestLanguage = "txt";


async function reviewCode() {
    const codeInput = document.getElementById("code");
    const mode = document.getElementById("reviewMode").value;
    const code = codeInput.value.trim();

    if (!code) {
        showError("Please paste some code before reviewing.");
        codeInput.focus();
        return;
    }

    setLoading(true);

    try {
        const response = await fetch("/review", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ code, mode })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || "The review request failed."
            );
        }

        latestMarkdown = data.markdown || "";
        latestOptimizedCode = extractOptimizedCode(latestMarkdown);
        latestLanguage = detectLanguage(latestMarkdown);

        const result = document.getElementById("result");

        result.className = "result-box";
        result.innerHTML = data.result;

        document
            .getElementById("resultActions")
            .classList.remove("hidden");

        setStatus("Completed", "success");
        saveHistory(code, mode);

    } catch (error) {
        showError(error.message);
    } finally {
        setLoading(false);
    }
}


function setLoading(loading) {
    const button = document.getElementById("reviewButton");
    const buttonText = document.getElementById("buttonText");
    const result = document.getElementById("result");

    button.disabled = loading;
    buttonText.textContent = loading ? "Reviewing..." : "Review Code";

    if (!loading) return;

    setStatus("Analyzing", "loading");

    document
        .getElementById("resultActions")
        .classList.add("hidden");

    result.className = "result-box";
    result.innerHTML = `
        <div class="loading-content">
            <div class="loader"></div>
            <h3>Analyzing your code</h3>
            <p>
                Checking correctness, security, complexity
                and performance...
            </p>
        </div>
    `;
}


function setStatus(text, type = "") {
    const badge = document.getElementById("statusBadge");

    badge.textContent = text;
    badge.className = `status-badge ${type}`.trim();
}


function showError(message) {
    const result = document.getElementById("result");

    result.className = "result-box";

    result.innerHTML = `
        <div class="error-message">
            <div class="empty-icon">!</div>
            <h3>Review failed</h3>
            <p>${escapeHtml(message)}</p>
        </div>
    `;

    setStatus("Error", "error");
}


function extractOptimizedCode(markdown) {
    const section = markdown.split(
        /## Correct and Optimized Code/i
    )[1];

    if (!section) return "";

    const match = section.match(/```[\w+#.-]*\n([\s\S]*?)```/);

    return match ? match[1].trim() : "";
}


function detectLanguage(markdown) {
    const match = markdown.match(
        /## Language Detected\s+([^\n#]+)/i
    );

    if (!match) return "txt";

    const language = match[1].trim().toLowerCase();

    const extensions = {
        python: "py",
        javascript: "js",
        typescript: "ts",
        java: "java",
        c: "c",
        "c++": "cpp",
        cpp: "cpp",
        "c#": "cs",
        html: "html",
        css: "css",
        php: "php",
        ruby: "rb",
        go: "go",
        rust: "rs",
        kotlin: "kt",
        swift: "swift",
        sql: "sql"
    };

    return extensions[language] || "txt";
}


async function copyOptimizedCode() {
    if (!latestOptimizedCode) {
        showToast("Optimized code was not found.");
        return;
    }

    await navigator.clipboard.writeText(latestOptimizedCode);
    showToast("Optimized code copied.");
}


function downloadOptimizedCode() {
    if (!latestOptimizedCode) {
        showToast("Optimized code was not found.");
        return;
    }

    downloadFile(
        `optimized-code.${latestLanguage}`,
        latestOptimizedCode
    );
}


function downloadReview() {
    if (!latestMarkdown) {
        showToast("No review is available.");
        return;
    }

    downloadFile("code-review.md", latestMarkdown);
}


function downloadFile(filename, content) {
    const blob = new Blob(
        [content],
        { type: "text/plain;charset=utf-8" }
    );

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = filename;
    link.click();

    URL.revokeObjectURL(url);
}


function clearCode() {
    document.getElementById("code").value = "";

    latestMarkdown = "";
    latestOptimizedCode = "";

    document
        .getElementById("resultActions")
        .classList.add("hidden");

    document.getElementById("result").className =
        "result-box empty-state";

    document.getElementById("result").innerHTML = `
        <div class="empty-icon">✦</div>
        <h3>Your review will appear here</h3>
        <p>Paste your code and start the AI review.</p>
    `;

    setStatus("Ready");
}


function saveHistory(code, mode) {
    const history = JSON.parse(
        localStorage.getItem("reviewHistory") || "[]"
    );

    history.unshift({
        preview: code.slice(0, 80),
        mode,
        date: new Date().toLocaleString()
    });

    localStorage.setItem(
        "reviewHistory",
        JSON.stringify(history.slice(0, 6))
    );

    renderHistory();
}


function renderHistory() {
    const list = document.getElementById("historyList");
    const history = JSON.parse(
        localStorage.getItem("reviewHistory") || "[]"
    );

    if (!history.length) {
        list.innerHTML = `
            <p class="history-empty">No reviews yet.</p>
        `;
        return;
    }

    list.innerHTML = history.map(item => `
        <article class="history-card">
            <div>
                <strong>${escapeHtml(item.mode)} review</strong>
                <p>${escapeHtml(item.preview)}...</p>
            </div>
            <span>${escapeHtml(item.date)}</span>
        </article>
    `).join("");
}


function clearHistory() {
    localStorage.removeItem("reviewHistory");
    renderHistory();
}


function showToast(message) {
    const oldToast = document.querySelector(".toast");

    if (oldToast) oldToast.remove();

    const toast = document.createElement("div");

    toast.className = "toast";
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 2500);
}


function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


document
    .getElementById("code")
    .addEventListener("keydown", function (event) {
        if (event.key === "Tab") {
            event.preventDefault();

            const start = this.selectionStart;
            const end = this.selectionEnd;

            this.value =
                this.value.substring(0, start) +
                "    " +
                this.value.substring(end);

            this.selectionStart =
                this.selectionEnd = start + 4;
        }

        if (event.ctrlKey && event.key === "Enter") {
            reviewCode();
        }
    });


renderHistory();