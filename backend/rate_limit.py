"""
Rate limits for endpoints that spend money (Anthropic API calls) or a
third-party quota (Adzuna job search).

Once the site is public, anyone can call these, and every AI call is billed
to the site owner's API key. Two layers:
  - per visitor (by IP): a short burst window and a daily allowance;
  - site-wide: a daily cap on AI calls, so even many visitors can't run up
    an unbounded bill.

Counters live in memory, which suits a single server instance (like Render's
free tier). They reset when the server restarts; that's acceptable for abuse
protection. Set a monthly spend limit in the Anthropic console too: this is a
backstop, not a billing control.
"""

import os
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

PER_IP_BURST = int(os.environ.get("AI_PER_IP_BURST", "20"))          # per 10 minutes
PER_IP_DAILY = int(os.environ.get("AI_PER_IP_DAILY", "100"))
SITE_DAILY = int(os.environ.get("AI_SITE_DAILY", "1000"))
BURST_WINDOW = 10 * 60
DAY = 24 * 60 * 60

_lock = threading.Lock()
_hits = defaultdict(deque)          # (bucket, ip) -> timestamps within the last day
_site_hits = defaultdict(deque)     # bucket -> timestamps within the last day


def client_ip(request: Request) -> str:
    # Hosts like Render put the real client first in X-Forwarded-For.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check(bucket: str, request: Request, burst: int, daily: int, site_daily: int | None):
    now = time.time()
    ip = client_ip(request)
    with _lock:
        hits = _hits[(bucket, ip)]
        while hits and now - hits[0] > DAY:
            hits.popleft()
        recent = sum(1 for t in hits if now - t <= BURST_WINDOW)
        if recent >= burst:
            raise HTTPException(status_code=429, detail="You're going a bit fast. Please wait a few minutes and try again.")
        if len(hits) >= daily:
            raise HTTPException(status_code=429, detail="You've reached today's limit for this feature. It resets within 24 hours.")
        if site_daily is not None:
            site = _site_hits[bucket]
            while site and now - site[0] > DAY:
                site.popleft()
            if len(site) >= site_daily:
                raise HTTPException(status_code=503, detail="This feature has hit its daily usage cap. Please try again tomorrow.")
            site.append(now)
        hits.append(now)


def limit_ai(request: Request):
    """FastAPI dependency for endpoints that call the Anthropic API."""
    _check("ai", request, PER_IP_BURST, PER_IP_DAILY, SITE_DAILY)


def limit_jobs(request: Request):
    """FastAPI dependency for the Adzuna-backed job search (shared API quota)."""
    _check("jobs", request, burst=40, daily=300, site_daily=None)


def reset_for_tests():
    with _lock:
        _hits.clear()
        _site_hits.clear()
