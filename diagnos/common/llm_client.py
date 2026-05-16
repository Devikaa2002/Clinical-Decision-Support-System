"""
LLM Client using Groq API (Free Tier).
Model: Llama 3.3 70B Versatile - open-source, fast inference.
"""

import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


def get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        raise ValueError(
            "GROQ_API_KEY not set! Get your free key at https://console.groq.com/keys"
        )
    return Groq(api_key=api_key)


def chat(
    system_prompt: str,
    user_message: str,
    model: str = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """Simple chat completion. Returns the text response."""
    client = get_client()
    model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def chat_json(
    system_prompt: str,
    user_message: str,
    model: str = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> dict:
    """Chat completion that returns parsed JSON."""
    client = get_client()
    model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )

    text = response.choices[0].message.content
    return json.loads(text)


def chat_with_tools(
    system_prompt: str,
    user_message: str,
    tools: list[dict],
    model: str = None,
    temperature: float = 0.1,
) -> dict:
    """Chat completion with tool/function calling."""
    client = get_client()
    model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        tools=tools,
        tool_choice="auto",
        temperature=temperature,
        max_tokens=2048,
    )

    message = response.choices[0].message
    return {
        "content": message.content,
        "tool_calls": [
            {
                "id": tc.id,
                "function": {
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                },
            }
            for tc in (message.tool_calls or [])
        ],
    }