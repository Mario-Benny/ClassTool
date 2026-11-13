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
advisories are enabled for the repository. Do not publish exploit details,
credentials, tokens, private classroom data, or a proof of concept in a public
issue. If private reporting is unavailable, open a public issue only to request
a private contact channel and include no technical details.

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
- Update manifests, trusted download hosts, cached installers, and installer launch behavior.

Third-party plugins are maintained by their authors unless they are included in
this repository.

## Update Security Model

ClassTool accepts stable update metadata only from its configured GitHub Release manifest URL. Installer downloads require HTTPS, trusted GitHub redirect hosts, an expected size, and a SHA-256 digest. The installer is verified after download and again immediately before launch, and it must remain inside the dedicated update cache directory.

SHA-256 confirms that the installer matches the downloaded manifest, but it does not independently authenticate a compromised publishing account. Protect repository release permissions and report unexpected `update.json` or installer changes as a security issue. A separately signed manifest may be added in a future release.
