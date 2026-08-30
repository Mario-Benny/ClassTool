# ClassTool 中文技术文档

## 1. 项目概述

ClassTool 是面向课堂场景的 Windows 桌面工具集，采用“单文件主程序 + 外置 Python 插件 + 外置运行数据”的架构。主程序负责窗口、主题、语言、导航、托盘行为与插件生命周期；具体功能由插件实现。

发布包结构如下：

GitHub Releases 提供版本化 ZIP 文件，例如 `ClassTool-v1.1.0-win-x64.zip`。解压后结构如下：

```text
ClassTool-v1.1.0-win-x64/
|-- ClassTool.exe            # 单文件主程序
|-- tools/                   # 正式插件目录
`-- data/                    # 用户设置与插件数据
```

`ClassTool.exe` 内置 Python 运行环境、PySide6 依赖和语言资源，因此目标 Windows 电脑不必另行安装 Python。`tools/` 与 `data/` 必须保持外置，并与 EXE 位于同一目录。

## 2. 源码结构

```text
src/ClassTool/
|-- language/                # 内置语言文本
|-- toolkit/                 # 主程序核心与界面代码
|-- tools/                   # 内置插件与示例插件
|-- data/                    # 本地开发运行数据，不应提交真实内容
`-- main.py                  # 程序入口
```

根目录的 `scripts/build_release.cmd` 负责在本地 `release/` 生成版本化发布包、ZIP 文件和 SHA-256 校验文件。发布附件应上传到 GitHub Releases，而不是提交到源码仓库。`assets/logo.ico` 是打包使用的 Windows 图标。

## 3. 从源码运行

运行环境为 Windows 10 或更高版本、Python 3.10 或更高版本。先在仓库根目录安装依赖：

```bat
python -m pip install -r requirements.txt
```

然后启动主程序：

```bat
cd src\ClassTool
python main.py
```

## 4. 主程序与语言机制

主程序提供首页、设置页和关于页。首页显示可用工具，设置页提供主题和语言选择。语言文本位于 `src/ClassTool/language/`，目前包含 `zh_CN.txt` 与 `en_US.txt`；打包时这些资源被写入 EXE，不会作为外置发布文件。

用户选择的主题、窗口状态和关闭行为保存于运行目录的 `data/settings.json`。插件静态元信息缓存保存在 `data/plugin_cache.json`，用于减少后续启动时的扫描开销。这些文件均是用户数据，不应作为个人配置提交到仓库。

## 5. 插件接口与示例

插件是放在 `tools/` 目录中的普通 Python 文件。启动时，ClassTool 会静态读取每个插件的 `TOOL_INFO`；只有在用户打开该工具时，才会导入插件模块。这样可以减少启动时的导入开销，并避免未使用插件的初始化副作用。

插件至少需要提供以下入口之一：

- `create_widget()`：返回一个 `QWidget` 页面。
- `get_widget()`：与 `create_widget()` 兼容的入口。
- `run()`：执行无界面任务。

一个最小插件需要提供元信息：

```python
TOOL_INFO = {
    "name": "工具名称",
    "color": "#2D89EF",
    "icon": "\uECAA",
    "description": "工具说明",
    "requirements": ["PySide6.QtWidgets"],
    "cache": True,
}
```

`name`、`color`、`icon` 和 `description` 用于工具卡片展示；`requirements` 声明插件所需模块；`cache` 控制已导入的插件模块是否缓存。

完整可运行的模板见 [example_tool.py](../src/ClassTool/tools/example_tool.py)。它位于源码插件目录中，便于开发者直接复制、重命名并改造；打包脚本会明确将其排除，不会复制到正式发布包的 `tools/` 中。

使用线程、计时器、摄像头、临时文件或其他外部资源的插件应提供 `cleanup()`。主程序退出时会调用该钩子，插件应在其中停止任务并释放资源。

## 6. 插件数据与第三方依赖

插件可通过 `toolkit.core.tools_config` 中的 `get_tool_config()` 与 `set_tool_config()` 读写配置。数据保存在运行目录 `data/tools_data.json`，不应提交包含真实用户内容的数据文件。

第三方插件会在主程序内部执行，并不拥有独立 Python 环境。若插件依赖 `requests`、`numpy` 等第三方库，开发者应：

1. 在 `TOOL_INFO["requirements"]` 中声明依赖。
2. 在打包环境中安装该依赖。
3. 按库的实际情况为 PyInstaller 增加 `--hidden-import` 或 `--collect-all` 参数，确保依赖被收集进 EXE。

## 7. 打包与发布

先安装开发依赖：

```bat
python -m pip install -r requirements-dev.txt
```

再从仓库根目录运行：

```bat
scripts\build_release.cmd
```

脚本会使用 PyInstaller 生成本地 `release/ClassTool-v<版本号>-win-x64.zip`，内置语言资源，并将正式插件复制到发布包的 `tools/`。ZIP 同目录会生成 `.sha256` 校验文件。发布时不应放入个人的 `settings.json`、`plugin_cache.json` 或真实课堂数据；将 ZIP 与校验文件上传到 [GitHub Releases](https://github.com/Mario-Benny/ClassTool/releases) 即可。

图标文件必须是有效的 Windows `.ico` 文件。若重新打包后资源管理器仍显示旧图标，可重启资源管理器或清理 Windows 图标缓存。

## 8. 安全说明

ClassTool 不会沙盒化插件。插件拥有与本地 Python 程序相近的权限，可能访问文件、网络、摄像头、麦克风或剪贴板。请仅安装可信来源的插件，并在使用前检查其源码、依赖和数据访问行为。

插件作者应说明所需权限，不应在未取得用户同意的情况下收集账号凭据、令牌、课堂数据或个人信息。完整安全策略见 [SECURITY.md](../SECURITY.md)。

## 9. 贡献

欢迎提交问题、改进建议和新的课堂插件。提交前请确认主程序可以启动、插件能够打开、依赖已经说明，并阅读 [CONTRIBUTING.md](../CONTRIBUTING.md)。
