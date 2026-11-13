# ClassTool 中文技术文档

本文面向希望从源码运行、开发插件、排查问题或制作发布包的开发者。普通用户请先阅读项目根目录的 [README](../README.md)。

[English Technical Documentation](README.en.md)

## 目录

1. [架构概览](#1-架构概览)
2. [源码结构](#2-源码结构)
3. [从源码运行](#3-从源码运行)
4. [资源与运行数据](#4-资源与运行数据)
5. [插件接口](#5-插件接口)
6. [插件依赖与安全边界](#6-插件依赖与安全边界)
7. [打包与发布原则](#7-打包与发布原则)
8. [安装器与绿色版](#8-安装器与绿色版)
9. [应用内更新](#9-应用内更新)
10. [日志与故障排查](#10-日志与故障排查)
11. [测试与贡献](#11-测试与贡献)

## 1. 架构概览

ClassTool 是面向 64 位 Windows 的 PySide6 桌面程序，采用以下结构：

- 主程序由 PyInstaller 以 `onedir` 多文件模式打包。
- Python、PySide6、Qt 和主程序模块位于 `_internal/`。
- 语言资源和 `version.json` 随主程序打包，不作为可编辑的外置配置。
- 插件保存在外置 `tools/` 目录中，以便单独添加、替换和检查源码。
- 设置、日志、插件缓存和插件数据保存在外置 `data/` 目录中。

主程序负责窗口、导航、主题、语言、单实例通信、日志、插件发现和插件生命周期。具体课堂功能由插件实现。

## 2. 源码结构

```text
ClassTool/
|-- assets/
|   `-- logo.ico                 # Windows 图标
|-- docs/
|   |-- README.zh-CN.md          # 中文技术文档
|   `-- README.en.md             # 英文技术文档
|-- release/                     # 当前安装包、绿色版和校验文件
|-- scripts/                     # PyInstaller、NSIS 和运行维护脚本
|-- src/ClassTool/
|   |-- language/                # 内置 JSON 语言资源
|   |-- toolkit/                 # 主程序核心与界面代码
|   |-- tools/                   # 正式插件和源码示例
|   |-- main.py                  # 程序入口
|   `-- version.json             # 唯一版本号来源
|-- tests/                       # 更新模块等自动化测试
|-- requirements.txt             # 运行依赖
`-- requirements-dev.txt         # 打包与开发依赖
```

源码树中不保存真实的 `data/`。程序首次运行时会在程序根目录自动创建 `data/` 和必要的数据文件。

## 3. 从源码运行

建议使用 64 位 Windows 10/11 和独立虚拟环境。项目要求 Python 3.10 或更高版本；发布前应以实际打包环境完成一次启动测试。

```bat
git clone https://github.com/Mario-Benny/ClassTool.git
cd ClassTool
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
cd src\ClassTool
python main.py
```

主程序使用 Windows 单实例互斥体。再次启动程序时，新进程会唤起已经运行的窗口；使用 `--tool <插件标识>` 可以请求已运行实例打开指定插件。

## 4. 资源与运行数据

### 语言资源

语言文件位于 `src/ClassTool/language/`，当前包含 `zh_CN.json` 和 `en_US.json`。每个文件是由翻译键和显示文本组成的 JSON 对象，两份文件应保持相同的键集合。`language.name` 用于语言选择列表中显示语言名称。缺少翻译时，程序先回退到简体中文，再回退到翻译键本身。

### 版本信息

`src/ClassTool/version.json` 是版本号的唯一来源。修改主程序版本时应更新该文件，不要在 README、构建脚本或 Python 模块中再维护第二份版本常量。

### 运行数据

程序在运行目录的 `data/` 中创建以下内容：

| 路径 | 用途 |
| --- | --- |
| `data/settings.json` | 语言、主题、窗口状态和关闭行为等设置。 |
| `data/tools_data.json` | 插件通过配置接口保存的数据。 |
| `data/plugin_cache.json` | 插件静态元信息缓存，用于减少重复扫描。 |
| `data/logs/` | 主程序运行日志和未处理异常记录。 |

不要向仓库提交包含真实课堂信息或个人设置的运行数据。

## 5. 插件接口

插件是放在外置 `tools/` 目录中的 `.py` 文件。主程序启动时通过 AST 静态读取 `TOOL_INFO`，用户打开工具时才真正导入插件模块，从而减少启动开销和未使用插件的初始化副作用。

```python
TOOL_INFO = {
    "name": "Example Tool",
    "color": "#2D89EF",
    "icon": "\uECAA",
    "description": "A minimal ClassTool plugin.",
    "requirements": ["PySide6.QtWidgets"],
    "cache": True,
}
```

| 字段 | 说明 |
| --- | --- |
| `name` | 首页工具卡片显示名称。 |
| `color` | 工具卡片颜色。 |
| `icon` | Segoe MDL2 Assets 字符或可显示文本。 |
| `description` | 工具简介。 |
| `requirements` | 运行前需要检查的导入模块或 Python 发行包名称。 |
| `cache` | 是否缓存已经导入的插件模块。 |

插件至少实现以下一个入口：

- `create_widget()`：返回一个 `QWidget`。
- `get_widget()`：兼容入口，同样返回一个 `QWidget`。
- `run()`：执行不需要嵌入页面的任务。

使用线程、计时器、摄像头、临时窗口或其他外部资源的插件应实现 `cleanup()`。主程序完全退出时会调用已缓存插件的清理函数；插件必须在其中停止后台任务并释放资源。

完整模板位于 [example_tool.py.txt](../src/ClassTool/tools/example_tool.py.txt)。为了避免模板被主程序当作正式插件加载，仓库使用 `.py.txt` 后缀。开发时请复制该文件并将副本改名为具有唯一英文名称的 `.py` 文件。

插件可以通过 `toolkit.core.tools_config` 中的 `get_tool_config()` 与 `set_tool_config()` 保存配置，数据统一写入 `data/tools_data.json`。

## 6. 插件依赖与安全边界

`requirements` 支持导入模块名或常见 Python 发行包名称，也可以包含简单版本约束。主程序只检查依赖是否存在，不会在用户电脑上自动安装依赖。

打包后的 ClassTool 使用内置 Python 环境。第三方插件需要额外库时，该库必须已经包含在发布包的 `_internal/` 中；仅把插件 `.py` 文件复制到无 Python 环境的电脑上，无法补充新的二进制依赖。制作发行版时应在打包环境安装依赖，并按库的实际情况为 PyInstaller 增加 `--hidden-import`、`--collect-submodules` 或 `--collect-all`。

插件不在沙盒中运行，拥有与主程序相近的文件、网络和设备访问能力。请仅运行可信来源的插件。插件作者应明确说明其网络、摄像头、麦克风、剪贴板和文件访问需求。完整策略见 [SECURITY.md](SECURITY.md)。

## 7. 打包与发布原则

当前正式发行版使用 PyInstaller `onedir`，而不是 `onefile`。多文件模式启动更快，也避免每次运行都将 Qt 和 Python 依赖解压到临时目录。

构建时必须满足以下条件：

1. 从 `version.json` 读取版本号。
2. 使用 `--onedir --windowed` 构建主程序。
3. 将 `language/` 和 `version.json` 作为内置资源收集。
4. 收集程序使用的 PySide6 网络和多媒体模块。
5. 将正式插件复制到外置 `tools/`，但排除 `example_tool.py.txt`。
6. 创建空的外置 `data/`。
7. 在普通 Windows 启动环境中验证 `ClassTool.exe`，不能只在开发终端中测试。

PyInstaller 构建时应使用干净的 `PATH`。如果开发终端向 `PATH` 注入了其他软件的 Qt、ICU、OpenSSL 或多媒体 DLL，PyInstaller 可能错误收集这些文件，导致程序离开开发终端后出现 `DLL load failed while importing QtCore`。

仓库的 `release/` 只保存准备公开的顶层发布附件：安装器、绿色版 ZIP、SHA-256 文件和 `update.json`。PyInstaller 的 `build/`、`dist/`、`.spec`、日志和临时目录不应提交。历史版本建议作为 GitHub Releases 附件发布。

仓库构建入口为：

```bat
scripts\build_release.cmd
```

该脚本从 `src/ClassTool/version.json` 读取版本，执行 PyInstaller `onedir` 构建和 NSIS 安装器构建，并在 `release/` 生成安装器、SHA-256 文件与更新清单。脚本要求 Python 可从 `PATH` 访问，并能够找到 NSIS `makensis.exe`。

```bat
certutil -hashfile ClassTool-v1.2.2-Setup.exe SHA256
certutil -hashfile ClassTool-v1.2.2-win-x64-portable.zip SHA256
```

## 8. 安装器与绿色版

### 绿色版结构

```text
ClassTool-v<版本>-win-x64-portable/
|-- ClassTool.exe
|-- _internal/
|-- tools/
|-- data/
|-- 重建ClassTool快捷方式.cmd
|-- 注册桌面右键菜单.cmd
`-- 清除桌面右键菜单.cmd
```

绿色版必须完整解压，不能单独移动 EXE。

### NSIS 安装器行为

- 仅允许在 64 位 Windows 上安装，并要求管理员权限。
- D 盘可用时默认安装到 `D:\ClassTool`，否则使用 `$PROGRAMFILES64\ClassTool`。
- 允许用户选择需要安装的课堂插件。
- 创建桌面快捷方式、开始菜单入口、ClassTool 开始菜单文件夹和卸载入口。
- 根据已安装插件注册桌面背景右键菜单。
- 安装完成后可选择启动程序，也可以将安装器移动到回收站。
- 卸载时移除主程序、官方插件、快捷方式和右键菜单。

`data/` 中的用户文件和第三方插件需要保持明确的数据保留策略，避免升级或卸载时误删用户内容。

## 9. 应用内更新

更新逻辑位于 `toolkit/core/update_manager.py` 与 `update_launcher.py`，通过 PySide6 `QtNetwork` 在界面线程中执行非阻塞网络请求。主程序默认读取：

```text
https://github.com/Mario-Benny/ClassTool/releases/latest/download/update.json
```

稳定版 Release 必须同时上传版本化安装器和名为 `update.json` 的附件。更新清单包含版本号、最低更新引擎版本、安装器 URL、文件大小和 SHA-256。客户端只接受 HTTPS GitHub 地址及受信任的 GitHub Release 重定向域名。

更新流程包括：

1. 启动后延迟检查，或由用户在设置页手动检查。
2. 严格比较三段数字版本号。
3. 将安装器下载到 `%LOCALAPPDATA%\ClassTool\updates`。
4. 使用 `.part` 与状态文件进行断点续传，并对临时网络错误执行退避重试。
5. 校验磁盘空间、HTTP Range、文件大小和 SHA-256。
6. 下载完成后通知用户；只有用户确认时才退出主程序。
7. 启动安装器前再次校验路径与 SHA-256，然后等待主程序完全退出并请求管理员权限。

自动检查失败不会打断主程序使用；手动检查会显示错误，详细原因同时写入日志。更新清单不是代码签名，发布者仍应保护 GitHub 账户，并可在后续版本中增加独立数字签名。

## 10. 日志与故障排查

遇到启动、插件或设备问题时，首先检查 `data/logs/`。

| 现象 | 检查事项 |
| --- | --- |
| `DLL load failed while importing QtCore` | 确认 `_internal/` 完整，并使用干净 PATH 重新打包。 |
| 插件未显示 | 确认文件位于外置 `tools/`、后缀为 `.py`，并检查 `TOOL_INFO` 是否为字面量字典。 |
| 提示缺少依赖 | 确认依赖已经被打入 `_internal/`，并检查 `requirements` 名称。 |
| 程序关闭后仍在后台 | 从系统托盘完全退出，并检查插件的 `cleanup()` 是否停止线程和设备。 |
| 摄像头不可用 | 检查 Windows 隐私权限、设备占用情况和多媒体依赖。 |
| 右键菜单失效 | 以管理员身份运行注册脚本，或先清除后重新注册。 |
| 更新检查返回 HTTP 404 | 确认最新 GitHub Release 已上传名称完全一致的 `update.json`。 |
| 更新下载校验失败 | 确认 Release 安装器与 `update.json` 中的大小、URL 和 SHA-256 来自同一次构建。 |

## 11. 测试与贡献

提交修改前至少完成：

1. 解析或编译检查全部 Python 文件。
2. 校验 `zh_CN.json` 与 `en_US.json` 的翻译键一致。
3. 从源码启动主程序并打开受影响的插件。
4. 若修改资源管理逻辑，确认退出后没有残留 ClassTool 进程。
5. 若修改打包流程，在非开发终端环境测试绿色版和安装版。
6. 确认发布包不包含个人设置、真实课堂数据、令牌或构建缓存。
7. 运行 `python -m unittest discover -s tests -v`，确认更新清单、Range 响应、重试和安装前校验测试通过。

更多贡献要求见 [CONTRIBUTING.md](CONTRIBUTING.md)。
