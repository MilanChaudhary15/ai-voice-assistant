from pathlib import Path
import subprocess
import sys
import sounddevice as sd
import soundfile as sf

MODEL_PATH = Path("models/piper/en_US-lessac-medium.onnx")
OUTPUT_PATH = Path("recordings/assistant_response.wav")


def generate_speech(text: str, output_path: str | Path = OUTPUT_PATH) -> Path:
    """Generate a WAV file with Piper without playing it."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Voice model not found: {MODEL_PATH.resolve()}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "piper",
            "--model", str(MODEL_PATH),
            "--output_file", str(output_path),
        ],
        input=text,
        text=True,
        check=True,
    )
    return output_path


def speak_text(text: str) -> None:
    """Generate speech and play it through the Python machine's speakers."""
    audio_path = generate_speech(text)
    audio, sample_rate = sf.read(str(audio_path), dtype="float32")
    sd.play(audio, sample_rate)
    sd.wait()
    print("Speech playback completed.")

def play_audio_file(audio_path: str | Path, stop_event=None) -> None:
    """Play a WAV file, allowing playback to be interrupted."""
    audio, sample_rate = sf.read(
        str(audio_path),
        dtype="float32",
    )

    if audio.ndim == 1:
        audio = audio.reshape(-1, 1)

    block_size = 1024

    with sd.OutputStream(
        samplerate=sample_rate,
        channels=audio.shape[1],
        dtype="float32",
    ) as stream:
        for start in range(0, len(audio), block_size):
            if stop_event is not None and stop_event.is_set():
                break

            chunk = audio[start:start + block_size]
            stream.write(chunk)

if __name__ == "__main__":
    speak_text("Hello! Your local AI voice assistant is ready.")


