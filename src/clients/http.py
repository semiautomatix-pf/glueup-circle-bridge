import os
import time
import json
from typing import Any, Dict, Optional
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

DEFAULT_TIMEOUT = 30

class HttpError(Exception):
    def __init__(self, status: int, body: Any):
        super().__init__(f"HTTP {status}: {body}")
        self.status = status
        self.body = body

class HttpClient:
    def __init__(self, base_url: str, headers: Optional[Dict[str, str]] = None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(headers or {})

    def _url(self, path: str) -> str:
        return self.base_url + ("" if path.startswith("/") else "/") + path

    @retry(
        reraise=True,
        retry=retry_if_exception_type((HttpError, requests.RequestException)),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        stop=stop_after_attempt(5),
    )
    def request(self, method: str, path: str, *, params: Optional[Dict[str, Any]] = None, json_body: Any = None) -> Dict[str, Any]:
        url = self._url(path)
        resp = self.session.request(method, url, params=params, json=json_body, timeout=DEFAULT_TIMEOUT)
        if resp.status_code >= 400:
            # surface body for visibility
            raise HttpError(resp.status_code, resp.text)
        if not resp.content:
            return {}
        try:
            return resp.json()
        except Exception:
            return {"raw": resp.text}
