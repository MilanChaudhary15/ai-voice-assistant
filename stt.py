
from faster_whisper import WhisperModel

# Small model suitable for local CPU inference
MODEL_SIZE = "base"

print("Loading Faster-Whisper model...")

model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8",
    cpu_threads=2,
    num_workers=1,
)

print("Faster-Whisper model loaded successfully!")


def transcribe_audio(audio_path: str) -> str:
    """Convert an audio file into text locally."""
    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
    )

    transcript = " ".join(
        segment.text.strip() for segment in segments
    ).strip()

    print(f"Detected language: {info.language}")
    return transcript


if __name__ == "__main__":
    print("STT component is ready.")
