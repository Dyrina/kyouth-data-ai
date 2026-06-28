import os
import tempfile
import ollama
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from week2.find_skill_gaps import find_skill_gaps
from week2.prompt_model import prompt_model

app = FastAPI()

# Default database path and model name
current_dir = Path(__file__).resolve().parent
DB_PATH = os.environ.get("DATABASE_PATH", str(current_dir / "week2" / "data" / "jobs_d3_eval.db"))
MODEL_NAME = os.environ.get("DEFAULT_MODEL", "gemini-3.1-flash-lite")

@app.get("/api/available-models")
def get_available_models():
    gemini_models = [m.strip() for m in os.environ.get("GEMINI_MODELS", "").split(",") if m.strip()]
    ollama_expected = [m.strip() for m in os.environ.get("OLLAMA_MODELS", "").split(",") if m.strip()]
    
    alive_ollama = []
    try:
        # Check who is actually alive
        response = ollama.list()
        alive_names = [m.model for m in response.models]
        
        # We can either return all alive ones, or only those matching our expected list.
        # Returning only the ones that match expected (and ignoring the :latest tag if not in expected)
        for expected in ollama_expected:
            # simple match (e.g., expected="phi3" matches "phi3:latest")
            if any(expected in name for name in alive_names):
                alive_ollama.append(expected)
    except Exception:
        pass # Ollama is dead or unreachable, leave list empty
        
    return JSONResponse(content={
        "gemini": gemini_models,
        "ollama": alive_ollama,
        "default": MODEL_NAME
    })


class ChatRequest(BaseModel):
    message: str
    pdf_text: Optional[str] = None
    model: Optional[str] = None


@app.post("/chat")
def chat_endpoint(payload: ChatRequest):
    message = payload.message
    pdf_text = payload.pdf_text or ""
    model_name = payload.model or MODEL_NAME

    # Use the selected LLM to determine if the user is asking for a skill gap analysis
    intent_prompt = (
        "You are an intent classifier. Does the following message ask to analyze, find, or evaluate "
        "skill gaps or missing skills based on a resume? "
        "Reply ONLY with 'YES' or 'NO'. Do not explain.\n\n"
        f"Message: '{message}'"
    )
    intent_response = prompt_model(model_name, intent_prompt)
    
    # Run skill gap analysis only when the intent is YES AND a PDF is attached
    if "yes" in intent_response.strip().lower():
        if pdf_text:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
                f.write(pdf_text)
                tmp_path = Path(f.name)
            try:
                result = find_skill_gaps(str(tmp_path), DB_PATH)
                return JSONResponse(content={"response": result.gaps})
            finally:
                tmp_path.unlink()
        else:
            return JSONResponse(content={"response": "Please upload a PDF resume to find skill gaps."})

    # For all other messages, forward to the LLM (include PDF context if provided)
    if message:
        prompt = f"{message}\n\nResume:\n{pdf_text}" if pdf_text else message
        return JSONResponse(content={"response": prompt_model(model_name, prompt)})

    return JSONResponse(content={"response": "Please provide a message or upload a PDF."})
