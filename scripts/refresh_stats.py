#!/usr/bin/env python3
"""Refresh verified, local GitHub activity SVG snapshots.

This script has no scheduler and no account-specific defaults. A missing
username, or the explicit ``REPLACE_WITH_MY_USERNAME`` placeholder, only
renders the local unconfigured card and never makes a network request.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable, Mapping, Optional


ROOT = Path(__file__).resolve().parents[1]
README_NAME = "README.md"
START_MARKER = "<!-- GITHUB-SNAPSHOTS:START -->"
END_MARKER = "<!-- GITHUB-SNAPSHOTS:END -->"
PLACEHOLDER = "REPLACE_WITH_MY_USERNAME"

MAX_BYTES = 1_500_000
TIMEOUT_SECONDS = 15
MAX_REQUESTS = 4

SNAPSHOT_FILES = {
    "stats": "stats.svg",
    "languages": "languages.svg",
    "streak": "streak.svg",
    "activity": "activity.svg",
}

ALLOWED_HOSTS = {
    "github-stats-extended.vercel.app",
    "streak-stats.demolab.com",
    "github-profile-summary-cards.vercel.app",
}

ERROR_MARKERS = (
    "something went wrong",
    "error fetching",
    "error loading",
    "failed to fetch",
    "failed to load",
    "unable to fetch",
    "unable to load",
    "couldn't fetch",
    "could not load",
    "user not found",
    "invalid username",
    "invalid user",
    "invalid response",
    "service unavailable",
    "temporarily unavailable",
    "api error",
    "rate limit",
    "not found",
    "could not fetch",
)

USERNAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
FORBIDDEN_TAGS = {
    "script",
    "foreignobject",
    "iframe",
    "object",
    "embed",
    "animate",
    "animatemotion",
    "animatetransform",
    "set",
}
EXTERNAL_URL_RE = re.compile(r"(?:https?:|//|data:|javascript:)", re.IGNORECASE)


class RefreshError(Exception):
    """An expected refresh or file-validation failure."""


def _query(params: Mapping[str, object]) -> str:
    """Encode service parameters with percent-encoded spaces and symbols."""

    return urllib.parse.urlencode(
        list(params.items()), quote_via=urllib.parse.quote, safe=""
    )


def build_urls(username: str) -> dict[str, str]:
    """Return documented SVG endpoints for one validated GitHub handle."""

    common = {
        "theme": "dark",
        "bg_color": "080A0F",
        "title_color": "FF2638",
        "text_color": "F3F5F7",
        "icon_color": "45C7FF",
        "border_color": "0B1220",
        "hide_border": "true",
        "disable_animations": "true",
    }
    stats = {"username": username, **common, "show_icons": "true", "hide_rank": "true"}
    languages = {
        "username": username,
        **common,
        "layout": "compact",
        "langs_count": "8",
        "custom_title": "Most Used Languages",
        "prog_bar_bg_color": "0B1220",
    }
    streak = {
        "user": username,
        "theme": "dark",
        "background": "080A0F",
        "border": "0B1220",
        "stroke": "0B1220",
        "ring": "FF2638",
        "fire": "45C7FF",
        "currStreakNum": "F3F5F7",
        "sideNums": "F3F5F7",
        "currStreakLabel": "FF2638",
        "sideLabels": "929BAA",
        "dates": "929BAA",
        "hide_border": "true",
        "disable_animations": "true",
    }
    activity = {
        "username": username,
        "theme": "github_dark",
        "bg_color": "080A0F",
        "title_color": "FF2638",
        "text_color": "F3F5F7",
        "icon_color": "45C7FF",
        "border_color": "0B1220",
        "chart_color": "FF2638",
        "animation": "none",
    }
    return {
        "stats": "https://github-stats-extended.vercel.app/api?" + _query(stats),
        "languages": "https://github-stats-extended.vercel.app/api/top-langs/?" + _query(languages),
        "streak": "https://streak-stats.demolab.com/?" + _query(streak),
        "activity": "https://github-profile-summary-cards.vercel.app/api/cards/profile-details?" + _query(activity),
    }


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def validate_svg(payload: bytes) -> None:
    """Reject non-SVG, service-error, executable, or externally-linked SVG."""

    if not payload or len(payload) > MAX_BYTES:
        raise RefreshError("empty or oversized response")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise RefreshError("response is not UTF-8 SVG") from exc
    lowered = text.lower()
    if "\x00" in text or "<!doctype" in lowered or "<!entity" in lowered:
        raise RefreshError("SVG contains a forbidden XML declaration")
    if re.search(r"<\s*(?:script|foreignobject|iframe|object|embed)\b", text, re.I):
        raise RefreshError("SVG contains executable or embedded content")
    if re.search(
        r"(?:javascript:|data:|@import|url\s*\(\s*(?:['\"]?(?:https?:|//)))",
        text,
        re.I,
    ):
        raise RefreshError("SVG contains an external dependency")
    for resource in re.findall(r"url\s*\(\s*['\"]?([^'\"\s)]+)", text, re.I):
        if not resource.startswith("#"):
            raise RefreshError("SVG contains an external dependency")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise RefreshError("response is not well-formed SVG") from exc
    if _local_name(root.tag) != "svg":
        raise RefreshError("response root is not SVG")
    visible_text = " ".join(" ".join(root.itertext()).split()).lower()
    if any(marker in visible_text for marker in ERROR_MARKERS) or re.match(
        r"^(?:error|failed|failure)\b", visible_text
    ):
        raise RefreshError("service returned an error card")
    for element in root.iter():
        tag = _local_name(element.tag)
        if tag in FORBIDDEN_TAGS:
            raise RefreshError("SVG contains forbidden embedded content")
        for name, value in element.attrib.items():
            attr = _local_name(name)
            value = value.strip()
            if attr.startswith("on"):
                raise RefreshError("SVG contains an event handler")
            if attr in {"href", "src"} and value and not value.startswith("#"):
                if EXTERNAL_URL_RE.search(value) or value.startswith("/"):
                    raise RefreshError("SVG contains an external link")
                raise RefreshError("SVG contains an unverified linked resource")
            if attr == "style" and re.search(
                r"url\s*\(\s*(?:['\"]?(?:https?:|//|data:|javascript:|/))",
                value,
                re.I,
            ):
                raise RefreshError("SVG style contains an external resource")


def _safe_path(root: Path, relative: str) -> Path:
    """Resolve a repository-relative path and refuse traversal."""

    root = root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise RefreshError(f"unsafe path: {relative}") from exc
    return candidate


def atomic_write(path: Path, payload: bytes) -> None:
    """Replace a file atomically using a temporary sibling."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _response_status(response: object) -> int:
    status = getattr(response, "status", None)
    if status is None and hasattr(response, "getcode"):
        status = response.getcode()  # type: ignore[union-attr]
    return int(status or 200)


