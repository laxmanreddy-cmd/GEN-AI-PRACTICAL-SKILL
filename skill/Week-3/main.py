"""Beginner-friendly command line app for the Week 3 practical."""

import os
from pathlib import Path

from dotenv import load_dotenv

from llm_client import GeminiProvider, LLMClient, OllamaProvider
from mongo_logger import MongoLogger


def main():
    load_dotenv(Path(__file__).with_name(".env"))

    print("================================")
    print("       WEEK 3: LLM MONITORING")
    print("================================")
    print("1. Gemini")
    print("2. Ollama")
    selection = input("\nSelect provider (1/2): ").strip()

    if selection == "1":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key or api_key == "YOUR_API_KEY_HERE":
            print("Gemini API key is missing. Add it to the Week-3/.env file.")
            return
        provider = GeminiProvider(
            api_key=api_key,
            model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        )
    elif selection == "2":
        provider = OllamaProvider(
            model=os.getenv("OLLAMA_MODEL", "llama3.2"),
            url=os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate"),
        )
    else:
        print("Invalid selection. Please run the program and choose 1 or 2.")
        return

    try:
        mongo_logger = MongoLogger()
        print("Connected to MongoDB.")
    except Exception as error:
        mongo_logger = None
        print(f"MongoDB is unavailable; the AI request can still run. Details: {error}")

    prompt = input("\nEnter your question: ").strip()
    if not prompt:
        print("Question cannot be empty.")
        if mongo_logger:
            mongo_logger.close()
        return

    try:
        answer = LLMClient(provider, mongo_logger).generate(prompt)
        print("\n===== AI RESPONSE =====")
        print(answer)
        print("\nRequest completed.")
    except Exception as error:
        print(f"AI request failed: {error}")
    finally:
        if mongo_logger:
            mongo_logger.close()


if __name__ == "__main__":
    main()
