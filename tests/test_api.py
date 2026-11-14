"""Protocol tests against synthetic fixtures and a local Digest server."""

import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import parse_http_list, parse_keqv_list

import pytest

from custom_components.toshiba_legacy.api import (
    CannotConnect,
    InvalidAuth,
    InvalidPin,
    ToshibaClient,
    ToshibaError,
    decrypt_password,
    normalize_host,
)

CHALLENGE = {
    "status": 0,
    "salt": "test-salt",
    "password": "a81e01b5b3cf8b3757984e846e66bd1220958dac61e932ab25dbc4ab5692cd5d",
}


def test_pairing_fixture_and_wrong_pin():
    assert decrypt_password("1234", CHALLENGE) == "synthetic-password"
    for pin in ["0000", "123", "１２３４", ""]:
        with pytest.raises(InvalidPin):
            decrypt_password(pin, CHALLENGE)
    with pytest.raises(InvalidPin):
        decrypt_password("1234", {"salt": "test-salt", "password": "not-hex"})


@pytest.mark.parametrize(
    "host", ["http://example.com", "user@example.com", "host/path", "host:8080", "", "a..b"]
)
def test_reject_host_urls_and_paths(host):
    with pytest.raises(ValueError):
        normalize_host(host)


def test_normalize_host():
    assert normalize_host(" TV.local. ") == "tv.local"
    assert normalize_host("192.0.2.10") == "192.0.2.10"
    assert normalize_host("::1") == "[::1]"


@pytest.fixture
def television():
    class Handler(BaseHTTPRequestHandler):
        requests_seen = []

        def log_message(self, *args):
            pass

        def do_GET(self):
            self.handle_api()

        def do_POST(self):
            self.handle_api()

        def handle_api(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            self.requests_seen.append((self.command, self.path, body))
            if self.path == "/public/feature":
                self.reply({"status": 0, "id": "synthetic-tv", "ipc_feature": ["PIN_Auth"]})
                return
            if self.path == "/v2/public/request_connection":
                self.reply(CHALLENGE)
                return
            authorization = self.headers.get("Authorization", "")
            valid = False
            if authorization.startswith("Digest "):
                auth = parse_keqv_list(parse_http_list(authorization[7:]))

                def md5(s):
                    return hashlib.md5(s.encode()).hexdigest()

                ha1 = md5("02-00-00-00-00-01:TOSHIBA-LCDTV:synthetic-password")
                ha2 = md5(f"{self.command}:{self.path}")
                expected = md5(f"{ha1}:test-nonce:{auth.get('nc')}:{auth.get('cnonce')}:auth:{ha2}")
                valid = auth.get("response") == expected
            if not valid:
                self.send_response(401)
                self.send_header(
                    "WWW-Authenticate",
                    'Digest realm="TOSHIBA-LCDTV", nonce="test-nonce", qop="auth"',
                )
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if self.path == "/v2/remote/status":
                self.reply({"status": 0, "power": "on", "external_input": "HDMI_2"})
            elif self.path == "/v2/remote/confirm_connection":
                self.reply({"status": 0})
            elif self.path == "/v2/remote/remote":
                self.reply({"status": 0 if body == b"key=40BF84" else 2})
            else:
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()

        def reply(self, data):
            encoded = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_port, Handler.requests_seen
    server.shutdown()
    server.server_close()
    thread.join()


def test_end_to_end_digest_pairing_and_command_errors(television):
    port, requests = television
    anonymous = ToshibaClient("127.0.0.1", port)
    assert anonymous.feature()["id"] == "synthetic-tv"
    challenge = anonymous.start_pairing("02-00-00-00-00-01")
    password = decrypt_password("1234", challenge)
    client = ToshibaClient("127.0.0.1", port, "02-00-00-00-00-01", password)
    client.confirm_pairing()
    assert client.status()["external_input"] == "HDMI_2"
    client.send_key("40BF84")
    with pytest.raises(ToshibaError, match="rejected"):
        client.send_key("not-a-key")
    with pytest.raises(ToshibaError, match="404"):
        client.request("/not-supported")
    with pytest.raises(InvalidAuth):
        ToshibaClient("127.0.0.1", port, "wrong", "wrong").status()
    assert ("POST", "/v2/remote/confirm_connection", b"") in requests


def test_unreachable_tv_is_connection_error():
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with pytest.raises(CannotConnect):
        ToshibaClient("127.0.0.1", port).status()