def fetch_svg(
    url: str,
    opener: Optional[Callable[..., object]] = None,
) -> bytes:
    """Fetch one bounded response and validate its fixed service origin."""

    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise RefreshError("refusing an unapproved service URL")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "image/svg+xml",
            "User-Agent": "portfolio-github-snapshots/1",
        },
    )
    open_url = opener or urllib.request.urlopen
    response = None
    try:
        response = open_url(request, timeout=TIMEOUT_SECONDS)
        status = _response_status(response)
        if status >= 400:
            raise RefreshError(f"service returned HTTP {status}")
        final_url = getattr(response, "geturl", lambda: url)()
        final_host = urllib.parse.urlsplit(final_url).hostname
        if final_host not in ALLOWED_HOSTS:
            raise RefreshError("service redirected to an unapproved host")
        payload = response.read(MAX_BYTES + 1)  # type: ignore[union-attr]
    except RefreshError:
        raise
    except (OSError, urllib.error.URLError, ValueError, TypeError) as exc:
        raise RefreshError(str(exc) or "network request failed") from exc
    finally:
        if response is not None and hasattr(response, "close"):
            response.close()  # type: ignore[union-attr]
    validate_svg(payload)
    return payload


def normalize_username(username: Optional[str]) -> Optional[str]:
    """Return a usable handle, or ``None`` when the account is unconfigured."""

    if username is None or not username.strip():
        return None
    value = username.strip()
    if value == PLACEHOLDER:
        return None
    if not USERNAME_RE.fullmatch(value):
        raise RefreshError("username must be a GitHub handle (1-39 letters, digits, or hyphens)")
    return value


