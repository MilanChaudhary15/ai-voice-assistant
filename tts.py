
from pathlib import Path
import subprocess
import sys
import sounddevice as sd
import soundfile as sf

MODEL_PATH = Path("models/piper/en_US-lessac-medium.onnx")
OUTPUT_PATH = Path("recordings/assistant_response.wav")


def speak_text(text: str) -> None:
    """Generate and play speech locally using Piper TTS."""

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Voice model not found: {MODEL_PATH.resolve()}"
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Generate speech
    subprocess.run(
        [
            sys.executable,
            "-m",
            "piper",
            "--model", str(MODEL_PATH),
            "--output_file", str(OUTPUT_PATH),
        ],
        input=text,
        text=True,
        check=True,
    )

    # Play the generated WAV file
    audio, sample_rate = sf.read(str(OUTPUT_PATH), dtype="float32")
    sd.play(audio, sample_rate)
    sd.wait()

    print("Speech playback completed.")


if __name__ == "__main__":
    speak_text(
        "Hello Milan! Your local AI voice assistant is ready."
    )
