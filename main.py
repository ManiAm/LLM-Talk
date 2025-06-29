
import asyncio
import signal

from hotword_client import run_hotword_listener
from litellm_proxy import process_llm_queue


async def main():

    llm_queue = asyncio.Queue()

    listener_task = asyncio.create_task(
        run_hotword_listener(llm_queue),
        name="hotword_listener"
    )

    llm_task = asyncio.create_task(
        process_llm_queue(llm_queue),
        name="process_llm_queue"
    )

    ######

    tasks = [listener_task, llm_task]

    def shutdown():
        print("\n[Main] Terminating tasks...", flush=True)
        for task in tasks:
            task.cancel()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)

    try:
        # Wait until the listener task finishes
        await listener_task
        print("[Main] Hotword listener exited. Shutting down...")
        shutdown()
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        print("[Main] Tasks cancelled gracefully.")
    finally:
        print("[Main] Shutdown complete.")


if __name__ == "__main__":

    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[Main] Unhandled exception: {e}")
