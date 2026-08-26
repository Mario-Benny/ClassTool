# ClassTool

> 面向课堂场景的轻量级 Windows 桌面工具集。
>
> A lightweight Windows desktop toolkit for classroom use.

ClassTool 让教师能在一个简洁的桌面程序中打开常用课堂工具。主程序是单文件 EXE，工具插件和用户数据保持在外置目录中，方便使用、更新与扩展。

ClassTool gives teachers a simple desktop application for everyday classroom tools. The host is a single-file EXE, while tool plugins and user data remain in external directories for convenient use, updates, and extension.

[下载发布包](download/) | [中文详细技术文档](docs/README.zh-CN.md) | [English Technical Documentation](docs/README.en.md)

## 课堂工具 / Classroom Tools

| 工具 | Tool | 简介 / Summary |
| --- | --- | --- |
| 倒计时 | Countdown Timer | 为限时课堂活动设置倒计时。 / Sets a timer for timed activities. |
| 随机抽取 | Random Picker | 随机选择学生或项目。 / Randomly selects students or items. |
| 屏幕涂鸦 | Screen Doodle | 用于屏幕冻结、批注与即时讲解。 / Freezes the screen for annotations and explanations. |
| 计算器 | Calculator | 提供快速、简单的课堂计算。 / Provides quick, simple calculations. |
| 实物展台 | Document Camera | 使用摄像头展示材料或实物。 / Uses a camera to present materials or objects. |
| 投票模块 | Voting | 打开独立投票页并实时计数。 / Opens an independent live voting page. |

## 主要特点 / Key Features

- **主页直达工具 / Tools on the home page**：打开程序即可选择当前工具，不需要搜索或复杂配置。 Choose an available tool immediately, without search or complex setup.
- **外置插件 / External plugins**：将新的插件放入 `tools/` 目录即可扩展工具箱。 Extend the toolkit by placing new plugins in `tools/`.
- **单文件主程序 / Single-file host**：`ClassTool.exe` 可在没有 Python 环境的 Windows 电脑上运行。 `ClassTool.exe` can run on Windows computers without Python installed.
- **中英文界面 / Chinese and English UI**：可在设置页面切换简体中文、英文和明暗主题。 Switch between Simplified Chinese, English, and light or dark themes on the Settings page.

## 下载与使用 / Download and Use

可直接运行的 Windows 发布包在 [download/](download/) 中。请将以下三个项目保持在同一目录：

The ready-to-run Windows package is in [download/](download/). Keep these three items in the same directory:

```text
download/
|-- ClassTool.exe
|-- tools/
`-- data/
```

## 进一步了解 / Learn More

- [中文详细技术文档](docs/README.zh-CN.md)
- [English Technical Documentation](docs/README.en.md)
- [MIT License](LICENSE)
