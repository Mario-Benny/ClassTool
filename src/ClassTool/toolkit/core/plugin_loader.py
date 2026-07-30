# -*- coding: utf-8 -*-

"""
插件加载器。

启动时只静态读取 TOOL_INFO，点击工具时才真正导入插件模块。
"""

import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Tuple

from toolkit.core.paths import app_root, ensure_tools_dir


class PluginMetadataError(Exception):
    """插件元信息不符合要求。"""


class PluginRuntimeError(Exception):
    """插件运行时加载失败。"""


class PluginLoader:
    def __init__(self, tools_dir: str = "tools"):
        path = Path(tools_dir)
        if tools_dir == "tools":
            self.tools_dir = ensure_tools_dir()
        else:
            self.tools_dir = path if path.is_absolute() else app_root() / path
            self.tools_dir.mkdir(exist_ok=True)

        self._metadata_cache: Dict[str, Dict[str, Any]] = {}
        self._module_cache: Dict[str, Dict[str, Any]] = {}
        self._requirements_cache: Dict[Tuple[str, ...], List[str]] = {}

    # -------------------- 插件发现 --------------------
    def _iter_plugin_files(self):
        for file_path in sorted(self.tools_dir.glob("*.py")):
            name = file_path.name
            if name == "__init__.py" or name.startswith((".", "~")):
                continue
            if file_path.is_file():
                yield file_path

    @staticmethod
    def _file_signature(file_path: Path) -> tuple[int, int]:
        stat = file_path.stat()
        return stat.st_mtime_ns, stat.st_size

    # -------------------- TOOL_INFO 静态读取 --------------------
    @staticmethod
    def _find_tool_info_node(tree: ast.Module):
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "TOOL_INFO":
                        return node.value
            elif (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "TOOL_INFO"
            ):
                return node.value
        return None

    def _read_tool_info(self, file_path: Path) -> dict | None:
        source = file_path.read_text(encoding="utf-8")
        if "TOOL_INFO" not in source:
            return None

        tree = ast.parse(source, filename=str(file_path))
        value_node = self._find_tool_info_node(tree)
        if value_node is None:
            return None

        try:
            value = ast.literal_eval(value_node)
        except (SyntaxError, ValueError) as exc:
            raise PluginMetadataError("TOOL_INFO 需要使用字面量字典") from exc

        if not isinstance(value, dict):
            raise PluginMetadataError("TOOL_INFO 必须是字典")
        return value

    @staticmethod
    def _as_text(value: Any, default: str) -> str:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return default

    @staticmethod
    def _as_requirements(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            requirements = [value]
        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
            requirements = value
        else:
            raise PluginMetadataError("requirements 必须是字符串或字符串列表")

        normalized = []
        seen = set()
        for item in requirements:
            item = item.strip()
            if item and item not in seen:
                normalized.append(item)
                seen.add(item)
        return normalized

    def _normalize_tool_info(self, file_path: Path, raw_info: dict) -> Dict[str, Any]:
        plugin_id = file_path.stem
        requirements = self._as_requirements(raw_info.get("requirements", []))
        icon = raw_info.get("icon")
        cache = raw_info.get("cache", True)

        if icon is not None and not isinstance(icon, str):
            icon = None
        if not isinstance(cache, bool):
            cache = True

        info = dict(raw_info)
        info.update({
            "id": plugin_id,
            "name": self._as_text(raw_info.get("name"), plugin_id),
            "color": self._as_text(raw_info.get("color"), "#2D89EF"),
            "icon": icon,
            "description": self._as_text(raw_info.get("description"), ""),
            "requirements": requirements,
            "cache": cache,
            "path": str(file_path),
            "module": None,
        })
        return info

    @staticmethod
    def _requirement_to_module_name(requirement: str) -> str:
        name = requirement.strip().split(";", 1)[0].strip()
        for sep in ("==", ">=", "<=", "~=", "!=", ">", "<"):
            name = name.split(sep, 1)[0]
        name = name.split("[", 1)[0]
        return name.strip().replace("-", "_")

    def _missing_requirements(self, requirements: List[str]) -> List[str]:
        cache_key = tuple(requirements)
        cached = self._requirements_cache.get(cache_key)
        if cached is not None:
            return list(cached)

        missing = []
        for req in requirements:
            module_name = self._requirement_to_module_name(req)
            if not module_name or importlib.util.find_spec(module_name) is None:
                missing.append(req)
        self._requirements_cache[cache_key] = list(missing)
        return missing

    def _error_tool(self, file_path: Path, message: str) -> Dict[str, Any]:
        return {
            "id": file_path.stem,
            "name": file_path.stem,
            "color": "#888888",
            "icon": "\uE711",
            "description": "",
            "requirements": [],
            "cache": False,
            "path": str(file_path),
            "module": None,
            "error": message,
        }

    def _build_metadata(self, file_path: Path) -> Dict[str, Any] | None:
        try:
            raw_info = self._read_tool_info(file_path)
            if raw_info is None:
                return None

            tool_info = self._normalize_tool_info(file_path, raw_info)
            missing = self._missing_requirements(tool_info["requirements"])
            if missing:
                tool_info["error"] = f"缺少依赖: {', '.join(missing)}"
            return tool_info
        except (OSError, UnicodeError, SyntaxError, PluginMetadataError) as exc:
            return self._error_tool(file_path, f"读取失败: {exc}")

    def load_plugins(self) -> List[Dict[str, Any]]:
        plugins = []
        for file_path in self._iter_plugin_files():
            try:
                cache_key = str(file_path.resolve())
                signature = self._file_signature(file_path)
            except OSError:
                continue

            cached = self._metadata_cache.get(cache_key)

            if cached and cached["signature"] == signature:
                metadata = dict(cached["metadata"])
            else:
                metadata = self._build_metadata(file_path)
                if metadata is not None:
                    self._metadata_cache[cache_key] = {
                        "signature": signature,
                        "metadata": dict(metadata),
                    }

            if metadata is not None:
                plugins.append(metadata)
        return plugins

    # -------------------- 运行时加载 --------------------
    def _validate_runtime_path(self, tool: Dict[str, Any]) -> Path:
        file_path = Path(tool.get("path", "")).resolve()
        tools_root = self.tools_dir.resolve()

        try:
            file_path.relative_to(tools_root)
        except ValueError as exc:
            raise PluginRuntimeError("插件路径必须位于 tools 目录内") from exc

        if not file_path.is_file() or file_path.suffix.lower() != ".py":
            raise PluginRuntimeError("插件文件不存在或不是 Python 文件")
        return file_path

    @staticmethod
    def _has_entry_point(module: ModuleType) -> bool:
        return any(
            callable(getattr(module, attr, None))
            for attr in ("create_widget", "get_widget", "run")
        )

    def load_plugin_module(self, tool: Dict[str, Any]) -> ModuleType:
        if "error" in tool:
            raise PluginRuntimeError(tool["error"])

        file_path = self._validate_runtime_path(tool)
        requirements = self._as_requirements(tool.get("requirements", []))
        missing = self._missing_requirements(requirements)
        if missing:
            raise PluginRuntimeError(f"缺少依赖: {', '.join(missing)}")

        cache_key = str(file_path)
        signature = self._file_signature(file_path)
        cached = self._module_cache.get(cache_key)
        if tool.get("cache", True) and cached and cached["signature"] == signature:
            return cached["module"]
        if cached and cached["signature"] != signature:
            old_module = cached.get("module")
            old_name = getattr(old_module, "__name__", "")
            if old_name:
                sys.modules.pop(old_name, None)
            self._module_cache.pop(cache_key, None)

        module_name = f"_classtool_plugin_{file_path.stem}_{signature[0]}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise PluginRuntimeError("无法创建插件加载器")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            sys.modules.pop(module_name, None)
            raise PluginRuntimeError(f"运行时加载失败: {exc}") from exc

        if not self._has_entry_point(module):
            sys.modules.pop(module_name, None)
            raise PluginRuntimeError("插件需要提供 create_widget()、get_widget() 或 run()")

        if tool.get("cache", True):
            self._module_cache[cache_key] = {
                "signature": signature,
                "module": module,
            }
        else:
            sys.modules.pop(module_name, None)
        return module

    def cleanup_plugins(self):
        """调用已加载插件的可选 cleanup() 钩子。"""
        for cached in list(self._module_cache.values()):
            module = cached.get("module")
            cleanup = getattr(module, "cleanup", None)
            if callable(cleanup):
                try:
                    cleanup()
                except Exception:
                    pass
