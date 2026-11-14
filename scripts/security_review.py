#!/usr/bin/env python3
"""Review sécurité dédiée — appelé par le workflow security-review.

Envoie le diff de la PR à Gemini avec un prompt 100% AppSec, puis
publie le résultat en commentaire sur la PR. Ne bloque jamais :
la review sécurité est consultative, le gate Humain reste souverain.
"""

import json
import os
import subprocess
import sys
import urllib.request

REPO = os.environ["GITHUB_REPOSITORY"]
PR = os.environ["PR_NUMBER"]
KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("SECURITY_MODEL", "gemini-3.8-flash")
GH_TOKEN = os.environ.get("GITHUB_TOKEN", "")


def gh(*args: str) -> str:
    env = dict(os.environ, GH_TOKEN=GH_TOKEN)
    return subprocess.run(
        ["gh", *args], capture_output=True, text=True, env=env
    ).stdout


def main() -> int:
    if not KEY:
        print("::notice::GEMINI_API_KEY absente — review sécu désactivée")
        return 0

    diff = gh("pr", "diff", PR, "-R", REPO)
    if not diff.strip():
        print("Diff vide, rien à reviewer")
        return 0
    diff = diff[:60000]  # garde-fou taille

    prompt = (
        "Tu es un ingénieur AppSec senior. Tu review le diff d'une pull request "
        "de la marketplace CS27 (NestJS/TypeScript, Next.js, Flutter — "
        "PostgreSQL, JWT, Cloudflare R2, Firebase).\n\n"
        "Analyse UNIQUEMENT la sécurité, par ordre de criticité :\n"
        "1. Secrets/crédentials commités ou loggés (mots de passe, tokens, "
        "clés API, JWT secrets, PII).\n"
        "2. Injection : SQL, NoSQL, commande, template — toute concaténation "
        "de données non validées dans une requête ou un shell.\n"
        "3. AuthN/AuthZ : bypass possible, IDOR (accès à la ressource d'un "
        "tiers), élévation de privilèges, validation JWT défaillante, "
        "endpoints sans garde.\n"
        "4. Validation des entrées : DTO sans whitelist, masses assignment, "
        "fichiers uploadés non contrôlés.\n"
        "5. Gestion des erreurs : stack traces ou données internes exposées.\n"
        "6. Dépendances : nouvelles dépendances sans justification.\n\n"
        "Format de sortie STRICT en markdown :\n"
        "- Commence par un verdict : ✅ RIEN DE BLOQUANT / ⚠️ POINTS À "
        "VÉRIFIER / 🔴 PROBLÈME(S) SÉRIEUX\n"
        "- Pour chaque problème : fichier:ligne, description courte, "
        "correction suggérée en une ligne.\n"
        "- Termine par une ligne 'Sévérité globale : X/10'.\n"
        "Sois chirurgical : pas de remarque de style, pas de spéculation "
        "sans rapport avec le diff. Réponds en français."
    )

    payload = {
        "contents": [
            {"parts": [{"text": prompt + "\n\n```diff\n" + diff + "\n```"}]}
        ],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096},
    }
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL}:generateContent?key={KEY}"
    )
    text = None
    last_err = None
    for attempt in range(2):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=90) as r:
                data = json.load(r)
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            break
        except Exception as e:  # noqa: BLE001 — retry puis repli
            last_err = e
            print(f"::warning::Appel Gemini tentative {attempt + 1}/2 échouée : {e}")

    if text is None:
        # Une review IA ne doit jamais faire échouer la CI : on logge et on sort.
        print(f"::warning::Review sécu indisponible ({last_err}) — merge inchangé")
        return 0

    body = (
        "## Review sécurité (agent AppSec)\n\n"
        "> Review automatique par IA — consultative, ne se substitue pas "
        "à la revue humaine des zones sensibles.\n\n" + text
    )
    gh("pr", "comment", PR, "-R", REPO, "--body", body)
    print("Review sécurité publiée")
    return 0


if __name__ == "__main__":
    sys.exit(main())
