import json
import threading
from http.client import HTTPConnection
from unittest.mock import patch

from mnamer.metadata import MetadataMovie
from mnamer.setting_store import SettingStore
from mnamer.target import Target
from mnamer.web import create_server


def _request(server, method: str, path: str, body=None):
    host, port = server.server_address[:2]
    connection = HTTPConnection(host, port)
    payload = None if body is None else json.dumps(body)
    headers = {"Content-Type": "application/json"} if payload else {}
    connection.request(method, path, payload, headers)
    response = connection.getresponse()
    result = (
        response.status,
        json.loads(response.read()) if path != "/" else response.read(),
    )
    connection.close()
    return result


def test_web_server_lists_only_active_targets(tmp_path):
    media = tmp_path / "movie (2020).mkv"
    media.write_bytes(b"media")
    settings = SettingStore(targets=[media], mask=[".mkv"])
    target = Target(media, settings)
    server = create_server(settings, [target])
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        status, body = _request(server, "GET", "/api/status")
        assert status == 200
        assert body["service"] == "mnamer"
        assert body["files"] == 1

        status, body = _request(server, "GET", "/api/files")
        assert status == 200
        assert body["files"][0]["path"] == str(media.resolve())
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_web_preview_and_process_are_headless(tmp_path):
    media = tmp_path / "movie (2020).mkv"
    media.write_bytes(b"media")
    settings = SettingStore(targets=[media], mask=[".mkv"])
    target = Target(media, settings)
    match = MetadataMovie(name="Movie", year="2020", id_imdb="tt1234567")
    server = create_server(settings, [target])
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        with patch.object(Target, "query", return_value=[match]):
            status, body = _request(
                server, "POST", "/api/preview", {"path": str(media)}
            )
            assert status == 200
            assert body["matches"][0]["name"] == "Movie"
            assert body["destination"]

            status, body = _request(
                server, "POST", "/api/process", {"path": str(tmp_path / "other.mkv")}
            )
            assert status == 404
            assert "active target" in body["error"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_web_index_is_html(tmp_path):
    media = tmp_path / "movie.mkv"
    media.write_bytes(b"media")
    settings = SettingStore(targets=[media], mask=[".mkv"])
    server = create_server(settings, [Target(media, settings)])
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        status, body = _request(server, "GET", "/")
        assert status == 200
        assert b"<title>mnamer</title>" in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
