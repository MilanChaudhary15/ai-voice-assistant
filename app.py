
import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from stt import transcribe_audio
from assistant import get_response
from tts import speak_text


# -------------------- PAGE CONFIG --------------------

st.set_page_config(
    page_title="Local AI Voice Assistant",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

RECORDINGS_DIR = Path("recordings")
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

INPUT_AUDIO = RECORDINGS_DIR / "browser_recording.wav"
OUTPUT_AUDIO = RECORDINGS_DIR / "assistant_response.wav"


# -------------------- CUSTOM STYLING --------------------

st.markdown(
    """
    <style>
    .block-container {
        max-width: 900px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .hero {
        padding: 28px 22px;
        border-radius: 20px;
        text-align: center;
        background: linear-gradient(
            135deg, #102a43, #243b53
        );
        color: white;
        margin-bottom: 22px;
    }

    .hero h1 {
        font-size: 2.2rem;
        margin-bottom: 8px;
        color: white;
    }

    .hero p {
        font-size: 1.05rem;
        margin-bottom: 0;
        color: #e6eef7;
    }

    .section-card {
        padding: 20px;
        border: 1px solid rgba(128,128,128,0.3);
        border-radius: 16px;
        margin: 12px 0;
    }

    .step-label {
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 8px;
    }

    div.stButton > button {
        min-height: 54px;
        border-radius: 12px;
        font-size: 1.05rem;
        font-weight: 650;
        width: 100%;
    }

    /* Make the microphone recording area more prominent */
    [data-testid="stAudioInput"] {
        padding: 28px;
        border: 3px solid #1769aa;
        border-radius: 20px;
        margin: 20px 0;
        min-height: 110px;
        background-color: rgba(23, 105, 170, 0.08);
    }
    
    /* Increase the recorder's text size */
    [data-testid="stAudioInput"] label {
        font-size: 1.25rem !important;
        font-weight: 700 !important;
    }
    
    /* Make the recording area easier to notice */
    [data-testid="stAudioInput"] button {
        min-width: 64px;
        min-height: 64px;
        border-radius: 50%;
    }

    [data-testid="stChatMessage"] {
        border-radius: 14px;
    }

    .hint {
        font-size: 0.95rem;
        opacity: 0.8;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------- SESSION STATE --------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_transcript" not in st.session_state:
    st.session_state.last_transcript = ""

if "last_response" not in st.session_state:
    st.session_state.last_response = ""


# -------------------- HEADER --------------------

st.markdown(
    """
    <div class="hero">
        <h1>🎙️ Your AI Voice Assistant</h1>
        <p>Speak naturally. Get intelligent answers.
        Listen to the response.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "Runs locally with Faster-Whisper, Qwen 2.5 3B and Piper TTS."
)


# -------------------- RECORDING --------------------

st.markdown("## 🎤 Ask your question")

st.markdown(
    """
    <div class="section-card">
        <div class="step-label">Step 1 — Record your voice</div>
        <p>Click the microphone control below, allow microphone
        access if asked, and speak your question clearly.</p>
        <p class="hint">When you finish, use the recorder's
        stop/done control. Then click Process my question.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

audio_file = st.audio_input(
    "🎙️ Click here to record your question",
    sample_rate=16000,
)

process_clicked = st.button(
    "✨ Process my question",
    type="primary",
    use_container_width=True,
)

if process_clicked:
    if audio_file is None:
        st.warning(
            "Please record a question using the microphone above first."
        )
    else:
        INPUT_AUDIO.write_bytes(audio_file.getvalue())

        try:
            with st.spinner("🎧 Step 2 of 3: Understanding your speech..."):
                user_text = transcribe_audio(str(INPUT_AUDIO))

            if not user_text:
                st.warning(
                    "We couldn't detect any speech. Please try again "
                    "and speak a little more clearly."
                )
            else:
                st.session_state.last_transcript = user_text

                with st.spinner("🧠 Step 3 of 3: Generating your answer..."):
                    response = get_response(user_text)

                st.session_state.last_response = response
                st.session_state.messages.append(
                    {"role": "user", "content": user_text}
                )
                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )

                # Generate the response audio.
                # The TTS function also plays audio on the server computer.
                with st.spinner("🔊 Preparing spoken response..."):
                    speak_text(response)

                st.success("Your answer is ready!")

        except Exception as error:
            st.error(f"Something went wrong: {error}")
            st.info(
                "Check that Ollama is running and the Whisper and "
                "Piper models are available."
            )


# -------------------- LATEST TRANSCRIPT --------------------

if st.session_state.last_transcript:
    st.markdown("---")
    st.markdown("### 📝 What you said")
    st.info(st.session_state.last_transcript)


# -------------------- LATEST RESPONSE --------------------

if st.session_state.last_response:
    st.markdown("## 🔊 Listen to the answer")

    st.markdown(
        """
        <div class="section-card">
            <div class="step-label">Your spoken response</div>
            <p>Use the large Play/Pause button below to listen.
            You can pause and resume at any time.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if OUTPUT_AUDIO.exists():
        audio_bytes = OUTPUT_AUDIO.read_bytes()
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        # A custom, larger playback control.
        audio_player_html = """
        <!DOCTYPE html>
        <html>
        <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 10px 0;
            }
            .player {
                border: 1px solid #8a9bad;
                border-radius: 16px;
                padding: 18px;
                display: flex;
                align-items: center;
                gap: 16px;
            }
            .play {
                width: 76px;
                height: 64px;
                flex-shrink: 0;
                border: none;
                border-radius: 14px;
                background: #1769aa;
                color: white;
                font-size: 21px;
                font-weight: bold;
                cursor: pointer;
            }
            .play:focus {
                outline: 3px solid #f0b429;
                outline-offset: 3px;
            }
            .details {
                flex: 1;
                min-width: 0;
            }
            .label {
                font-size: 17px;
                font-weight: bold;
                margin-bottom: 9px;
            }
            input[type=range] {
                width: 100%;
                min-height: 30px;
                cursor: pointer;
            }
            .time {
                font-size: 14px;
                opacity: 0.8;
                display: flex;
                justify-content: space-between;
            }
        </style>
        </head>
        <body>
        <div class="player">
            <button class="play" id="toggle"
                aria-label="Play response">▶ Play</button>
            <div class="details">
                <div class="label">Assistant voice response</div>
                <input id="seek" type="range" min="0" max="100"
                    value="0" step="0.1"
                    aria-label="Audio position">
                <div class="time">
                    <span id="current">0:00</span>
                    <span id="duration">0:00</span>
                </div>
            </div>
        </div>
        <audio id="audio" preload="metadata"
            src="data:audio/wav;base64,__AUDIO_DATA__"></audio>
        <script>
            const audio = document.getElementById("audio");
            const toggle = document.getElementById("toggle");
            const seek = document.getElementById("seek");
            const current = document.getElementById("current");
            const duration = document.getElementById("duration");

            function fmt(seconds) {
                if (!Number.isFinite(seconds)) return "0:00";
                const m = Math.floor(seconds / 60);
                const s = Math.floor(seconds % 60);
                return m + ":" + String(s).padStart(2, "0");
            }

            toggle.addEventListener("click", () => {
                if (audio.paused) {
                    audio.play().catch(() => {
                        toggle.textContent = "▶ Retry";
                    });
                } else {
                    audio.pause();
                }
            });

            audio.addEventListener("play", () => {
                toggle.textContent = "Ⅱ Pause";
                toggle.setAttribute("aria-label", "Pause response");
            });

            audio.addEventListener("pause", () => {
                toggle.textContent = "▶ Play";
                toggle.setAttribute("aria-label", "Play response");
            });

            audio.addEventListener("loadedmetadata", () => {
                duration.textContent = fmt(audio.duration);
            });

            audio.addEventListener("timeupdate", () => {
                current.textContent = fmt(audio.currentTime);
                if (audio.duration) {
                    seek.value = (audio.currentTime / audio.duration) * 100;
                }
            });

            seek.addEventListener("input", () => {
                if (audio.duration) {
                    audio.currentTime = (Number(seek.value) / 100)
                        * audio.duration;
                }
            });

            audio.addEventListener("ended", () => {
                toggle.textContent = "▶ Replay";
                toggle.setAttribute("aria-label", "Replay response");
                seek.value = 0;
            });
        </script>
        </body>
        </html>
        """

        components.html(
            audio_player_html.replace("__AUDIO_DATA__", audio_base64),
            height=125,
            scrolling=False,
        )

    st.markdown("### 💬 Answer text")
    st.write(st.session_state.last_response)


# -------------------- CONVERSATION HISTORY --------------------

st.markdown("---")
st.markdown("## 💬 Conversation history")

if not st.session_state.messages:
    st.caption(
        "Your conversation will appear here after your first question."
    )
else:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.markdown("**You asked:**")
            else:
                st.markdown("**Assistant:**")
            st.write(message["content"])

    if st.button("🗑️ Clear visible conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_transcript = ""
        st.session_state.last_response = ""
        st.rerun()


# -------------------- FOOTER --------------------

st.markdown("---")
st.caption(
    "🔒 Local AI pipeline • Faster-Whisper STT • Qwen 2.5 3B • Piper TTS"
)
