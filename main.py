import json
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pypdf import PdfReader

try:
    import google.generativeai as genai
except Exception:
    genai = None

BASE_DIR = Path(__file__).resolve().parent
API_KEY = os.getenv("GEMINI_API_KEY")

if genai is not None and API_KEY:
    genai.configure(api_key=API_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

users = {
    "admin": "1234",
    "student": "study",
}


def get_ai_status() -> dict:
    return {
        "ai_enabled": bool(API_KEY and genai is not None),
        "mode": "gemini" if (API_KEY and genai is not None) else "local-fallback",
    }


def summarize_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return "Please upload or paste some text to summarize."

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    key_points = []
    for sentence in sentences[:3]:
        if len(sentence) > 20:
            key_points.append(f"- {sentence}")

    if not key_points:
        key_points = [f"- {cleaned[:200]}..."]

    return "Summary:\n" + "\n".join(key_points)


def build_chat_reply(message: str) -> str:
    normalized = message.lower()
    if genai is not None and API_KEY:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(
                f"You are a helpful study tutor. Answer briefly and clearly: {message}"
            )
            return response.text.strip()
        except Exception:
            pass

    if "quiz" in normalized:
        return "I can help you make a quiz. Paste your notes and I will turn them into practice questions."
    if "pdf" in normalized:
        return "Upload a PDF and I will generate a short study summary for you."
    if "photo" in normalized or "photosynthesis" in normalized:
        return "Photosynthesis is the process plants use to make food from sunlight, water, and carbon dioxide. Study tip: remember the inputs and the output."
    return f"You asked about: {message}. I can help you study this topic by turning it into notes, flashcards, or quiz questions."


def build_quiz_from_text(text: str) -> str:
    if genai is not None and API_KEY:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(
                f"Turn the following study notes into a short quiz with 3 questions and answers. Notes: {text}"
            )
            return response.text.strip()
        except Exception:
            pass

    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return "Please paste some study notes to generate a quiz."

    words = [word for word in re.split(r"[^a-zA-Z0-9]+", cleaned) if word]
    meaningful_words = [word for word in words if word.lower() not in {"the", "a", "an", "and", "of", "to", "is", "in", "for", "on", "are", "with", "this", "that", "it"}]
    topic = meaningful_words[0] if meaningful_words else (words[0] if words else "topic")
    quiz = [
        f"1. What is the main idea of the topic '{topic}'?",
        "2. Name one important detail mentioned in the text.",
        "3. Why is this concept useful for studying?",
    ]
    return "Quiz:\n" + "\n".join(quiz)


def extract_text_from_pdf(path: Path) -> str:
    try:
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages).strip()
        return re.sub(r"\s+", " ", text)
    except Exception:
        return ""


def load_session_store(path: Path | None = None) -> dict:
    store_path = path or BASE_DIR / "study_sessions.json"
    if store_path.exists():
        try:
            return json.loads(store_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"entries": []}
    return {"entries": []}


def get_streak_info(path: Path | None = None) -> dict:
    store = load_session_store(path)
    entries = store.get("entries", [])
    if not entries:
        return {"streak": 0, "message": "Start your first study session to build a streak."}

    dates = []
    for entry in entries:
        timestamp = entry.get("timestamp")
        if timestamp:
            try:
                parsed = datetime.fromisoformat(timestamp)
                dates.append(parsed.date())
            except ValueError:
                continue
        else:
            dates.append(date.today())

    if not dates:
        return {"streak": 0, "message": "Start your first study session to build a streak."}

    unique_dates = sorted(set(dates), reverse=True)
    streak = 1
    current = unique_dates[0]
    for day in unique_dates[1:]:
        if current - day == timedelta(days=1):
            streak += 1
            current = day
        else:
            break

    if streak == 1:
        message = "You are on a 1-day study streak. Keep going!"
    else:
        message = f"Amazing! You are on a {streak}-day study streak."

    return {"streak": streak, "message": message}


def get_daily_goal_progress(path: Path | None = None) -> dict:
    store = load_session_store(path)
    entries = store.get("entries", [])
    today = date.today().isoformat()
    completed = 0
    for entry in entries:
        timestamp = entry.get("timestamp")
        if not timestamp:
            continue
        try:
            if datetime.fromisoformat(timestamp).date().isoformat() == today:
                completed += 1
        except ValueError:
            continue

    percent = min(100, int((completed / 3) * 100)) if completed else 0
    return {
        "completed": completed,
        "goal": 3,
        "percent": percent,
        "message": f"{completed}/3 study actions today" if completed else "No study actions yet today",
    }


def append_session_entry(entry_type: str, content: str, detail: str, path: Path | None = None) -> list[dict]:
    store_path = path or BASE_DIR / "study_sessions.json"
    store = load_session_store(store_path)
    entry = {
        "type": entry_type,
        "content": content,
        "detail": detail,
        "timestamp": datetime.now().isoformat(),
    }
    store.setdefault("entries", []).insert(0, entry)
    store_path.write_text(json.dumps(store, indent=2), encoding="utf-8")
    return store["entries"]


@app.get("/")
def read_root():
    return FileResponse(BASE_DIR / "index.html")


@app.get("/history")
def history():
    return load_session_store()


@app.get("/status")
def status():
    return get_ai_status()


@app.get("/streak")
def streak():
    return get_streak_info()


@app.get("/goal")
def goal():
    return get_daily_goal_progress()


@app.get("/{page_name}")
def serve_page(page_name: str):
    allowed_files = {
        "index.html",
        "login.html",
        "dashboard.html",
        "frontend.html",
        "frontend.css",
        "frontend.js",
    }

    if page_name in allowed_files:
        file_path = BASE_DIR / page_name
        if file_path.exists():
            return FileResponse(file_path)

    raise HTTPException(status_code=404, detail="Page not found")


@app.post("/login")
def login(data: dict):
    username = data.get("username")
    password = data.get("password")

    if username in users and users[username] == password:
        return {"success": True, "message": "Login successful"}

    return {"success": False, "message": "Invalid credentials"}


@app.post("/chat")
def chat(data: dict):
    message = data.get("message", "")
    reply = build_chat_reply(message)
    append_session_entry("chat", message, reply)
    return {"reply": reply}


@app.post("/upload-pdf")
def upload_pdf(file: UploadFile = File(...)):
    tmp_path = BASE_DIR / file.filename
    try:
        contents = file.file.read()
        tmp_path.write_bytes(contents)
        extracted_text = extract_text_from_pdf(tmp_path)
        summary = summarize_text(extracted_text) if extracted_text else "No readable text found in the uploaded PDF."
        append_session_entry("pdf", file.filename, summary)
        return {"summary": summary}
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


@app.post("/generate-quiz")
def generate_quiz(data: dict):
    text = data.get("text", "")
    quiz = build_quiz_from_text(text)
    append_session_entry("quiz", text[:80], quiz)
    return {"quiz": quiz}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
