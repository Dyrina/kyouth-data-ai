import os
import tempfile
import ollama
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from week2.find_skill_gaps import find_skill_gaps
from week2.prompt_model import prompt_model

app = FastAPI()

current_dir = Path(__file__).resolve().parent
DB_PATH = str(
    current_dir / os.environ.get("DATABASE_PATH", "week2/data/jobs_d3_eval.db")
)
MODEL_NAME = os.environ.get("DEFAULT_MODEL", "gemini-3.1-flash-lite")

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
ollama_client = ollama.Client(host=OLLAMA_HOST)


@app.get("/api/available-models")
def get_available_models():
    gemini_models = [
        m.strip() for m in os.environ.get("GEMINI_MODELS", "").split(",") if m.strip()
    ]
    ollama_expected = [
        m.strip() for m in os.environ.get("OLLAMA_MODELS", "").split(",") if m.strip()
    ]

    alive_ollama = []
    try:
        response = ollama_client.list()
        alive_names = [m.model for m in response.models]

        for expected in ollama_expected:
            if any(expected in name for name in alive_names):
                alive_ollama.append(expected)
    except Exception as e:
        print(f"Ollama offline during model scan: {e}")

    return JSONResponse(
        content={"gemini": gemini_models, "ollama": alive_ollama, "default": MODEL_NAME}
    )


class ChatRequest(BaseModel):
    message: str
    pdf_text: str | None = None
    model: str | None = None


@app.post("/chat")
def chat_endpoint(payload: ChatRequest):
    message = payload.message.strip()
    pdf_text = payload.pdf_text or ""
    model_name = payload.model or MODEL_NAME

    if not message and not pdf_text:
        return JSONResponse(
            status_code=400, content={"response": "Please provide a prompt or a PDF."}
        )
    intent_prompt = (
        "Does the following message ask to analyze or find missing job skills based on a resume? "
        "Reply strictly with only the word YES or NO.\n\n"
        f"Message: '{message}'"
    )
    intent = prompt_model(model_name, intent_prompt).strip().lower()

    if intent == "yes":
        if not pdf_text:
            return JSONResponse(
                content={
                    "response": "Please upload a PDF resume to run a Skill Gap Analysis."
                }
            )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(pdf_text)
            tmp_path = Path(f.name)
        try:
            result = find_skill_gaps(str(tmp_path), DB_PATH)
            return JSONResponse(content={"response": result.gaps})
        finally:
            tmp_path.unlink(missing_ok=True)

    prompt = (
        f"{message}\n\n[Attached Resume Context]:\n{pdf_text}" if pdf_text else message
    )
    ai_answer = prompt_model(model_name, prompt)
    return JSONResponse(content={"response": ai_answer})
