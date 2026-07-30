# Plugin Development Guide

ClassTool plugins are ordinary Python files placed in the runtime `tools/`
directory. At startup, ClassTool reads each plugin's `TOOL_INFO` by static
analysis. The module itself is imported only when the user opens the tool.

## Minimal Plugin

```python
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


TOOL_INFO = {
    "name": "Example Tool",
    "color": "#2D89EF",
    "icon": "\uECAA",
    "description": "A minimal ClassTool plugin.",
    "requirements": ["PySide6.QtWidgets"],
    "cache": True,
}


def create_widget():
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.addWidget(QLabel("Hello from a ClassTool plugin."))
    return page
```

## `TOOL_INFO` Fields

- `name`: display name shown in the tool list.
- `color`: tile color, usually a hex color such as `#2D89EF`.
- `icon`: optional Segoe MDL2 Assets icon character.
- `description`: short plugin description.
- `requirements`: import names or package names required by the plugin.
- `cache`: whether the loaded module should be cached. Defaults to `True`.

## Supported Entry Points

A plugin must provide at least one of these functions:

- `create_widget()`: returns a `QWidget`.
- `get_widget()`: compatibility entry point that also returns a `QWidget`.
- `run()`: runs a non-visual task.

If both a widget entry point and `run()` exist, ClassTool opens the widget entry
point first.

## Plugin Settings

Plugins may store settings through the shared config helpers:

```python
from toolkit.core.tools_config import get_tool_config, set_tool_config
```

Data is stored in the runtime `data/tools_data.json` file. This file is user data
and should not be committed to GitHub.

## Third-Party Dependencies

List plugin dependencies in `TOOL_INFO["requirements"]`:

```python
"requirements": ["requests", "numpy"]
```

For release builds, those packages must also be available in the PyInstaller
build environment. Depending on the package, add PyInstaller options such as:

```bat
--hidden-import requests --collect-all numpy
```

## Plugin Security

ClassTool plugins are Python code executed on the user's computer. A plugin can
read files, access devices, start processes, or make network requests if its code
does so. For this reason, users should install plugins only from trusted sources.

Plugin authors should follow these rules:

- Keep plugin behavior transparent and explain any network, camera, microphone,
  file system, or clipboard access.
- Avoid executing shell commands unless the plugin's purpose clearly requires it.
- Do not collect credentials, tokens, classroom data, or personal information
  without explicit user consent.
- Validate user-provided file paths and inputs before using them.
- Release threads, timers, cameras, and temporary files in `cleanup()`.
- List third-party dependencies in `TOOL_INFO["requirements"]`.

ClassTool currently does not sandbox plugins. Treat third-party plugins with the
same caution as any other executable program.

## Cleanup Hook

If a plugin starts threads, opens cameras, creates timers, or holds temporary
resources, provide an optional cleanup hook:

```python
def cleanup():
    ...
```

ClassTool calls `cleanup()` when the application exits.

## Example

See [docs/examples/example_tool.py](examples/example_tool.py).
