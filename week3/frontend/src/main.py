import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional
import httpx

# Load env variables from .env if present
load_dotenv()

app = FastAPI()

# Setup Jinja2 templates path
templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Read the backend API URL from the environment variable (inside the container network, this is http://backend:8000/chat)
backend_service_url = os.environ.get("BACKEND_URL", "http://localhost:8000/chat")
backend_base_url = backend_service_url.replace("/chat", "")

class ChatRequest(BaseModel):
    message: str
    pdf_text: Optional[str] = None
    model: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
def get_chat_page(request: Request):
    """
    Renders the chat page and configures the client JS to call the same-origin relative URL "/chat".
    Also fetches the available models dynamically from the backend.
    """
    gemini_models = []
    ollama_models = []
    default_model = ""
    
    try:
        with httpx.Client() as client:
            resp = client.get(f"{backend_base_url}/api/available-models", timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                gemini_models = data.get("gemini", [])
                ollama_models = data.get("ollama", [])
                default_model = data.get("default", "")
    except Exception as e:
        print(f"Warning: Could not fetch models from backend: {e}")

    return templates.TemplateResponse(
        request,
        "chat_page.html",
        {
            "backend_url": "/chat",
            "gemini_models": gemini_models,
            "ollama_models": ollama_models,
            "default_model": default_model,
        }
    )

@app.post("/chat")
def chat_endpoint(payload: ChatRequest):
    """
    Acts as a proxy, forwarding user chat requests to the backend server synchronously.
    """
    with httpx.Client() as client:
        try:
            response = client.post(
                backend_service_url,
                json=payload.model_dump(),
                timeout=120.0
            )
            return JSONResponse(content=response.json())
        except Exception as e:
            return JSONResponse(content={"response": f"Error communicating with backend service: {str(e)}"})
