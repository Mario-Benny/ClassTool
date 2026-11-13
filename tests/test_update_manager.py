# -*- coding: utf-8 -*-

import json
import hashlib
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "src" / "ClassTool"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from toolkit.core.update_manager import (  # noqa: E402
    DISK_RESERVE_BYTES,
    InstallerAsset,
    UpdateManager,
    UpdateMetadataError,
    has_sufficient_disk_space,
    is_transient_failure,
    parse_content_range,
    parse_manifest,
    parse_version,
)
from PySide6.QtNetwork import QNetworkReply  # noqa: E402


def manifest_payload(**changes) -> bytes:
    data = {
        "schema_version": 1,
        "version": "1.2.2",
        "minimum_updater_version": "1.0.0",
        "channel": "stable",
        "mandatory": False,
        "published_at": "2026-11-11",
        "installer": {
            "name": "ClassTool-v1.2.2-Setup.exe",
            "url": (
                "https://github.com/Mario-Benny/ClassTool/releases/download/"
                "v1.2.2/ClassTool-v1.2.2-Setup.exe"
            ),
            "size": 1024,
            "sha256": "ab" * 32,
        },
        "release_notes_url": (
            "https://github.com/Mario-Benny/ClassTool/releases/tag/v1.2.2"
        ),
    }
    for key, value in changes.items():
        if key.startswith("installer_"):
            data["installer"][key.removeprefix("installer_")] = value
        else:
            data[key] = value
    return json.dumps(data).encode("utf-8")


