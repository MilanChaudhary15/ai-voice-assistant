from pathlib import Path
from queue import Queue, Empty
import threading
import time

import av
import numpy as np
import soundfile as sf
import streamlit as st
from streamlit_webrtc import (
    AudioProcessorBase,
    WebRtcMode,
    webrtc_streamer,
)

from stt import transcribe_audio
from assistant import get_response, SYSTEM_MESSAGE
from tts import generate_speech, play_audio_file

st.set_page_config(
    page_title="Local AI Voice Assistant",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

RECORDINGS_DIR = Path("recordings")
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
INPUT_AUDIO = RECORDINGS_DIR / "browser_recording.wav"
LIVE_INPUT_AUDIO = RECORDINGS_DIR / "live_recording.wav"
OUTPUT_AUDIO = RECORDINGS_DIR / "assistant_response.wav"

st.markdown(
    """
    <style>
    .block-container { max-width: 900px; padding-top: 2rem; padding-bottom: 3rem; }
    .hero {
        padding: 26px 20px; border-radius: 18px; text-align: center;
        background: linear-gradient(135deg, #102a43, #243b53);
        color: white; margin-bottom: 20px;
    }
    .hero h1 { color: white; margin-bottom: 8px; }
    .hero p { color: #e6eef7; margin-bottom: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "llm_history" not in st.session_state:
    st.session_state.llm_history = [SYSTEM_MESSAGE.copy()]
if "last_transcript" not in st.session_state:
    st.session_state.last_transcript = ""
if "last_response" not in st.session_state:
    st.session_state.last_response = ""
if "live_status" not in st.session_state:
    st.session_state.live_status = "Start the microphone to begin."
if "live_audio_chunks" not in st.session_state:
    st.session_state.live_audio_chunks = []
if "live_silence_samples" not in st.session_state:
    st.session_state.live_silence_samples = 0
if "live_speech_started" not in st.session_state:
    st.session_state.live_speech_started = False
if "live_last_audio" not in st.session_state:
    st.session_state.live_last_audio = b""
if "live_turn_id" not in st.session_state:
    st.session_state.live_turn_id = 0
if "live_stop_event" not in st.session_state:
    st.session_state.live_stop_event = threading.Event()
if "live_playback_thread" not in st.session_state:
    st.session_state.live_playback_thread = None
if "live_is_speaking" not in st.session_state:
    st.session_state.live_is_speaking = False

st.markdown(
    """
    <div class="hero">
      <h1>🎙️ Your AI Voice Assistant</h1>
      <p>Speak naturally. Get an answer from your local AI and listen to it.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption("Local pipeline: Faster-Whisper • Ollama Qwen 2.5 3B • Piper TTS")

mode = st.radio(
    "Choose your interaction mode",
    ["Record & Send", "Live Conversation"],
    horizontal=True,
    key="interaction_mode",
)

def add_turn(user_text: str, response: str):
    st.session_state.last_transcript = user_text
    st.session_state.last_response = response
    st.session_state.messages.append({"role": "user", "content": user_text})
    st.session_state.messages.append({"role": "assistant", "content": response})


def handle_audio_file(audio_bytes: bytes, input_path: Path, play_locally: bool = False):
    input_path.write_bytes(audio_bytes)
    with st.spinner("🎧 Transcribing speech..."):
        user_text = transcribe_audio(str(input_path))
    if not user_text.strip():
        st.warning("No speech detected. Please try again and speak clearly.")
        return
    with st.spinner("🧠 Generating the answer with Ollama..."):
        response = get_response(user_text, st.session_state.llm_history)
    st.session_state.last_transcript = user_text
    st.session_state.last_response = response
    st.session_state.messages.extend([
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": response},
    ])
    with st.spinner("🔊 Generating speech with Piper..."):
        generated_path = generate_speech(response, OUTPUT_AUDIO)
    st.success("Answer ready.")
    st.markdown("**You said:**")
    st.info(user_text)
    st.markdown("**Assistant:**")
    st.write(response)
    st.audio(generated_path.read_bytes(), format="audio/wav")


if mode == "Record & Send":
    st.markdown("### 🎤 Record your question")
    st.write("Record one question, stop the recording, then press Process.")
    audio_file = st.audio_input("🎙️ Click to record your question", sample_rate=16000)
    if st.button("✨ Process my question", type="primary", use_container_width=True):
        if audio_file is None:
            st.warning("Please record a question first.")
        else:
            try:
                handle_audio_file(audio_file.getvalue(), INPUT_AUDIO)
            except Exception as error:
                st.error(f"Something went wrong: {error}")
                st.info("Check that Ollama is running and the Whisper/Piper models are available.")
    
else:
    st.markdown("### 🟢 Live Conversation")
    st.write(
        "Speak naturally. You can interrupt the assistant by speaking "
        "while it is answering, or use Stop speaking."
    )

    st.info(
        "Interruption detection uses microphone audio levels. "
        "Headphones are recommended to reduce the assistant's voice "
        "being mistaken for your speech."
    )

    class AudioQueueProcessor(AudioProcessorBase):
        def __init__(self):
            self.frames = Queue(maxsize=250)
            self.resampler = av.AudioResampler(
                format="s16", layout="mono", rate=16000
            )

        def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
            try:
                converted = self.resampler.resample(frame)
                for converted_frame in converted:
                    samples = converted_frame.to_ndarray().reshape(-1).copy()
                    try:
                        self.frames.put_nowait(samples)
                    except Exception:
                        pass
            except Exception:
                pass
            return frame

    ctx = webrtc_streamer(
        key="live-conversation-audio",
        mode=WebRtcMode.SENDONLY,
        audio_processor_factory=AudioQueueProcessor,
        media_stream_constraints={"video": False, "audio": True},
        async_processing=True,
    )

    st.caption(
        "Microphone status: "
        + ("active" if ctx.state.playing else "stopped")
    )

    if ctx.state.playing and ctx.audio_processor:
        if st.session_state.live_status == "Click START to enable the microphone.":
            st.session_state.live_status = "Listening… speak when ready."

        @st.fragment(run_every=0.2)
        def live_turn_worker():
            # All UI containers are created and used inside this fragment.
            status_box = st.empty()
            transcript_box = st.empty()
            answer_box = st.empty()
            audio_box = st.empty()

            status_box.info(st.session_state.live_status)
            # Manual interruption control
            if st.button("⏹️ Stop speaking", key="stop_live_speaking"):
                st.session_state.live_stop_event.set()
                st.session_state.live_status = "Playback stopped."
                st.session_state.live_is_speaking = False
            
            # Display the complete conversation in a scrollable panel
            with st.container(height=420, border=True):
                if not st.session_state.messages:
                    st.caption("Your conversation will appear here.")

                for message in st.session_state.messages:
                    if message["role"] == "user":
                        st.markdown("**You:**")
                        st.write(message["content"])

                    elif message["role"] == "assistant":
                        st.markdown("**Assistant:**")
                        st.write(message["content"])


            saved_audio = st.session_state.get("live_audio_bytes", b"")
            if saved_audio:
                audio_box.audio(
                    saved_audio, format="audio/wav", autoplay=False
                )

            processor = ctx.audio_processor
            if not ctx.state.playing or processor is None:
                st.session_state.live_status = "Microphone stopped."
                status_box.warning(st.session_state.live_status)
                return

            samples_per_second = 16000
            silence_limit = int(0.8 * samples_per_second)
            min_speech_samples = int(0.35 * samples_per_second)
            max_turn_samples = int(15 * samples_per_second)
            threshold = 420

            
            received = []

            try:
                while True:
                    received.append(processor.frames.get_nowait())
            except Empty:
                pass
            
            # DEBUG: Check incoming microphone audio
            if received:
                latest = received[-1].astype(np.float32)
                rms = float(np.sqrt(np.mean(latest ** 2)))

                status_box.info(
                    f"DEBUG: Receiving audio | "
                    f"Frames: {len(received)} | RMS: {rms:.1f}"
                )
            else:
                status_box.warning(
                    "DEBUG: No audio frames received from microphone."
                )


            completed_turn = None

            # completed_turn = None

            for samples in received:
                if len(samples) == 0:
                    continue

                rms = float(
                    np.sqrt(
                        np.mean(samples.astype(np.float32) ** 2)
                    )
                )
                speechy = rms >= threshold

                if speechy:
                    st.session_state.live_speech_started = True
                    st.session_state.live_silence_samples = 0
                    st.session_state.live_audio_chunks.append(samples)

                elif st.session_state.live_speech_started:
                    st.session_state.live_audio_chunks.append(samples)
                    st.session_state.live_silence_samples += len(samples)

                total_samples = sum(
                    len(chunk)
                    for chunk in st.session_state.live_audio_chunks
                )

                if st.session_state.live_speech_started and (
                    st.session_state.live_silence_samples >= silence_limit
                    or total_samples >= max_turn_samples
                ):
                    if total_samples >= min_speech_samples:
                        completed_turn = np.concatenate(
                            st.session_state.live_audio_chunks
                        )

                    st.session_state.live_audio_chunks = []
                    st.session_state.live_silence_samples = 0
                    st.session_state.live_speech_started = False

                    if completed_turn is not None:
                        break

            if completed_turn is None:
                if st.session_state.live_speech_started:
                    st.session_state.live_status = (
                        "Speech detected… finish your sentence."
                    )
                    status_box.info(st.session_state.live_status)
                return

            st.session_state.live_status = "Processing your turn…"
            status_box.info(st.session_state.live_status)

            try:
                sf.write(
                    str(LIVE_INPUT_AUDIO),
                    completed_turn,
                    samples_per_second,
                    subtype="PCM_16",
                )

                user_text = transcribe_audio(
                    str(LIVE_INPUT_AUDIO)
                ).strip()

                if not user_text:
                    st.session_state.live_status = (
                        "No speech recognized. Please try again."
                    )
                    status_box.warning(
                        st.session_state.live_status
                    )
                    return

                st.session_state.last_transcript = user_text
                transcript_box.markdown(
                    "**You said:** " + user_text
                )

                response = get_response(
                    user_text,
                    st.session_state.llm_history,
                )

                st.session_state.messages.extend([
                    {"role": "user", "content": user_text},
                    {"role": "assistant", "content": response},
                ])

                st.session_state.last_response = response
                answer_box.markdown(
                    "**Assistant:** " + response
                )

                # Generate the assistant's spoken answer.
                generated_path = generate_speech(
                    response,
                    OUTPUT_AUDIO,
                )

                audio_bytes = generated_path.read_bytes()
                st.session_state.live_audio_bytes = audio_bytes

                # Discard stale microphone frames captured while
                # the previous question was being processed.
                try:
                    while True:
                        processor.frames.get_nowait()
                except Empty:
                    pass

                # Prepare an interruptible background playback.
                stop_event = st.session_state.live_stop_event
                stop_event.clear()

                playback_thread = threading.Thread(
                    target=play_audio_file,
                    args=(generated_path, stop_event),
                    daemon=True,
                )

                st.session_state.live_playback_thread = (
                    playback_thread
                )
                st.session_state.live_is_speaking = True

                # Keep the audio recording available for replay.
                audio_box.audio(
                    audio_bytes,
                    format="audio/wav",
                    autoplay=False,
                )

                # Start playback without blocking microphone processing.
                playback_thread.start()

                st.session_state.live_status = (
                    "Speaking… interrupt me anytime by asking "
                    "another question."
                )
                status_box.success(
                    st.session_state.live_status
                )

            except Exception as error:
                st.session_state.live_status = (
                    f"Turn failed: {error}"
                )
                status_box.error(
                    st.session_state.live_status
                )
        
        live_turn_worker()

    else:
        st.session_state.live_status = (
            "Click START to enable the microphone."
        )
        st.info(st.session_state.live_status)


st.markdown("---")
st.caption("Local AI pipeline • Faster-Whisper STT • Qwen 2.5 3B • Piper TTS")

