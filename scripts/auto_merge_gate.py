#!/usr/bin/env python3
"""Gate de merge automatique — niveau de confiance CS27.

Merge en squash UNIQUEMENT si toutes les conditions sont réunies :
  1. Au moins une review APPROVED d'un HUMAIN (les bots ne comptent pas)
  2. Tous les checks de la CI sur le head sont success/skipped/neutral
  3. La PR ne touche aucune zone sensible

Zones sensibles (merge toujours manuel) :
  .github/, workflows, render.yaml, .env*, migrations, auth, guards,
  audit, openapi.yaml, schema.sql, .pr_agent.toml, .gitleaks.toml

Déclenché par : pull_request_review (submitted) et workflow_run (CI completed).
"""

import json
import os
import re
import subprocess
import sys

REPO = os.environ["GITHUB_REPOSITORY"]
EVENT = os.environ["GITHUB_EVENT_NAME"]
TOKEN = os.environ.get("GITHUB_TOKEN", "")

SENSITIVE = re.compile(
    r"(^|/)\.github/|(^|/)\.github$|render\.yaml|(^|/)\.env|"
    r"migrations?/|src/modules/auth/|src/common/(guards|audit)/|"
    r"openapi\.yaml|schema\.sql|\.pr_agent\.toml|\.gitleaks\.toml|"
    r"package(-lock)?\.json$"
)
BOT_LOGINS = {"github-actions[bot]", "github-actions", "dependabot[bot]"}


def gh_json(*args: str):
    env = dict(os.environ, GH_TOKEN=TOKEN)
    out = subprocess.run(
        ["gh", "api", *args], capture_output=True, text=True, env=env
    )
    if out.returncode != 0:
        print(f"gh api {' '.join(args)} -> {out.stderr.strip()}")
        return None
    return json.loads(out.stdout) if out.stdout.strip() else None


def gh(*args: str) -> str:
    env = dict(os.environ, GH_TOKEN=TOKEN)
    return subprocess.run(
        ["gh", *args], capture_output=True, text=True, env=env
    ).stdout


def find_pr(head_sha: str):
    data = gh_json(f"repos/{REPO}/commits/{head_sha}/pulls") or []
    open_prs = [p for p in data if p.get("state") == "open"]
    return open_prs[0]["number"] if open_prs else None


def main() -> int:
    if EVENT == "pull_request_review":
        pr = int(os.environ["PR_NUMBER"])
        payload = json.loads(open(os.environ["GITHUB_EVENT_PATH"]).read())
        head_sha = payload["pull_request"]["head"]["sha"]
    else:  # workflow_run
        payload = json.loads(open(os.environ["GITHUB_EVENT_PATH"]).read())
        head_sha = payload["workflow_run"]["head_sha"]
        pr = find_pr(head_sha)
        if not pr:
            print("Aucune PR ouverte associée, skip")
            return 0

    pr_data = gh_json(f"repos/{REPO}/pulls/{pr}")
    if not pr_data or pr_data.get("state") != "open" or pr_data.get("merged_at"):
        return 0
    if pr_data["head"]["sha"] != head_sha:
        print("Head SHA différent (nouveau push), on attend le prochain trigger")
        return 0

    # 1. Approbation humaine
    reviews = gh_json(f"repos/{REPO}/pulls/{pr}/reviews?per_page=100") or []
    approved = any(
        r["state"] == "APPROVED"
        and r["user"]["login"] not in BOT_LOGINS
        and not r["user"]["login"].endswith("[bot]")
        for r in reviews
    )
    if not approved:
        print("Pas encore d'approbation humaine — attente")
        return 0

    # 2. Checks CI sur le head
    checks = gh_json(f"repos/{REPO}/commits/{head_sha}/check-runs?per_page=100") or {}
    runs = checks.get("check_runs", [])
    if not runs:
        print("Aucun check sur ce commit — attente")
        return 0
    bad = [
        c["name"] for c in runs
        if c["status"] != "completed"
        or c["conclusion"] not in ("success", "skipped", "neutral")
    ]
    if bad:
        print(f"Checks non verts : {bad} — merge reporté")
        return 0

    # 3. Zones sensibles
    files = gh_json(f"repos/{REPO}/pulls/{pr}/files?per_page=100") or []
    touched = [f["filename"] for f in files]
    sensitive = [f for f in touched if SENSITIVE.search(f)]
    if sensitive:
        print(f"Zone(s) sensible(s) touchée(s) : {sensitive} — merge manuel requis")
        return 0

    print(f"PR #{pr} : approbation humaine + CI verte + hors zone sensible → merge squash")
    gh("pr", "merge", str(pr), "-R", REPO, "--squash")
    gh("pr", "comment", str(pr), "-R", REPO,
       "--body", "Merge automatique : approbation humaine + CI verte + hors zone sensible.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
