import os
import sys
import ollama
from dotenv import load_dotenv
from google import genai
from google.genai import errors


load_dotenv()


def call_gemini(model: str, prompt: str) -> str:
    try:
        client = genai.Client()
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
        return response.text
    except errors.APIError as e:
        return f"[Gemini Error] API Error: {str(e.code)} {str(e.message)}"
    except Exception as e:
        return f"[Gemini Error] Unexpected error: {str(e)}"


def call_ollama(model: str, prompt: str) -> str:
    try:
        response = ollama.generate(model=model, prompt=prompt)
        return response.get(
            "response", f"[Ollama Error] Unexpected response structure: {response}"
        )
    except Exception as e:
        return f"[Ollama Error] Connection failed: {str(e)}"


def prompt_model(model: str, prompt: str) -> str:
    gemini_models = [
        m.strip() for m in os.environ.get("GEMINI_MODELS").split(",") if m.strip()
    ]
    ollama_models = [
        m.strip() for m in os.environ.get("OLLAMA_MODELS").split(",") if m.strip()
    ]

    if model not in gemini_models and model not in ollama_models:
        print(f"Error: Invalid model '{model}'.")
        print(f"Available Gemini models: {', '.join(gemini_models)}")
        print(f"Available Local models: {', '.join(ollama_models)}")
        sys.exit(1)

    if model in gemini_models:
        return call_gemini(model, prompt)
    else:
        return call_ollama(model, prompt)


def main():
    if len(sys.argv) != 3:
        print("Usage: uv run prompt_model.py <model> <prompt>")
        sys.exit(1)

    model = sys.argv[1]
    prompt = sys.argv[2]

    response = prompt_model(model, prompt)
    print("\n--- RESPONSE ---\n")
    print(response)


if __name__ == "__main__":
    main()
