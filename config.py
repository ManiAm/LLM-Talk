
hotword_url = "ws://localhost:5600/api/hotword/listen"

hotword_params = {
    "dev_index": None,
    "hotwords": ["hey_jarvis"],
    "model_engine_hotword": "openwakeword",
    "model_name_hotword": None,
    "model_engine_stt": "openai_whisper",
    "model_name_stt": "small.en",
    "target_latency": 80,
    "silence_duration": 3
}

hotword_audio = "sounds/jarvis/at_your_service.wav"
silence_audio = "sounds/bell_1.wav"

system_prompt = """
Your name is Jarvis.
You are a friendly assistant.
Speak in short, natural, spoken sentences suitable for text-to-speech output.
Do not combine multiple sentences without proper spacing.
"""

MAX_HISTORY = 20
MIN_BUFFER_LENGTH = 100

lite_llm_url = "http://apollo.home:4000"
llm_model = "ollama/llama3.1:8b"

text_to_speech_url = "http://172.29.198.1:5500/api/tts"

# tts_engine = "coqui"
# tts_model = "tts_models/en/ljspeech/fast_pitch"

# tts_engine = "bark"
# tts_model = "v2/en_speaker_6"

# tts_engine = "chatterbox"
# tts_model = "jarvis.wav"

tts_engine = "piper"
tts_model = "en_US-bryce-medium"

# tts_engine = "piper"
# tts_model = "en_US-ryan-high"

# tts_engine = "piper"
# tts_model = "en_US-ljspeech-high"
