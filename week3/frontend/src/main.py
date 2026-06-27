import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

# Load env variables from .env if present
load_dotenv()

app = FastAPI()

# Setup Jinja2 templates path
templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Read the backend API URL from the environment variable (fallback to localhost)
backend_url = os.environ.get("BACKEND_URL", "http://localhost:8000/chat")

@app.get("/", response_class=HTMLResponse)
def get_chat_page(request: Request):
    return templates.TemplateResponse(
        request,
        "chat_page.html",
        {"backend_url": backend_url}
    )
