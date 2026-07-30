# Packaging Guide

ClassTool releases are intended to use this layout:

```text
ClassTool_pack/
|-- ClassTool.exe
|-- tools/
`-- data/
```

- `ClassTool.exe` is the single-file host application.
- `tools/` contains external Python plugins.
- `data/` contains user data and plugin settings.

## Build Command

From the repository root:

```bat
python -m pip install -r requirements-dev.txt
scripts\build_release.cmd
```

The package is generated at:

```text
release\ClassTool_pack
```

## Icon

The default build script uses:

```text
assets/logo.ico
```

Make sure the icon is a real Windows `.ico` file, not a renamed PNG. If Windows
Explorer keeps showing an old icon after rebuilding, restart Explorer or clear
the Windows icon cache.

## What Should Not Be Committed

The following are generated or runtime files and should stay out of Git:

- `build/`
- `dist/`
- `release/`
- `*.spec`
- `__pycache__/`
- `*.pyc`
- `src/ClassTool/data/tools_data.json`
