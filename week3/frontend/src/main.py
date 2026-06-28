import os
import httpx
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

app = FastAPI()

templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

BACKEND_BASE_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
BACKEND_CHAT_URL = f"{BACKEND_BASE_URL}/chat"

http_client = httpx.Client(timeout=120.0)


class ChatRequest(BaseModel):
    message: str
    pdf_text: str | None = None
    model: str | None = None


@app.get("/", response_class=HTMLResponse)
def get_chat_page(request: Request):
    gemini_models, ollama_models, default_model = [], [], ""

    try:
        resp = http_client.get(f"{BACKEND_BASE_URL}/api/available-models")
        if resp.status_code == 200:
            data = resp.json()
            gemini_models = data.get("gemini", [])
            ollama_models = data.get("ollama", [])
            default_model = data.get("default", "")
    except Exception as e:
        print(f"Warning: Could not fetch models from backend: {e}")

    return templates.TemplateResponse(
        request=request,
        name="chat_page.html",
        context={
            "backend_url": "/chat",
            "gemini_models": gemini_models,
            "ollama_models": ollama_models,
            "default_model": default_model,
        },
    )


@app.post("/chat")
def chat_endpoint(payload: ChatRequest):
    try:
        response = http_client.post(BACKEND_CHAT_URL, json=payload.model_dump())
        return JSONResponse(content=response.json(), status_code=response.status_code)
    except httpx.RequestError as e:
        return JSONResponse(
            status_code=503,
            content={"error": f"AI Backend Service Unavailable: {str(e)}"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"error": f"Frontend Proxy Error: {str(e)}"}
        )