def verified_snapshots(root: Path) -> dict[str, Path]:
    """Return only existing, safe, locally valid snapshot files."""

    found: dict[str, Path] = {}
    for key, filename in SNAPSHOT_FILES.items():
        path = _safe_path(root, f"assets/github/{filename}")
        try:
            payload = path.read_bytes()
        except OSError:
            continue
        try:
            validate_svg(payload)
        except RefreshError:
            continue
        found[key] = path
    return found


def _snapshot_block(paths: Mapping[str, Path], fallback: Path, root: Path) -> str:
    labels = {
        "stats": "GitHub stats",
        "languages": "Most used languages",
        "streak": "Contribution streak",
        "activity": "GitHub activity graph",
    }
    rows = ["", "<div align=\"center\">", ""]
    for key, filename in SNAPSHOT_FILES.items():
        path = paths.get(key, fallback)
        relative = path.resolve().relative_to(root.resolve()).as_posix()
        rows.append(f'  <img src="{relative}" alt="{labels[key]}" />')
    rows.extend(["", "</div>", ""])
    return "\n".join(rows)


def update_readme(root: Path, paths: Mapping[str, Path]) -> None:
    """Replace only the exact managed snapshot region in ``README.md``."""

    readme = _safe_path(root, README_NAME)
    fallback = _safe_path(root, "assets/github/unconfigured.svg")
    try:
        validate_svg(fallback.read_bytes())
        text = readme.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise RefreshError(f"cannot read README or fallback card: {exc}") from exc
    if text.count(START_MARKER) != 1 or text.count(END_MARKER) != 1:
        raise RefreshError(
            "README.md must contain exactly one GITHUB-SNAPSHOTS start/end marker pair"
        )
    start = text.index(START_MARKER)
    end = text.index(END_MARKER)
    if end < start + len(START_MARKER):
        raise RefreshError("README snapshot markers are out of order")
    block = _snapshot_block(paths, fallback, root)
    updated = text[: start + len(START_MARKER)] + block + text[end:]
    if updated != text:
        atomic_write(readme, updated.encode("utf-8"))


def refresh(
    username: Optional[str],
    root: Path = ROOT,
    opener: Optional[Callable[..., object]] = None,
) -> list[str]:
    """Fetch once per card, preserve verified stale files, and update README.

    The returned list contains non-fatal errors. A failed service never writes
    over its previous local snapshot; the managed README region falls back to
    ``unconfigured.svg`` for missing or invalid cards.
    """

    root = root.resolve()
    configured = normalize_username(username)
    errors: list[str] = []
    paths = verified_snapshots(root)
    if configured is None:
        print("No GitHub username configured; skipped remote requests.")
    else:
        urls = build_urls(configured)
        for index, key in enumerate(SNAPSHOT_FILES):
            if index >= MAX_REQUESTS:
                break
            try:
                payload = fetch_svg(urls[key], opener=opener)
                destination = _safe_path(root, f"assets/github/{SNAPSHOT_FILES[key]}")
                atomic_write(destination, payload)
                paths[key] = destination
                print(f"updated {destination.relative_to(root)}")
            except (RefreshError, OSError) as exc:
                errors.append(f"{key}: {exc}")
                print(f"skipped {key}: {exc}", file=sys.stderr)
    try:
        update_readme(root, paths)
    except RefreshError as exc:
        errors.append(f"README: {exc}")
        print(f"skipped README: {exc}", file=sys.stderr)
    return errors


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download verified local GitHub activity SVG snapshots once."
    )
    parser.add_argument(
        "--username",
        metavar="REAL_HANDLE",
        help="GitHub username; omit or use REPLACE_WITH_MY_USERNAME to stay unconfigured",
    )
    args = parser.parse_args(argv)
    try:
        errors = refresh(args.username)
    except RefreshError as exc:
        print(f"refresh failed: {exc}", file=sys.stderr)
        return 2
    if errors:
        print(f"refresh completed with {len(errors)} error(s)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
