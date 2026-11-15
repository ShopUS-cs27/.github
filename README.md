# .github — Plateforme CI/CD · Marketplace CS27

Dépôt d'orchestration DevSecOps de l'org `ShopUS-cs27`. Les workflows CI/CD
**transverses** vivent ici sous forme de *reusable workflows*
(`workflow_call`) : chaque dépôt métier (`api`, `web`, `mobile`, `docs`)
se contente de les appeler. Une correction ici se propage partout.

**Principe : simple et utile.** Pas de bots bavards — une PR propre ne
reçoit aucun commentaire. Seuls les échecs actionnables publient un
commentaire. Tout le reste est visible dans les checks et les résumés
de jobs.

## Workflows disponibles

| Workflow | Rôle | Déclencheur |
|---|---|---|
| `secrets-scan.yml` | Scan Gitleaks (historique complet, allowlist tests) | PR + push |
| `node-ci.yml` | npm ci → lint → tests → e2e → build → audit | PR + push |
| `flutter-ci.yml` | format → analyze → test (skip si pas de pubspec) | PR + push |
| `semgrep.yml` | SAST — règles OWASP `p/default` | PR + push |
| `pr-guardrails.yml` | Template PR, fichiers interdits, nommage branches, back-merge release | PR uniquement |

Le dépôt `api` ajoute `pr-title.yml` (conventional commits) et `docs`
sa CI locale `contract` (Redocly + schema.sql).

## Ce que voit une PR

```
push → PR vers dev
  ├─ Gitleaks      → secrets commités ?         BLOQUANT
  ├─ build/tests   → lint, tests, audit deps    BLOQUANT
  ├─ Semgrep       → vulnérabilités SAST        BLOQUANT
  ├─ guardrails    → template, fichiers, branches, back-merge
  │                 → silencieux si OK ; 1 commentaire SEULEMENT si échec
  └─ humain        → ≥1 approbation (Aida ou NICE-DEV226) → merge manuel
```

Promotion `dev → main` : PR `chore(release): promotion dev → main — <date>`,
**merge commit** obligatoire (le SHA testé est préservé), et le guardrail
vérifie que `main` est contenu dans `dev` (back-merge).

## Secrets

Aucun secret requis : tous les jobs utilisent le `GITHUB_TOKEN`
automatique à permissions minimales.

## Appeler depuis un dépôt

```yaml
name: CI
on:
  pull_request:
    branches: [main, dev]
  push:
    branches: [main, dev]

permissions:
  contents: read
  pull-requests: write   # requis : le commentaire d'échec guardrails
  issues: write

jobs:
  secrets:
    uses: ShopUS-cs27/.github/.github/workflows/secrets-scan.yml@main
  node:
    uses: ShopUS-cs27/.github/.github/workflows/node-ci.yml@main
  semgrep:
    uses: ShopUS-cs27/.github/.github/workflows/semgrep.yml@main
  guardrails:
    uses: ShopUS-cs27/.github/.github/workflows/pr-guardrails.yml@main
```

Points importants : `permissions:` dans l'appelant obligatoire si un
workflow appelé commente les PR ; les workflows appelés ne peuvent pas
élever les droits de l'appelant.

## Règles

- Versionner les appels sur `@main` ; passer à un tag `v1` quand figé.
- Jamais de secret en dur — `secrets.` du dépôt appelant.
- Toute modification = PR avec relecture DevSecOps (zone sensible :
  `.github/`, `render.yaml`, auth, gardes, audit, migrations).
- Merge : squash pour features → `dev` ; merge commit pour releases
  et back-merges.

## Licence

MIT — copyright CS27.
