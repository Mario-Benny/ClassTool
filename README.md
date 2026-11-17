# ClassTool

> 面向课堂场景的轻量级 Windows 桌面工具集。

ClassTool 将常用课堂工具集中在一个简洁的桌面程序中。打开程序后即可从首页选择工具，不需要搜索功能或进行复杂配置。主程序支持简体中文、英文、明亮主题和暗色主题，并通过外置插件扩展功能。

[English README](README.en.md) | [下载程序](release/) | [中文技术文档](docs/README.zh-CN.md) | [安全说明](docs/SECURITY.md)

## 内置工具

| 工具 | 用途 |
| --- | --- |
| 倒计时 | 为课堂活动设置最长 99 小时 99 分钟 99 秒的倒计时。 |
| 随机抽取 | 从名单或项目中随机选择结果。 |
| 屏幕涂鸦 | 冻结屏幕并进行临时批注和讲解。 |
| 计算器 | 完成常用课堂计算。 |
| 实物展台 | 调用摄像头展示纸质材料或实物。 |
| 投票模块 | 创建独立投票窗口并实时统计各选项票数。 |

## 主要特点

- **打开即可使用**：首页直接展示所有可用工具。
- **无需安装 Python**：安装版和绿色版均已包含运行环境。
- **插件式扩展**：将兼容的 `.py` 插件放入 `tools/` 目录即可扩展工具箱。
- **中英文界面**：可在设置页切换简体中文和英文。
- **明暗主题**：可根据教室环境切换明亮或暗色主题。
- **数据保持外置**：设置、日志和插件数据保存在 `data/` 目录，便于备份和排错。
- **安全的应用内更新**：支持后台检查、断点续传、失败重试、磁盘空间检查及 SHA-256 二次校验，安装前仍由用户确认。

## 下载选择

发布文件位于仓库的 [release](release/) 目录，也可以通过 [GitHub Releases](https://github.com/Mario-Benny/ClassTool/releases) 发布和下载历史版本。

| 类型 | 适合场景 | 使用方法 |
| --- | --- | --- |
| 安装版 `ClassTool-v*-Setup.exe` | 日常使用，推荐普通用户选择 | 运行安装器，选择需要的插件并完成安装。 |
| 绿色版 `ClassTool-v*-win-x64-portable.zip` | U 盘、临时电脑或免安装使用 | 完整解压 ZIP，然后运行目录中的 `ClassTool.exe`。 |

绿色版采用多文件结构。请勿只复制 `ClassTool.exe`，也不要删除 `_internal/`，否则程序无法启动。

## 系统要求

- 64 位 Windows 10 或 Windows 11。
- 安装版需要管理员权限。
- 实物展台需要可用摄像头及相应的系统权限。
- 屏幕涂鸦、右键菜单等功能可能受到学校一体机安全策略的限制。

## 快速开始

### 安装版

1. 下载并运行 `ClassTool-v*-Setup.exe`。
2. 选择安装目录和需要安装的课堂插件。
3. 安装完成后，通过桌面或开始菜单快捷方式启动 ClassTool。

安装器优先使用 `D:\ClassTool`。如果 D 盘不可用，则使用 Windows 的 `Program Files\ClassTool`。安装器会创建桌面快捷方式、开始菜单项目、卸载入口和已安装插件的桌面右键菜单。

主程序可在启动后检查 GitHub Releases 中的稳定版更新。安装包下载完成并通过大小与 SHA-256 校验后，程序会询问是否退出并启动安装器；不会在未确认的情况下自动安装。

### 绿色版

1. 完整解压 `ClassTool-v*-win-x64-portable.zip`。
2. 保持 `ClassTool.exe`、`_internal/`、`tools/` 和 `data/` 的相对位置不变。
3. 双击 `ClassTool.exe` 启动程序。

绿色版附带三个维护脚本，可用于重建快捷方式、注册桌面右键菜单或清除右键菜单。注册系统功能时可能需要管理员权限。

## 插件安全

ClassTool 插件不是沙盒程序。插件与主程序拥有相近的本机权限，可能访问文件、网络、摄像头、麦克风或剪贴板。请只使用可信来源的插件，并在运行前检查其源码和依赖。详细说明见 [SECURITY.md](docs/SECURITY.md)。

## 进一步了解

- [中文详细技术文档](docs/README.zh-CN.md)
- [English README](README.en.md)
- [English Technical Documentation](docs/README.en.md)
- [参与贡献](docs/CONTRIBUTING.md)
- [更新记录](docs/CHANGELOG.md)
- [MIT License](LICENSE)
