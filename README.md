# ClassTool

ClassTool is a lightweight classroom desktop toolkit built with Python and PySide6.
It uses a host-and-plugin architecture: the main application provides the window,
navigation, tray behavior, theme handling, and plugin loading, while classroom
tools are kept as external `.py` plugins.

- 中文说明: [README.zh-CN.md](README.zh-CN.md)
- English guide: [README_EN.md](README_EN.md)

## Highlights

- Single-file host executable for Windows releases.
- External `tools/` directory for plugins.
- External `data/` directory for user data and plugin settings.
- Lazy plugin loading: metadata is read first, and plugin modules are imported only when opened.
- Built-in classroom tools such as random picker, calculator, document camera, screen doodle, and countdown timer.

## Repository Layout

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
|-- README.zh-CN.md
|-- README_CN.md
|-- README_EN.md
|-- requirements.txt
`-- requirements-dev.txt
```

## Quick Start

```bat
python -m pip install -r requirements.txt
cd src\ClassTool
python main.py
```

## Build

```bat
python -m pip install -r requirements-dev.txt
scripts\build_release.cmd
```

The release package is generated under:

```text
release\ClassTool_pack
```

The generated release folder is intentionally ignored by Git.

## Plugin Development

See:

- [docs/plugin-development.md](docs/plugin-development.md)
- [docs/examples/example_tool.py](docs/examples/example_tool.py)

## Security

ClassTool plugins are local Python code and are not sandboxed. Install third-party
plugins only from trusted sources. See [SECURITY.md](SECURITY.md).

## License

ClassTool is released under the [MIT License](LICENSE).
