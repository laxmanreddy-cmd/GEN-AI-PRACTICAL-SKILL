"""Small, easy-to-edit cost estimates for supported models."""

# Sample prices in USD per 1 million tokens. Replace with verified current
# provider pricing before using these estimates for billing decisions.
GEMINI_SAMPLE_PRICING_PER_MILLION = {
    # Example configuration; update the model name and rates as needed.
    "gemini-3.8-flash": {"input": 0.10, "output": 0.40},
}


def calculate_cost(provider, model, input_tokens, output_tokens):
    """Return estimated USD cost, 0.0 for Ollama, or None if unconfigured."""
    if provider.lower() == "ollama":
        return 0.0
    if provider.lower() != "gemini":
        return None

    rates = GEMINI_SAMPLE_PRICING_PER_MILLION.get(model)
    if rates is None:
        return None

    return (
        input_tokens * rates["input"] + output_tokens * rates["output"]
    ) / 1_000_000
