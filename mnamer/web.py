"""Small dependency-free HTTP UI for remote preview and processing."""

from __future__ import annotations

import datetime as dt
import json
from enum import Enum
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

from mnamer.const import VERSION
from mnamer.exceptions import MnamerException
from mnamer.metadata import Metadata
from mnamer.target import Target
from mnamer.utils import is_subtitle

MAX_REQUEST_BYTES = 1024 * 1024

INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>mnamer</title>
  <style>
    :root { color-scheme: dark; font-family: system-ui, sans-serif; }
    body { background: #17191c; color: #f4f5f6; margin: 0; }
    main { margin: 0 auto; max-width: 1100px; padding: 2rem; }
    h1 { margin: 0 0 .25rem; }
    .muted { color: #aeb4bb; }
    .toolbar { display: flex; gap: .75rem; margin: 1.5rem 0; }
    button { background: #3c82f6; border: 0; border-radius: .35rem; color: white;
      cursor: pointer; padding: .55rem .8rem; }
    button.secondary { background: #3a4048; }
    button:disabled { cursor: wait; opacity: .6; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border-bottom: 1px solid #343941; padding: .65rem .5rem; text-align: left; }
    th { color: #aeb4bb; font-size: .85rem; }
    code { color: #9cc4ff; overflow-wrap: anywhere; }
    #details { background: #20242a; border-radius: .4rem; margin-top: 1.5rem;
      min-height: 3rem; padding: 1rem; white-space: pre-wrap; }
  </style>
</head>
<body>
  <main>
    <h1>mnamer</h1>
    <div class="muted">Preview and process media files on this host.</div>
    <div class="toolbar">
      <button id="refresh" class="secondary">Refresh</button>
      <span id="status" class="muted"></span>
    </div>
    <table>
      <thead><tr><th>File</th><th>Type</th><th>Action</th></tr></thead>
      <tbody id="files"></tbody>
    </table>
    <pre id="details">Select a file to preview it.</pre>
  </main>
  <script>
    const files = document.querySelector("#files");
    const details = document.querySelector("#details");
    const status = document.querySelector("#status");
    const request = (url, options) => fetch(url, options).then(async response => {
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || response.statusText);
      return body;
    });
    const show = value => { details.textContent = JSON.stringify(value, null, 2); };
    const action = (button, path, operation) => {
      button.disabled = true;
      const endpoint = operation === "process" ? "/api/process" : "/api/preview";
      request(endpoint, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path }) })
        .then(show).catch(error => { details.textContent = error.message; })
        .finally(() => { button.disabled = false; });
    };
    const load = () => request("/api/files").then(data => {
      files.replaceChildren(...data.files.map(file => {
        const row = document.createElement("tr");
        const name = document.createElement("td");
        const path = document.createElement("code");
        path.textContent = file.path;
        name.append(path);
        const type = document.createElement("td");
        type.textContent = file.media_type;
        const actions = document.createElement("td");
        const preview = document.createElement("button");
        preview.textContent = "Preview";
        preview.onclick = () => action(preview, file.path, "preview");
        const process = document.createElement("button");
        process.className = "secondary";
        process.textContent = "Process";
        process.onclick = () => action(process, file.path, "process");
        actions.append(preview, document.createTextNode(" "), process);
        row.append(name, type, actions);
        return row;
      }));
      status.textContent = `${data.files.length} file(s)`;
    }).catch(error => { status.textContent = error.message; });
    document.querySelector("#refresh").onclick = load;
    load();
  </script>
</body>
</html>
"""


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Enum):
        return _json_value(value.value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dt.date | dt.datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [_json_value(item) for item in value]
    return str(value)


class WebRequestError(Exception):
    """An expected request error with an HTTP status."""

    def __init__(self, status: HTTPStatus, message: str):
        super().__init__(message)
        self.status = status


class WebApplication:
    """Application state and operations exposed by the HTTP handler."""

    def __init__(self, targets: list[Target], *, test: bool = False):
        self.targets = targets
        self.test = test

    def _target(self, value: Any) -> Target:
        if not isinstance(value, str) or not value:
            raise WebRequestError(HTTPStatus.BAD_REQUEST, "path must be a string")
        source = Path(value).expanduser().resolve()
        for target in self.targets:
            if target.source.resolve() == source:
                return target
        raise WebRequestError(HTTPStatus.NOT_FOUND, "path is not an active target")

    @staticmethod
    def _metadata(metadata: Metadata) -> dict[str, Any]:
        return _json_value(metadata.as_dict())

    def _file(self, target: Target) -> dict[str, Any]:
        return {
            "path": str(target.source.resolve()),
            "name": target.source.name,
            "media_type": target.metadata.to_media_type().value,
            "subtitle": is_subtitle(target.metadata.container),
            "metadata": self._metadata(target.metadata),
        }

    def files(self) -> list[dict[str, Any]]:
        return [self._file(target) for target in self.targets if target.source.exists()]

    def _query(self, target: Target) -> dict[str, Any]:
        try:
            matches = target.query()
        except MnamerException as error:
            raise WebRequestError(HTTPStatus.BAD_GATEWAY, str(error)) from error
        if matches:
            target.metadata.update(matches[0])
        return {
            "source": str(target.source.resolve()),
            "metadata": self._metadata(target.metadata),
            "matches": [self._metadata(match) for match in matches],
            "destination": str(target.destination.resolve()) if matches else None,
        }

    def preview(self, value: Any) -> dict[str, Any]:
        return self._query(self._target(value))

    def process(self, value: Any) -> dict[str, Any]:
        target = self._target(value)
        result = self._query(target)
        if target.destination == target.source:
            raise WebRequestError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "source and destination paths are the same",
            )
        if target._settings.no_overwrite and target.destination.exists():
            raise WebRequestError(HTTPStatus.CONFLICT, "destination already exists")
        if self.test:
            result["processed"] = False
            result["test"] = True
            return result
        try:
            target.relocate()
        except MnamerException as error:
            raise WebRequestError(HTTPStatus.INTERNAL_SERVER_ERROR, str(error)) from error
        result["processed"] = True
        result["destination"] = str(target.destination.resolve())
        return result


class _RequestHandler(BaseHTTPRequestHandler):
    application: WebApplication

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _send(self, status: HTTPStatus, body: Any, content_type: str) -> None:
        payload = body if isinstance(body, bytes) else str(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, status: HTTPStatus, body: Any) -> None:
        payload = json.dumps(body, ensure_ascii=True, default=str)
        self._send(status, payload, "application/json; charset=utf-8")

    def _error(self, error: WebRequestError) -> None:
        self._json(error.status, {"error": str(error)})

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/":
            self._send(HTTPStatus.OK, INDEX_HTML, "text/html; charset=utf-8")
        elif route == "/api/files":
            self._json(HTTPStatus.OK, {"files": self.application.files()})
        elif route == "/api/status":
            self._json(
                HTTPStatus.OK,
                {
                    "service": "mnamer",
                    "version": VERSION,
                    "files": len(self.application.files()),
                },
            )
        else:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise WebRequestError(HTTPStatus.BAD_REQUEST, "invalid content length") from error
        if length <= 0 or length > MAX_REQUEST_BYTES:
            raise WebRequestError(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request body is too large"
            )
        try:
            body = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise WebRequestError(HTTPStatus.BAD_REQUEST, "request body must be JSON") from error
        if not isinstance(body, dict):
            raise WebRequestError(HTTPStatus.BAD_REQUEST, "request body must be an object")
        return body

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        try:
            body = self._read_json()
            if route == "/api/preview":
                result = self.application.preview(body.get("path"))
            elif route == "/api/process":
                result = self.application.process(body.get("path"))
            else:
                raise WebRequestError(HTTPStatus.NOT_FOUND, "not found")
        except WebRequestError as error:
            self._error(error)
            return
        self._json(HTTPStatus.OK, result)


def create_server(settings: Any, targets: list[Target]) -> ThreadingHTTPServer:
    """Create a server without starting it, useful for headless tests."""
    application = WebApplication(targets, test=settings.test)

    class RequestHandler(_RequestHandler):
        pass

    RequestHandler.application = application
    return ThreadingHTTPServer(
        (settings.serve_host, settings.serve_port), RequestHandler
    )


def run_web(settings: Any, targets: list[Target]) -> None:
    """Run the blocking HTTP service until interrupted."""
    server = create_server(settings, targets)
    host, port = cast(tuple[str, int], server.server_address)
    print(f"mnamer web listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
