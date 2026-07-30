# Contributing

Thanks for helping improve ClassTool.

## Development Setup

```bat
python -m pip install -r requirements-dev.txt
cd src\ClassTool
python main.py
```

## Plugin Contributions

Plugin files live under:

```text
src/ClassTool/tools/
```

Plugin requirements:

- Use a readable English file name, for example `timer_tool.py`.
- Define a `TOOL_INFO` dictionary.
- Implement `create_widget()`, `get_widget()`, or `run()`.
- List third-party dependencies in `TOOL_INFO["requirements"]`.
- Avoid heavy work during module import.
- Release threads, cameras, timers, and temporary resources in `cleanup()` when needed.

## Before Submitting

```bat
python -B -m py_compile src\ClassTool\main.py
```

If you changed a plugin, open ClassTool and test that plugin manually.
