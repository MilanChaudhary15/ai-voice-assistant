
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5:3b"

# Keep the conversation history between turns.
conversation_history = [
    {
        "role": "system",
        "content": (
            "You are a helpful voice assistant. "
            "Give clear, concise, natural-sounding answers. "
            "Respond in the language used by the user."
        ),
    }
]


def get_response(user_message: str) -> str:
    """Send a message to Ollama and preserve conversation context."""

    conversation_history.append({
        "role": "user",
        "content": user_message,
    })

    payload = {
        "model": MODEL_NAME,
        "messages": conversation_history,
        "stream": False,
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=180,
        )
        response.raise_for_status()

        answer = response.json()["message"]["content"]

        conversation_history.append({
            "role": "assistant",
            "content": answer,
        })

        return answer

    except requests.RequestException as error:
        # Remove the unanswered user message so history stays consistent.
        conversation_history.pop()
        return f"Could not connect to Ollama: {error}"


if __name__ == "__main__":
    print("Local Voice Assistant - LLM Test")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() == "exit":
            print("Goodbye!")
            break

        if not user_input:
            continue

        print("\nAssistant:", get_response(user_input), "\n")

