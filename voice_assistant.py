
from record_audio import record_audio
from stt import transcribe_audio
from assistant import get_response
from tts import speak_text


def run_voice_assistant():
    print("\n=== Local AI Voice Assistant ===")
    print("Press Ctrl+C to exit.")

    try:
        while True:
            input("\nPress Enter to start recording...")

            # Step 1: Record the user's voice
            audio_path = record_audio()

            # Step 2: Convert speech into text
            print("\nTranscribing your speech...")
            user_text = transcribe_audio(audio_path)

            if not user_text:
                print("No speech detected. Please try again.")
                continue

            print(f"\nYou said: {user_text}")

            # Step 3: Generate an AI response
            print("\nThinking...")
            response = get_response(user_text)
            print(f"\nAssistant: {response}")

            # Step 4: Convert the response into speech
            print("\nSpeaking response...")
            speak_text(response)

    except KeyboardInterrupt:
        print("\nAssistant stopped. Goodbye!")


if __name__ == "__main__":
    run_voice_assistant()
