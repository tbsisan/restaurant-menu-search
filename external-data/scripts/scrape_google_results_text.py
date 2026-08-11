#!/usr/bin/env python3
"""Search Google through a running camofox-browser server and save text results."""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = ROOT / "external-data/google-results"
DEFAULT_PORT = 9377
DEFAULT_LATITUDE = 42.19351025
DEFAULT_LONGITUDE = -83.1795100375
DEFAULT_TIMEZONE = "America/Detroit"
DEFAULT_LOCALE = "en-US"


EXTRACT_JS = r"""
(() => {
  const clean = (value) => String(value || "").replace(/\s+/g, " ").trim();
  const unwrapGoogleUrl = (href) => {
    try {
      const url = new URL(href, location.href);
      if (url.hostname.endsWith("google.com") && url.pathname === "/url") {
        return url.searchParams.get("q") || url.searchParams.get("url") || url.href;
      }
      return url.href;
    } catch {
      return href || "";
    }
  };

  const results = [];
  const seen = new Set();
  for (const h3 of Array.from(document.querySelectorAll("h3"))) {
    const link = h3.closest("a") || h3.parentElement?.closest("a");
    if (!link || !link.href) continue;

    const href = unwrapGoogleUrl(link.href);
    if (!href || /(^|\/\/)(www\.)?google\./i.test(href)) continue;

    let container = h3.closest("div[data-sokoban-container]") || h3.closest("div.g") || h3.parentElement;
    for (let i = 0; container && i < 4; i += 1) {
      const text = clean(container.innerText);
      if (text.length > 80) break;
      container = container.parentElement;
    }

    const title = clean(h3.innerText);
    const text = clean(container?.innerText || title);
    const key = `${title}\n${href}`;
    if (!title || seen.has(key)) continue;
    seen.add(key);

    results.push({
      index: results.length + 1,
      title,
      url: href,
      text,
    });
  }

  return {
    url: location.href,
    title: document.title,
    result_count: results.length,
    results,
    body_text: clean(document.body ? document.body.innerText : "").slice(0, 20000),
  };
})()
"""


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:100] or "google-results"


def request_json(method: str, url: str, body: dict | None = None, timeout: int = 60) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def create_tab(args: argparse.Namespace, url: str) -> str:
    body = {
        "userId": args.user_id,
        "sessionKey": args.session_key,
        "url": url,
        "locale": args.locale,
        "timezoneId": args.timezone,
        "geolocation": {
            "latitude": args.latitude,
            "longitude": args.longitude,
        },
        "viewport": {
            "width": args.viewport_width,
            "height": args.viewport_height,
        },
    }
    response = request_json("POST", f"{args.base_url}/tabs", body=body, timeout=args.timeout)
    tab_id = response.get("tabId") or response.get("targetId")
    if not tab_id:
        raise RuntimeError(f"Could not find tab id in create-tab response: {response}")
    return tab_id


def navigate_google(args: argparse.Namespace, tab_id: str, page_index: int = 0) -> None:
    if page_index:
        url = "https://www.google.com/search?" + urllib.parse.urlencode(
            {"q": args.query, "start": page_index * 10}
        )
        body = {
            "userId": args.user_id,
            "url": url,
        }
        request_json("POST", f"{args.base_url}/tabs/{tab_id}/navigate", body=body, timeout=args.timeout)
        return

    body = {
        "userId": args.user_id,
        "macro": "@google_search",
        "query": args.query,
    }
    request_json("POST", f"{args.base_url}/tabs/{tab_id}/navigate", body=body, timeout=args.timeout)


def evaluate(args: argparse.Namespace, tab_id: str) -> dict:
    body = {
        "userId": args.user_id,
        "expression": EXTRACT_JS,
        "timeout": args.timeout * 1000,
    }
    response = request_json("POST", f"{args.base_url}/tabs/{tab_id}/evaluate", body=body, timeout=args.timeout)
    return (
        response.get("result", {}).get("value")
        or response.get("value")
        or response.get("result")
        or response
    )


def render_markdown(query: str, data: dict) -> str:
    lines = [
        f"# Google Results: {query}",
        "",
        f"Pages captured: {len(data.get('pages') or [])}",
        f"Total parsed results: {len(data.get('results') or [])}",
        "",
    ]
    results = data.get("results") or []
    if results:
        for result in results:
            lines.extend(
                [
                    f"## {result.get('index')}. {result.get('title', '')}",
                    "",
                    f"Page: {result.get('page', '')}",
                    "",
                    str(result.get("url", "")),
                    "",
                    str(result.get("text", "")).strip(),
                    "",
                ]
            )
    else:
        lines.extend(
            [
                "## No Parsed Results",
                "",
                "The page did not expose normal Google result headings. Body text follows for debugging.",
                "",
                "\n\n".join(str(page.get("body_text", "")) for page in data.get("pages", [])),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="?", help="Google search query")
    parser.add_argument("--query", dest="query_option", help="Google search query")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-prefix")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--user-id", default="restaurant-menu-search-google")
    parser.add_argument("--session-key", default="google-search")
    parser.add_argument("--latitude", type=float, default=DEFAULT_LATITUDE)
    parser.add_argument("--longitude", type=float, default=DEFAULT_LONGITUDE)
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    parser.add_argument("--locale", default=DEFAULT_LOCALE)
    parser.add_argument("--viewport-width", type=int, default=1365)
    parser.add_argument("--viewport-height", type=int, default=900)
    parser.add_argument("--wait", type=float, default=8.0)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--pages", type=int, default=1, help="Number of Google result pages to capture.")
    args = parser.parse_args()

    args.query = args.query_option or args.query
    if not args.query:
        raise SystemExit("Provide a query as an argument or with --query")

    args.base_url = f"http://{args.host}:{args.port}"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    prefix = args.output_prefix or slugify(args.query)
    run_output_dir = args.output_dir / prefix
    run_output_dir.mkdir(parents=True, exist_ok=True)

    if args.pages < 1:
        raise SystemExit("--pages must be at least 1")

    search_url = "https://www.google.com/search?q=" + urllib.parse.quote(args.query)
    try:
        tab_id = create_tab(args, search_url)
        pages = []
        combined_results = []
        seen = set()
        for page_index in range(args.pages):
            if page_index:
                navigate_google(args, tab_id, page_index=page_index)
            time.sleep(args.wait)
            page_data = evaluate(args, tab_id)
            page_data["page"] = page_index + 1
            pages.append(page_data)
            for result in page_data.get("results") or []:
                key = (result.get("title"), result.get("url"))
                if key in seen:
                    continue
                seen.add(key)
                result = dict(result)
                result["page"] = page_index + 1
                result["index"] = len(combined_results) + 1
                combined_results.append(result)
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Could not reach camofox-browser at {args.base_url}: {exc}\n"
            "Start it with: CAMOFOX_HUMANIZE=true camofox server start --background"
        )

    data = {
        "query": args.query,
        "tab_id": tab_id,
        "requested_url": search_url,
        "pages_requested": args.pages,
        "pages": pages,
        "results": combined_results,
    }
    json_path = run_output_dir / f"{prefix}.json"
    md_path = run_output_dir / f"{prefix}.md"
    txt_path = run_output_dir / f"{prefix}.txt"

    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown = render_markdown(args.query, data)
    md_path.write_text(markdown, encoding="utf-8")
    txt_path.write_text(markdown, encoding="utf-8")

    print(f"Wrote {md_path}")
    print(f"Wrote {txt_path}")
    print(f"Wrote {json_path}")


if __name__ == "__main__":
    main()
