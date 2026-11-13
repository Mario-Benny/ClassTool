# -*- coding: utf-8 -*-

"""GitHub Release 更新检查、断点续传、校验与安装调度。"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from toolkit.core.app_info import APP_VERSION
from toolkit.core.app_logging import get_logger
from toolkit.core.safe_io import atomic_write_text, read_text_with_fallback
from toolkit.core.update_launcher import schedule_installer


UPDATE_MANIFEST_URL = (
    "https://github.com/Mario-Benny/ClassTool/releases/latest/download/update.json"
)
UPDATE_ENGINE_VERSION = "1.0.0"
MANIFEST_MAX_BYTES = 256 * 1024
MAX_INSTALLER_BYTES = 1024 * 1024 * 1024
CHECK_TIMEOUT_MS = 20_000
DOWNLOAD_STALL_TIMEOUT_MS = 60_000
CHECK_RETRY_DELAYS_MS = (2_000, 5_000)
DOWNLOAD_RETRY_DELAYS_MS = (2_000, 5_000, 10_000)
DISK_RESERVE_BYTES = 64 * 1024 * 1024
PROGRESS_EMIT_INTERVAL_SECONDS = 0.1
PROGRESS_EMIT_BYTES = 64 * 1024
TRANSIENT_HTTP_STATUS = {408, 429, 500, 502, 503, 504}
ALLOWED_DOWNLOAD_HOSTS = {"github.com"}
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
SAFE_FILE_RE = re.compile(r"^[A-Za-z0-9._-]+\.exe$", re.IGNORECASE)
CONTENT_RANGE_RE = re.compile(r"^bytes (\d+)-(\d+)/(\d+)$", re.IGNORECASE)

_logger = get_logger("update")


class UpdateMetadataError(ValueError):
    """远程更新元数据不可用或不安全。"""


@dataclass(frozen=True)
class InstallerAsset:
    name: str
    url: str
    size: int
    sha256: str


@dataclass(frozen=True)
class UpdateManifest:
    version: str
    minimum_updater_version: str
    channel: str
    mandatory: bool
    published_at: str
    release_notes_url: str
    installer: InstallerAsset


def parse_version(value: str) -> tuple[int, int, int]:
    """按 ClassTool 三段数字版本规则解析版本号。"""
    if not isinstance(value, str):
        raise ValueError("版本号必须是字符串")
    parts = value.strip().lstrip("vV").split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise ValueError(f"无效版本号: {value!r}")
    numbers = tuple(int(part) for part in parts)
    if numbers[1] > 99 or numbers[2] > 99:
        raise ValueError(f"版本号分段超出 0-99: {value!r}")
    return numbers


def parse_content_range(value: str) -> tuple[int, int, int]:
    """严格解析 HTTP ``Content-Range``，拒绝不完整或矛盾的范围。"""
    match = CONTENT_RANGE_RE.fullmatch(value.strip())
    if not match:
        raise ValueError("无效的 Content-Range")
    start, end, total = (int(item) for item in match.groups())
    if start > end or end >= total:
        raise ValueError("Content-Range 范围越界")
    return start, end, total


def is_transient_failure(error: QNetworkReply.NetworkError, status: int | None) -> bool:
    """判断错误是否适合自动重试，永久性 HTTP/协议错误不重试。"""
    if status in TRANSIENT_HTTP_STATUS:
        return True
    if error in (
        QNetworkReply.NetworkError.NoError,
        QNetworkReply.NetworkError.OperationCanceledError,
    ):
        return False
    error_code = getattr(error, "value", error)
    return 0 < int(error_code) < 100


def has_sufficient_disk_space(
    directory: Path,
    remaining_bytes: int,
    *,
    free_bytes: int | None = None,
) -> bool:
    """为剩余下载内容预留固定安全空间。``free_bytes`` 仅供测试注入。"""
    if remaining_bytes < 0:
        return False
    if remaining_bytes == 0:
        return True
    if free_bytes is None:
        free_bytes = shutil.disk_usage(directory).free
    return free_bytes >= remaining_bytes + DISK_RESERVE_BYTES


def _is_allowed_https_url(value: str, allow_cdn: bool = False) -> bool:
    url = QUrl(value)
    if not url.isValid() or url.scheme().lower() != "https":
        return False
    host = url.host().lower()
    if host in ALLOWED_DOWNLOAD_HOSTS:
        return True
    return allow_cdn and host.endswith(".githubusercontent.com")


def parse_manifest(payload: bytes) -> UpdateManifest:
    """解析并严格校验 GitHub 上的 ``update.json``。"""
    if not payload or len(payload) > MANIFEST_MAX_BYTES:
        raise UpdateMetadataError("更新清单为空或过大")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateMetadataError("更新清单不是有效的 UTF-8 JSON") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise UpdateMetadataError("不支持的更新清单格式")

    version = data.get("version")
    try:
        parse_version(version)
    except ValueError as exc:
        raise UpdateMetadataError(str(exc)) from exc

    channel = data.get("channel", "stable")
    if channel != "stable":
        raise UpdateMetadataError("当前版本只接受 stable 更新通道")
    mandatory = data.get("mandatory", False)
    if not isinstance(mandatory, bool):
        raise UpdateMetadataError("mandatory 必须是布尔值")

    minimum_updater_version = data.get("minimum_updater_version", "1.0.0")
    try:
        required_updater = parse_version(minimum_updater_version)
        current_updater = parse_version(UPDATE_ENGINE_VERSION)
    except ValueError as exc:
        raise UpdateMetadataError("minimum_updater_version 无效") from exc
    if required_updater > current_updater:
        raise UpdateMetadataError("该更新需要更高版本的更新引擎，请手动下载安装")

    installer = data.get("installer")
    if not isinstance(installer, dict):
        raise UpdateMetadataError("更新清单缺少 installer")
    name = installer.get("name")
    url = installer.get("url")
    size = installer.get("size")
    digest = installer.get("sha256")
    if not isinstance(name, str) or not SAFE_FILE_RE.fullmatch(name):
        raise UpdateMetadataError("安装器文件名不安全")
    if Path(name).name != name:
        raise UpdateMetadataError("安装器文件名不能包含路径")
    if not isinstance(url, str) or not _is_allowed_https_url(url):
        raise UpdateMetadataError("安装器必须使用可信 GitHub HTTPS 地址")
    if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= MAX_INSTALLER_BYTES:
        raise UpdateMetadataError("安装器大小无效")
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        raise UpdateMetadataError("安装器 SHA-256 无效")

    notes_url = data.get("release_notes_url", "")
    if notes_url and (not isinstance(notes_url, str) or not _is_allowed_https_url(notes_url)):
        raise UpdateMetadataError("更新说明地址无效")

    published_at = data.get("published_at", "")
    if not isinstance(published_at, str):
        published_at = ""

    return UpdateManifest(
        version=version.strip().lstrip("vV"),
        minimum_updater_version=minimum_updater_version,
        channel=channel,
        mandatory=mandatory,
        published_at=published_at,
        release_notes_url=notes_url,
        installer=InstallerAsset(
            name=name,
            url=url,
            size=size,
            sha256=digest.lower(),
        ),
    )


def update_storage_dir() -> Path:
    """返回不受 Program Files 写权限影响的更新缓存目录。"""
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path(tempfile.gettempdir())
    path = root / "ClassTool" / "updates"
    path.mkdir(parents=True, exist_ok=True)
    return path


class UpdateManager(QObject):
    """在 Qt 事件循环中执行非阻塞更新检查和下载。"""

    state_changed = Signal(str)
    download_progress = Signal(int, int)
    update_ready = Signal(str, str)
    no_update = Signal(str)
    error = Signal(str)

    def __init__(self, parent: QObject | None = None, manifest_url: str = UPDATE_MANIFEST_URL):
        super().__init__(parent)
        self.manifest_url = manifest_url
        self.network = QNetworkAccessManager(self)
        self.state = "idle"
        self.latest_version = ""
        self.received_bytes = 0
        self.total_bytes = 0
        self.ready_installer: Path | None = None
        self._manifest: UpdateManifest | None = None
        self._check_reply: QNetworkReply | None = None
        self._download_reply: QNetworkReply | None = None
        self._download_file = None
        self._download_base = 0
        self._output_ready = False
        self._range_retry_used = False
        self._shutting_down = False
        self._manual_check = False
        self._check_retry_count = 0
        self._download_retry_count = 0
        self._check_timed_out = False
        self._download_stalled = False
        self._download_protocol_error = ""
        self._last_progress_emit_at = 0.0
        self._last_progress_emit_bytes = 0

        self._check_timer = QTimer(self)
        self._check_timer.setSingleShot(True)
        self._check_timer.timeout.connect(self._abort_check_timeout)
        self._stall_timer = QTimer(self)
        self._stall_timer.setSingleShot(True)
        self._stall_timer.timeout.connect(self._abort_download_stall)
        self._retry_timer = QTimer(self)
        self._retry_timer.setSingleShot(True)

    def _set_state(self, state: str) -> None:
        self.state = state
        self.state_changed.emit(state)

    @staticmethod
    def _make_request(url: str) -> QNetworkRequest:
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"Accept", b"application/json, application/octet-stream")
        request.setRawHeader(b"Cache-Control", b"no-cache")
        request.setRawHeader(
            b"User-Agent",
            f"ClassTool-Updater/{UPDATE_ENGINE_VERSION}".encode("ascii"),
        )
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
        )
        return request

    def check_for_updates(self, manual: bool = False) -> bool:
        """检查远程版本；发现新版后立即开始后台下载。"""
        if (
            self._check_reply is not None
            or self._download_reply is not None
            or self._retry_timer.isActive()
        ):
            return False
        if not _is_allowed_https_url(self.manifest_url):
            self._report_error("更新清单地址不安全")
            return False

        self._manual_check = manual
        self._shutting_down = False
        self._check_retry_count = 0
        self._check_timed_out = False
        self._set_state("checking")
        self._start_check_request()
        return True

    def _start_check_request(self) -> None:
        reply = self.network.get(self._make_request(self.manifest_url))
        self._check_reply = reply
        reply.finished.connect(lambda: self._finish_check(reply))
        self._check_timer.start(CHECK_TIMEOUT_MS)

    def _abort_check_timeout(self) -> None:
        if self._check_reply is not None and self._check_reply.isRunning():
            self._check_timed_out = True
            self._check_reply.abort()

    def _finish_check(self, reply: QNetworkReply) -> None:
        if reply is not self._check_reply:
            return
        self._check_timer.stop()
        self._check_reply = None
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        error = reply.error()
        payload = bytes(reply.readAll())
        message = reply.errorString()
        final_url = reply.url().toString()
        reply.deleteLater()

        if self._shutting_down:
            return
        if self._check_timed_out:
            message = "检查更新超时"
        if error != QNetworkReply.NetworkError.NoError or status != 200:
            if self._retry_check(error, status):
                return
            self._report_error(f"更新检查失败（HTTP {status or 0}）：{message}")
            return
        if not _is_allowed_https_url(final_url, allow_cdn=True):
            self._report_error("更新清单被重定向到不可信地址")
            return
        try:
            manifest = parse_manifest(payload)
            local_version = parse_version(APP_VERSION)
            remote_version = parse_version(manifest.version)
        except (UpdateMetadataError, ValueError) as exc:
            self._report_error(str(exc))
            return

        self.latest_version = manifest.version
        if remote_version <= local_version:
            self._cleanup_cached_updates()
            self._set_state("up_to_date")
            self.no_update.emit(APP_VERSION)
            return

        self._manifest = manifest
        self._prepare_download(manifest)

    def _retry_check(
        self,
        error: QNetworkReply.NetworkError,
        status: int | None,
    ) -> bool:
        retryable = self._check_timed_out or is_transient_failure(error, status)
        if not retryable or self._check_retry_count >= len(CHECK_RETRY_DELAYS_MS):
            return False
        delay = CHECK_RETRY_DELAYS_MS[self._check_retry_count]
        self._check_retry_count += 1
        self._check_timed_out = False
        _logger.info("更新检查将在 %.1f 秒后重试", delay / 1000)
        try:
            self._retry_timer.timeout.disconnect()
        except (RuntimeError, TypeError):
            pass
        self._retry_timer.timeout.connect(self._start_check_request)
        self._retry_timer.start(delay)
        return True

    def _paths_for(self, manifest: UpdateManifest) -> tuple[Path, Path, Path]:
        directory = update_storage_dir()
        final_path = directory / manifest.installer.name
        part_path = directory / f"{manifest.installer.name}.part"
        state_path = directory / f"{manifest.installer.name}.download.json"
        return final_path, part_path, state_path

    def _prepare_download(self, manifest: UpdateManifest) -> None:
        self._range_retry_used = False
        self._download_retry_count = 0
        try:
            final_path, part_path, state_path = self._paths_for(manifest)
        except OSError as exc:
            self._report_error(f"无法创建更新缓存目录：{exc}")
            return
        self._cleanup_cached_updates(keep_prefix=manifest.installer.name)
        try:
            if final_path.is_file():
                self._set_state("verifying")
                if self._verify_file(final_path, manifest.installer):
                    self.ready_installer = final_path
                    self._set_state("ready")
                    self.update_ready.emit(manifest.version, str(final_path))
                    return
            final_path.unlink(missing_ok=True)

            state = self._read_state(state_path)
            expected = {
                "version": manifest.version,
                "url": manifest.installer.url,
                "size": manifest.installer.size,
                "sha256": manifest.installer.sha256,
            }
            if any(state.get(key) != value for key, value in expected.items()):
                part_path.unlink(missing_ok=True)
                state_path.unlink(missing_ok=True)
                state = {}

            base = part_path.stat().st_size if part_path.is_file() else 0
            if base > manifest.installer.size:
                part_path.unlink(missing_ok=True)
                base = 0
        except OSError as exc:
            self._report_error(f"无法整理更新缓存文件：{exc}")
            return
        self._start_download(manifest, base, state.get("etag", ""))

    def _start_download(self, manifest: UpdateManifest, base: int, etag: str) -> None:
        try:
            directory = update_storage_dir()
            remaining = max(manifest.installer.size - base, 0)
            if not has_sufficient_disk_space(directory, remaining):
                self._report_error("更新缓存所在磁盘空间不足")
                return
        except OSError as exc:
            self._report_error(f"无法检查更新缓存磁盘空间：{exc}")
            return

        self._manifest = manifest
        self._download_base = base
        self._output_ready = False
        self._download_stalled = False
        self._download_protocol_error = ""
        self.received_bytes = base
        self.total_bytes = manifest.installer.size
        self._last_progress_emit_at = 0.0
        self._last_progress_emit_bytes = base
        request = self._make_request(manifest.installer.url)
        request.setRawHeader(b"Accept", b"application/octet-stream")
        if base:
            request.setRawHeader(b"Range", f"bytes={base}-".encode("ascii"))
            if etag:
                request.setRawHeader(b"If-Range", etag.encode("utf-8"))
        reply = self.network.get(request)
        self._download_reply = reply
        reply.metaDataChanged.connect(lambda: self._prepare_output(reply))
        reply.readyRead.connect(lambda: self._read_download_data(reply))
        reply.downloadProgress.connect(self._on_download_progress)
        reply.finished.connect(lambda: self._finish_download(reply))
        self._stall_timer.start(DOWNLOAD_STALL_TIMEOUT_MS)
        self._set_state("downloading")

    def _prepare_output(self, reply: QNetworkReply) -> None:
        if self._shutting_down or reply is not self._download_reply or self._output_ready:
            return
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        if status is None:
            return
        if 300 <= status < 400:
            return
        if not _is_allowed_https_url(reply.url().toString(), allow_cdn=True):
            self._download_protocol_error = "安装包被重定向到不可信地址"
            reply.abort()
            return

        try:
            _, part_path, state_path = self._paths_for(self._manifest)
        except OSError as exc:
            self._download_protocol_error = f"无法访问更新缓存目录：{exc}"
            reply.abort()
            return
        mode = "wb"
        if status == 416:
            return
        try:
            mode = self._validate_download_response(reply, status)
        except UpdateMetadataError as exc:
            self._download_protocol_error = str(exc)
            reply.abort()
            return

        try:
            self._download_file = part_path.open(mode)
        except OSError as exc:
            _logger.error("无法打开更新临时文件: %s", exc)
            self._download_protocol_error = f"无法打开更新临时文件：{exc}"
            reply.abort()
            return
        self._output_ready = True
        self._write_state(
            state_path,
            self._manifest,
            bytes(reply.rawHeader(b"ETag")).decode("utf-8", "ignore"),
            "downloading",
        )

    def _validate_download_response(self, reply: QNetworkReply, status: int) -> str:
        """校验服务器声明的响应范围，返回临时文件打开模式。"""
        manifest = self._manifest
        if manifest is None:
            raise UpdateMetadataError("更新下载状态丢失")

        content_length_text = bytes(reply.rawHeader(b"Content-Length")).decode(
            "ascii", "ignore"
        ).strip()
        content_length: int | None = None
        if content_length_text:
            if not content_length_text.isdigit():
                raise UpdateMetadataError("安装包 Content-Length 无效")
            content_length = int(content_length_text)

        if status == 200:
            if content_length is not None and content_length != manifest.installer.size:
                raise UpdateMetadataError("安装包响应长度与更新清单不一致")
            self._download_base = 0
            return "wb"

        if status != 206:
            raise UpdateMetadataError(f"安装包服务器返回了不支持的 HTTP {status}")

        raw_range = bytes(reply.rawHeader(b"Content-Range")).decode("ascii", "ignore")
        try:
            start, end, total = parse_content_range(raw_range)
        except ValueError as exc:
            raise UpdateMetadataError(str(exc)) from exc
        if (
            start != self._download_base
            or total != manifest.installer.size
            or end != total - 1
        ):
            raise UpdateMetadataError("安装包分段范围与本地断点不一致")
        expected_length = end - start + 1
        if content_length is not None and content_length != expected_length:
            raise UpdateMetadataError("安装包分段长度与 Content-Range 不一致")
        return "ab" if self._download_base else "wb"

    def _read_download_data(self, reply: QNetworkReply) -> None:
        self._prepare_output(reply)
        if self._download_file is None:
            return
        chunk = bytes(reply.readAll())
        if chunk:
            try:
                self._download_file.write(chunk)
                self._stall_timer.start(DOWNLOAD_STALL_TIMEOUT_MS)
            except OSError as exc:
                _logger.error("更新文件写入失败: %s", exc)
                self._download_protocol_error = f"更新文件写入失败：{exc}"
                reply.abort()

    def _on_download_progress(self, received: int, _total: int) -> None:
        self.received_bytes = min(self._download_base + max(received, 0), self.total_bytes)
        now = time.monotonic()
        bytes_delta = self.received_bytes - self._last_progress_emit_bytes
        if (
            self.received_bytes >= self.total_bytes
            or bytes_delta >= PROGRESS_EMIT_BYTES
            or now - self._last_progress_emit_at >= PROGRESS_EMIT_INTERVAL_SECONDS
        ):
            self._last_progress_emit_at = now
            self._last_progress_emit_bytes = self.received_bytes
            self.download_progress.emit(self.received_bytes, self.total_bytes)
        if received > 0:
            self._stall_timer.start(DOWNLOAD_STALL_TIMEOUT_MS)

    def _abort_download_stall(self) -> None:
        if self._download_reply is not None and self._download_reply.isRunning():
            self._download_stalled = True
            self._download_reply.abort()

    def _finish_download(self, reply: QNetworkReply) -> None:
        if reply is not self._download_reply:
            return
        self._stall_timer.stop()
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        self._read_download_data(reply)
        self._close_download_file()
        self._download_reply = None
        error = reply.error()
        message = reply.errorString()
        reply.deleteLater()

        if self._shutting_down:
            return
        manifest = self._manifest
        if manifest is None:
            self._report_error("更新下载状态丢失")
            return
        try:
            final_path, part_path, state_path = self._paths_for(manifest)
        except OSError as exc:
            self._report_error(f"无法访问更新缓存目录：{exc}")
            return

        if status == 416 and not self._range_retry_used:
            if part_path.is_file() and self._verify_file(part_path, manifest.installer):
                try:
                    os.replace(part_path, final_path)
                except OSError as exc:
                    self._report_error(f"无法完成安装包文件：{exc}")
                    return
                self._mark_ready(manifest, final_path, state_path)
                return
            self._range_retry_used = True
            try:
                part_path.unlink(missing_ok=True)
                state_path.unlink(missing_ok=True)
            except OSError as exc:
                self._report_error(f"无法重置更新断点文件：{exc}")
                return
            self._start_download(manifest, 0, "")
            return

        if self._download_protocol_error:
            self._report_error(self._download_protocol_error)
            return
        if error != QNetworkReply.NetworkError.NoError or status not in (200, 206):
            if self._retry_download(error, status, manifest):
                return
            self._report_error(f"更新下载中断（HTTP {status or 0}）：{message}")
            return
        try:
            part_size = part_path.stat().st_size if part_path.is_file() else -1
        except OSError as exc:
            self._report_error(f"无法读取更新临时文件：{exc}")
            return
        if part_size != manifest.installer.size:
            self._report_error("安装包大小与更新清单不一致")
            return
        self._set_state("verifying")
        if not self._verify_file(part_path, manifest.installer):
            try:
                part_path.unlink(missing_ok=True)
                state_path.unlink(missing_ok=True)
            except OSError as exc:
                _logger.warning("损坏更新文件清理失败: %s", exc)
            self._report_error("安装包 SHA-256 校验失败，已拒绝使用该文件")
            return

        try:
            os.replace(part_path, final_path)
        except OSError as exc:
            self._report_error(f"无法完成安装包文件：{exc}")
            return
        self._mark_ready(manifest, final_path, state_path)

    def _retry_download(
        self,
        error: QNetworkReply.NetworkError,
        status: int | None,
        manifest: UpdateManifest,
    ) -> bool:
        retryable = self._download_stalled or is_transient_failure(error, status)
        if not retryable or self._download_retry_count >= len(DOWNLOAD_RETRY_DELAYS_MS):
            return False
        delay = DOWNLOAD_RETRY_DELAYS_MS[self._download_retry_count]
        self._download_retry_count += 1
        try:
            _, part_path, state_path = self._paths_for(manifest)
            base = part_path.stat().st_size if part_path.is_file() else 0
            state = self._read_state(state_path)
        except OSError as exc:
            self._report_error(f"无法恢复更新下载：{exc}")
            return True

        _logger.info(
            "更新下载将在 %.1f 秒后从 %d 字节处重试",
            delay / 1000,
            base,
        )
        self._set_state("downloading")
        try:
            self._retry_timer.timeout.disconnect()
        except (RuntimeError, TypeError):
            pass
        self._retry_timer.timeout.connect(
            lambda: self._start_download(manifest, base, state.get("etag", ""))
        )
        self._retry_timer.start(delay)
        return True

    def _mark_ready(self, manifest: UpdateManifest, path: Path, state_path: Path) -> None:
        self.ready_installer = path
        self.received_bytes = manifest.installer.size
        self._write_state(state_path, manifest, "", "ready")
        self._set_state("ready")
        self.update_ready.emit(manifest.version, str(path))

    def _close_download_file(self) -> None:
        if self._download_file is not None:
            try:
                self._download_file.flush()
                self._download_file.close()
            except OSError:
                pass
            self._download_file = None

    @staticmethod
    def _verify_file(path: Path, asset: InstallerAsset) -> bool:
        try:
            if path.stat().st_size != asset.size:
                return False
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            return digest.hexdigest().lower() == asset.sha256
        except OSError:
            return False

    @staticmethod
    def _read_state(path: Path) -> dict[str, Any]:
        if not path.is_file():
            return {}
        try:
            data = json.loads(read_text_with_fallback(path))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _write_state(path: Path, manifest: UpdateManifest, etag: str, status: str) -> None:
        payload = {
            "version": manifest.version,
            "url": manifest.installer.url,
            "size": manifest.installer.size,
            "sha256": manifest.installer.sha256,
            "etag": etag,
            "status": status,
        }
        try:
            atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))
        except OSError as exc:
            _logger.warning("无法保存更新下载状态: %s", exc)

    @staticmethod
    def _cleanup_cached_updates(keep_prefix: str = "") -> None:
        """清理专用缓存目录中的旧官方安装器和分段文件。"""
        try:
            directory = update_storage_dir()
            for path in directory.iterdir():
                if not path.is_file() or not path.name.startswith("ClassTool-v"):
                    continue
                if "-Setup.exe" not in path.name:
                    continue
                if keep_prefix and path.name.startswith(keep_prefix):
                    continue
                path.unlink(missing_ok=True)
        except OSError as exc:
            _logger.warning("旧更新缓存清理失败: %s", exc)

    def _report_error(self, message: str) -> None:
        _logger.warning("%s", message)
        self._set_state("failed")
        self.error.emit(message)

    def schedule_install(self) -> bool:
        """二次校验安装器后，安排其在主程序退出后启动。"""
        manifest = self._manifest
        if manifest is None or self.ready_installer is None:
            return False
        try:
            installer = self.ready_installer.resolve(strict=True)
            cache_dir = update_storage_dir().resolve(strict=True)
        except OSError as exc:
            _logger.error("无法访问待安装更新: %s", exc)
            return False
        if installer.parent != cache_dir or installer.name != manifest.installer.name:
            _logger.error("拒绝启动更新缓存目录之外的安装器: %s", installer)
            return False

        self._set_state("verifying")
        if not self._verify_file(installer, manifest.installer):
            self.ready_installer = None
            try:
                installer.unlink(missing_ok=True)
            except OSError:
                pass
            self._report_error("安装前校验失败，更新文件可能已被修改")
            return False
        if not schedule_installer(installer):
            self._set_state("ready")
            return False
        self._set_state("install_scheduled")
        return True

    def shutdown(self) -> None:
        """退出时中止网络任务；已写入的分段留给下次续传。"""
        self._shutting_down = True
        self._check_timer.stop()
        self._stall_timer.stop()
        self._retry_timer.stop()
        if self._check_reply is not None:
            self._check_reply.abort()
        if self._download_reply is not None:
            self._download_reply.abort()
        self._close_download_file()

