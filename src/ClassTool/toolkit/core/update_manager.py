# -*- coding: utf-8 -*-

"""PyUpdateCore JSON Lines IPC adapter for the ClassTool UI."""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEventLoop, QObject, QProcess, QTimer, Signal

from toolkit.core.app_info import APP_VERSION
from toolkit.core.app_logging import get_logger
from toolkit.core.paths import app_root, ensure_data_dir

UPDATER_VERSION = "1.0.1"
UPDATER_FILE_NAME = f"PyUpdateCore-v{UPDATER_VERSION}.exe"
PROTOCOL_VERSION = 1
INSTALL_RESPONSE_TIMEOUT_MS = 15_000
logger = get_logger("updates")


def updater_executable() -> Path:
    return app_root() / "updater" / UPDATER_FILE_NAME


def updater_data_root() -> Path:
    return ensure_data_dir() / "updater"


def _config_documents() -> tuple[dict[str, Any], dict[str, Any]]:
    user = {
        "schema_version": 1,
        "application": {"id": "io.github.mario-benny.classtool", "name": "ClassTool"},
        "current_version": {"source": "command_line", "value": "", "path": "", "json_key": "version"},
        "update_source": {
            "provider": "github_release", "manifest_url": "", "channel": "stable",
            "repository": "Mario-Benny/ClassTool", "asset_pattern": "ClassTool-v*-Setup.exe",
            "sha256_asset_pattern": "ClassTool-v*-Setup.exe.sha256", "release_tag": "",
        },
        "installer": {"wait_for_main_program": True, "wait_timeout_seconds": 600, "request_admin": True, "arguments": [], "delete_after_install": False},
        "restart": {"enabled": False, "program_path": "", "arguments": []},
        "interface": {"language": "zh-CN", "show_progress": True, "confirm_before_download": True, "confirm_before_install": True},
    }
    core = {
        "schema_version": 1,
        "download": {
            "default_threads": 4, "allowed_threads": [1, 4, 16], "fallback_to_single": True,
            "resume": True, "retry_count": 5, "timeout_seconds": 30, "stall_timeout_seconds": 60,
            "max_file_size_mb": 2048, "segment_storage": "separate_files", "min_segment_size_mb": 1,
            "verify_etag": True, "delete_parts_after_merge": True,
        },
        "security": {
            "require_https": True, "require_sha256": True,
            "allowed_hosts": ["api.github.com", "github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"],
            "signature_required": False, "trusted_manifest_keys": {},
        },
        "logging": {"enabled": True, "retention_days": 14},
        "network": {"download_channel": "native", "proxy_mode": "system", "proxy_url": "", "browser": {"type": "auto", "mode": "proxy_probe"}},
    }
    return user, core


def ensure_updater_configuration() -> Path:
    root = updater_data_root()
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    user, core = _config_documents()
    for path, payload in ((data_dir / "userdata.json", user), (data_dir / "coredata.json", core)):
        encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        if not path.exists() or path.read_text(encoding="utf-8") != encoded:
            path.write_text(encoded, encoding="utf-8")
    return root


