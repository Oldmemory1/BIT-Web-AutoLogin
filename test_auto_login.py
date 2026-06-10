"""Tests for BIT Web AutoLogin — mock bitsrun network calls."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).parent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def settings():
    with open(ROOT / "settings.json") as f:
        return json.load(f)


@pytest.fixture
def online_status():
    return {
        "user_name": "3120250000",
        "online_ip": "10.0.0.123",
        "sum_bytes": 922000000,
        "sum_seconds": 10800,
        "user_balance": 10.00,
        "wallet_balance": 0.00,
    }


@pytest.fixture
def offline_status():
    return {
        "user_name": None,
        "online_ip": "10.0.0.123",
    }


# ---------------------------------------------------------------------------
# settings.json
# ---------------------------------------------------------------------------

class TestSettings:
    def test_file_exists(self):
        assert (ROOT / "settings.json").exists()

    def test_has_username(self, settings):
        assert "username" in settings
        assert isinstance(settings["username"], str)
        assert len(settings["username"]) > 0

    def test_has_password(self, settings):
        assert "password" in settings
        assert isinstance(settings["password"], str)
        assert len(settings["password"]) > 0


# ---------------------------------------------------------------------------
# helper.py — status
# ---------------------------------------------------------------------------

class TestHelperStatus:
    def test_status_online(self, capsys, online_status):
        from helper import cmd_status

        with patch("helper.get_login_status", return_value=online_status):
            cmd_status()
        out = capsys.readouterr().out
        assert "is online" in out

    def test_status_offline(self, capsys, offline_status):
        from helper import cmd_status

        with patch("helper.get_login_status", return_value=offline_status):
            cmd_status()
        out = capsys.readouterr().out
        assert "is offline" in out

    def test_status_json(self, capsys, online_status):
        from helper import cmd_status

        with patch("helper.get_login_status", return_value=online_status):
            cmd_status(json_fmt=True)
        out = capsys.readouterr().out
        data = json.loads(out.strip())
        assert data["user_name"] == "3120250000"


# ---------------------------------------------------------------------------
# helper.py — login / logout
# ---------------------------------------------------------------------------

class TestHelperLoginLogout:
    def test_login_success(self, capsys, online_status):
        from helper import cmd_login

        mock_user = MagicMock()
        mock_user.login.return_value = {
            "error": "ok",
            "online_ip": "10.0.0.123",
            "error_msg": "",
        }

        with patch("helper.User", return_value=mock_user):
            cmd_login()
        out = capsys.readouterr().out
        assert "logged in" in out

    def test_login_failure(self, capsys):
        from helper import cmd_login

        mock_user = MagicMock()
        mock_user.login.return_value = {
            "error": "not_ok",
            "online_ip": "",
            "error_msg": "wrong password",
        }

        with patch("helper.User", return_value=mock_user):
            with pytest.raises(SystemExit) as exc_info:
                cmd_login()
        out = capsys.readouterr().out + capsys.readouterr().err
        assert "wrong password" in str(exc_info.value) or "wrong password" in out

    def test_logout_success(self, capsys):
        from helper import cmd_logout

        mock_user = MagicMock()
        mock_user.logout.return_value = {
            "error": "ok",
            "online_ip": "10.0.0.123",
        }

        with patch("helper.User", return_value=mock_user):
            cmd_logout()
        out = capsys.readouterr().out
        assert "logged out" in out

    def test_logout_failure(self, capsys):
        from helper import cmd_logout

        mock_user = MagicMock()
        mock_user.logout.return_value = {
            "error": "not_ok",
            "online_ip": "",
            "error_msg": "already offline",
        }

        with patch("helper.User", return_value=mock_user):
            with pytest.raises(SystemExit) as exc_info:
                cmd_logout()
        out = capsys.readouterr().out + capsys.readouterr().err
        assert "already offline" in str(exc_info.value) or "already offline" in out


# ---------------------------------------------------------------------------
# auto_login.py — core loop logic
# ---------------------------------------------------------------------------

class TestAutoLoginLoop:
    def test_load_settings(self):
        from auto_login import load_settings

        s = load_settings()
        assert s["username"] == "3120250000"

    def test_ts_format(self):
        from auto_login import ts

        t = ts()
        assert len(t) == 19  # YYYY-MM-DD HH:MM:SS
        assert t[4] == "-" and t[7] == "-"
        assert t[10] == " " and t[13] == ":" and t[16] == ":"

    def test_online_loop_prints_status(self, capsys, online_status):
        """One iteration: online → prints user info, no login attempt."""
        from auto_login import main

        call_count = 0

        def fake_status():
            nonlocal call_count
            call_count += 1
            # first call returns online; second call would loop
            # we raise StopIteration after first to break the loop
            if call_count == 1:
                return online_status
            raise KeyboardInterrupt

        with patch("auto_login.get_login_status", fake_status):
            try:
                main()
            except KeyboardInterrupt:
                pass

        out = capsys.readouterr().out
        assert "在线" in out
        assert "3120250000" in out

    def test_offline_triggers_login(self, capsys, offline_status, online_status):
        """One iteration: offline → attempts login → succeeds."""
        from auto_login import main

        call_count = 0

        def fake_status():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return offline_status
            raise KeyboardInterrupt

        mock_user = MagicMock()
        mock_user.login.return_value = {
            "error": "ok",
            "online_ip": "10.0.0.123",
            "error_msg": "",
        }

        with patch("auto_login.get_login_status", fake_status):
            with patch("auto_login.User", return_value=mock_user):
                try:
                    main()
                except KeyboardInterrupt:
                    pass

        out = capsys.readouterr().out
        assert "已离线" in out
        assert "登录成功" in out
