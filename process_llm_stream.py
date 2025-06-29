
import sys
import json
import asyncio
import re
import nltk
from nltk.tokenize import sent_tokenize
from extract_numbers import ExtractNumbers

import config
from wav_player import play_bytes
from text_to_speech_api import TTS_REST_API_Client

########

tts_client = TTS_REST_API_Client(url=config.text_to_speech_url)
if not tts_client.check_health():
    print("TTS service is not reachable")
    sys.exit(1)

status, output = tts_client.load_model(config.tts_engine, config.tts_model)
if not status:
    print(output)
    sys.exit(1)
print(output["message"])

########

nltk.download('punkt')


async def process_llm_stream_response(resp):

    try:

        buffer = ""
        partial = ""
        full_text = ""

        async for chunk in resp.content.iter_any():

            await asyncio.sleep(0)

            partial += chunk.decode("utf-8")

            lines = partial.splitlines(keepends=False)
            if not partial.endswith('\n'):
                partial = lines.pop()
            else:
                partial = ""

            for line in lines:

                await asyncio.sleep(0)
                line = line.strip()

                if not line or not line.startswith("data: "):
                    continue
                if line == "data: [DONE]":
                    sentences = tokenize_sentense(buffer)
                    for sentence in sentences:
                        await synthesize_and_play(sentence)
                    return full_text

                try:

                    data_str = line[len("data: "):]
                    delta_chunk = json.loads(data_str)
                    content = delta_chunk["choices"][0]["delta"].get("content")

                    if content:

                        full_text += content
                        buffer += content

                        if len(buffer) >= config.MIN_BUFFER_LENGTH:
                            sentences = tokenize_sentense(buffer)
                        else:
                            sentences = []

                        if sentences:

                            if len(sentences) == 1:

                                # Not enough to split, just hold onto it
                                buffer = sentences[0]

                            elif len(sentences) >= 2:

                                # Play all but the last sentence
                                for sentence in sentences[:-1]:
                                    await synthesize_and_play(sentence)

                                # Keep the last sentence (possibly incomplete) in the buffer
                                buffer = sentences[-1]

                except Exception as e:
                    print("[Parse Error]", e)

        raise RuntimeError("data: [DONE] was not received!")

    except asyncio.CancelledError:
        print("[process_llm_queue] Streaming task cancelled.", flush=True)
        raise


def tokenize_sentense(text):

    sentences_all = []

    sentence_list = [
        s.strip() for s in re.split(
            r'(?<=[.!?])(?=[A-Z])',  # only split if followed by capital letter
            text
        ) if s.strip()
    ]

    for sentence in sentence_list:

        sentence = sentence.strip()
        if not sentence:
            continue

        sentences = sent_tokenize(sentence)
        sentences_all.extend(sentences)

    # Flatten the list by splitting on newlines and removing empty strings
    sentences_all_flatten = [
        line.strip() for s in sentences_all for line in s.split('\n') if line.strip()
    ]

    sentences_final = [
        clean_numbers(s) for s in sentences_all_flatten
    ]

    return sentences_final


def clean_numbers(text: str) -> str:

    extractor = ExtractNumbers({'as_string': True})

    numbers = extractor.extractNumbers(text)

    text_buffer = text
    offset = 0

    for num in numbers:

        search_start = offset
        idx = text_buffer.find(num, search_start)

        if idx == -1:
            continue  # Just in case

        before = text_buffer[idx - 1] if idx > 0 else ' '
        after = text_buffer[idx + len(num)] if idx + len(num) < len(text_buffer) else ' '

        # Add space before number if needed
        if not before.isspace():
            text_buffer = text_buffer[:idx] + ' ' + text_buffer[idx:]
            idx += 1
            offset += 1

        # Add space after number if needed
        after_idx = idx + len(num)
        if after_idx < len(text_buffer) and not text_buffer[after_idx].isspace():
            text_buffer = text_buffer[:after_idx] + ' ' + text_buffer[after_idx:]
            offset += 1

    # Normalize spacing
    text_buffer = re.sub(r'\s+', ' ', text_buffer).strip()

    return text_buffer


async def synthesize_and_play(text):

    text = text.strip()

    if not text:
        return

    print(f"#### Text to synthesize: {repr(text)}", flush=True)

    status, output = tts_client.synthesize(text, config.tts_engine, config.tts_model)
    if status:
        await play_bytes(output)
