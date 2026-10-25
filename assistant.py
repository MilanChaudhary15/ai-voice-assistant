import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5:3b"

SYSTEM_MESSAGE = {
    "role": "system",
    "content": (
        "You are a helpful voice assistant. "
        "Give clear, concise, natural-sounding answers. "
        "Respond in the language used by the user."
    ),
}

# Backward-compatible history for terminal use.
conversation_history = [SYSTEM_MESSAGE.copy()]


def get_response(user_message: str, history=None) -> str:
    """Send a message to Ollama. Pass a per-session history when using Streamlit."""
    active_history = history if history is not None else conversation_history

    active_history.append({"role": "user", "content": user_message})
    payload = {
        "model": MODEL_NAME,
        "messages": active_history,
        "stream": False,
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=180)
        response.raise_for_status()
        answer = response.json()["message"]["content"]
        active_history.append({"role": "assistant", "content": answer})
        return answer
    except requests.RequestException as error:
        # Keep history consistent if Ollama cannot answer.
        if active_history and active_history[-1].get("role") == "user":
            active_history.pop()
        return f"Could not connect to Ollama: {error}"


if __name__ == "__main__":
    print("Local Voice Assistant - LLM Test")
    print("Type 'exit' to quit.\n")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        if user_input:
            print("\nAssistant:", get_response(user_input), "\n")


