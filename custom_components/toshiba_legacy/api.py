"""Local Toshiba IPC v2 client. All methods run in the executor."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import threading
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import (
    HTTPDigestAuthHandler,
    HTTPPasswordMgrWithDefaultRealm,
    Request,
    build_opener,
)

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class ToshibaError(Exception):
    """An API request failed."""


class CannotConnect(ToshibaError):
    """The television could not be reached."""


class InvalidAuth(ToshibaError):
    """The television rejected authentication."""


class InvalidPin(ToshibaError):
    """PIN decryption or validation failed."""


def normalize_host(host: str) -> str:
    """Accept an address/hostname, never a URL, credentials, or path."""
    host = host.strip().rstrip(".")
    try:
        address = ipaddress.ip_address(host.strip("[]"))
        return f"[{address}]" if address.version == 6 else str(address)
    except ValueError:
        if (
            len(host) > 253
            or not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", host)
            or any(not label or len(label) > 63 for label in host.split("."))
        ):
            raise ValueError("Enter an IP address or hostname") from None
        return host.lower()


def decrypt_password(pin: str, challenge: dict) -> str:
    """Derive the credential using the TV's PIN, PBKDF2 and AES-CBC.

    Protocol reference: https://github.com/9SQ/regza-digest-auth
    """
    if not re.fullmatch(r"[0-9]{4}", pin):
        raise InvalidPin("A four-digit PIN is required")
    try:
        key = hashlib.pbkdf2_hmac(
            "sha1", pin.encode("ascii"), challenge["salt"].encode("ascii"), 1331, 16
        )
        decryptor = Cipher(algorithms.AES(key), modes.CBC(bytes(16))).decryptor()
        plain = decryptor.update(bytes.fromhex(challenge["password"])) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        result = (unpadder.update(plain) + unpadder.finalize()).decode("ascii")
        if not result:
            raise ValueError("Empty credential")
        return result
    except KeyError, ValueError, TypeError, AttributeError, UnicodeError:
        raise InvalidPin("PIN or pairing challenge is invalid") from None


class ToshibaClient:
    """A serialized local HTTP client; credentials are never logged."""

    def __init__(self, host: str, port: int = 8080, username: str = "", password: str = ""):
        self.host = normalize_host(host)
        self.port = int(port)
        if not 1 <= self.port <= 65535:
            raise ValueError("Invalid port")
        self.base_url = f"http://{self.host}:{self.port}"
        self.username = username
        self._lock = threading.Lock()
        manager = HTTPPasswordMgrWithDefaultRealm()
        manager.add_password(None, self.base_url, username, password)
        self._opener = build_opener(HTTPDigestAuthHandler(manager))

    def request(self, path: str, data: dict | None = None) -> dict:
        body = None if data is None else urlencode(data).encode("ascii")
        req = Request(self.base_url + path, data=body)
        try:
            with self._lock, self._opener.open(req, timeout=6) as response:
                result = json.loads(response.read(1024 * 1024))
        except HTTPError as err:
            if err.code in (401, 403):
                raise InvalidAuth("Authentication rejected") from None
            raise ToshibaError(f"TV returned HTTP {err.code}") from None
        except URLError, OSError, TimeoutError:
            raise CannotConnect("TV did not respond") from None
        except ValueError, UnicodeError:
            raise ToshibaError("TV returned an invalid JSON response") from None
        if not isinstance(result, dict) or result.get("status") != 0:
            raise ToshibaError("TV rejected the request")
        return result

    def feature(self) -> dict:
        return self.request("/public/feature")

    def start_pairing(self, user_id: str) -> dict:
        challenge = self.request("/v2/public/request_connection", {"user_id": user_id})
        if not all(isinstance(challenge.get(k), str) for k in ("salt", "password")):
            raise ToshibaError("TV did not supply a PIN pairing challenge")
        return challenge

    def confirm_pairing(self) -> None:
        self.request("/v2/remote/confirm_connection", {})

    def status(self) -> dict:
        result = self.request("/v2/remote/status")
        if result.get("power") not in ("on", "off"):
            raise ToshibaError("TV returned an invalid power state")
        return result

    def send_key(self, key: str) -> None:
        self.request("/v2/remote/remote", {"key": key})

    def select_input(self, source: str) -> None:
        self.request("/v2/remote/status/external_input", {"external_input": source})
