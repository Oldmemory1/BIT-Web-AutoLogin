"""CLI helper that reads settings.json and delegates to bitsrun."""

import json
import sys
from pathlib import Path

from bitsrun.user import User, get_login_status
from bitsrun.utils import print_status_table
from rich import print_json

SETTINGS = Path(__file__).parent / "settings.json"


def load_creds():
    with open(SETTINGS) as f:
        data = json.load(f)
    return data["username"], data["password"]


def cmd_status(json_fmt: bool = False):
    status = get_login_status()
    if json_fmt:
        print(json.dumps(status))
        return
    if status.get("user_name"):
        print(f"bitsrun: {status['user_name']} ({status['online_ip']}) is online")
        print_status_table(status)
    else:
        print(f"bitsrun: {status['online_ip']} is offline")


def cmd_login(verbose: bool = False):
    username, password = load_creds()
    user = User(username, password)
    resp = user.login()
    if verbose:
        print_json(data=resp)
    if resp["error"] != "ok":
        sys.exit(f"error: {resp.get('error_msg', 'unknown')}")
    print(f"bitsrun: {username} ({resp['online_ip']}) logged in")


def cmd_logout(verbose: bool = False):
    username, password = load_creds()
    user = User(username, password)
    resp = user.logout()
    if verbose:
        print_json(data=resp)
    if resp["error"] != "ok":
        sys.exit(f"error: {resp.get('error_msg', 'unknown')}")
    print(f"bitsrun: {resp['online_ip']} logged out")


def cmd_test():
    """Full test flow: status → logout → status → login → status."""
    print("=== Step 1: 检查当前状态 ===")
    cmd_status()

    print("\n=== Step 2: 登出 ===")
    cmd_logout()

    print("\n=== Step 3: 检查状态确认已离线 ===")
    cmd_status()

    print("\n=== Step 4: 重新登录 ===")
    cmd_login()

    print("\n=== Step 5: 检查状态确认已在线 ===")
    cmd_status()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status")
    p = sub.add_parser("status-json")

    p = sub.add_parser("login")
    p.add_argument("-v", "--verbose", action="store_true")

    p = sub.add_parser("logout")
    p.add_argument("-v", "--verbose", action="store_true")

    sub.add_parser("test")

    args = parser.parse_args()

    if args.command == "status":
        cmd_status()
    elif args.command == "status-json":
        cmd_status(json_fmt=True)
    elif args.command == "login":
        cmd_login(verbose=args.verbose)
    elif args.command == "logout":
        cmd_logout(verbose=args.verbose)
    elif args.command == "test":
        cmd_test()
    else:
        parser.print_help()
