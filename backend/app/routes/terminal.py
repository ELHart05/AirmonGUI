"""
WebSocket-based PTY terminal.

Opens a bash shell in a pseudoterminal and relays bytes between the
WebSocket client (xterm.js) and the shell process.  Resize events are
sent as a JSON text frame: {"type":"resize","cols":<n>,"rows":<n>}.
"""

import asyncio
import fcntl
import json
import os
import pty
import signal
import struct
import termios

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["terminal"])

_SHELL = os.environ.get("SHELL", "/bin/bash")
_SHELL_ARGS = [_SHELL]


@router.websocket("/ws/terminal")
async def terminal_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()

    # Create a pseudoterminal pair
    master_fd, slave_fd = pty.openpty()

    # Inherit a clean environment; force a 256-colour TERM so xterm.js renders correctly
    env = {**os.environ, "TERM": "xterm-256color", "COLORTERM": "truecolor"}

    # preexec_fn runs in the child process before exec
    def _child_setup() -> None:
        os.setsid()
        # Make slave the controlling terminal
        fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)

    proc = await asyncio.create_subprocess_exec(
        *_SHELL_ARGS,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
        env=env,
        preexec_fn=_child_setup,
    )
    # Parent no longer needs the slave side
    os.close(slave_fd)

    # Make the master fd non-blocking so asyncio can poll it without blocking the loop
    flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    # Queue used to hand bytes from the pty-readable callback to the relay coroutine
    pty_queue: asyncio.Queue = asyncio.Queue()

    def _on_pty_readable() -> None:
        try:
            data = os.read(master_fd, 4096)
            pty_queue.put_nowait(data)
        except OSError:
            pty_queue.put_nowait(None)  # signal EOF

    loop = asyncio.get_event_loop()
    loop.add_reader(master_fd, _on_pty_readable)

    async def pty_to_ws() -> None:
        """Forward PTY output to the WebSocket."""
        while True:
            data = await pty_queue.get()
            if data is None:
                break
            try:
                await websocket.send_bytes(data)
            except Exception:
                break

    async def ws_to_pty() -> None:
        """Forward WebSocket input to the PTY."""
        while True:
            try:
                msg = await websocket.receive()
                msg_type = msg.get("type")

                if msg_type == "websocket.disconnect":
                    break

                if msg_type == "websocket.receive":
                    raw_bytes = msg.get("bytes")
                    raw_text = msg.get("text")

                    if raw_bytes:
                        os.write(master_fd, raw_bytes)
                    elif raw_text:
                        # Try to parse as a control message (e.g. resize)
                        try:
                            ctrl = json.loads(raw_text)
                            if ctrl.get("type") == "resize":
                                cols = max(1, int(ctrl.get("cols", 80)))
                                rows = max(1, int(ctrl.get("rows", 24)))
                                fcntl.ioctl(
                                    master_fd,
                                    termios.TIOCSWINSZ,
                                    struct.pack("HHHH", rows, cols, 0, 0),
                                )
                        except (json.JSONDecodeError, ValueError, KeyError):
                            # Plain text (shouldn't normally occur, but handle gracefully)
                            os.write(master_fd, raw_text.encode())
            except WebSocketDisconnect:
                break
            except Exception:
                break

    try:
        await asyncio.gather(pty_to_ws(), ws_to_pty())
    finally:
        loop.remove_reader(master_fd)
        try:
            os.close(master_fd)
        except OSError:
            pass
        try:
            proc.send_signal(signal.SIGTERM)
            await asyncio.wait_for(proc.wait(), timeout=3.0)
        except (ProcessLookupError, asyncio.TimeoutError):
            try:
                proc.kill()
            except ProcessLookupError:
                pass
