# ClassTool - Classroom Toolkit

ClassTool is a lightweight classroom desktop toolkit built with Python and PySide6.
It uses a host-and-plugin architecture: the host application handles the window,
navigation, tray behavior, theme, and plugin loading; classroom tools are external
`.py` files placed in the `tools/` directory.

## Features

- **Single-file host executable**: the main application can be packaged as one Windows exe.
- **External plugins**: plugins remain editable `.py` files under `tools/`.
- **External data**: user data and plugin settings are stored under `data/`.
- **Lazy loading**: ClassTool reads `TOOL_INFO` first and imports a plugin only when the user opens it.
- **Classroom tools**: random picker, calculator, document camera, screen doodle, and countdown timer are included.

## Directory Layout

```text
ClassTool/
|-- .github/                 # Issue and pull request templates
|-- assets/                  # Logo and visual assets
|-- docs/                    # Plugin and packaging guides
|-- scripts/                 # Build scripts
|-- src/
|   `-- ClassTool/           # Application source code
|-- .gitattributes
|-- .gitignore
|-- CHANGELOG.md
|-- CONTRIBUTING.md
|-- LICENSE
|-- README.md
|-- README_CN.md
|-- README_EN.md
|-- requirements.txt
`-- requirements-dev.txt
```

## Run from Source

```bat
python -m pip install -r requirements.txt
cd src\ClassTool
python main.py
```

## Build Release

Install development dependencies first:

```bat
python -m pip install -r requirements-dev.txt
```

Then run:

```bat
scripts\build_release.cmd
```

The generated package will be:

```text
release\ClassTool_pack
|-- ClassTool.exe
|-- tools/
`-- data/
```

`release/` is a build artifact and should not be committed to GitHub.

## Plugin Development

See:

- [docs/plugin-development.md](docs/plugin-development.md)
- [docs/examples/example_tool.py](docs/examples/example_tool.py)

## Plugin Security

ClassTool plugins are local Python code and are not sandboxed. Install third-party
plugins only from trusted sources, and review plugins that request file, network,
camera, microphone, or clipboard access.

See [SECURITY.md](SECURITY.md) for details.

## Notes

- `build/`, `dist/`, `release/`, `*.spec`, and `__pycache__/` are build/runtime cache files.
- `src/ClassTool/data/tools_data.json` is runtime data and should not be committed.
- If a plugin depends on third-party packages, list them in `TOOL_INFO["requirements"]` and make sure PyInstaller collects them during release builds.

## License

ClassTool is released under the [MIT License](LICENSE).
