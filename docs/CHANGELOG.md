# Changelog

## Unreleased

- No unreleased user-facing changes yet.

## 1.2.1 - 2026-11-08

- Redesigned the main interface around Home, Settings, and About pages.
- Added persistent theme selection and built-in Chinese/English UI language packs.
- Added the voting plugin with an independent presentation window.
- Added persisted window state, close-to-tray preference, settings import/export, and About-page build information.
- Added persistent static plugin metadata caching to reduce repeated startup scans.
- Added single-instance communication and plugin cleanup during full shutdown.
- Switched Windows distribution from a single-file executable to a faster multi-file package.
- Added an NSIS installer with selectable plugins, shortcuts, context-menu registration, and uninstall support.
- Added versioned installer and portable assets with SHA-256 checksums under `release/`.

## 0.1.0

- Prepared the project as a GitHub-ready source repository.
- Added external `tools/` and `data/` release layout.
- Added built-in plugins: random picker, calculator, document camera, screen doodle, and countdown timer.
- Added plugin development docs, packaging docs, example plugin, and GitHub templates.
