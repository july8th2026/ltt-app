"""Small local wire server for real Codex/Claude client smoke tests.

It never contacts a model and records only request paths and non-secret body
metadata. The process prints its chosen port, then serves until terminated.
"""
from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LOG = Path(sys.argv[1])
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
MODE = sys.argv[2] if len(sys.argv) > 2 else "ok"
FAILURES_REMAINING = (1 if MODE == "rate-once" else
                      -1 if MODE in {"400", "413", "429-rate", "429-capacity",
                                     "503", "disconnect"} else 0)
FAILURE_LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args) -> None:
        return

    def _body(self) -> dict:
        raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        try:
            return json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return {}

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
        body = self._body()
        self._last_body = body
        with LOG.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({
                "path": self.path,
                "model": body.get("model"),
                "stream": body.get("stream"),
                "tools": len(body.get("tools") or []),
            }) + "\n")
        global FAILURES_REMAINING
        with FAILURE_LOCK:
            if FAILURES_REMAINING:
                if FAILURES_REMAINING > 0:
                    FAILURES_REMAINING -= 1
                if MODE in {"rate-once", "429-rate"}:
                    return self._json({"code": "rate_limited", "scope": "key",
                                       "reason": "create_rate", "retry_after": 1},
                                      status=429, headers={"Retry-After": "1"})
                if MODE == "429-capacity":
                    return self._json({"code": "concurrency_limited",
                                       "scope": "execution", "reason": "het_cho",
                                       "resource": "ltt_38_3090", "retry_after": 2},
                                      status=429, headers={"Retry-After": "2"})
                if MODE == "400":
                    return self._json({"code": "invalid_request",
                                       "detail": "mock bad parameter"}, status=400)
                if MODE == "413":
                    return self._json({"code": "payload_too_large",
                                       "limit_name": "input_tokens",
                                       "limit_value": 171458}, status=413)
                if MODE == "503":
                    return self._json({"code": "service_unavailable",
                                       "detail": "mock model unavailable"}, status=503,
                                      headers={"Retry-After": "3"})
                if MODE == "disconnect":
                    return self._disconnect_stream()
        if self.path.startswith("/api/v1/messages/count_tokens"):
            return self._json({"input_tokens": 8})
        if self.path.startswith("/api/v1/messages"):
            return self._claude(bool(body.get("stream")))
        if self.path.startswith("/api/v1/responses"):
            return self._codex()
        self._json({"error": "not found"}, status=404)

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
        if self.path.startswith("/api/v1/tools"):
            return self._json({"items": [{"name": "text.chat"}]})
        if self.path.startswith("/api/v1/credits/balance"):
            return self._json({"balance": 1000})
        self._json({"error": "not found"}, status=404)

    def _json(self, payload: dict, status: int = 200,
              headers: dict[str, str] | None = None) -> None:
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(raw)

    def _claude(self, stream: bool) -> None:
        # Exercise a real two-turn tool cycle, not only the presence of a
        # `tools` field. The second reply proves the tool result survived the
        # Anthropic wire shape used by Claude clients.
        body = getattr(self, "_last_body", {})
        messages = body.get("messages") or []
        has_result = any(
            isinstance(block, dict) and block.get("type") == "tool_result"
            for message in messages if isinstance(message, dict)
            for block in (message.get("content")
                          if isinstance(message.get("content"), list) else [])
        )
        if has_result:
            return self._json({
                "id": "msg_mock_tool_done", "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "42"}],
                "model": body.get("model") or "ltt-3.8",
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 12, "output_tokens": 4},
            })
        if body.get("tools"):
            return self._json({
                "id": "msg_mock_tool", "type": "message", "role": "assistant",
                "content": [{"type": "tool_use", "id": "toolu_mock",
                             "name": "report_marker", "input": {"value": 42}}],
                "model": body.get("model") or "ltt-3.8",
                "stop_reason": "tool_use",
                "usage": {"input_tokens": 10, "output_tokens": 5},
            })
        if not stream:
            marker = ("56" if
                      body.get("model") == "ltt-llm-claude-compat"
                      else "144")
            return self._json({"id": "msg_mock", "type": "message",
                               "role": "assistant", "content": [{"type": "text", "text": marker}],
                               "model": "ltt-3.8", "stop_reason": "end_turn",
                               "usage": {"input_tokens": 8, "output_tokens": 1}})
        from server.api.streaming import _luong_thu
        self._stream(list(_luong_thu("/v1/messages")))

    def _codex(self) -> None:
        from server.api.streaming import _luong_thu
        self._stream(list(_luong_thu("/v1/responses")))

    def _stream(self, chunks: list[bytes]) -> None:
        raw = b"".join(chunks)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _disconnect_stream(self) -> None:
        raw = b'event: response.created\ndata: {"type":"response.created"}\n\n'
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(raw) + 100))
        self.end_headers()
        self.wfile.write(raw)
        self.wfile.flush()
        self.close_connection = True


class QuietThreadingHTTPServer(ThreadingHTTPServer):
    def handle_error(self, _request, _client_address) -> None:
        """Real clients close pooled sockets; that is expected during smoke."""


if __name__ == "__main__":
    server = QuietThreadingHTTPServer(("127.0.0.1", 0), Handler)
    print(server.server_port, flush=True)
    server.serve_forever()
