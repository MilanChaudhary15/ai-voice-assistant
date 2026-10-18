
import sounddevice as sd
from scipy.io.wavfile import write
from pathlib import Path

SAMPLE_RATE = 16000
DURATION = 5

# Create the recordings folder automatically
RECORDINGS_DIR = Path("recordings")
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = RECORDINGS_DIR / "recording.wav"


def record_audio():
    print(f"Recording for {DURATION} seconds. Speak now!")

    audio = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
    )
    sd.wait()

    write(str(OUTPUT_FILE), SAMPLE_RATE, audio)
    print(f"Recording saved to: {OUTPUT_FILE}")

    return str(OUTPUT_FILE)


if __name__ == "__main__":
    record_audio()
