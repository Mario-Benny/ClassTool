# ClassTool 技术总览 / Technical Overview

## 架构 / Architecture

ClassTool 由单文件主程序、外置插件和外置运行数据组成。主程序负责界面、主题、语言、导航、托盘行为和插件生命周期；插件负责具体课堂功能。

ClassTool consists of a single-file host application, external plugins, and external runtime data. The host owns the interface, themes, language, navigation, tray behavior, and plugin lifecycle; plugins provide individual classroom functions.

```text
download/
|-- ClassTool.exe            # 主程序；内置语言资源 / host; language resources embedded
|-- tools/                   # 可扩展的 Python 插件 / extensible Python plugins
`-- data/                    # 用户设置和插件数据 / user settings and plugin data
```

## 资源与设置 / Resources and Settings

语言文本存放在源码的 `src/ClassTool/language/`，由打包脚本写入 EXE。运行时不会要求用户维护外置语言文件。语言和主题设置会保存到 `data/settings.json`。

Language text is kept in `src/ClassTool/language/` and embedded in the EXE by the build script. Users do not need to maintain external language files at runtime. Language and theme preferences are saved in `data/settings.json`.

## 插件机制 / Plugin Model

插件是放入 `tools/` 的 Python 文件，至少提供 `create_widget()`、`get_widget()` 或 `run()` 之一，并以 `TOOL_INFO` 描述名称、颜色、图标、依赖和缓存策略。主程序先静态读取 `TOOL_INFO`，仅在用户打开工具时导入插件。

Plugins are Python files in `tools/`. Each plugin provides at least one of `create_widget()`, `get_widget()`, or `run()`, and uses `TOOL_INFO` to describe its name, color, icon, dependencies, and cache behavior. The host reads `TOOL_INFO` statically first and imports the plugin only when it is opened.

涉及线程、计时器、设备或临时资源的插件应提供 `cleanup()`。主程序退出时会调用该钩子，以帮助插件释放资源。

Plugins that use threads, timers, devices, or temporary resources should provide `cleanup()`. The host calls this hook during shutdown to help plugins release resources.

详细接口、模板和第三方依赖处理见 [插件开发指南](plugin-development.md)。

For complete interfaces, templates, and third-party dependency handling, see the [plugin development guide](plugin-development.md).

## 打包 / Packaging

打包脚本使用 PyInstaller 生成 `download/ClassTool.exe`，同时复制内置插件到 `download/tools/` 并创建 `download/data/`。因此，没有 Python 环境的 Windows 电脑也能运行主程序；外置插件使用的第三方库必须被主程序打包时收集。

The build script uses PyInstaller to create `download/ClassTool.exe`, copy bundled plugins to `download/tools/`, and create `download/data/`. Therefore, the host can run on Windows computers without Python installed; third-party libraries used by external plugins must be collected when the host is built.

具体打包命令、图标与发布目录说明见 [打包说明](packaging.md)。

For build commands, icons, and release layout details, see the [packaging guide](packaging.md).

## 安全 / Security

ClassTool 不会沙盒化插件。第三方插件具有与普通本地 Python 程序相同的权限，可能访问文件、网络、摄像头、麦克风或剪贴板。请仅安装可信来源的插件，并查看其源码和依赖声明。

ClassTool does not sandbox plugins. Third-party plugins have the same permissions as ordinary local Python programs and may access files, networks, cameras, microphones, or the clipboard. Install plugins only from trusted sources, and inspect their source code and declared dependencies.

完整的漏洞报告方式与安全原则见 [SECURITY.md](../SECURITY.md)。

For vulnerability reporting and full security guidance, see [SECURITY.md](../SECURITY.md).