class UpdateManager(QObject):
    state_changed = Signal(str)
    download_progress = Signal(int, int)
    update_ready = Signal(str, str)
    no_update = Signal(str)
    error = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.state = "idle"
        self.latest_version = ""
        self.received_bytes = 0
        self.total_bytes = 0
        self.ready_installer: Path | None = None
        self._process: QProcess | None = None
        self._stdout_buffer = b""
        self._callbacks: dict[str, Callable[[dict[str, Any]], None]] = {}
        self._check_task_id = ""
        self._download_task_id = ""
        self._finished_tasks: dict[str, dict[str, Any]] = {}

    def _set_state(self, state: str) -> None:
        if self.state != state:
            self.state = state
            self.state_changed.emit(state)

    def _fail(self, message: str) -> None:
        logger.warning("Updater failure: %s", message)
        self._set_state("failed")
        self.error.emit(message)

    def _ensure_process(self) -> bool:
        if self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning:
            return True
        executable = updater_executable()
        if not executable.is_file():
            self._fail(f"更新核心不存在：{executable}")
            return False
        try:
            root = ensure_updater_configuration()
        except OSError as exc:
            self._fail(f"无法创建更新数据目录：{exc}")
            return False
        process = QProcess(self)
        process.setProgram(str(executable))
        process.setArguments(["serve", "--stdio", "--data-root", str(root)])
        process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        process.readyReadStandardOutput.connect(self._read_stdout)
        process.readyReadStandardError.connect(self._read_stderr)
        process.finished.connect(self._on_process_finished)
        process.start()
        if not process.waitForStarted(5_000):
            self._fail(f"更新核心启动失败：{process.errorString()}")
            process.deleteLater()
            return False
        self._process = process
        return True

    def _send_request(self, command: str, params: dict[str, Any] | None = None, callback: Callable[[dict[str, Any]], None] | None = None) -> str | None:
        if not self._ensure_process() or self._process is None:
            return None
        request_id = uuid.uuid4().hex
        if callback is not None:
            self._callbacks[request_id] = callback
        payload = {"protocol_version": PROTOCOL_VERSION, "type": "request", "request_id": request_id, "command": command, "params": params or {}}
        if self._process.write((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")) < 0:
            self._callbacks.pop(request_id, None)
            self._fail("无法向更新核心发送请求")
            return None
        return request_id

    def _read_stdout(self) -> None:
        if self._process is None:
            return
        self._stdout_buffer += bytes(self._process.readAllStandardOutput())
        while b"\n" in self._stdout_buffer:
            raw, self._stdout_buffer = self._stdout_buffer.split(b"\n", 1)
            if not raw.strip():
                continue
            try:
                self._handle_record(json.loads(raw.decode("utf-8")))
            except (UnicodeDecodeError, json.JSONDecodeError):
                logger.warning("Ignored invalid updater IPC record")

    def _read_stderr(self) -> None:
        if self._process is not None:
            message = bytes(self._process.readAllStandardError()).decode("utf-8", errors="replace").strip()
            if message:
                logger.warning("Updater stderr: %s", message)

    def _handle_record(self, record: dict[str, Any]) -> None:
        if record.get("type") == "response":
            callback = self._callbacks.pop(str(record.get("request_id", "")), None)
            if callback is not None:
                callback(record)
            return
        if record.get("type") != "event":
            return
        if record.get("event") == "progress":
            self._handle_progress(record.get("data") or {})
        elif record.get("event") == "task_finished":
            self._handle_task_finished(str(record.get("task_id", "")), record.get("data") or {})

    def _handle_progress(self, data: dict[str, Any]) -> None:
        status = str(data.get("status", ""))
        self._set_state("verifying" if status == "download_verifying" else "downloading")
        received, total = data.get("downloaded_bytes"), data.get("total_bytes")
        if isinstance(received, int) and isinstance(total, int):
            self.received_bytes, self.total_bytes = received, total
            self.download_progress.emit(received, total)

    def _handle_task_finished(self, task_id: str, data: dict[str, Any]) -> None:
        if task_id == self._check_task_id:
            self._check_task_id = ""
            if data.get("status") != "completed":
                self._fail(self._task_error(data))
                return
            result = data.get("result") or {}
            if not result.get("available"):
                self._set_state("up_to_date")
                self.no_update.emit(APP_VERSION)
                return
            self.latest_version = str(result.get("remote_version", ""))
            self._start_download()
        elif task_id == self._download_task_id:
            if data.get("status") != "completed":
                self._download_task_id = ""
                self._fail(self._task_error(data))
                return
            result, installer = data.get("result") or {}, data.get("installer")
            if not result.get("available") or not result.get("verified") or not isinstance(installer, str):
                self._download_task_id = ""
                self._fail("更新核心未返回已验证的安装包")
                return
            self.latest_version = str(result.get("version", self.latest_version))
            self.ready_installer = Path(installer)
            self._set_state("ready")
            self.update_ready.emit(self.latest_version, installer)
        else:
            # A very fast worker can finish before its acceptance response is read.
            self._finished_tasks[task_id] = data

    @staticmethod
    def _task_error(data: dict[str, Any]) -> str:
        return str((data.get("error") or {}).get("message") or "更新任务失败")

    def check_for_updates(self, manual: bool = False) -> bool:
        del manual
        if self.state in {"checking", "downloading", "verifying", "install_scheduled"}:
            return False
        self.latest_version = ""
        self.ready_installer = None
        self.received_bytes = self.total_bytes = 0
        self._set_state("checking")

        def accepted(record: dict[str, Any]) -> None:
            if not record.get("success"):
                self._fail(str((record.get("error") or {}).get("message", "检查更新失败")))
                return
            self._check_task_id = str((record.get("result") or {}).get("task_id", ""))
            if not self._check_task_id:
                self._fail("更新核心未返回检查任务编号")
                return
            finished = self._finished_tasks.pop(self._check_task_id, None)
            if finished is not None:
                self._handle_task_finished(self._check_task_id, finished)

        return self._send_request("check", {"current_version": APP_VERSION}, accepted) is not None

    def _start_download(self) -> None:
        self._set_state("downloading")

        def accepted(record: dict[str, Any]) -> None:
            if not record.get("success"):
                self._fail(str((record.get("error") or {}).get("message", "下载更新失败")))
                return
            self._download_task_id = str((record.get("result") or {}).get("task_id", ""))
            if not self._download_task_id:
                self._fail("更新核心未返回下载任务编号")
                return
            finished = self._finished_tasks.pop(self._download_task_id, None)
            if finished is not None:
                self._handle_task_finished(self._download_task_id, finished)

        self._send_request("download", {"current_version": APP_VERSION, "threads": 4, "confirmed": True}, accepted)

    def schedule_install(self) -> bool:
        if not self._download_task_id or self.ready_installer is None:
            return False
        loop, result, timer = QEventLoop(), {"accepted": False, "answered": False}, QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)

        def completed(record: dict[str, Any]) -> None:
            result["answered"] = True
            result["accepted"] = bool(record.get("success") and (record.get("result") or {}).get("accepted"))
            timer.stop()
            loop.quit()

        request_id = self._send_request("install", {"task_id": self._download_task_id, "process_id": os.getpid(), "confirmed": True}, completed)
        if request_id is None:
            return False
        timer.start(INSTALL_RESPONSE_TIMEOUT_MS)
        loop.exec()
        if not result["answered"]:
            self._callbacks.pop(request_id, None)
            self._fail("等待更新核心确认安装超时")
            return False
        if not result["accepted"]:
            self._fail("更新核心拒绝安装请求")
            return False
        self._set_state("install_scheduled")
        return True

    def _on_process_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        self._process = None
        if self.state in {"checking", "downloading", "verifying"}:
            self._fail(f"更新核心意外退出（代码 {exit_code}）")

    def shutdown(self) -> None:
        process = self._process
        if process is None or process.state() == QProcess.ProcessState.NotRunning:
            return
        self._send_request("shutdown")
        if not process.waitForFinished(5_000):
            process.terminate()
            if not process.waitForFinished(2_000):
                process.kill()
                process.waitForFinished(1_000)
        self._process = None
        self._callbacks.clear()
        self._finished_tasks.clear()
