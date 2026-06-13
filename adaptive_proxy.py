#!/usr/bin/env python3
"""
Adaptive Reasoning Proxy
========================
A local OpenAI-compatible proxy that classifies each incoming prompt and
automatically sets reasoning_effort (low / medium / high) before forwarding
to the upstream provider.

Works with any OpenAI-compatible provider (TokenRouter, OpenAI, OpenRouter,
Anthropic-via-proxy, local llama.cpp, etc.) — just point your client at
http://localhost:8400/v1 instead of the real base URL.

Usage:
    adaptive-proxy [--port PORT] [--upstream URL] [--api-key KEY] [--upstream-model NAME]

Env vars (override CLI):
    ADAPTIVE_PORT        (default 8400)
    ADAPTIVE_UPSTREAM    (required, e.g. https://api.tokenrouter.com/v1)
    ADAPTIVE_API_KEY     (required)
    ADAPTIVE_MODEL       (optional, override model in forwarded requests)

Heuristic:
    - low    : short chat, greetings, simple lookups
    - medium : normal Q&A, code, explanations  (default)
    - high   : complex analysis, multi-step, math, debug, long prompts
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

# ----------------------------------------------------------------------------
# Heuristic classifier
# ----------------------------------------------------------------------------

# Keywords that strongly suggest deep reasoning is worth the token cost.
# Bilingual (Thai + English) because the user mixes both.
HIGH_SIGNALS_TH = [
    "วิเคราะห์", "อธิบายละเอียด", "เปรียบเทียบ", "พิสูจน์", "ออกแบบ",
    "วางแผน", "กลยุทธ์", "แก้ปัญหา", "debug", "ดีบัก", "optimize",
    "ปรับแต่ง", "ทำไมถึง", "อย่างไร", "ขั้นตอน", "หลายขั้น",
]
HIGH_SIGNALS_EN = [
    "analyze", "analyse", "explain in detail", "compare", "prove",
    "design", "architect", "strategy", "step by step", "step-by-step",
    "multi-step", "debug", "optimize", "refactor", "trade-off",
    "tradeoff", "evaluate", "assess", "implications", "reasoning",
    "pros and cons", "root cause", "why does", "how does", "complex",
]

LOW_SIGNALS_TH = ["สวัสดี", "หวัดดี", "ขอบคุณ", "โอเค", "ok ", "เออ",
                  "แปลว่า", "แปล ", "คืออะไร", "อะไรคือ", "เท่าไหร่"]
LOW_SIGNALS_EN = [
    "hello", "hi ", "hey", "thanks", "thank you", "bye",
    "translate", "what is", "define", "meaning of", "= ",
]

# Code-specific tokens (we surface these so the user can budget tokens).
CODE_TOKENS_TH = ["โค้ด", "โปรแกรม", "เขียน", "ฟังก์ชัน", "คลาส", "ไฟล์",
                  "รัน", "คอมไพล์", "import ", "def ", "class "]
CODE_TOKENS_EN = ["code", "function", "class ", "script", "compile",
                  "implement", "refactor", "bug ", "fix the", "write a"]

# Math / code markers that often warrant deeper reasoning.
CODE_OR_MATH = re.compile(
    r"(```|<code>|def\s+\w+\s*\(|class\s+\w+\s*[:(]|import\s+\w+|"
    r"function\s+\w+\s*\(|=>|\bO\([^)]*\)|"
    r"\\\[|\\\(|\$[^$]+\$|"
    r"\b\d+\s*[+\-*/^]\s*\d+|\btheorem\b|\blemma\b|\bproof\b)",
    re.IGNORECASE,
)

# (multi-question heuristic lives inline in classify() to keep things simple)


def extract_last_user_prompt(body: dict[str, Any]) -> str:
    """Pull the most recent user message text from a chat-completions payload."""
    msgs = body.get("messages") or []
    for m in reversed(msgs):
        if m.get("role") == "user":
            content = m.get("content", "")
            if isinstance(content, list):
                # multimodal: concatenate text parts
                return " ".join(
                    p.get("text", "") for p in content
                    if isinstance(p, dict) and p.get("type") in ("text", None)
                )
            return str(content or "")
    return ""


# Approximate reasoning-token cost per level (so users can budget).
COST_HINT = {
    "low":    "~1-2k tokens (trivial chitchat / lookup)",
    "medium": "~5-10k tokens (normal Q&A, explanations)",
    "high":   "~20-50k tokens (analysis, code, multi-step, math)",
}


def classify(prompt: str) -> tuple[str, str]:
    """Return (level, reason) for a user prompt.

    Reason is a short human-readable tag so the user can tell at a glance
    WHY the classifier chose the level — especially useful for code/math
    tasks that auto-escalate to HIGH.
    """
    p = (prompt or "").strip()
    plen = len(p)
    p_low = p.lower()

    if plen == 0:
        return "low", "empty"

    has_high = (
        any(s in p for s in HIGH_SIGNALS_TH)
        or any(s in p_low for s in HIGH_SIGNALS_EN)
        or bool(CODE_OR_MATH.search(p))
    )
    has_low = (
        any(s in p for s in LOW_SIGNALS_TH)
        or any(s in p_low for s in LOW_SIGNALS_EN)
    )

    # --- HIGH branch: pick the most informative reason
    if has_high:
        if CODE_OR_MATH.search(p):
            # Differentiate code vs math for the user
            code_match = bool(re.search(
                r"```|<code>|def\s+\w+\s*\(|class\s+\w+\s*[:(]|"
                r"import\s+\w+|function\s+\w+\s*\(|=>",
                p, re.IGNORECASE,
            ))
            if code_match:
                return "high", "code"
            return "high", "math"
        if any(s in p for s in HIGH_SIGNALS_TH):
            return "high", "th-keyword"
        return "high", "en-keyword"

    if plen < 30 and not has_high:
        return "low", "short"

    if plen < 80 and has_low:
        return "low", "smalltalk"

    if plen > 800:
        return "high", "long-prompt"
    q_count = p.count("?") + p.count("？")
    if q_count >= 3:
        return "high", "multi-question"

    return "medium", "default"


# ----------------------------------------------------------------------------
# Proxy server
# ----------------------------------------------------------------------------

UPSTREAM = os.environ.get("ADAPTIVE_UPSTREAM", "").rstrip("/")
API_KEY = os.environ.get("ADAPTIVE_API_KEY", "")
MODEL_OVERRIDE = os.environ.get("ADAPTIVE_MODEL", "").strip()
FORCE_LEVEL = os.environ.get("ADAPTIVE_FORCE_LEVEL", "").strip().lower()  # low/medium/high/""
VERBOSE = os.environ.get("ADAPTIVE_VERBOSE", "0") == "1"


class ProxyHandler(BaseHTTPRequestHandler):
    server_version = "AdaptiveReasoningProxy/1.0"

    # Silence default access log unless verbose
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """log_message - TODO: describe."""
        if VERBOSE:
            sys.stderr.write("%s - - [%s] %s\n" % (
                self.address_string(), self.log_date_time_string(), format % args))
        else:
            sys.stderr.write(".")

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0") or "0")
        return self.rfile.read(length) if length else b""

    def _forward(
        self,
        body: bytes,
        override_reasoning: str | None = None,
        adaptive_header: tuple[str, str, str] | None = None,
    ) -> None:
        # Parse and patch
        try:
            payload = json.loads(body or b"{}")
        except json.JSONDecodeError:
            payload = {}

        if override_reasoning is not None and "messages" in payload:
            payload["reasoning_effort"] = override_reasoning
        if MODEL_OVERRIDE and "model" in payload:
            payload["model"] = MODEL_OVERRIDE

        new_body = json.dumps(payload).encode("utf-8")

        # Build upstream URL, avoiding /v1/v1 duplication.
        base = UPSTREAM
        req_path = self.path
        if req_path.startswith("/v1/") and base.endswith("/v1"):
            base = base[:-3].rstrip("/")
        url = base + req_path
        req = urllib.request.Request(url, data=new_body, method=self.command)
        # Pass through most headers, override auth + content-length
        for h, v in self.headers.items():
            if h.lower() in ("host", "content-length", "authorization"):
                continue
            req.add_header(h, v)
        req.add_header("Authorization", f"Bearer {API_KEY}")
        req.add_header("Content-Type", "application/json")
        req.add_header("Content-Length", str(len(new_body)))

        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                resp_body = resp.read()
                self.send_response(resp.status)
                for h, v in resp.getheaders():
                    if h.lower() in ("transfer-encoding", "connection", "content-length"):
                        continue
                    self.send_header(h, v)
                # Surface adaptive reasoning decision to the client
                if adaptive_header is not None:
                    level, reason, cost = adaptive_header
                    self.send_header("X-Adaptive-Reasoning", level)
                    self.send_header("X-Adaptive-Reason", reason)
                    self.send_header("X-Adaptive-Cost-Hint", cost)
                self.send_header("Content-Length", str(len(resp_body)))
                self.end_headers()
                self.wfile.write(resp_body)
        except urllib.error.HTTPError as e:
            err_body = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            if adaptive_header is not None:
                level, reason, cost = adaptive_header
                self.send_header("X-Adaptive-Reasoning", level)
                self.send_header("X-Adaptive-Reason", reason)
                self.send_header("X-Adaptive-Cost-Hint", cost)
            self.send_header("Content-Length", str(len(err_body)))
            self.end_headers()
            self.wfile.write(err_body)
        except Exception as e:  # noqa: BLE001
            err = json.dumps({"error": f"proxy upstream error: {e!r}"}).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            if adaptive_header is not None:
                level, reason, cost = adaptive_header
                self.send_header("X-Adaptive-Reasoning", level)
                self.send_header("X-Adaptive-Reason", reason)
                self.send_header("X-Adaptive-Cost-Hint", cost)
            self.send_header("Content-Length", str(len(err)))
            self.end_headers()
            self.wfile.write(err)

    # --- POST /v1/chat/completions → classify + inject reasoning_effort
        """do_POST - TODO: describe."""
    def do_POST(self) -> None:  # noqa: N802
        body = self._read_body()
        adaptive_level = ""
        adaptive_reason = ""
        adaptive_cost = ""
        if "/chat/completions" in self.path:
            try:
                payload = json.loads(body or b"{}")
                prompt = extract_last_user_prompt(payload)
                if FORCE_LEVEL in ("low", "medium", "high"):
                    level = FORCE_LEVEL
                    reason = "FORCED"
                else:
                    level, reason = classify(prompt)
                # Respect client's explicit choice — only inject if absent
                if "reasoning_effort" not in payload or not payload["reasoning_effort"]:
                    payload["reasoning_effort"] = level
                    body = json.dumps(payload).encode("utf-8")
                adaptive_level = level
                adaptive_reason = reason
                adaptive_cost = COST_HINT.get(level, "")
                if VERBOSE:
                    sys.stderr.write(
                        f"\n[adaptive] {reason:14s} → {level.upper():6s} "
                        f"| {adaptive_cost} "
                        f"| len={len(prompt):4d} | preview={prompt[:50]!r}\n"
                    )
            except Exception as e:  # noqa: BLE001
                sys.stderr.write(f"\n[adaptive] classify error: {e!r}\n")
        self._forward(
            body,
            adaptive_header=(adaptive_level, adaptive_reason, adaptive_cost) if adaptive_level else None,
        )

    """do_GET - TODO: describe."""
    # --- GET /v1/models → advertise same model list as upstream
    def do_GET(self) -> None:  # noqa: N802
        if "/models" in self.path:
            self._forward(b"")
            return
        # Health check
        if self.path in ("/", "/health", "/healthz"):
            msg = json.dumps({
                "status": "ok",
                "upstream": UPSTREAM,
                "model_override": MODEL_OVERRIDE or None,
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
            return
        self._forward(b"")


def main() -> int:
    """main - TODO: describe."""
    global UPSTREAM, API_KEY, MODEL_OVERRIDE
    ap = argparse.ArgumentParser(description="Adaptive reasoning proxy")
    ap.add_argument("--port", type=int, default=int(os.environ.get("ADAPTIVE_PORT", "8400")))
    ap.add_argument("--upstream", default=os.environ.get("ADAPTIVE_UPSTREAM", ""))
    ap.add_argument("--api-key", default=os.environ.get("ADAPTIVE_API_KEY", ""))
    ap.add_argument("--upstream-model", default=os.environ.get("ADAPTIVE_MODEL", ""))
    ap.add_argument("--verbose", action="store_true",
                    help="Log classification decisions")
    ap.add_argument("--force", default=os.environ.get("ADAPTIVE_FORCE_LEVEL", ""),
                    choices=["", "low", "medium", "high"],
                    help="Force a fixed reasoning_effort (skips adaptive classification)")
    args = ap.parse_args()

    UPSTREAM = (args.upstream or UPSTREAM).rstrip("/")
    API_KEY = args.api_key or API_KEY
    MODEL_OVERRIDE = args.upstream_model or MODEL_OVERRIDE
    if args.verbose:
        global VERBOSE
        VERBOSE = True
    if args.force:
        global FORCE_LEVEL
        FORCE_LEVEL = args.force

    if not UPSTREAM:
        print("error: --upstream / ADAPTIVE_UPSTREAM is required", file=sys.stderr)
        return 2
    if not API_KEY:
        print("error: --api-key / ADAPTIVE_API_KEY is required", file=sys.stderr)
        return 2

    print(f"[adaptive] upstream = {UPSTREAM}", file=sys.stderr)
    print(f"[adaptive] model    = {MODEL_OVERRIDE or '(passthrough)'}", file=sys.stderr)
    print(f"[adaptive] force    = {FORCE_LEVEL or '(adaptive)'}", file=sys.stderr)
    print(f"[adaptive] listen   = http://127.0.0.1:{args.port}/v1", file=sys.stderr)
    print(
        f"[adaptive] hint: point your client's base_url to "
        f"http://127.0.0.1:{args.port}/v1 (or just /) — auto-strips /v1 suffix to avoid double-prefix",
        file=sys.stderr,
    )

    srv = ThreadingHTTPServer(("127.0.0.1", args.port), ProxyHandler)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[adaptive] shutting down", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
