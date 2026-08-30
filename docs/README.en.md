# ClassTool Technical Documentation

## 1. Overview

ClassTool is a Windows desktop toolkit for classroom use. It uses a single-file host application, external Python plugins, and external runtime data. The host owns windows, themes, language, navigation, tray behavior, and plugin lifecycle management; plugins provide individual classroom features.

The release package has this layout:

GitHub Releases provides versioned ZIP files, such as `ClassTool-v1.1.0-win-x64.zip`. After extraction, the layout is:

```text
ClassTool-v1.1.0-win-x64/
|-- ClassTool.exe            # Single-file host application
|-- tools/                   # Released plugins
`-- data/                    # User settings and plugin data
```

`ClassTool.exe` includes the Python runtime, PySide6 dependencies, and language resources, so target Windows computers do not need Python installed. Keep `tools/` and `data/` external and beside the EXE.

## 2. Source Layout

```text
src/ClassTool/
|-- language/                # Embedded language text
|-- toolkit/                 # Host core and user interface
|-- tools/                   # Bundled plugins and the example plugin
|-- data/                    # Local development data; do not commit real content
`-- main.py                  # Application entry point
```

The root-level `scripts/build_release.cmd` creates a versioned package, ZIP file, and SHA-256 checksum under the local `release/` directory. Release assets should be uploaded to GitHub Releases instead of committed to the source repository. `assets/logo.ico` is the Windows icon used during packaging.

## 3. Run from Source

ClassTool requires Windows 10 or later and Python 3.10 or later. From the repository root, install dependencies first:

```bat
python -m pip install -r requirements.txt
```

Then start the host:

```bat
cd src\ClassTool
python main.py
```

## 4. Host and Language System

The host provides Home, Settings, and About pages. Home shows available tools; Settings provides theme and language controls. Language text lives in `src/ClassTool/language/`, currently `zh_CN.txt` and `en_US.txt`. These resources are embedded in the EXE during packaging and are not published as external runtime files.

The selected theme, window state, and close behavior are stored in `data/settings.json` beside the running program. Static plugin metadata is cached in `data/plugin_cache.json` to reduce later startup scans. Both are user data and personal settings should not be committed to the repository.

## 5. Plugin Interface and Example

Plugins are ordinary Python files placed in `tools/`. At startup, ClassTool reads each plugin's `TOOL_INFO` statically. A plugin module is imported only after the user opens that tool. This reduces startup imports and avoids initialization side effects from unused plugins.

A plugin must provide at least one of these entry points:

- `create_widget()`: returns a `QWidget` page.
- `get_widget()`: a compatibility entry point equivalent to `create_widget()`.
- `run()`: runs a non-visual task.

A minimal plugin exposes metadata such as:

```python
TOOL_INFO = {
    "name": "Tool name",
    "color": "#2D89EF",
    "icon": "\uECAA",
    "description": "Tool description",
    "requirements": ["PySide6.QtWidgets"],
    "cache": True,
}
```

`name`, `color`, `icon`, and `description` are used by the tool tile. `requirements` declares modules needed by the plugin, while `cache` controls whether an imported plugin module is retained.

See the complete working template: [example_tool.py](../src/ClassTool/tools/example_tool.py). It lives in the source plugin directory so developers can copy, rename, and adapt it directly. The build script explicitly excludes it from the released package's `tools/` directory.

Plugins that use threads, timers, cameras, temporary files, or other external resources should provide `cleanup()`. The host calls this hook during shutdown; the plugin should stop work and release its resources there.

## 6. Plugin Data and Third-Party Dependencies

Plugins can read and write configuration through `get_tool_config()` and `set_tool_config()` in `toolkit.core.tools_config`. Data is stored in `data/tools_data.json` beside the running application. Do not commit data files containing real user content.

Third-party plugins run inside the host and do not have an independent Python environment. When a plugin needs packages such as `requests` or `numpy`, its author must:

1. Declare the dependency in `TOOL_INFO["requirements"]`.
2. Install the dependency in the packaging environment.
3. Add appropriate PyInstaller options, such as `--hidden-import` or `--collect-all`, so the dependency is collected into the EXE.

## 7. Build and Release

Install development dependencies first:

```bat
python -m pip install -r requirements-dev.txt
```

Then, from the repository root, run:

```bat
scripts\build_release.cmd
```

The script uses PyInstaller to create `release/ClassTool-v<version>-win-x64.zip`, embeds language resources, and copies released plugins into the package's `tools/` directory. A matching `.sha256` checksum file is created beside the ZIP. Do not publish personal `settings.json`, `plugin_cache.json`, or real classroom data; upload the ZIP and checksum to [GitHub Releases](https://github.com/Mario-Benny/ClassTool/releases).

The icon must be a valid Windows `.ico` file. If Explorer still shows an old icon after rebuilding, restart Explorer or clear the Windows icon cache.

## 8. Security

ClassTool does not sandbox plugins. A plugin has permissions similar to a local Python program and may access files, networks, cameras, microphones, or the clipboard. Install plugins only from trusted sources and inspect their source, dependencies, and data access behavior first.

Plugin authors should describe required permissions and must not collect credentials, tokens, classroom data, or personal information without consent. See [SECURITY.md](../SECURITY.md) for the complete policy.

## 9. Contributing

Bug reports, improvements, and new classroom plugins are welcome. Before contributing, ensure that the host starts, the changed plugin opens, and its dependencies are documented. Read [CONTRIBUTING.md](../CONTRIBUTING.md) first.
