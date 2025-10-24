import argparse
import multiprocessing as mp
import time
from pathlib import Path

from .writer import JournalWriter
from .socket_server import SocketCommandServer
from . import config

def build_parser():
    p = argparse.ArgumentParser(description="Daily-journal-sync Service")
    p.add_argument("--repo", type=Path, default=config.DEFAULT_REPO, help="Journal repository root")
    p.add_argument("--with-weather", action="store_true", help="Add weather line to header")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--serve", action="store_true", help="Run background service with socket (default)")
    mode.add_argument("--interactive", action="store_true", help="Run interactive add/quit mode")
    p.add_argument("--socket", default=config.SOCKET_PATH, help="Unix socket path for IPC")
    return p

def interactive_loop(queue):
    print("Type: add <message>  — or  quit")
    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting…")
            break
        if not raw:
            continue
        if raw.lower() in {"q", "quit", "exit"}:
            break
        if raw.startswith("add "):
            msg = raw[4:].strip()
            if msg:
                queue.put(msg)
                print("queued.")
        else:
            print("Unknown command. Use: add <message>  or  quit")

def main():
    args = build_parser().parse_args()
    queue = mp.Queue()
    writer = JournalWriter(args.repo, args.with_weather, queue)
    proc = mp.Process(target=writer.run, daemon=True)
    proc.start()

    if args.interactive:
        try:
            interactive_loop(queue)
        finally:
            queue.put(None)
            proc.join(timeout=5)
        return

    server = SocketCommandServer(
        socket_path=args.socket,
        submit_fn=lambda msg: queue.put(msg),
        logger=writer._logger,
    )
    server.start()
    writer._logger.info("Service started. Repo=%s Socket=%s", args.repo, args.socket)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        writer._logger.info("Shutting down…")
    finally:
        server.stop()
        queue.put(None)
        proc.join(timeout=5)

if __name__ == "__main__":
    main()
