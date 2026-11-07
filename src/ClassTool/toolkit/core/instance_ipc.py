# -*- coding: utf-8 -*-

"""实例间通信：把后启动进程的请求转交给已经在运行的实例。"""

import json
import time

from PySide6.QtNetwork import QLocalServer, QLocalSocket

from toolkit.core.app_logging import get_logger

_logger = get_logger("instance_ipc")

SERVER_NAME = "ClassTool_Yexiaxingkong233_OpenTool"
ACTION_OPEN_TOOL = "open_tool"
ACTION_SHOW_MAIN = "show_main"

# 首个实例要跑完 EXE 解包和 Qt 导入才会开始监听，这期间管道不收连接。
# 转交方是一次性的短命进程，多等一会儿比把请求丢掉划算。
_CONNECT_BUDGET_SECONDS = 8.0
_CONNECT_RETRY_INTERVAL_MS = 200
_WRITE_TIMEOUT_MS = 1000


def _send_request(request: dict) -> bool:
    payload = json.dumps(request, ensure_ascii=False) + "\n"

    deadline = time.monotonic() + _CONNECT_BUDGET_SECONDS
    while True:
        if _try_send(payload.encode("utf-8")):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(_CONNECT_RETRY_INTERVAL_MS / 1000)


def send_open_request(tool_id: str) -> bool:
    """把"打开某个插件"的请求发给运行中的实例。"""
    return _send_request({"action": ACTION_OPEN_TOOL, "tool_id": tool_id})


def send_show_request() -> bool:
    """请求运行中的实例显示并激活主窗口。"""
    return _send_request({"action": ACTION_SHOW_MAIN})


def _try_send(payload: bytes) -> bool:
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if not socket.waitForConnected(_CONNECT_RETRY_INTERVAL_MS):
        return False

    try:
        socket.write(payload)
        if not socket.waitForBytesWritten(_WRITE_TIMEOUT_MS):
            _logger.warning("实例请求写入管道失败: %s", SERVER_NAME)
            return False
        return True
    finally:
        socket.close()


class OpenToolServer:
    """接收其他实例转来的请求，交给主线程的回调处理。

    newConnection 只由事件循环投递，因此回调被调用时主窗口一定已经建好。
    """

    def __init__(self, handler, show_handler=None) -> None:
        self._handler = handler
        self._show_handler = show_handler
        self._sockets: list[QLocalSocket] = []
        self._server = QLocalServer()
        self._server.newConnection.connect(self._on_new_connection)

    def start(self) -> bool:
        """开始监听管道，失败时返回 False 并留下日志。"""
        if not self._server.listen(SERVER_NAME):
            _logger.error(
                "实例通信管道监听失败: %s", self._server.errorString()
            )
            return False
        return True

    def _on_new_connection(self) -> None:
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            socket.readyRead.connect(lambda connected=socket: self._drain(connected))
            socket.disconnected.connect(
                lambda connected=socket: self._forget(connected)
            )
            self._sockets.append(socket)
            self._drain(socket)

    def _drain(self, socket: QLocalSocket) -> None:
        while socket.canReadLine():
            line = socket.readLine().data().decode("utf-8", "replace").strip()
            if line:
                self._dispatch(line)

    def _dispatch(self, line: str) -> None:
        try:
            request = json.loads(line)
        except ValueError:
            _logger.warning("忽略无法解析的实例请求: %s", line[:120])
            return

        if not isinstance(request, dict):
            _logger.warning("忽略不认识的实例请求: %s", line[:120])
            return

        action = request.get("action")
        if action == ACTION_SHOW_MAIN:
            if callable(self._show_handler):
                self._show_handler()
            return
        if action != ACTION_OPEN_TOOL:
            _logger.warning("忽略不认识的实例请求: %s", line[:120])
            return

        tool_id = request.get("tool_id")
        if not isinstance(tool_id, str) or not tool_id.strip():
            _logger.warning("实例请求缺少插件标识: %s", line[:120])
            return

        self._handler(tool_id.strip())

    def _forget(self, socket: QLocalSocket) -> None:
        if socket in self._sockets:
            self._sockets.remove(socket)
