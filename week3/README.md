# Week 3 — Full-Stack AI Chat Application

## Project Overview

A containerized full-stack chat application that integrates the AI model and skill gap analysis from Week 2 into a web-based chat interface. The system consists of two Docker services:

- **Frontend** — A FastAPI server that serves a Bootstrap 5 chat page and proxies all API requests to the backend over a private Docker network. The browser never communicates with the backend directly.
- **Backend** — A FastAPI server that receives JSON requests from the frontend and dispatches them to either the LLM (`prompt_model`) for general chat or the `find_skill_gaps` function for resume analysis.

Users can upload a PDF resume, have it parsed client-side, and ask the AI to analyze skill gaps or answer general questions.


## Setup Instructions

### Prerequisites
- Docker
- Docker compose
- uv

### Environment Variables

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your API key:

   ```dotenv
   # Required — your Google Gemini API key
   GOOGLE_API_KEY=your_gemini_api_key_here

   # Available Gemini models (comma-separated)
   GEMINI_MODELS=gemini-2.5-flash,gemini-2.5-flash-lite,gemini-3-flash-preview,gemini-3.1-flash-lite

   # Available Ollama models (requires Ollama running on the host)
   OLLAMA_MODELS=phi3,llama3.1,deepseek-r1:1.5b
   ```

### Manual Setup (without Docker)

If you prefer to run the services locally without Docker:

```bash
# Frontend
cd frontend
uv sync
uv run uvicorn --app-dir src --host 0.0.0.0 --port 8080 main:app

# Backend (in a separate terminal)
cd backend
uv sync
uv run uvicorn --app-dir src --host 0.0.0.0 --port 8000 app:app
```

When running locally, set the `BACKEND_URL` environment variable for the frontend:

```bash
export BACKEND_URL=http://localhost:8000/chat
```

## Usage

### Running with Docker Compose

```bash
cd week3
docker compose up --build
```

### Accessing the Application

Open your browser and navigate to:

```
http://localhost:8000
```

### Interacting with the Chat

| Action | How |
| --- | --- |
| **Send a message** | Type a question in the input box and press Enter or click Send. |
| **Upload a PDF resume** | Click the attachment button to select a PDF file. The file is parsed client-side using PDF.js. |
| **Find skill gaps** | Upload a PDF resume and type a message containing `"find skill gaps"` (case-insensitive). |
| **General chat with resume context** | Upload a PDF and type any other message — the resume text is appended as context to the LLM prompt. |
| **Remove PDF** | Click the Remove button on the attachment preview bar. |

### Expected Output

- **General chat:** The LLM returns a markdown-formatted response, rendered in the chat bubble.
- **Skill gap analysis:** Returns a list of missing skills identified by comparing the resume against the jobs database.

### Stopping the Application

```bash
docker compose down
```

## API / Function Reference

### Backend — `POST /chat`

The backend exposes a single endpoint that dispatches to the appropriate Week 2 function.

**Request:**

```json
{
  "message": "analyze my gaps",
  "pdf_text": "Extracted text from a PDF resume...",
  "model": "gemini-6.7-lite"
}
```

| Field      | Type              | Required | Description |
| ---------- | ----------------- | -------- | ----------- |
| `message`  | `string`          | Yes      | The user's chat message. |
| `pdf_text` | `string` or `null`| No       | Extracted text from a PDF resume. |
| `model`    | `string` or `null`| No       | The ID of the LLM model selected by the client (defaults to backend fallback). |

**Response:**

```json
{
  "response": "LLM response text or list of skill gaps"
}
```

**Routing Logic:**

| Condition | Action |
| --- | --- |
| LLM Intention Function determines if user wants skill gaps message and resume PDF provided | Calls `find_skill_gaps()`, returns a list of missing skills. |
| LLM Intention Function determines if user wants skill gaps + no resume PDF | Returns a prompt asking the user to upload a resume PDF. |
| Any other message (with or without PDF) | Forwards to `prompt_model()` with the message (and resume as context if provided). |
| No message and no PDF | Returns a default prompt. |

### Frontend — `POST /chat` (Proxy)

The frontend exposes the same `/chat` endpoint as a proxy. It receives the JSON payload from the browser and forwards it to the backend service over the internal Docker network using `httpx.Client`.

### Frontend — Key JavaScript Functions

| Function | Description |
| --- | --- |
| `sendMessage()` | Collects user input and extracted PDF text, sends a `POST /chat` request to the frontend proxy, and appends the response to the chat history. |
| `parsePdf(file)` | Uses PDF.js to extract text content from a PDF file client-side. Returns the extracted text as a string. |
| `appendMessage(text, sender, filename)` | Creates a chat bubble in the DOM. Bot messages are rendered as markdown using `marked.js`; user messages are plain text. Array responses (e.g., skill gaps) are converted to a bullet list. |
| `appendTyping()` | Inserts a temporary "Thinking..." bubble while waiting for the backend response. |
| `clearAttachment()` | Resets the PDF attachment state and hides the preview bar. |

### Service Communication

```
Browser ──POST /chat──► Frontend (port 8000)
                            │
                    httpx.Client.post()
                            │
                            ▼
                        Backend (port 8000 inside container, exposed on 8001)
                            │
                     ┌──────┴──────┐
                     ▼             ▼
              find_skill_gaps  prompt_model
                     │             │
                     └──────┬──────┘
                            ▼
            Ollama (Local) OR Gemini (Cloud)
```

