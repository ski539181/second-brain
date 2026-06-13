"""
FTScraper.py - Production-grade web scraper for Cloudflare-protected sites

Based on the 2025-26 Cloudflare bypass brief (notes.md §Cloudflare 2025-26):
  - Primary: patchright (browser-based, CDP-level leak patches)
  - Secondary: camoufox (Firefox-based)
  - HTTP-only: curl_cffi (TLS fingerprint impersonation) ← this file

Why curl_cffi?
  - Pure Python, no browser binary needed
  - Impersonates real browser TLS/HTTP2 fingerprints (bypasses CF TLS checks)
  - Works on Termux (no libgtk dependency)
  - Fastest of the three (~10x faster than browser)
  - Tradeoff: cannot execute JS, so miss JS-rendered content
    → Use browser-based for SPA sites, curl_cffi for static/semi-dynamic

Usage:
    from FTScraper import FTScraper
    with FTScraper() as s:
        result = s.get('https://example.com')
        result = s.get('https://example.com', selector='h1', extract='text')

CLI:
    python FTScraper.py <url> [selector] [--impersonate chrome]
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    from curl_cffi import requests as cffi_requests
    from curl_cffi.requests.exceptions import RequestException
except ImportError as e:
    print(f"❌ curl_cffi not installed: {e}", file=sys.stderr)
    print("   Run: pip install curl_cffi", file=sys.stderr)
    sys.exit(1)


# Available impersonation targets (curl_cffi 0.15.0+)
IMPERSONATE_TARGETS = [
    "chrome", "chrome99", "chrome100", "chrome101", "chrome104", "chrome107",
    "chrome110", "chrome116", "chrome119", "chrome120", "chrome123", "chrome124",
    "chrome131", "chrome133a", "chrome136",
    "edge", "edge99", "edge101", "edge122", "edge127",
    "safari", "safari15_3", "safari15_5", "safari17_0", "safari17_2_ios",
    "firefox", "firefox109", "firefox117", "firefox128", "firefox133",
    "tor",
]


@dataclass
class ScrapeResult:
    """Result of a scrape operation."""
    ok: bool
    url: str
    status: int = 0
    elapsed: float = 0.0
    title: str = ''
    text: str = ''
    html: str = ''
    data: Any = None
    cookies: dict = field(default_factory=dict)
    error: str = ''
    method: str = 'curl_cffi'  # for future multi-method support

    def to_dict(self) -> dict:
        return {
            'ok': self.ok,
            'url': self.url,
            'status': self.status,
            'elapsed': round(self.elapsed, 3),
            'title': self.title[:200] if self.title else '',
            'text_len': len(self.text),
            'html_len': len(self.html),
            'data': self.data,
            'error': self.error,
            'method': self.method,
        }


class FTScraper:
    """Cloudflare-resistant HTTP scraper using curl_cffi TLS impersonation.

    Parameters
    ----------
    impersonate : str
        Browser to impersonate. Default: 'chrome124' (stable, widely accepted).
    timeout : float
        Request timeout in seconds. Default: 30.
    retries : int
        Number of retry attempts on failure. Default: 3.
    backoff : float
        Initial backoff between retries (multiplied by attempt). Default: 1.0.
    headers : dict
        Extra HTTP headers to send.
    proxy : str, optional
        Proxy URL (http://, https://, socks5://).
    follow_redirects : bool
        Follow HTTP redirects. Default: True.
    """

    DEFAULT_HEADERS = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
    }

    def __init__(
        self,
        impersonate: str = 'chrome124',
        timeout: float = 30.0,
        retries: int = 3,
        backoff: float = 1.0,
        headers: Optional[dict] = None,
        proxy: Optional[str] = None,
        follow_redirects: bool = True,
    ):
        if impersonate not in IMPERSONATE_TARGETS:
            raise ValueError(
                f"Unknown impersonate target: {impersonate!r}. "
                f"Choose from: {IMPERSONATE_TARGETS[:10]}..."
            )
        self.impersonate = impersonate
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.proxy = proxy
        self.follow_redirects = follow_redirects
        self.session: Optional[cffi_requests.Session] = None
        self._merged_headers = {**self.DEFAULT_HEADERS, **(headers or {})}

    def __enter__(self) -> 'FTScraper':
        self._open_session()
        return self

    def __exit__(self, *exc) -> None:
        self._close_session()

    def _open_session(self) -> None:
        """Initialize the curl_cffi session with cookie persistence."""
        self.session = cffi_requests.Session()
        # Note: cookies persist in session across requests

    def _close_session(self) -> None:
        """Cleanly close the session."""
        if self.session:
            try:
                self.session.close()
            except Exception:
                pass
            self.session = None

    def _request_with_retry(self, method: str, url: str, **kwargs) -> cffi_requests.Response:
        """Execute request with exponential backoff retry."""
        if not self.session:
            self._open_session()

        last_exc: Optional[Exception] = None
        for attempt in range(self.retries):
            try:
                resp = self.session.request(
                    method, url,
                    impersonate=self.impersonate,
                    timeout=self.timeout,
                    allow_redirects=self.follow_redirects,
                    proxy=self.proxy,
                    **kwargs,
                )
                return resp
            except RequestException as e:
                last_exc = e
                if attempt < self.retries - 1:
                    wait = self.backoff * (2 ** attempt)
                    time.sleep(wait)
        raise last_exc  # type: ignore[misc]

    def get(self, url: str, selector: Optional[str] = None,
            extract: str = 'auto', **kwargs) -> ScrapeResult:
        """Scrape a URL.

        Parameters
        ----------
        url : str
            Target URL.
        selector : str, optional
            CSS selector. If provided, returns matching elements.
        extract : str
            'auto' (default), 'text', 'html', or 'data' (selector result).
        **kwargs
            Extra arguments to pass to session.get().
        """
        start = time.monotonic()
        try:
            resp = self._request_with_retry('GET', url, headers=self._merged_headers, **kwargs)
            elapsed = time.monotonic() - start

            if resp.status_code >= 400:
                return ScrapeResult(
                    ok=False, url=url, status=resp.status_code, elapsed=elapsed,
                    error=f"HTTP {resp.status_code}",
                )

            html = resp.text
            title = self._extract_title(html)
            text = self._extract_text(html)

            data = None
            if selector:
                data = self._extract_by_selector(html, selector)

            return ScrapeResult(
                ok=True, url=url, status=resp.status_code, elapsed=elapsed,
                title=title, text=text, html=html, data=data,
                cookies=dict(self.session.cookies) if self.session else {},
            )
        except Exception as e:
            return ScrapeResult(
                ok=False, url=url, elapsed=time.monotonic() - start,
                error=f"{type(e).__name__}: {e}",
            )

    def post(self, url: str, data: Optional[dict] = None,
             json_body: Optional[dict] = None, **kwargs) -> ScrapeResult:
        """POST request with same retry/TLS handling."""
        start = time.monotonic()
        try:
            kwargs.setdefault('headers', {}).update(self._merged_headers)
            resp = self._request_with_retry('POST', url, data=data, json=json_body, **kwargs)
            return ScrapeResult(
                ok=resp.status_code < 400,
                url=url, status=resp.status_code,
                elapsed=time.monotonic() - start,
                title=self._extract_title(resp.text),
                text=self._extract_text(resp.text),
                html=resp.text,
                error='' if resp.status_code < 400 else f"HTTP {resp.status_code}",
            )
        except Exception as e:
            return ScrapeResult(
                ok=False, url=url, elapsed=time.monotonic() - start,
                error=f"{type(e).__name__}: {e}",
            )

    @staticmethod
    def _extract_title(html: str) -> str:
        """Extract <title> from HTML."""
        m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else ''

    @staticmethod
    def _extract_text(html: str) -> str:
        """Extract visible text from HTML (rough but effective)."""
        # Remove script/style
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.IGNORECASE | re.DOTALL)
        # Strip tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Decode common entities
        text = (text.replace('&nbsp;', ' ')
                   .replace('&amp;', '&')
                   .replace('&lt;', '<')
                   .replace('&gt;', '>')
                   .replace('&quot;', '"')
                   .replace('&#39;', "'"))
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def _extract_by_selector(html: str, selector: str) -> list[str]:
        """Simple CSS selector extraction (subset: tag, .class, #id, attr)."""
        # Note: For complex selectors, use BeautifulSoup. This is a fast rough impl.
        if selector.startswith('#'):
            pattern = rf'id="{selector[1:]}"[^>]*>(.*?)</'
        elif selector.startswith('.'):
            pattern = rf'class="[^"]*{selector[1:]}[^"]*"[^>]*>(.*?)</'
        elif '[' in selector:
            # attr selector (very rough)
            m = re.match(r'(\w+)\[(\w+)=["\']?([^"\']+)["\']?\]', selector)
            if m:
                tag, attr, val = m.groups()
                pattern = rf'<{tag}[^>]*{attr}="{val}"[^>]*>(.*?)</{tag}>'
            else:
                return []
        else:
            pattern = rf'<{selector}[^>]*>(.*?)</{selector}>'

        return [m.group(1).strip() for m in re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)]


# ============ CLI ============

def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print("Usage: python FTScraper.py <url> [selector] [--impersonate chrome124]")
        print(f"\nAvailable impersonate targets ({len(IMPERSONATE_TARGETS)}):")
        for t in IMPERSONATE_TARGETS[:8]:
            print(f"  - {t}")
        print("  ... and more")
        return 0

    url = sys.argv[1]
    selector = None
    impersonate = 'chrome124'

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == '--impersonate' and i + 1 < len(args):
            impersonate = args[i + 1]
            i += 2
        elif a.startswith('--impersonate='):
            impersonate = a.split('=', 1)[1]
            i += 1
        else:
            selector = a
            i += 1

    print(f"🧪 FTScraper | impersonate={impersonate} | url={url}")
    if selector:
        print(f"   selector={selector}")

    with FTScraper(impersonate=impersonate) as s:
        result = s.get(url, selector=selector)

    print(f"\n📊 Result:")
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False)[:2000])
    if result.data:
        print(f"\n🎯 Selector data ({len(result.data)} items):")
        for i, item in enumerate(result.data[:5]):
            print(f"  [{i}] {item[:200]}")
    if result.text and not selector:
        print(f"\n📝 Text preview (first 500 chars):")
        print(f"  {result.text[:500]}")
    return 0 if result.ok else 1


if __name__ == '__main__':
    sys.exit(main())
