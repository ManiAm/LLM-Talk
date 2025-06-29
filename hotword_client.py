
import os
import sys
import json
import asyncio
import websockets
from tabulate import tabulate

import config
from hotword_types import MessageStatus, MessageType
from wav_player import play_file

script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)

hotword_audio = os.path.join(script_dir, config.hotword_audio)
if not os.path.exists(hotword_audio):
    print("hotword_audio is not accessible")
    sys.exit(1)

silence_audio = os.path.join(script_dir, config.silence_audio)
if not os.path.exists(silence_audio):
    print("silence_audio is not accessible")
    sys.exit(1)


async def run_hotword_listener(transcription_queue: asyncio.Queue):

    try:

        print(f"[hotword_listener]: Starting...\n")

        async with websockets.connect(config.hotword_url) as websocket:

            await websocket.send(json.dumps(config.hotword_params))

            while True:

                try:

                    msg = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(msg)

                    data_status = data.get("status")
                    data_type = data.get("type")
                    msg = data.get("text")

                    if data_status != MessageStatus.OK.value:
                        print(f"[hotword_listener]: {data}", flush=True)
                        continue

                    if data_type in (MessageType.HOST_INFO.value, MessageType.DEV_INPUT.value, MessageType.DEV_OUTPUT.value):
                        json_obj = json.loads(msg)
                        print_dict_tabular(json_obj, data_type)
                        continue

                    print(f"[hotword_listener]: {data}")

                    if data_type == MessageType.HOTWORD.value:
                        await play_file(hotword_audio)

                    if data_type == MessageType.SILENCE.value:
                        await play_file(silence_audio)

                    await transcription_queue.put(data)

                except asyncio.TimeoutError:
                    continue  # Check stop_event again
                except websockets.exceptions.ConnectionClosed:
                    print("[hotword_listener] WebSocket closed.")
                    break

    except asyncio.CancelledError:
        print("[hotword_listener] Cancelled.")

    except Exception as e:
        print(f"[hotword_listener] Unexpected error: {e}")


def print_dict_tabular(d, title):

    print(f"=== {title} ===")
    print(tabulate(d.items(), headers=["Key", "Value"], tablefmt="grid"))
    print("")
