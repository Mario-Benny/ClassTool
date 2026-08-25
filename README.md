# ClassTool

> 面向课堂场景的轻量级 Windows 桌面工具集。
>
> A lightweight Windows desktop toolkit for classroom use.

ClassTool 采用“主程序 + 外置插件”的结构。教师可以直接运行主程序，并按需在 `tools/` 目录中添加、更新或移除工具插件。

ClassTool uses a host-and-plugin architecture. Teachers can run the host directly, then add, update, or remove tool plugins in the external `tools/` directory as needed.

[下载发布包](download/) | [技术总览](docs/technical-overview.md) | [插件开发指南](docs/plugin-development.md) | [打包说明](docs/packaging.md) | [安全说明](SECURITY.md)

[Download package](download/) | [Technical overview](docs/technical-overview.md) | [Plugin development](docs/plugin-development.md) | [Packaging](docs/packaging.md) | [Security](SECURITY.md)

## 功能概览 / Features at a Glance

ClassTool 为课堂中的抽选、计时、讲解、展示和即时统计提供一组可独立打开的工具。主页会直接展示当前可用工具，无需搜索或额外配置。

ClassTool provides independently usable tools for classroom selection, timing, explanation, presentation, and live counting. The home page presents the available tools directly, without a search or extra setup step.

| 工具 | 用途 |
| --- | --- |
| 倒计时 | 设置最长 99 小时 99 分 99 秒的倒计时，适合限时课堂活动。 |
| 随机抽取 | 随机选择学生或项目，用于点名和互动。 |
| 屏幕涂鸦 | 冻结屏幕并进行临时批注、标记或讲解。 |
| 计算器 | 提供简单、快速的课堂计算。 |
| 实物展台 | 调用摄像头展示纸质材料或实物。 |
| 投票模块 | 创建独立投票页，为多个投票位实时加减计数。 |

| Tool | Purpose |
| --- | --- |
| Countdown Timer | Sets a timer up to 99 hours, 99 minutes, and 99 seconds for timed activities. |
| Random Picker | Randomly selects students or items for roll calls and interaction. |
| Screen Doodle | Freezes the screen for temporary annotations, marks, and explanations. |
| Calculator | Provides quick, simple calculations during class. |
| Document Camera | Uses a camera to present paper materials or physical objects. |
| Voting | Opens an independent voting page with live counters for multiple voting positions. |

## 下载与运行 / Download and Run

可直接运行的 Windows 发布包位于 [download/](download/)。请始终将 `ClassTool.exe`、`tools/` 和 `data/` 保持在同一目录中；其中插件和运行数据均为外置内容。

The ready-to-run Windows package is in [download/](download/). Always keep `ClassTool.exe`, `tools/`, and `data/` together. Plugins and runtime data both remain external.

```text
download/
|-- ClassTool.exe            # 单文件主程序 / single-file host application
|-- tools/                   # 插件目录 / plugin directory
`-- data/                    # 用户数据目录 / user data directory
```

主程序内置了简体中文与英文语言资源。可在“设置”页面切换语言和主题；所选设置会保存至 `data/settings.json`。

The host includes Simplified Chinese and English language resources. Language and theme can be changed on the Settings page; the selected settings are saved to `data/settings.json`.

## 开发者说明 / For Developers

主程序负责窗口、主题、语言、导航和插件加载；插件以普通 Python 文件的形式放在 `tools/` 中。启动时，ClassTool 仅静态读取插件的 `TOOL_INFO`；用户打开工具时才导入插件模块，从而避免不必要的启动开销。

The host handles windows, themes, language, navigation, and plugin loading. Plugins are ordinary Python files placed in `tools/`. On startup, ClassTool reads only a plugin's `TOOL_INFO` statically; the plugin module is imported only when the user opens it, avoiding unnecessary startup work.

插件可提供 `create_widget()`、`get_widget()` 或 `run()` 入口。涉及线程、计时器、摄像头或临时文件的插件应实现 `cleanup()`，以便主程序退出时释放资源。第三方插件会在本机执行，安装前应确认来源可信并审阅其代码与依赖。

Plugins may expose `create_widget()`, `get_widget()`, or `run()`. Plugins that use threads, timers, cameras, or temporary files should implement `cleanup()` so resources can be released when the host exits. Third-party plugins execute locally; install them only from trusted sources and review their code and dependencies first.

有关目录职责、插件接口、第三方依赖、打包方式和安全边界，请阅读 [技术总览](docs/technical-overview.md)。

For directory responsibilities, plugin interfaces, third-party dependencies, packaging, and security boundaries, read the [technical overview](docs/technical-overview.md).

## 从源码运行与打包 / Run from Source and Build

使用 Python 3.10 或更高版本，在仓库根目录安装依赖后运行以下命令：

Use Python 3.10 or later. From the repository root, install dependencies and run:

```bat
python -m pip install -r requirements.txt
cd src\ClassTool
python main.py
```

要生成发布包，请先安装开发依赖，再运行打包脚本。语言资源会被内置到 EXE；当前内置插件会复制到 `download/tools/`。

To create a release package, install development dependencies and run the build script. Language resources are embedded in the EXE, while bundled plugins are copied to `download/tools/`.

```bat
python -m pip install -r requirements-dev.txt
scripts\build_release.cmd
```

## 参与贡献与许可 / Contributing and License

欢迎提交问题、改进建议和新的课堂插件。贡献前请阅读 [贡献指南](CONTRIBUTING.md) 与 [安全说明](SECURITY.md)。

Issues, improvements, and new classroom plugins are welcome. Before contributing, read the [contribution guide](CONTRIBUTING.md) and [security policy](SECURITY.md).

本项目基于 [MIT License](LICENSE) 开源。

This project is released under the [MIT License](LICENSE).
