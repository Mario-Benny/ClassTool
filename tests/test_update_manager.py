# -*- coding: utf-8 -*-

from pathlib import Path
from unittest.mock import patch

from toolkit.core.update_manager import UPDATER_FILE_NAME, UpdateManager, _config_documents


def test_updater_binary_is_versioned() -> None:
    assert UPDATER_FILE_NAME == "PyUpdateCore-v1.0.1.exe"


def test_config_uses_specific_github_release_assets() -> None:
    user, core = _config_documents()
    source = user["update_source"]
    assert source["provider"] == "github_release"
    assert source["repository"] == "Mario-Benny/ClassTool"
    assert source["asset_pattern"] == "ClassTool-v*-Setup.exe"
    assert source["sha256_asset_pattern"] == "ClassTool-v*-Setup.exe.sha256"
    assert core["security"]["require_https"] is True
    assert core["security"]["require_sha256"] is True
    assert "api.github.com" in core["security"]["allowed_hosts"]


def test_check_completion_starts_download() -> None:
    manager = UpdateManager()
    manager._check_task_id = "check"
    with patch.object(manager, "_start_download") as start:
        manager._handle_task_finished("check", {"status": "completed", "result": {"available": True, "remote_version": "1.2.3"}})
    assert manager.latest_version == "1.2.3"
    start.assert_called_once_with()


def test_no_update_emits_current_version() -> None:
    manager = UpdateManager()
    manager._check_task_id = "check"
    received: list[str] = []
    manager.no_update.connect(received.append)
    manager._handle_task_finished("check", {"status": "completed", "result": {"available": False}})
    assert manager.state == "up_to_date"
    assert received


def test_download_completion_exposes_verified_installer(tmp_path: Path) -> None:
    manager = UpdateManager()
    manager._download_task_id = "download"
    installer = tmp_path / "ClassTool-v1.2.3-Setup.exe"
    manager._handle_task_finished("download", {"status": "completed", "installer": str(installer), "result": {"available": True, "verified": True, "version": "1.2.3"}})
    assert manager.state == "ready"
    assert manager.ready_installer == installer


def test_progress_updates_counters() -> None:
    manager = UpdateManager()
    manager._handle_progress({"status": "download_progress", "downloaded_bytes": 5, "total_bytes": 10})
    assert (manager.received_bytes, manager.total_bytes) == (5, 10)
    assert manager.state == "downloading"


def test_install_requires_verified_download_task() -> None:
    assert UpdateManager().schedule_install() is False


def test_fast_task_completion_is_replayed_after_acceptance() -> None:
    manager = UpdateManager()
    manager._handle_task_finished("fast", {"status": "completed", "result": {"available": False}})
    with patch.object(manager, "_send_request") as send:
        assert manager.check_for_updates() is True
        callback = send.call_args.args[2]
        callback({"success": True, "result": {"task_id": "fast"}})
    assert manager.state == "up_to_date"
