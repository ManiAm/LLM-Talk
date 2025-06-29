
import os
import sys
import re
import asyncio
import aiohttp
from aiohttp import ClientTimeout
from dotenv import load_dotenv

import config
from hotword_types import MessageType
from process_llm_stream import process_llm_stream_response

load_dotenv()

###########

url_chat = os.path.join(config.lite_llm_url, "v1/chat/completions")

LITE_LLM_API_KEY = os.getenv('LITE_LLM_API_KEY', None)
if not LITE_LLM_API_KEY:
    print("LITE_LLM_API_KEY environment variable is not set")
    sys.exit(1)

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {LITE_LLM_API_KEY}"
}

###########

conversation_memory = {}


async def process_llm_queue(llm_queue):

    current_task = None

    try:

        while True:

            try:
                data = await asyncio.wait_for(llm_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue  # check cancellation again

            msg_type = data.get("type", None)
            if not msg_type:
                continue

            if msg_type == MessageType.HOTWORD.value:

                # Cancel any ongoing task
                if current_task:

                    task_name = current_task.get_name()

                    print(
                        "[process_llm_queue] Cancelling ongoing response:\n"
                        f"  • Task name: {task_name}\n"
                        f"  • Task done: {current_task.done()}",
                        flush=True
                    )

                    current_task.cancel()
                    try:
                        await current_task
                    except asyncio.CancelledError:
                        pass

            elif msg_type == MessageType.TRANSCRIBED.value:

                user_text = data.get("text", None)
                if not user_text:
                    continue

                print(f"\n\n[process_llm_queue] New prompt: {user_text}", flush=True)
                task_name = make_task_name(user_text)

                current_task = asyncio.create_task(run_llm_stream(user_text), name=task_name)

    except asyncio.CancelledError:

        print("[process_llm_queue] Cancelled.")

        if current_task:
            current_task.cancel()
            try:
                await current_task
            except asyncio.CancelledError:
                pass


async def run_llm_stream(user_text, session_id="default"):

    task = asyncio.current_task()
    task_name = task.get_name()
    print(f"[process_llm_queue] task '{task_name}': started.", flush=True)

    if session_id not in conversation_memory:
        conversation_memory[session_id] = [
            {"role": "system", "content": config.system_prompt.strip()}
        ]

    conversation_memory[session_id].append({"role": "user", "content": user_text})

    conversation_memory[session_id] = conversation_memory[session_id][-config.MAX_HISTORY:]

    payload = {
        "model": config.llm_model,
        "messages": conversation_memory[session_id],
        "stream": True
    }

    try:

        timeout = ClientTimeout(total=20)

        async with aiohttp.ClientSession(timeout=timeout) as session:

            print(f"[process_llm_queue] task '{task_name}': sending request to LLM.", flush=True)

            async with session.post(url_chat, json=payload, headers=headers) as resp:

                if resp.status != 200:
                    print(f"[process_llm_queue] Request failed: {resp.status}")
                    return

                print(f"[process_llm_queue] task '{task_name}': processing LLM response.", flush=True)

                assistant_reply = await process_llm_stream_response(resp)

                conversation_memory[session_id].append({
                    "role": "assistant", "content": assistant_reply
                })

    except asyncio.CancelledError:
        print(f"[process_llm_queue] task '{task_name}': canceled.", flush=True)

    except Exception as e:
        print(f"[process_llm_queue] task '{task_name}': {e.__class__.__name__}: {e}", flush=True)

    finally:
        print(f"[process_llm_queue] task '{task_name}': done.", flush=True)


def make_task_name(user_text: str, prefix: str = "llm") -> str:

    # Remove non-word characters and collapse spaces
    clean_text = re.sub(r'\W+', '_', user_text).strip('_')

    # Limit to 30 chars for readability
    truncated = clean_text[:30] if clean_text else "empty"

    return f"{prefix}_{truncated}"
