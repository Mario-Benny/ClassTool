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

Before submitting a change:

- Parse or compile-check every Python file under `src/ClassTool/`.
- Confirm that `zh_CN.json` and `en_US.json` contain the same translation keys.
- Start ClassTool from source and open every affected plugin.
- Confirm that a full exit leaves no ClassTool process running.
- Keep personal settings, classroom data, logs, tokens, and build output out of the commit.
- If packaging changed, test the result outside the development terminal.

The source-only plugin template is stored as `src/ClassTool/tools/example_tool.py.txt`. Copy it and rename the copy to a unique `.py` file when creating a plugin; do not turn the template itself into an installed plugin.
