# BASELINE

SE3002 Software Quality Engineering, Final Project (Fall 2026).
System under test: Django Library, Orders module (lend a book, return a book).

## 1. Upstream reference

| Item | Value |
| --- | --- |
| Upstream repository | https://github.com/Arezzon/Library-Django |
| Licence | MIT (`LICENSE` file in the repository root) |
| Baseline commit hash | '41387855b3154761925b4eb8a00660e7e661a5c8' |
| Team commit adding documentation and scripts | '1885ca9' |
| Baseline recorded on | 2026-11-21 by Maha |
| Rule | Do not `git pull` from upstream after the hash is recorded |

Do not rely on the hash seen on GitHub today. Use the hash from the team's own clone.

## 2. Tool versions

Fill in from the machine that produced the evidence. Re-run if a tool is upgraded.

| Tool | Command | Version |
| --- | --- | --- |
| Docker | `docker --version` | 29.8.0 |
| Docker Compose | `docker compose version` | 5.5.1 |
| Python (in the image) | `docker compose -f docker-compose-dev.yml exec web python --version` | 3.12.16 |
| Django (in the image) | `docker compose -f docker-compose-dev.yml exec web python -m django --version` | 5.2.18 |
| Node.js (Playwright, Lighthouse) | `node --version` | 22.18.0 |
| Playwright | `npx playwright --version` | 1.65.1 |
| Lighthouse | `npx lighthouse --version` | 12.8.2 |
| axe-core / @axe-core/playwright | `npm ls axe-core @axe-core/playwright` | `<fill>` |
| OWASP ZAP | (About dialog or `zap.sh -version`) | `<fill>` |
| pip-audit | `pip-audit --version` | `<fill>` |
| k6 | `k6 version` | `<fill>` |

## 3. Install, start, seed, reset

Never commit `.env`. Use placeholders for secrets in anything you share.

| Step | Command or action |
| --- | --- |
| Clone | `git clone https://github.com/Arezzon/Library-Django.git` (our team fork: `<TEAM REPO URL>`) |
| Create `.env` | `cp .env.example .env` (PowerShell: `Copy-Item .env.example .env`) |
| Edit `.env` | Uncomment `COMPOSE_FILE=docker-compose-dev.yml`; set `SECRET_KEY` to a long random value; set `DB_PASSWORD` to your own value |
| Start | `docker compose -f docker-compose-dev.yml up --build` (first build is slow; keep Docker Desktop running) |
| Open | http://localhost:8000 (API docs `/api/docs/`, schema `/api/schema/`, version `/api/v1/version/`) |
| Seed | Automatic on first start into an empty database (`DJANGO_SEED=true`, the default) |
| Reset between runs | `powershell -ExecutionPolicy Bypass -File tests/team/baseline/reset.ps1` or `bash tests/team/baseline/reset.sh` |
| Manual reset | `docker compose -f docker-compose-dev.yml down -v`, then `docker compose -f docker-compose-dev.yml up -d` |
| Verify baseline | The reset scripts run `tests/team/baseline/check_seed.py` and print `BASELINE CLEAN` |

### Why reset must use `down -v`

`seed_db.py` does nothing if any user already exists. Restarting the containers or running the seed
again does not restore the data. Only deleting the database volume (`down -v`) returns the app to the
documented starting state. Every automated run (unit, API, Playwright, k6) must start from a reset.

## 4. Expected baseline state

Created by `library/seed_db.py` at the baseline commit.

### Accounts (synthetic, local only)

| Role | Email | Password |
| --- | --- | --- |
| Librarian | `librarian@library.com` | `admin123password` |
| Reader | `reader@library.com` | `reader123password` |
| Reader | `alice@library.com` | `alice123password` |
| Reader | `bob@library.com` | `bob123password` |

### Data

| Record | Count | Notes |
| --- | --- | --- |
| Users | 4 | 1 librarian, 3 readers |
| Authors | 8 | |
| Books | 9 | |
| Loans (orders) | 3 | 2 open, 1 returned |
| Reservations | 0 | |

### Shared record: available copies of a book

Available copies = total copies, less open loans, less active unexpired reservations (never below 0).

| Book | Total | Open loans | Available at baseline |
| --- | --- | --- | --- |
| Kobzar | 5 | 1 (reader@library.com) | 4 |
| 1984 | 8 | 1 (alice@library.com) | 7 |
| Clean Code: A Handbook of Agile Software Craftsmanship | 3 | 0 (bob's loan already returned) | 3 |
| Animal Farm | 7 | 0 | 7 |

## 5. Folder layout for our work

All team work lives under `tests/team/` so it stays separate from upstream code and upstream tests
(upstream tests earn no marks).

```
tests/team/
  baseline/        reset.ps1, reset.sh, check_seed.py
  unit/            Area 1
  api/             Area 2
  e2e/             Playwright specs (Area 3 and each member's use cases)
  perf/            k6 scripts and raw output
  security/        access matrix, ZAP and pip-audit evidence
```

## 6. Known baseline notes

- The first start is slow: the entrypoint re-encodes book embeddings, and the web container's
  health check allows a long start period.
- The upstream repository already contains its own tests and workflows (`codeql.yml`,
  `docker-build.yml`). None of these count as team work.
- Reservation expiry runs in a Celery worker started by the dev compose file; keep the `worker`
  service running when testing anything time-dependent.
