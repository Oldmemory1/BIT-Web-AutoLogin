#!/usr/bin/env python3
"""BIT Web AutoLogin — monitor network status and auto re-login on disconnect."""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

from bitsrun.user import User, get_login_status

SETTINGS_PATH = Path(__file__).parent / "settings.json"
CHECK_INTERVAL = 30


def load_settings() -> dict:
    with open(SETTINGS_PATH) as f:
        return json.load(f)


def ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    settings = load_settings()
    username = settings.get("username")
    password = settings.get("password")

    if not username or not password:
        print(f"[{ts()}] ERROR: settings.json 中缺少 username 或 password", file=sys.stderr)
        sys.exit(1)

    print(f"[{ts()}] BIT Web AutoLogin 已启动")
    print(f"[{ts()}] 用户: {username}  检测间隔: {CHECK_INTERVAL}s")
    print(f"[{ts()}] 按 Ctrl+C 退出\n")

    while True:
        try:
            status = get_login_status()
            online_user = status.get("user_name")

            if online_user:
                print(
                    f"[{ts()}] 在线 — 用户: {online_user}  "
                    f"IP: {status['online_ip']}  "
                    f"已用流量: {status.get('sum_bytes', 0) / 1024 / 1024:.1f} MiB"
                )
            else:
                print(f"[{ts()}] 已离线 (IP: {status.get('online_ip')}), 尝试重新登录...")
                user = User(username, password)
                resp = user.login()
                if resp.get("error") == "ok":
                    print(
                        f"[{ts()}] 登录成功 — "
                        f"{username} ({resp.get('online_ip')}) 已上线"
                    )
                else:
                    print(
                        f"[{ts()}] 登录失败: {resp.get('error_msg', '未知错误')}",
                        file=sys.stderr,
                    )
        except Exception as e:
            print(f"[{ts()}] 异常: {e}", file=sys.stderr)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
