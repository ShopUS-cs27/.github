# .github — Workflows réutilisables · Marketplace CS27

Workflows CI réutilisables (`workflow_call`) pour tous les dépôts de l'org
`ShopUS-cs27`. Chaque dépôt n'a qu'à appeler le workflow central — une
correction ici se propage partout (golden path plateforme).

## Workflows disponibles

| Workflow | Usage | Contenu |
|---|---|---|
| `secrets-scan.yml` | Tous les dépôts | Scan Gitleaks de l'historique complet |
| `node-ci.yml` | `api`, `web` | npm ci → lint → tests → e2e → build → audit |
| `flutter-ci.yml` | `mobile` | flutter pub get → format → analyze → test |

## Comment appeler depuis un dépôt

```yaml
name: CI
on:
  pull_request:
    branches: [main, dev]
  push:
    branches: [main, dev]

jobs:
  secrets:
    uses: ShopUS-cs27/.github/.github/workflows/secrets-scan.yml@main

  ci:
    uses: ShopUS-cs27/.github/.github/workflows/node-ci.yml@main
    # with:                      # optionnel
    #   node-version: '20'
    #   working-directory: '.'
```

## Règles

- Versionner les appels sur un tag/branche stable (`@main` aujourd'hui ;
  passer à un tag `v1` quand le pipeline sera figé)
- Ne jamais mettre de secret en dur dans ces workflows — utiliser
  `secrets.` du dépôt appelant si besoin
- Toute modification = PR avec relecture DevSecOps
- Le dépôt `docs` garde sa CI contrat en local (validation OpenAPI +
  schéma SQL) mais appelle `secrets-scan.yml` pour le scan

## Licence

MIT — copyright CS27.
