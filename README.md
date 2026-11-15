# .github — Plateforme CI/CD · Marketplace CS27

Dépôt d'orchestration DevSecOps de l'org `ShopUS-cs27`. Tous les workflows
CI/CD **transverses** vivent ici sous forme de *reusable workflows*
(`workflow_call`) : chaque dépôt métier (`api`, `web`, `mobile`, `docs`)
se contente de les appeler. Une correction ici se propage partout —
c'est la golden path plateforme.

## Architecture

```
DevSecOps (NICE-DEV226 + Aida-Zongo)
        │  maintient
        ▼
ShopUS-cs27/.github  ── workflows réutilisables + scripts
        │  appelé par @main
        ▼
api · web · mobile · docs  ── .github/workflows/ci.yml (appels uniquement)
```

Les équipes métier **ne modifient jamais** les workflows : ils codent,
la CI s'applique automatiquement. Toute évolution du pipeline passe par
une PR sur ce dépôt avec relecture DevSecOps.

## Workflows disponibles

| Workflow | Rôle | Déclencheur |
|---|---|---|
| `secrets-scan.yml` | Scan Gitleaks (historique complet, allowlist tests) | PR + push |
| `node-ci.yml` | npm ci → lint → tests → e2e → build → audit | PR + push |
| `flutter-ci.yml` | format → analyze → test (skip si pas de pubspec) | PR + push |
| `semgrep.yml` | SAST — règles OWASP `p/default` | PR + push |
| `pr-guardrails.yml` | Template PR, fichiers interdits, taille diff | PR uniquement |
| `ai-review.yml` | Review IA PR-Agent (générale + AppSec via `.pr_agent.toml`) | PR uniquement |
| `reviewdog.yml` | Commentaires ESLint inline sur les lignes du diff | PR uniquement |
| `auto-merge-gate.yml` | Merge auto conditionnel (CI verte + approbation humaine, hors zones sensibles) | review + workflow_run |

Le dépôt `docs` a en plus une CI locale `contract` (Redocly + schema.sql).

## Pipeline de review (ce que voit une PR)

```
push → PR vers dev
  ├─ Gitleaks      → secrets commités ?        BLOQUANT
  ├─ Semgrep       → vulnérabilités SAST       BLOQUANT
  ├─ tests/build   → lint, tests, audit deps   BLOQUANT
  ├─ guardrails    → template, fichiers, taille  BLOQUANT si incomplet
  ├─ PR-Agent      → review IA générale + AppSec  consultatif
  ├─ reviewdog     → warnings ESLint inline       consultatif
  └─ humain        → ≥1 approbation (Aida ou NICE-DEV226)
        │
        ▼  auto-merge-gate : merge auto SI
           CI verte + approbation humaine
           ET aucun fichier sensible touché
           (auth, gardes, audit, migrations,
            workflows, render.yaml, .env*)
           → sinon merge manuel obligatoire
```

## Secrets requis par dépôt

| Secret | Usage |
|---|---|
| `GEMINI_API_KEY` | PR-Agent (review IA) — Google AI Studio, free tier |

Les autres jobs n'ont besoin que du `GITHUB_TOKEN` automatique.

## Comment appeler depuis un dépôt

```yaml
name: CI
on:
  pull_request:
    branches: [main, dev]
  push:
    branches: [main, dev]

permissions:
  contents: read
  pull-requests: write   # requis : les bots commentent les PR
  issues: write

jobs:
  secrets:
    uses: ShopUS-cs27/.github/.github/workflows/secrets-scan.yml@main
  node:
    uses: ShopUS-cs27/.github/.github/workflows/node-ci.yml@main
  semgrep:
    uses: ShopUS-cs27/.github/.github/workflows/semgrep.yml@main
  reviewdog:
    uses: ShopUS-cs27/.github/.github/workflows/reviewdog.yml@main
  guardrails:
    uses: ShopUS-cs27/.github/.github/workflows/pr-guardrails.yml@main
  ai-review:
    uses: ShopUS-cs27/.github/.github/workflows/ai-review.yml@main
    secrets:
      GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

Points importants :

- `permissions:` dans l'appelant **obligatoire** si un workflow appelé
  commente les PR — sinon `startup_failure`.
- `secrets:` passés **explicitement** (pas de `secrets: inherit` sur les
  workflows `workflow_call`).
- Les workflows appelés ne peuvent pas élever les droits de l'appelant.

## Règles

- Versionner les appels sur `@main` aujourd'hui ; passer à un tag `v1`
  quand le pipeline sera figé.
- Jamais de secret en dur — `secrets.` du dépôt appelant.
- Toute modification = PR avec relecture DevSecOps (zone sensible).
- Une review IA est **consultative** : elle ne remplace jamais
  l'approbation humaine, et ne doit jamais faire échouer la CI.

## Licence

MIT — copyright CS27.
