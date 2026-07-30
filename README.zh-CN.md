<div align="center">

# ClassTool

### 面向课堂场景的轻量级桌面工具集

*一个以“主程序 + 外置插件”为核心的 Windows 课堂工具箱。*

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/UI-PySide6-41CD52?style=flat-square&logo=qt&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Windows-0078D4?style=flat-square&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)

[English](README_EN.md) | **简体中文**

</div>

---

## 亮点

- **适合课堂使用**：内置随机点名、计算器、展台、屏幕涂鸦、倒计时等常用工具。
- **插件化架构**：把符合规范的 `.py` 文件放进 `tools/`，即可扩展新的课堂工具。
- **单文件主程序**：主程序可以打包成一个独立 exe，方便复制、分发和移动。
- **数据与插件外置**：正式发布时保留 `tools/` 和 `data/` 两个目录，插件和用户数据不塞进 exe。
- **按需加载插件**：启动时只读取插件元信息，用户打开工具时才导入插件模块。
- **更容易二次开发**：项目结构清晰，文档中提供了插件模板和打包说明。

## 当前功能概览

| 功能 | 说明 |
|---|---|
| 随机点名 | 用于课堂抽选、随机提问等场景。 |
| 计算器 | 提供简单的课堂计算辅助。 |
| 展台 | 调用摄像头展示纸质材料或实物。 |
| 屏幕涂鸦 | 用于屏幕冻结、批注和临时讲解。 |
| 倒计时 | 横向数字单元倒计时，适合课堂限时活动。 |
| 插件加载器 | 自动发现 `tools/` 中的 Python 插件。 |
| 数据配置 | 将插件配置保存到 `data/tools_data.json`。 |

## 项目结构

```text
ClassTool/
|-- .github/                 # Issue 和 Pull Request 模板
|-- assets/                  # logo 等视觉资源
|-- docs/                    # 插件开发、打包说明和示例
|-- scripts/                 # 打包脚本
|-- src/
|   `-- ClassTool/           # 主程序源码
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

## 从源码运行

### 环境要求

- Windows 10 或更新版本
- Python 3.10 或更新版本

### 安装依赖

```bat
python -m pip install -r requirements.txt
```

### 启动程序

```bat
cd src\ClassTool
python main.py
```

## 打包发布

先安装开发依赖：

```bat
python -m pip install -r requirements-dev.txt
```

再从仓库根目录运行：

```bat
scripts\build_release.cmd
```

打包完成后会生成：

```text
release\ClassTool_pack/
|-- ClassTool.exe
|-- tools/
`-- data/
```

其中：

- `ClassTool.exe` 是单文件主程序。
- `tools/` 用于放置插件。
- `data/` 用于保存用户数据和插件配置。

`release/` 是构建产物，不应提交到 GitHub。

## 插件开发

最小插件结构如下：

```python
TOOL_INFO = {
    "name": "工具名称",
    "color": "#2D89EF",
    "icon": "\uECAA",
    "description": "工具说明",
    "requirements": ["PySide6.QtWidgets"],
    "cache": True,
}


def create_widget():
    ...
```

插件至少需要提供以下入口之一：

- `create_widget()`：返回一个 `QWidget` 页面。
- `get_widget()`：兼容入口，同样返回一个 `QWidget` 页面。
- `run()`：执行无界面任务。

更多说明见：

- [插件开发指南](docs/plugin-development.md)
- [示例插件](docs/examples/example_tool.py)
- [打包说明](docs/packaging.md)

## 插件安全

ClassTool 插件本质上是会在本机执行的 Python 代码。第三方插件可以在代码中访问文件、
设备、剪贴板或网络，因此安装插件应当和运行普通 exe 一样谨慎。

建议：

- 只安装可信来源的插件。
- 使用前简单查看插件源码，尤其关注文件、网络、摄像头、麦克风和剪贴板访问。
- 插件作者应在文档或 `TOOL_INFO["requirements"]` 中说明第三方依赖。
- 如果插件启动线程、计时器或设备，应提供 `cleanup()` 释放资源。

更多安全说明见 [SECURITY.md](SECURITY.md)。

## 不应提交的内容

以下内容是构建产物、运行缓存或用户数据，不应进入 GitHub 仓库：

- `build/`
- `dist/`
- `release/`
- `*.spec`
- `*.exe`
- `__pycache__/`
- `*.pyc`
- `src/ClassTool/data/tools_data.json`

## 参与贡献

欢迎提交 Bug、功能建议或新的课堂插件。提交前建议先确认：

- 主程序可以正常启动。
- 被修改的插件可以从工具列表打开。
- 新插件已经填写 `TOOL_INFO`。
- 新增第三方依赖已经写入文档或插件 `requirements`。

更多说明见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

<div align="center">

如果这个项目对你的课堂工具流有帮助，欢迎点一个 Star。

</div>
