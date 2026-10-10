#!/usr/bin/env python3
"""Safely promote a complete, dated ChatGPT intelligence brief to GitHub main.

Requires no Supabase key or model API. Never changes the brief date or invents news.
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from zoneinfo import ZoneInfo

SITE = "https://edb-key-ai-accounts-daily-intelligence-briefs.pages.dev"
FIELDS = ("h", "u", "s", "d", "x", "o", "c", "m", "f")
THEMES = ("World & AI", "AI Trends & Trajectory", "APAC & AI", "Singapore & AI")
REQUIRED = ("Anthropic", "ElevenLabs", "AMI Labs", "Prometheus", "Datadog", "Manus AI", "Cognition AI")

def git(*args, check=True):
    p = subprocess.run(["git", *args], text=True, capture_output=True)
    if check and p.returncode:
        raise RuntimeError("git " + " ".join(args) + ": " + p.stderr[-1000:])
    return p

def section(src, field):
    match = re.search(r"\b" + re.escape(field) + r"\s*:\s*", src)
    if not match:
        raise ValueError("Missing " + field)
    return json.JSONDecoder().raw_decode(src[match.end():])[0]

def inspect(src, expected):
    date = re.search(r"\bdate\s*:\s*(['\"])(.*?)\1", src)
    if not date or date.group(2) != expected:
        raise ValueError("Brief is not dated " + expected)
    overview, world, apac, current = (section(src, x) for x in ("overview", "world", "apac", "current"))
    if not isinstance(overview, dict) or any(not overview.get(x) for x in THEMES):
        raise ValueError("Missing one or more overview themes")
    if len(world) < 2 or len(apac) < 2:
        raise ValueError("World/APAC require two lead stories each")
    if not isinstance(current, dict) or len(current) != 40:
        raise ValueError("Expected exactly 40 account stories")
    if any(name not in current for name in REQUIRED):
        raise ValueError("A required key account is missing")
    # Some previously generated briefs append verified More Reading in a
    # constant M rather than rewriting the main account object.
    extra = re.search(r"\bconst\s+M\s*=\s*", src)
    if extra:
        reading = json.JSONDecoder().raw_decode(src[extra.end():])[0]
        for name, entries in reading.items():
            if name in current:
                current[name]["m"] = [entry for entry in entries if entry[1] != current[name]["u"]][:5]
    for name, story in list(current.items()) + [(f"World {i}", v) for i, v in enumerate(world)] + [(f"APAC {i}", v) for i, v in enumerate(apac)]:
        needs = FIELDS if name in current else FIELDS[:7]
        if any(field not in story for field in needs):
            raise ValueError(name + ": missing analysis or metadata")
        if any(not isinstance(story[k], str) or not story[k].strip() for k in ("h", "u", "s", "d", "x", "o", "c")):
            raise ValueError(name + ": incomplete story or analysis")
        if not story["u"].startswith(("https://", "http://")):
            raise ValueError(name + ": invalid source URL")
        if name in current:
            if not isinstance(story["m"], list) or len(story["m"]) > 5:
                raise ValueError(name + ": invalid More Reading")
            for item in story["m"]:
                if len(item) < 4 or not item[1].startswith(("https://", "http://")):
                    raise ValueError(name + ": invalid More Reading link")
    return sum(not v["f"] for v in current.values()), sum(bool(v["m"]) for v in current.values())

def main():
    today = dt.datetime.now(ZoneInfo("Asia/Singapore")).date()
    expected = f"{today.day} {today.strftime('%b %Y')}"
    iso = today.isoformat()
    git("fetch", "origin", "--prune", "+refs/heads/*:refs/remotes/origin/*")
    baseline = git("show", "origin/main:data/latest.js").stdout
    try:
        fresh, reading = inspect(baseline, expected)
        print(f"Production already current: {expected}, {fresh} fresh-account leads, {reading} accounts with More Reading")
        return
    except ValueError as exc:
        print("Production needs refreshing:", exc)
    branches = git("branch", "-r", "--list", f"origin/daily-brief-{iso}*").stdout.splitlines()
    candidates = []
    for remote in branches:
        remote = remote.strip()
        if not re.fullmatch(r"origin/daily-brief-\d{4}-\d{2}-\d{2}[\w-]*", remote):
            continue
        result = git("show", f"{remote}:data/latest.js", check=False)
        if result.returncode:
            continue
        try:
            fresh, reading = inspect(result.stdout, expected)
            # Prefer fully prepared briefs and rich verified reading history.
            rank = (int(remote.endswith("-complete")), reading, fresh, int(git("log", "-1", "--format=%ct", remote).stdout.strip()))
            candidates.append((rank, remote, result.stdout))
        except (ValueError, json.JSONDecodeError) as exc:
            print("Skipped incomplete candidate", remote, "-", exc)
    if not candidates:
        raise RuntimeError("No complete " + expected + " brief on main or dated recovery branches. Intelligence generation has not published a valid candidate.")
    _, branch, content = max(candidates, key=lambda x: x[0])
    print("Publishing validated candidate:", branch)
    for attempt in range(3):
        git("fetch", "origin", "main")
        git("checkout", "-B", "main", "origin/main")
        with open("data/latest.js", "w", encoding="utf-8") as f:
            f.write(content)
        git("add", "data/latest.js")
        git("config", "user.name", "daily-brief-publisher[bot]")
        git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
        git("commit", "-m", f"Publish verified {expected} daily intelligence to production")
        pushed = git("push", "origin", "HEAD:main", check=False)
        if pushed.returncode == 0:
            break
        print("Push conflict; retrying", pushed.stderr[-500:])
        if attempt == 2:
            raise RuntimeError("Could not publish after three attempts")
        time.sleep(3)
    # Never treat a commit alone as live verification.
    for attempt in range(12):
        try:
            url = SITE + "/data/latest.js?verify=" + str(int(time.time()))
            request = urllib.request.Request(url, headers={"Cache-Control": "no-cache", "User-Agent": "DailyAIIntegrityCheck/1.0"})
            with urllib.request.urlopen(request, timeout=25) as response:
                live = response.read().decode("utf-8")
            inspect(live, expected)
            if live == content:
                print("VERIFIED: production Cloudflare site serves the exact current brief:", expected)
                return
        except Exception as exc:
            print("Deployment verification pending:", exc)
        time.sleep(15)
    raise RuntimeError("GitHub was updated but Cloudflare did not serve matching content within verification window")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("::error::Daily AI publication failed: " + str(exc), file=sys.stderr)
        sys.exit(1)