The backend is now accessible from the host machine on port `8001`, though the frontend continues to proxy requests internally via the `chat_network` on port `8000`.

---

## Data / Assumptions

### JSON Message Format

All communication between the browser, frontend, and backend uses JSON:

- **Browser → Frontend:** `{ "message": "...", "pdf_text": "..." | null }`
- **Frontend → Backend:** Same JSON payload, forwarded via `httpx`.
- **Backend → Frontend → Browser:** `{ "response": "..." }` (string or list)

### Assumptions

- **PDF Processing:** PDFs are parsed entirely client-side using PDF.js. Only the extracted text is sent to the backend — the raw PDF file never leaves the browser.
- **Input Limitations:** Very large PDFs may cause slow extraction in the browser. There is no enforced file size limit.
- **Intent Classification:** The `find_skill_gaps` function is triggered dynamically using an LLM-based intent function. The selected LLM analyzes the message to determine if the user wants to analyze skill gaps before routing.
- **Dynamic Models:** The frontend dynamically fetches the list of available models from the backend via `GET /api/available-models` to populate the dropdown.
- **Week 2 Integration:** The `find_skill_gaps` and `prompt_model` functions from Week 2 are imported directly into the backend. The jobs database (`jobs_d3_eval.db`) is bundled inside the backend container image.
- **Ollama Models:** Using Ollama-based models requires the Ollama server to be running on the host machine. The backend connects to it via `host.docker.internal:11434`.

### Data Flow

1. User types a message and optionally attaches a PDF in the browser.
2. PDF.js extracts text from the PDF client-side.
3. The browser sends a JSON `POST /chat` request to the frontend server (same origin).
4. The frontend proxy forwards the JSON payload to the backend over the Docker network.
5. The backend uses the LLM to classify the intent of the message:
   - If the intent is to find skill gaps and PDF text is present: writes the text to a temp file, runs `find_skill_gaps()`, returns the gaps list.
   - Otherwise: forwards the message (with optional resume context) to `prompt_model()`.
6. The backend returns a JSON response.
7. The frontend proxy passes the response back to the browser.
8. The browser renders the response as markdown in a chat bubble using `marked.js`.

---

## Testing

### Frontend Testing

| Test Case | Steps | Expected Result |
| --- | --- | --- |
| Page loads | Navigate to `http://localhost:8000` | UI fetches available models, selects one, and auto-sends an initial prompt. Bot replies with a dynamic greeting. |
| Send a message | Type "Hello" and press Enter | User bubble appears, inputs are disabled during processing, bot responds. |
| Upload PDF | Click attachment, select a PDF | Preview bar shows filename and size, status shows "PDF Loaded". |
| Upload non-PDF | Click attachment, select a `.txt` file | Alert: "Only PDF files are supported." |
| Skill gap analysis | Upload PDF, ask "What am I missing?", send | LLM classifies intent and returns a list of missing skills. |
| Remove attachment | Click Remove on the preview bar | Preview bar disappears, status resets to "Ready". |

### Backend Testing with `curl`

```bash
# General chat (Frontend Proxy)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is Python?", "model": "gemini-3.1-flash-lite"}'

# Skill gap analysis directly to Backend (port 8001)
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "analyze my gaps", "pdf_text": "Python, Docker...", "model": "gemini-3.1-flash-lite"}'

# Get available models
curl http://localhost:8001/api/available-models
```

## Limitations

- No chat history persistence, the conversation is stored locally on browser. The chat history is reset on refresh.
- No streaming, the LLM response are return as a whole. It's not token-by-token basis.
- Only text PDF are supported.
- The quality of responses and skill gap analysis depends on the underlying LLM. Results may be inaccurate or incomplete.
- Backend only uses single synchronous endpoint. As local LLM are not multiprocessing friendly.

## Architecture Reflection

### Design Choices

The application uses a **microservices architecture** with a clear frontend/backend separation:

- The frontend handles presentation, user interaction, and PDF parsing. The backend handles AI model orchestration and business logic (skill gap analysis). This separation allows each service to be developed, tested, and scaled independently.
- The frontend asks the backend (`/api/available-models`) for a list of valid, online models instead of hardcoding them. This prevents the UI from offering dead models.
- Instead of relying on a rigid keyword like `"find skill gaps"`, the backend uses the LLM to dynamically determine if the user's intent is to analyze their resume, making the interface more natural.
- Each service runs in its own container with its own virtual environment built via `uv`. This eliminates "works on my machine" issues and makes deployment reproducible.
- Using PDF.js to extract text in the browser avoids uploading raw files to the server, reducing bandwidth usage and backend complexity.

### Trade-offs

- The chat interface uses vanilla Bootstrap and JavaScript instead of a framework like React or Vue. This keeps the codebase small and dependency-free on the frontend, but limits scalability for more complex UI features.
- Extra API Call and Latency Using LLM for Intent Classification
- Both the frontend proxy and backend use synchronous request handling. This simplifies the code and avoids async complexity, but limits throughput under concurrent load.
- Docker Compose provides a single-command deployment (`docker compose up --build`), prioritizing developer experience over production-grade orchestration (e.g., Kubernetes).

### Improvements

Given more time, the following improvements would be considered:

- Store conversation history in a database (e.g., SQLite or PostgreSQL) so users can resume sessions.
- Implement Server-Sent Events (SSE) to stream LLM responses token-by-token for a more responsive user experience.
- Migrate to a framework like React or Vue for better state management and component reusability.
- Use better LLM Model as the current selections are not that great at reasoning and also add more models to choose from.
