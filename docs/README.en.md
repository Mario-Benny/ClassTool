# ClassTool Technical Documentation

This document is intended for developers who want to run ClassTool from source, create plugins, diagnose failures, or prepare a release. General users should start with the [English README](../README.en.md).

[中文技术文档](README.zh-CN.md)

## Contents

1. [Architecture](#1-architecture)
2. [Repository Layout](#2-repository-layout)
3. [Running from Source](#3-running-from-source)
4. [Resources and Runtime Data](#4-resources-and-runtime-data)
5. [Plugin Interface](#5-plugin-interface)
6. [Plugin Dependencies and Security](#6-plugin-dependencies-and-security)
7. [Packaging and Releases](#7-packaging-and-releases)
8. [Installer and Portable Build](#8-installer-and-portable-build)
9. [In-App Updates](#9-in-app-updates)
10. [Logs and Troubleshooting](#10-logs-and-troubleshooting)
11. [Testing and Contributions](#11-testing-and-contributions)

## 1. Architecture

ClassTool is a PySide6 desktop application for 64-bit Windows.

- The application is packaged with PyInstaller in `onedir` mode.
- Python, PySide6, Qt, and application modules are stored under `_internal/`.
- Language resources and `version.json` are bundled with the application.
- Plugins remain as inspectable Python files in the external `tools/` directory.
- Settings, logs, plugin metadata, and plugin data remain in the external `data/` directory.

The host owns the window, navigation, themes, languages, single-instance communication, logging, plugin discovery, update checks, and plugin lifecycle. Classroom features are implemented as plugins.

## 2. Repository Layout

```text
ClassTool/
|-- assets/
|   `-- logo.ico
|-- docs/
|   |-- README.zh-CN.md
|   `-- README.en.md
|-- release/                     # Public release assets only
|-- scripts/                     # PyInstaller, NSIS, and maintenance scripts
|-- src/ClassTool/
|   |-- language/                # Bundled JSON translations
|   |-- toolkit/                 # Host core and UI modules
|   |-- tools/                   # Official plugins and source template
|   |-- main.py
|   `-- version.json             # Single version source
|-- tests/
|-- requirements.txt
`-- requirements-dev.txt
```

Real runtime data is not stored in the source tree. ClassTool creates `data/` when it first runs.

## 3. Running from Source

Use 64-bit Windows 10 or Windows 11 and an isolated virtual environment. Python 3.10 or newer is recommended.

```bat
git clone https://github.com/Mario-Benny/ClassTool.git
cd ClassTool
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
cd src\ClassTool
python main.py
```

ClassTool uses a Windows single-instance mutex. A second launch activates the existing window. The `--tool <plugin-id>` argument asks the existing instance to open a specific plugin.

## 4. Resources and Runtime Data

### Languages

`src/ClassTool/language/` contains `zh_CN.json` and `en_US.json`. Both files must contain the same keys. Missing entries fall back to Simplified Chinese and then to the key itself.

### Version

`src/ClassTool/version.json` is the only application version source. Do not maintain a second hard-coded version in Python or a build script.

### Runtime data

| Path | Purpose |
| --- | --- |
| `data/settings.json` | Theme, language, window, update, and close behavior. |
| `data/tools_data.json` | Data stored through the plugin configuration API. |
| `data/plugin_cache.json` | Static plugin metadata cache. |
| `data/logs/` | Runtime and unhandled-exception logs. |

Never commit real classroom data, personal settings, tokens, or logs.

## 5. Plugin Interface

Plugins are `.py` files placed in the external `tools/` directory. ClassTool reads a literal `TOOL_INFO` dictionary through the AST and delays module import until the user opens the tool.

```python
TOOL_INFO = {
    "name": "Example Tool",
    "color": "#2D89EF",
    "icon": "\uECAA",
    "description": "A minimal ClassTool plugin.",
    "requirements": ["PySide6.QtWidgets"],
    "cache": True,
}
```

A plugin must provide at least one entry point:

- `create_widget()` returns a `QWidget`.
- `get_widget()` is a compatible widget entry point.
- `run()` executes a tool that does not need an embedded page.

Plugins that own threads, timers, cameras, devices, or independent windows should implement `cleanup()`. ClassTool calls it during a full application exit.

The complete template is [example_tool.py.txt](../src/ClassTool/tools/example_tool.py.txt). Copy and rename it to a unique `.py` file; the `.py.txt` suffix prevents the template from loading as an installed plugin.

Plugins can persist data through `get_tool_config()` and `set_tool_config()` from `toolkit.core.tools_config`.

## 6. Plugin Dependencies and Security

`TOOL_INFO["requirements"]` may contain import names or common package names with simple version constraints. ClassTool checks availability but never installs dependencies automatically.

Packaged ClassTool builds contain an embedded Python runtime. If a third-party plugin requires another library, that dependency must already exist under `_internal/`. A plugin file alone cannot add binary dependencies to a computer without Python.

Plugins are not sandboxed and run with permissions similar to the host. Install only trusted plugins and document any network, camera, microphone, clipboard, or file-system access. See the [Security Policy](SECURITY.md).

## 7. Packaging and Releases

Official builds use PyInstaller `onedir`, not `onefile`, to avoid extracting Python and Qt on every startup.

Release requirements:

1. Read the version from `version.json`.
2. Build with `--onedir --windowed`.
3. Bundle `language/` and `version.json`.
4. Include the required PySide6 network and multimedia modules.
5. Copy official plugins into external `tools/`, excluding `example_tool.py.txt`.
6. Create an empty external `data/` directory.
7. Test the result outside the development terminal.

Run the public build entry point with:

```bat
scripts\build_release.cmd
```

The script discovers Python and NSIS, builds the onedir application and NSIS installer, and writes the installer, SHA-256 checksum, and `update.json` to `release/`.

Do not commit PyInstaller `build/`, `dist/`, `.spec`, logs, or temporary directories. Historical binaries should be published as GitHub Release assets.

## 8. Installer and Portable Build

The NSIS installer:

- Requires 64-bit Windows and administrator privileges.
- Prefers `D:\ClassTool`, falling back to `Program Files\ClassTool` if drive D is unavailable.
- Allows users to select official plugins.
- Creates desktop, Start menu, uninstall, and context-menu entries.
- Can start ClassTool after installation.
- Can move itself to the Recycle Bin when requested.
- Preserves a clear boundary around user data and third-party plugins.

A portable package must keep this layout intact:

```text
ClassTool-v<version>-win-x64-portable/
|-- ClassTool.exe
|-- _internal/
|-- tools/
|-- data/
|-- 重建ClassTool快捷方式.cmd
|-- 注册桌面右键菜单.cmd
`-- 清除桌面右键菜单.cmd
```

Do not move `ClassTool.exe` without `_internal/`.

## 9. In-App Updates

The update engine is implemented by `toolkit/core/update_manager.py` and `update_launcher.py`. It uses PySide6 `QtNetwork` for non-blocking requests and reads the stable manifest from:

```text
https://github.com/Mario-Benny/ClassTool/releases/latest/download/update.json
```

Each stable GitHub Release must include the versioned installer and an asset named exactly `update.json`. The manifest declares the version, minimum updater version, installer URL, size, and SHA-256 digest.

The update flow:

1. Performs a delayed startup check or a user-requested manual check.
2. Compares strict three-part numeric versions.
3. Downloads to `%LOCALAPPDATA%\ClassTool\updates`.
4. Uses `.part` and state files for Range resume and retry backoff.
5. Validates free space, trusted HTTPS hosts, response ranges, size, and SHA-256.
6. Prompts the user after a verified installer is ready.
7. Re-verifies the path and SHA-256 before waiting for ClassTool to exit and launching the installer with elevation.

Automatic-check failures do not block normal application use. Manual failures are shown to the user and written to the log. SHA-256 protects consistency with the manifest but is not a replacement for a signed release manifest.

## 10. Logs and Troubleshooting

Start with `data/logs/` when diagnosing startup, plugin, device, or update failures.

| Symptom | Check |
| --- | --- |
| `DLL load failed while importing QtCore` | Confirm `_internal/` is complete and rebuild with a clean `PATH`. |
| Plugin is missing | Confirm the `.py` file, literal `TOOL_INFO`, and required dependencies. |
| Process remains after closing | Exit from the tray and confirm plugin `cleanup()` releases resources. |
| Camera is unavailable | Check Windows privacy permissions and multimedia dependencies. |
| Context menu is missing | Run the registration script as administrator or clear and re-register it. |
| Update check returns HTTP 404 | Upload an asset named exactly `update.json` to the latest GitHub Release. |
| Download verification fails | Regenerate the manifest from the same installer build. |

## 11. Testing and Contributions

Before submitting a change:

1. Parse or compile-check every Python file.
2. Confirm Chinese and English translation keys match.
3. Run `python -m unittest discover -s tests -v`.
4. Launch from source and open each affected plugin.
5. Confirm a full exit leaves no ClassTool process.
6. Test packaging changes outside the development terminal.
7. Check that no personal data, tokens, logs, or build caches are included.

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution requirements.
