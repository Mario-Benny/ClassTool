# ClassTool

> A lightweight Windows desktop toolkit for classroom use.

ClassTool brings common classroom utilities together in a clean desktop application. Teachers can choose a tool directly from the Home page without searching through menus or completing complex setup. The host supports Simplified Chinese, English, light and dark themes, and external plugins.

[中文说明](README.md) | [Download](release/) | [English Technical Documentation](docs/README.en.md) | [Security Policy](docs/SECURITY.md)

## Included Tools

| Tool | Purpose |
| --- | --- |
| Countdown Timer | Runs classroom countdowns up to 99 hours, 99 minutes, and 99 seconds. |
| Random Picker | Randomly selects a student or item from a list. |
| Screen Doodle | Freezes the screen for temporary annotations and explanations. |
| Calculator | Handles common classroom calculations. |
| Document Camera | Uses a camera to present printed materials or physical objects. |
| Voting | Opens an independent voting window and counts votes in real time. |

## Key Features

- **Tools on the Home page**: available tools are visible as soon as the application opens.
- **No separate Python installation**: both installer and portable packages include the required runtime.
- **Plugin-based expansion**: compatible `.py` plugins can be added to the external `tools/` directory.
- **Chinese and English interface**: the display language can be changed from Settings.
- **Light and dark themes**: the interface can be adjusted for different classroom environments.
- **External runtime data**: settings, logs, and plugin data remain under `data/` for easier backup and troubleshooting.
- **Secure in-app updates**: background checks, resumable downloads, retries, disk-space checks, and SHA-256 re-verification are built in; installation still requires user confirmation.

## Choose a Download

Current packages are available from the repository's [release](release/) directory. Versioned historical packages can also be published through [GitHub Releases](https://github.com/Mario-Benny/ClassTool/releases).

| Package | Recommended for | How to use it |
| --- | --- | --- |
| Installer `ClassTool-v*-Setup.exe` | Normal use; recommended for most users | Run the installer, select the required plugins, and finish installation. |
| Portable `ClassTool-v*-win-x64-portable.zip` | USB drives, temporary computers, or use without installation | Extract the complete ZIP and run `ClassTool.exe` inside the extracted directory. |

The portable build uses a multi-file layout. Do not copy `ClassTool.exe` by itself or remove `_internal/`; the application cannot start without its bundled dependencies.

## System Requirements

- 64-bit Windows 10 or Windows 11.
- Administrator privileges for the installer.
- A working camera and the appropriate Windows permissions for Document Camera.
- School computer security policies may restrict Screen Doodle, context-menu registration, or other system integrations.

## Quick Start

### Installer

1. Download and run `ClassTool-v*-Setup.exe`.
2. Choose the installation directory and classroom plugins to install.
3. Start ClassTool from the desktop or Start menu shortcut.

The installer prefers `D:\ClassTool`. If drive D is unavailable, it falls back to the Windows `Program Files\ClassTool` directory. It creates desktop and Start menu shortcuts, an uninstall entry, and desktop-background context-menu items for installed plugins.

The application can check GitHub Releases for stable updates after startup. Once an installer has been downloaded and verified by size and SHA-256, ClassTool asks before exiting and launching it. Updates are never installed without confirmation.

### Portable Package

1. Extract `ClassTool-v*-win-x64-portable.zip` completely.
2. Keep `ClassTool.exe`, `_internal/`, `tools/`, and `data/` in their original relative locations.
3. Double-click `ClassTool.exe`.

The portable package includes three maintenance scripts for rebuilding shortcuts, registering the desktop context menu, and removing the context menu. Administrator privileges may be required when registering system integrations.

## Plugin Security

ClassTool plugins are not sandboxed. A plugin has permissions comparable to the host application and may access files, networks, cameras, microphones, or the clipboard. Install plugins only from trusted sources and inspect their source code and dependencies before running them. See [SECURITY.md](docs/SECURITY.md) for details.

## Learn More

- [English Technical Documentation](docs/README.en.md)
- [中文说明](README.md)
- [中文详细技术文档](docs/README.zh-CN.md)
- [Contributing](docs/CONTRIBUTING.md)
- [Changelog](docs/CHANGELOG.md)
- [MIT License](LICENSE)
