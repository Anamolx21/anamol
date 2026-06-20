const API_BASE_URL = window.location.origin;

function applyTheme(theme) {
    const selectedTheme = theme === "dark" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", selectedTheme);
    document.body.setAttribute("data-theme", selectedTheme);
    const toggleButtons = document.querySelectorAll(".theme-toggle");
    toggleButtons.forEach(button => {
        button.textContent = selectedTheme === "dark" ? "☀️ Light Mode" : "🌙 Dark Mode";
    });
    localStorage.setItem("studylift-theme", selectedTheme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
    applyTheme(currentTheme === "dark" ? "light" : "dark");
}

function renderHistory(entries) {
    const historyList = document.getElementById("history-list");
    if (!historyList) return;

    if (!entries || entries.length === 0) {
        historyList.innerHTML = '<div class="history-item">No study activity yet. Start with a chat or quiz.</div>';
        return;
    }

    historyList.innerHTML = entries.map(entry => `
        <div class="history-item">
            <strong>${entry.type.toUpperCase()}</strong>
            <div>${entry.content}</div>
            <small>${entry.detail}</small>
        </div>
    `).join("");
}

function loadHistory() {
    fetch(`${API_BASE_URL}/history`)
        .then(res => res.json())
        .then(data => {
            renderHistory(data.entries || []);
        });
}

function updateStreak() {
    const streakBox = document.getElementById("streak-info");
    if (!streakBox) return;

    fetch(`${API_BASE_URL}/streak`)
        .then(res => res.json())
        .then(data => {
            streakBox.innerText = data.message || "Start your first study session to build a streak.";
        });
}

function updateGoal() {
    const goalInfo = document.getElementById("goal-info");
    const goalBar = document.getElementById("goal-bar-fill");
    if (!goalInfo || !goalBar) return;

    fetch(`${API_BASE_URL}/goal`)
        .then(res => res.json())
        .then(data => {
            goalInfo.innerText = data.message || "No study actions yet today";
            goalBar.style.width = `${data.percent || 0}%`;
        });
}

function updateAiStatus() {
    const statusBox = document.getElementById("ai-status");
    if (!statusBox) return;

    fetch(`${API_BASE_URL}/status`)
        .then(res => res.json())
        .then(data => {
            const modeLabel = data.mode === "gemini" ? "AI mode: Gemini" : "AI mode: Local fallback";
            statusBox.innerText = modeLabel;
        });
}

function startApp() {
    window.location.href = "login.html";
}

function login() {
    let user = document.getElementById("username").value;
    let pass = document.getElementById("password").value;
    let msg = document.getElementById("msg");

    fetch(`${API_BASE_URL}/login`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            username: user,
            password: pass
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            msg.style.color = "green";
            msg.innerText = "Login successful! Redirecting...";

            setTimeout(() => {
                window.location.href = "dashboard.html";
            }, 1000);
        } else {
            msg.style.color = "red";
            msg.innerText = data.message;
        }
    });
}

function logout() {
    window.location.href = "index.html";
}

window.addEventListener("DOMContentLoaded", () => {
    const storedTheme = localStorage.getItem("studylift-theme");
    applyTheme(storedTheme || "light");

    if (document.getElementById("history-list")) {
        loadHistory();
    }
    updateStreak();
    updateGoal();
    updateAiStatus();

    document.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
            if (document.getElementById("user-input") && document.activeElement?.id === "user-input") {
                sendMessage();
            } else if (document.getElementById("text") && document.activeElement?.id === "text") {
                generateQuiz();
            }
        }
    });
});

function sendMessage() {
    let input = document.getElementById("user-input");
    let chatBox = document.getElementById("chat-box");

    let userText = input.value.trim();
    if (!userText) {
        chatBox.innerHTML += `<p><b>AI:</b> Please type a question or topic first.</p>`;
        return;
    }

    input.value = "";
    chatBox.innerHTML += `<p><b>You:</b> ${userText}</p>`;
    chatBox.innerHTML += `<p><b>AI:</b> Thinking...</p>`;
    chatBox.scrollTop = chatBox.scrollHeight;

    fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: userText })
    })
    .then(res => res.json())
    .then(data => {
        const messages = chatBox.innerHTML.split('<p><b>AI:</b> Thinking...</p>');
        chatBox.innerHTML = messages[0] + `<p><b>AI:</b> ${data.reply}</p>`;
        chatBox.scrollTop = chatBox.scrollHeight;
        loadHistory();
        updateStreak();
        updateGoal();
    });
}

function goBack() {
    window.location.href = "dashboard.html";
}

function uploadPDF() {
    let fileInput = document.getElementById("pdfFile");
    let file = fileInput.files[0];
    let output = document.getElementById("output");

    if (!file) {
        output.innerText = "Please choose a PDF file first.";
        return;
    }

    output.innerText = "Uploading and extracting text...";

    let formData = new FormData();
    formData.append("file", file);

    fetch(`${API_BASE_URL}/upload-pdf`, {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        output.innerText = data.summary;
        loadHistory();
        updateStreak();
        updateGoal();
    });
}

function generateQuiz() {
    let text = document.getElementById("text").value.trim();
    let output = document.getElementById("quiz-output");

    if (!text) {
        output.innerText = "Please paste some notes or a topic first.";
        return;
    }

    output.innerText = "Generating quiz...";

    fetch(`${API_BASE_URL}/generate-quiz`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ text: text })
    })
    .then(res => res.json())
    .then(data => {
        output.innerText = data.quiz;
        loadHistory();
        updateStreak();
        updateGoal();
    });
}
function generateFlashcards() {

    let text =
        document.getElementById("notes").value;

    fetch(
        "http://127.0.0.1:8000/flashcards",
        {
            method: "POST",
            headers: {
                "Content-Type":
                "application/json"
            },
            body: JSON.stringify({
                text: text
            })
        }
    )
    .then(res => res.json())
    .then(data => {

        document.getElementById("output")
        .innerText =
        data.flashcards;

    });
}