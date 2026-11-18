# Changelog

## Unreleased

- No unreleased user-facing changes yet.

## 1.2.3 - 2026-11-18

- Replaced the in-process update implementation with the independently packaged PyUpdateCore 1.0.1 engine.
- Added a versioned JSON Lines IPC adapter while preserving the existing ClassTool update interface and UI states.
- Added safe updater configuration generation under the external `data/updater/` directory.
- Added handling for out-of-order task completion messages from very fast updater workers.
- Bundled the updater executable in multi-file, portable, and installer distributions.
- Updated updater integration tests and the packaging workflow.

## 1.2.2 - 2026-11-13

- Added a production-ready in-app update engine for stable GitHub Releases.
- Added automatic and manual update checks, resumable downloads, retry backoff, stall detection, disk-space checks, and strict HTTP Range validation.
- Added installer size and SHA-256 verification both after download and immediately before launch.
- Added a trusted update-cache boundary and a detached Windows installer launcher that waits for ClassTool to exit.
- Added bilingual update controls and progress states to Settings.
- Added `update.json` generation to the NSIS build workflow, including the minimum updater version and release metadata.
- Replaced the obsolete single-file repository build script with the current PyInstaller `onedir` and NSIS workflow.
- Added automated tests for manifest validation, version ordering, Range responses, retry classification, disk-space policy, and installer re-verification.
- Separated the English user README from the English technical documentation and repaired repository-relative documentation links.

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
