# -*- coding: utf-8 -*-

"""
插件加载器。

启动时只静态读取 TOOL_INFO，点击工具时才真正导入插件模块。
"""

import ast
import importlib.metadata
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Tuple

from toolkit.core.app_logging import get_logger
from toolkit.core.paths import app_root, ensure_tools_dir, plugin_cache_path
from toolkit.core.safe_io import atomic_write_text, read_text_with_fallback

_logger = get_logger("plugin_loader")


class PluginMetadataError(Exception):
    """插件元信息不符合要求。"""


class PluginRuntimeError(Exception):
    """插件运行时加载失败。"""


class PluginLoader:
    CACHE_VERSION = 1
    PACKAGE_IMPORT_ALIASES = {
        "beautifulsoup4": ("bs4",),
        "opencv-python": ("cv2",),
        "pillow": ("PIL",),
        "pyyaml": ("yaml",),
        "python-dateutil": ("dateutil",),
        "scikit-learn": ("sklearn",),
    }

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
        self._distribution_imports: dict[str, tuple[str, ...]] | None = None
        self._persistent_cache = self._load_persistent_cache()

    # -------------------- 磁盘缓存 --------------------
    @staticmethod
    def _signature_to_list(signature: tuple[int, int]) -> list[int]:
        return [signature[0], signature[1]]

    @staticmethod
    def _signature_from_record(record: dict[str, Any]) -> tuple[int, int] | None:
        signature = record.get("signature")
        if (
            isinstance(signature, list)
            and len(signature) == 2
            and all(isinstance(item, int) for item in signature)
        ):
            return signature[0], signature[1]
        return None

    def _load_persistent_cache(self) -> dict[str, dict[str, Any]]:
        path = plugin_cache_path()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            if path.exists():
                _logger.warning("插件缓存不可用，本次改为重新扫描: %s", exc)
            return {}

        if not isinstance(payload, dict) or payload.get("version") != self.CACHE_VERSION:
            return {}
        plugins = payload.get("plugins")
        if not isinstance(plugins, dict):
            return {}
        return {
            key: value
            for key, value in plugins.items()
            if isinstance(key, str) and isinstance(value, dict)
        }

    def _save_persistent_cache(self) -> None:
        payload = {
            "version": self.CACHE_VERSION,
            "plugins": self._persistent_cache,
        }
        try:
            atomic_write_text(
                plugin_cache_path(),
                json.dumps(payload, ensure_ascii=False, indent=2),
            )
        except OSError as exc:
            # 缓存写不进磁盘只影响下次启动的扫描速度，不值得干扰运行。
            _logger.warning("插件缓存写入失败: %s", exc)

    @staticmethod
    def _cached_metadata(record: dict[str, Any], file_path: Path) -> Dict[str, Any] | None:
        metadata = record.get("metadata")
        if not isinstance(metadata, dict):
            return None
        result = dict(metadata)
        result["path"] = str(file_path)
        result["module"] = None
        return result

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

    @staticmethod
    def _read_source(file_path: Path) -> str:
        """读取插件源码，编码回退规则见 safe_io。"""
        try:
            return read_text_with_fallback(file_path)
        except UnicodeDecodeError as exc:
            raise PluginMetadataError(
                "插件源码不是 UTF-8 或 GBK 编码，请用记事本'另存为'选择 UTF-8 后重试"
                f"（原始错误: {exc}）"
            ) from exc

    def _read_tool_info(self, file_path: Path) -> dict | None:
        source = self._read_source(file_path)
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

    @staticmethod
    def _canonical_distribution_name(name: str) -> str:
        return re.sub(r"[-_.]+", "-", name).lower()

    def _requirement_to_distribution_name(self, requirement: str) -> str:
        name = requirement.strip().split(";", 1)[0].strip()
        for sep in ("==", ">=", "<=", "~=", "!=", ">", "<"):
            name = name.split(sep, 1)[0]
        name = name.split("[", 1)[0].strip()
        return self._canonical_distribution_name(name)

    def _get_distribution_imports(self) -> dict[str, tuple[str, ...]]:
        if self._distribution_imports is not None:
            return self._distribution_imports

        mapping: dict[str, list[str]] = {}
        try:
            packages = importlib.metadata.packages_distributions()
        except Exception as exc:
            _logger.warning("无法读取已安装包与导入名映射: %s", exc)
            packages = {}
        for module_name, distributions in packages.items():
            for distribution in distributions:
                key = self._canonical_distribution_name(distribution)
                mapping.setdefault(key, []).append(module_name)
        self._distribution_imports = {
            key: tuple(dict.fromkeys(values)) for key, values in mapping.items()
        }
        return self._distribution_imports

    def _requirement_available(self, requirement: str) -> bool:
        module_name = self._requirement_to_module_name(requirement)
        if module_name and self._module_available(module_name):
            return True

        distribution = self._requirement_to_distribution_name(requirement)
        candidates = list(self.PACKAGE_IMPORT_ALIASES.get(distribution, ()))
        candidates.extend(self._get_distribution_imports().get(distribution, ()))
        return any(self._module_available(candidate) for candidate in dict.fromkeys(candidates))

    @staticmethod
    def _module_available(module_name: str) -> bool:
        """探测依赖是否可用，任何探测失败都按"不可用"处理。

        find_spec 对多级点号名（如 torch.nn）不是返回 None，而是导入父包失败时
        直接抛 ModuleNotFoundError。这个异常若一路穿出 load_plugins，首页会整个
        空白且没有提示——一个插件的依赖写法就能拖垮全部工具。
        """
        try:
            return importlib.util.find_spec(module_name) is not None
        except Exception as exc:
            _logger.warning("依赖探测失败 %s: %s", module_name, exc)
            return False

    def _missing_requirements(self, requirements: List[str]) -> List[str]:
        cache_key = tuple(requirements)
        cached = self._requirements_cache.get(cache_key)
        if cached is not None:
            return list(cached)

        missing = []
        for req in requirements:
            if not self._requirement_available(req):
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
        except PluginMetadataError as exc:
            # 这里抛出的是我们自己写好的可执行提示，直接展示给用户。
            _logger.warning("插件元信息不合规 %s: %s", file_path, exc)
            return self._error_tool(file_path, str(exc))
        except SyntaxError as exc:
            _logger.warning("插件源码语法错误 %s: %s", file_path, exc)
            return self._error_tool(file_path, f"插件语法有误：第 {exc.lineno} 行 {exc.msg}")
        except (OSError, UnicodeError) as exc:
            _logger.exception("读取插件失败: %s", file_path)
            return self._error_tool(file_path, f"读取失败: {exc}")

    def _refresh_requirement_status(self, metadata: Dict[str, Any]) -> None:
        """在命中磁盘缓存时仍检查当前运行环境中的依赖。"""
        error = metadata.get("error")
        if isinstance(error, str) and error.startswith("缺少依赖:"):
            metadata.pop("error", None)
        if "error" in metadata:
            return

        missing = self._missing_requirements(metadata.get("requirements", []))
        if missing:
            metadata["error"] = f"缺少依赖: {', '.join(missing)}"

    def load_plugins(self) -> List[Dict[str, Any]]:
        plugins = []
        active_paths = set()
        cache_changed = False
        try:
            plugin_files = list(self._iter_plugin_files())
        except OSError as exc:
            _logger.warning("无法列出 tools 目录: %s", exc)
            plugin_files = []

        for file_path in plugin_files:
            try:
                cache_key = str(file_path.resolve())
                signature = self._file_signature(file_path)
                active_paths.add(cache_key)

                cached = self._metadata_cache.get(cache_key)

                if cached and cached["signature"] == signature:
                    metadata = dict(cached["metadata"])
                else:
                    disk_record = self._persistent_cache.get(cache_key)
                    if (
                        disk_record is not None
                        and self._signature_from_record(disk_record) == signature
                    ):
                        metadata = self._cached_metadata(disk_record, file_path)
                    else:
                        metadata = self._build_metadata(file_path)
                        if metadata is not None:
                            self._persistent_cache[cache_key] = {
                                "signature": self._signature_to_list(signature),
                                "metadata": dict(metadata),
                            }
                            cache_changed = True
                    if metadata is not None:
                        self._metadata_cache[cache_key] = {
                            "signature": signature,
                            "metadata": dict(metadata),
                        }

                if metadata is not None:
                    self._refresh_requirement_status(metadata)
                    plugins.append(metadata)
            except OSError as exc:
                # 扫描期间文件被删除或占用是正常竞态，跳过这一个即可。
                _logger.info("跳过暂不可读的插件 %s: %s", file_path, exc)
            except Exception as exc:
                # 任何一个插件的意外故障只能让它自己变成错误磁贴，不能带走整页工具。
                _logger.exception("插件扫描失败: %s", file_path)
                plugins.append(self._error_tool(file_path, f"扫描失败: {exc}"))

        stale_paths = set(self._persistent_cache) - active_paths
        if stale_paths:
            for cache_key in stale_paths:
                self._persistent_cache.pop(cache_key, None)
            cache_changed = True
        if cache_changed:
            self._save_persistent_cache()
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
            _logger.exception("插件模块执行失败: %s", file_path)
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
                    # 摄像头、线程这类资源没释放必须留下痕迹，否则现场无从查证。
                    _logger.exception(
                        "插件 cleanup 失败，资源可能未释放: %s",
                        getattr(module, "__name__", module),
                    )
