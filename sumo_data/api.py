from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ApiError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class FetchResult:
    payload: Any
    cache_path: Path
    from_cache: bool


class SumoApiClient:
    def __init__(
        self,
        data_dir: Path,
        *,
        base_url: str = "https://www.sumo-api.com",
        timeout: int = 30,
        polite_delay: float = 0.2,
        user_agent: str = "sumo-data-foundation/0.1",
    ) -> None:
        self.data_dir = Path(data_dir)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.polite_delay = polite_delay
        self.user_agent = user_agent
        self.api_raw_dir = self.data_dir / "raw" / "sumo_api"
        self.jsa_raw_dir = self.data_dir / "raw" / "jsa_profiles"
        self.api_raw_dir.mkdir(parents=True, exist_ok=True)
        self.jsa_raw_dir.mkdir(parents=True, exist_ok=True)

    def fetch_json(
        self,
        endpoint: str,
        *,
        query: dict[str, Any] | None = None,
        force: bool = False,
        required: bool = True,
    ) -> FetchResult | None:
        cache_path = self._api_cache_path(endpoint, query)
        if cache_path.exists() and not force:
            return FetchResult(
                payload=json.loads(cache_path.read_text(encoding="utf-8")),
                cache_path=cache_path,
                from_cache=True,
            )

        url = self._url(endpoint, query)
        request = Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                text = response.read().decode("utf-8")
        except HTTPError as exc:
            if not required and exc.code in {400, 404}:
                return None
            raise ApiError(f"GET {url} failed with HTTP {exc.code}", status=exc.code) from exc
        except URLError as exc:
            raise ApiError(f"GET {url} failed: {exc.reason}") from exc

        cache_path.write_text(text, encoding="utf-8")
        if self.polite_delay:
            time.sleep(self.polite_delay)
        return FetchResult(payload=json.loads(text), cache_path=cache_path, from_cache=False)

    def fetch_jsa_profile(
        self,
        nsk_id: int,
        *,
        force: bool = False,
        required: bool = False,
    ) -> tuple[str | None, Path, int | None]:
        cache_path = self.jsa_raw_dir / f"profile_{nsk_id}.html"
        if cache_path.exists() and not force:
            return cache_path.read_text(encoding="utf-8", errors="replace"), cache_path, None

        url = f"https://www.sumo.or.jp/EnSumoDataRikishi/profile/{nsk_id}/"
        request = Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                status = getattr(response, "status", None)
        except HTTPError as exc:
            if not required and exc.code in {400, 404}:
                return None, cache_path, exc.code
            raise ApiError(f"GET {url} failed with HTTP {exc.code}", status=exc.code) from exc
        except URLError as exc:
            if not required:
                return None, cache_path, None
            raise ApiError(f"GET {url} failed: {exc.reason}") from exc

        cache_path.write_text(body, encoding="utf-8")
        if self.polite_delay:
            time.sleep(self.polite_delay)
        return body, cache_path, status

    def _url(self, endpoint: str, query: dict[str, Any] | None) -> str:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        if query:
            url = f"{url}?{urlencode(query)}"
        return url

    def _api_cache_path(self, endpoint: str, query: dict[str, Any] | None) -> Path:
        slug = endpoint.strip("/").replace("/", "__")
        if query:
            query_slug = urlencode(sorted(query.items())).replace("&", "__").replace("=", "-")
            slug = f"{slug}__{query_slug}"
        return self.api_raw_dir / f"{slug}.json"
