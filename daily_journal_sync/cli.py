import argparse
import json
import socket
import sys

from . import config


def send_command(cmd, msg=None, socket_path=config.SOCKET_PATH):
    """Connect to the Unix socket and send a command."""
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(socket_path)
        payload = {"cmd": cmd}
        if msg:
            payload["msg"] = msg
        s.sendall(json.dumps(payload).encode("utf-8") + b"\n")
        data = s.recv(4096).decode("utf-8").strip()
        s.close()
        return data
    except FileNotFoundError:
        return "Error: socket not found — is the service running?"
    except ConnectionRefusedError:
        return "Error: connection refused — service inactive?"
    except Exception as e:
        return f"Error: {e}"


def build_parser():
    p = argparse.ArgumentParser(description="Daily-journal-sync client")
    sub = p.add_subparsers(dest="cmd")

    addp = sub.add_parser("add", help="Add a note to today's journal")
    addp.add_argument("message", help="The note to add")

    sub.add_parser("ping", help="Check if service is reachable")

    return p


def main():
    args = build_parser().parse_args()
    if not args.cmd:
        print("Usage: python3 -m daily_journal_sync.cli add \"message\"")
        sys.exit(1)

    if args.cmd == "add":
        resp = send_command("add", args.message)
    elif args.cmd == "ping":
        resp = send_command("ping")
    else:
        resp = "Unknown command"

    print(resp)


if __name__ == "__main__":
    main()
