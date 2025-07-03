
import io
import wave
import asyncio
import numpy as np
import sounddevice as sd
import soundfile as sf


async def play_bytes(wav_bytes: bytes):

    def blocking_play():

        with io.BytesIO(wav_bytes) as wav_io:

            with wave.open(wav_io, 'rb') as wf:

                samplerate = wf.getframerate()
                num_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                num_frames = wf.getnframes()

                audio_bytes = wf.readframes(num_frames)
                dtype = {1: np.int8, 2: np.int16, 4: np.int32}[sampwidth]
                audio = np.frombuffer(audio_bytes, dtype=dtype)

                if num_channels > 1:
                    audio = audio.reshape(-1, num_channels)

                audio = audio.astype(np.float32) / np.iinfo(dtype).max
                audio *= 0.8

                sd.play(audio, samplerate=samplerate)
                sd.wait()

    await asyncio.to_thread(blocking_play)


async def play_file(filepath: str):

    def blocking_play():

        audio, samplerate = sf.read(filepath, dtype='float32')

        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio = audio * 0.8  # cap at 80% volume to avoid clipping

        # Upmix mono to stereo
        if audio.ndim == 1:
            audio = np.stack([audio, audio], axis=1)

        sd.play(audio, samplerate=samplerate)
        sd.wait()

    await asyncio.to_thread(blocking_play)