class VersionTests(unittest.TestCase):
    def test_numeric_order(self):
        self.assertLess(parse_version("1.2.9"), parse_version("1.2.10"))
        self.assertLess(parse_version("1.2.99"), parse_version("1.3.0"))

    def test_optional_v_prefix(self):
        self.assertEqual(parse_version("v1.2.3"), (1, 2, 3))

    def test_invalid_version_rejected(self):
        for value in ("1.2", "1.2.beta", "1.2.100", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_version(value)


class ManifestTests(unittest.TestCase):
    def test_valid_manifest(self):
        manifest = parse_manifest(manifest_payload())
        self.assertEqual(manifest.version, "1.2.2")
        self.assertEqual(manifest.installer.size, 1024)
        self.assertEqual(manifest.installer.sha256, "ab" * 32)

    def test_http_download_rejected(self):
        with self.assertRaises(UpdateMetadataError):
            parse_manifest(manifest_payload(installer_url="http://example.com/a.exe"))

    def test_path_in_installer_name_rejected(self):
        with self.assertRaises(UpdateMetadataError):
            parse_manifest(manifest_payload(installer_name="../update.exe"))

    def test_bad_digest_rejected(self):
        with self.assertRaises(UpdateMetadataError):
            parse_manifest(manifest_payload(installer_sha256="not-a-hash"))

    def test_non_stable_channel_rejected(self):
        with self.assertRaises(UpdateMetadataError):
            parse_manifest(manifest_payload(channel="beta"))

    def test_newer_updater_requirement_rejected(self):
        with self.assertRaises(UpdateMetadataError):
            parse_manifest(manifest_payload(minimum_updater_version="1.0.1"))


class TransportValidationTests(unittest.TestCase):
    class Reply:
        def __init__(self, **headers):
            self.headers = {
                key.lower().replace("_", "-").encode("ascii"): str(value).encode("ascii")
                for key, value in headers.items()
            }

        def rawHeader(self, name):
            return self.headers.get(bytes(name).lower(), b"")

    def setUp(self):
        self.manifest = parse_manifest(manifest_payload(installer_size=1024))

    def test_content_range_parser(self):
        self.assertEqual(parse_content_range("bytes 128-1023/1024"), (128, 1023, 1024))
        for value in ("bytes */1024", "bytes 5-4/10", "bytes 0-10/10", "0-9/10"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_content_range(value)

    def test_resume_response_must_match_requested_range(self):
        manager = SimpleNamespace(_manifest=self.manifest, _download_base=128)
        reply = self.Reply(content_range="bytes 128-1023/1024", content_length=896)
        mode = UpdateManager._validate_download_response(manager, reply, 206)
        self.assertEqual(mode, "ab")

        bad_reply = self.Reply(content_range="bytes 127-1023/1024", content_length=897)
        with self.assertRaises(UpdateMetadataError):
            UpdateManager._validate_download_response(manager, bad_reply, 206)

    def test_full_response_length_must_match_manifest(self):
        manager = SimpleNamespace(_manifest=self.manifest, _download_base=128)
        reply = self.Reply(content_length=1000)
        with self.assertRaises(UpdateMetadataError):
            UpdateManager._validate_download_response(manager, reply, 200)

    def test_retry_classification(self):
        self.assertTrue(
            is_transient_failure(QNetworkReply.NetworkError.NoError, 503)
        )
        self.assertTrue(
            is_transient_failure(QNetworkReply.NetworkError.TimeoutError, None)
        )
        self.assertFalse(
            is_transient_failure(QNetworkReply.NetworkError.NoError, 404)
        )
        self.assertFalse(
            is_transient_failure(
                QNetworkReply.NetworkError.OperationCanceledError,
                None,
            )
        )

    def test_disk_space_reserve(self):
        required = 1024
        self.assertTrue(
            has_sufficient_disk_space(
                ROOT,
                required,
                free_bytes=required + DISK_RESERVE_BYTES,
            )
        )
        self.assertFalse(
            has_sufficient_disk_space(
                ROOT,
                required,
                free_bytes=required + DISK_RESERVE_BYTES - 1,
            )
        )
        self.assertTrue(has_sufficient_disk_space(ROOT, 0, free_bytes=0))


class InstallerVerificationTests(unittest.TestCase):
    def test_size_and_hash_must_both_match(self):
        path = APP_ROOT / "version.json"
        content = path.read_bytes()
        asset = InstallerAsset(
            name="ClassTool-v1.2.2-Setup.exe",
            url=(
                "https://github.com/Mario-Benny/ClassTool/releases/download/"
                "v1.2.2/ClassTool-v1.2.2-Setup.exe"
            ),
            size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )
        self.assertTrue(UpdateManager._verify_file(path, asset))
        wrong_size = InstallerAsset(
            name=asset.name,
            url=asset.url,
            size=asset.size + 1,
            sha256=asset.sha256,
        )
        wrong_hash = InstallerAsset(
            name=asset.name,
            url=asset.url,
            size=asset.size,
            sha256="00" * 32,
        )
        self.assertFalse(UpdateManager._verify_file(path, wrong_size))
        self.assertFalse(UpdateManager._verify_file(path, wrong_hash))

    def test_schedule_install_reverifies_cached_file(self):
        installer = APP_ROOT / "version.json"
        content = installer.read_bytes()
        asset = InstallerAsset(
            name=installer.name,
            url=(
                "https://github.com/Mario-Benny/ClassTool/releases/download/"
                "v1.2.2/ClassTool-v1.2.2-Setup.exe"
            ),
            size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )
        states = []
        manager = SimpleNamespace(
            _manifest=SimpleNamespace(installer=asset),
            ready_installer=installer,
            _verify_file=UpdateManager._verify_file,
            _set_state=states.append,
            _report_error=Mock(),
        )
        with (
            patch("toolkit.core.update_manager.update_storage_dir", return_value=APP_ROOT),
            patch("toolkit.core.update_manager.schedule_installer", return_value=True) as launch,
        ):
            self.assertTrue(UpdateManager.schedule_install(manager))
            launch.assert_called_once_with(installer.resolve())
        self.assertEqual(states, ["verifying", "install_scheduled"])

        bad_asset = InstallerAsset(
            name=asset.name,
            url=asset.url,
            size=asset.size,
            sha256="00" * 32,
        )
        manager._manifest = SimpleNamespace(installer=bad_asset)
        manager.ready_installer = installer
        states.clear()
        with (
            patch("toolkit.core.update_manager.update_storage_dir", return_value=APP_ROOT),
            patch("toolkit.core.update_manager.schedule_installer") as launch,
            patch.object(Path, "unlink") as unlink,
        ):
            self.assertFalse(UpdateManager.schedule_install(manager))
            launch.assert_not_called()
            unlink.assert_called_once()
        manager._report_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
