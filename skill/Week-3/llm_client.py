"""Provider classes and a retrying client for Gemini and local Ollama."""

from abc import ABC, abstractmethod
import time

import requests
from google import genai

from cost_calculator import calculate_cost


class LLMProvider(ABC):
    """Common interface for language model providers."""

    provider_name = "unknown"

    @property
    @abstractmethod
    def model(self):
        """Name of the configured model."""

    @abstractmethod
    def generate(self, prompt):
        """Return (answer, input token count, output token count)."""


class GeminiProvider(LLMProvider):
    provider_name = "gemini"

    def __init__(self, api_key, model="gemini-3.8-flash"):
        self._model = model
        self.client = genai.Client(api_key=api_key)

    @property
    def model(self):
        return self._model

    def generate(self, prompt):
        response = self.client.models.generate_content(
            model=self.model, contents=prompt
        )
        answer = response.text
        if not answer:
            raise RuntimeError("Gemini returned no text response.")

        usage = getattr(response, "usage_metadata", None)
        input_tokens = getattr(usage, "prompt_token_count", None) or 0
        output_tokens = getattr(usage, "candidates_token_count", None) or 0
        # Some API responses omit usage metadata. These estimates keep logs useful.
        if not input_tokens:
            input_tokens = max(1, len(prompt.split()))
        if not output_tokens:
            output_tokens = max(1, len(answer.split()))
        return answer, input_tokens, output_tokens


class OllamaProvider(LLMProvider):
    provider_name = "ollama"

    def __init__(self, model="llama3.2", url="http://localhost:11434/api/generate"):
        self._model = model
        self.url = url

    @property
    def model(self):
        return self._model

    def generate(self, prompt):
        response = requests.post(
            self.url,
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            if response.status_code == 404:
                raise RuntimeError(
                    f"Ollama model '{self.model}' was not found. "
                    f"Download it with: ollama pull {self.model}"
                ) from error
            raise
        data = response.json()
        answer = data.get("response")
        if not answer:
            raise RuntimeError("Ollama returned no text response.")
        # Ollama supplies actual token counts in these response fields.
        input_tokens = data.get("prompt_eval_count") or max(1, len(prompt.split()))
        output_tokens = data.get("eval_count") or max(1, len(answer.split()))
        return answer, input_tokens, output_tokens


class LLMClient:
    """Generate an answer, retry temporary errors, then log the outcome."""

    MAX_ATTEMPTS = 3

    def __init__(self, provider, mongo_logger=None):
        self.provider = provider
        self.mongo_logger = mongo_logger

    @staticmethod
    def _is_retryable(error):
        if isinstance(error, (requests.Timeout, requests.ConnectionError)):
            return True
        if isinstance(error, requests.HTTPError):
            status = error.response.status_code if error.response else 0
            return status in (408, 429) or status >= 500
        # Gemini SDK errors commonly expose an HTTP status code.
        status = getattr(error, "code", None) or getattr(error, "status_code", None)
        return status in (408, 429, 500, 502, 503, 504)

    def _save(self, document):
        if self.mongo_logger is None:
            return
        try:
            self.mongo_logger.log_request(document)
        except Exception as error:
            # Logging failure must never cause a successful AI call to run again.
            print(f"Warning: could not save this request to MongoDB: {error}")

    def generate(self, prompt):
        started = time.perf_counter()
        attempts = 0
        try:
            while attempts < self.MAX_ATTEMPTS:
                attempts += 1
                try:
                    answer, input_tokens, output_tokens = self.provider.generate(prompt)
                    break
                except Exception as error:
                    if attempts >= self.MAX_ATTEMPTS or not self._is_retryable(error):
                        raise
                    time.sleep(2 ** (attempts - 1))

            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            document = {
                "provider": self.provider.provider_name,
                "model": self.provider.model,
                "prompt": prompt,
                "input_tokens": int(input_tokens),
                "output_tokens": int(output_tokens),
                "total_tokens": int(input_tokens) + int(output_tokens),
                "latency_ms": latency_ms,
                "cost": calculate_cost(
                    self.provider.provider_name, self.provider.model,
                    int(input_tokens), int(output_tokens),
                ),
                "attempts": attempts,
                "status": "success",
                "error": None,
            }
            self._save(document)
            return answer
        except Exception as error:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            self._save({
                "provider": self.provider.provider_name,
                "model": self.provider.model,
                "prompt": prompt,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "latency_ms": latency_ms,
                "cost": None,
                "attempts": attempts,
                "status": "failed",
                "error": str(error),
            })
            raise
