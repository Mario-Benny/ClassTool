# Security Policy

## Supported Versions

ClassTool is currently in early development. Security fixes are applied to the
latest source version on the default branch.

## Plugin Security Model

ClassTool plugins are local Python files. They run with the same permissions as
the main application and are not sandboxed. A plugin may access local files,
devices, the network, or the clipboard if its code does so.

Install plugins only from sources you trust. Review plugin code before using it,
especially when it requests network access, camera access, microphone access,
file access, or third-party dependencies.

## Reporting a Vulnerability

If you find a vulnerability, please open a private report if GitHub security
advisories are enabled for the repository. If private reporting is unavailable,
open a GitHub issue with a minimal description and avoid posting exploit details
publicly.

Please include:

- Affected version or commit.
- Steps to reproduce.
- Expected and actual behavior.
- Whether the issue involves the main application, the plugin loader, or a plugin.

## Scope

Security-sensitive areas include:

- Plugin discovery and loading.
- Runtime data stored under `data/`.
- Camera, screen, clipboard, and file-system access.
- Packaging behavior that includes third-party dependencies.

Third-party plugins are maintained by their authors unless they are included in
this repository.
