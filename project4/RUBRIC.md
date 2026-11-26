---
course: DS 3022, Systems II: Advanced Data Science Systems
term: Fall 2026, UVA in Valencia
artifact: Data Project 4, Grading Rubric
project: Data Project 4, Event-Driven Ingestion (individual)
assigned: Project 4 Session 1, Thursday 26 November 2026
due: Thursday 03 December 2026, 23:59 (after Project 4 Session 3)
total: 100 points
weight: 20% of the course grade
---

# Data Project 4: Rubric

**Event-Driven Ingestion** · brief: [BRIEF.md](BRIEF.md) · checkpoints: [CHECKPOINTS.md](CHECKPOINTS.md) · chaos round: [CHAOS_CARDS.md](CHAOS_CARDS.md)

## Point structure at a glance

| Section | Points | Mostly built in |
|---|---:|---|
| 1. Data model and infrastructure | 15 | Session 1 · Thu 26 Nov (A) |
| 2. Ingestion and validation | 25 | Sessions 1 and 2 (B, C) |
| 3. Robustness | 20 | Session 2 · Mon 30 Nov (C, D) |
| 4. API and tests | 15 | Between sessions, Tue 01 and Wed 02 Dec (E) |
| 5. README, design justification and hygiene | **25** | Throughout; finished in Session 3 (Thu 03 Dec) |
| **Total** | **100** | |

> There is no interview for this project. You explain and defend your design **in writing** in your README, so part 5 is a quarter of the grade.

Three things worth noticing before you plan your time:

1. **Event-driven is required.** If events reach DynamoDB in any way other than `on_file()` triggered by the bucket, the project is capped at **60**.
2. **The check is the contract.** Rows 2.x and 4.1 start from `kit/check_project.py`. The grader runs it on your tag; a check you never saw pass is unlikely to pass then.
3. **No Scan for P1, P2 or P3.** A route that answers an access pattern with a Scan scores 0 on row 1.2, even if its answer is right.

## How to use this

**Before you submit,** mark the Self column `Y` (done and verified), `P` (partial) or `N` (not attempted) for every row, commit this file, and upload it to the course platform with your repository link. Partial credit is real; an honest `N` costs you that row and nothing more.

**How it is marked.** The grader checks out your `dp4-submit` tag, follows your README (emulator, `kit/stack.py create`, `kit/local_lambda.py`, `chalice local`), runs `python kit/check_project.py` and `pytest -q`, uploads extra files with `kit/doors.py` (including the chaos-card commands), and reads your code. Where the Evidence column says "code", the grader reads the relevant function.

---

## 1. Data model and infrastructure (15 pts)

| # | Requirement | Pts | Evidence to look for | Self | Score |
|---|---|---:|---|:--:|:--:|
| 1.1 | **Stack from your template**: `template.yaml` with your keys deploys with `kit/stack.py create`; only key attributes declared | 4 | `template.yaml`; grader deploys it | | |
| 1.2 | **Keys serve the access patterns**: P1 and P2 by Query, P3 by Query or GetItem, on keys you designed; no Scan for them | 7 | `model.py`, the three routes; Data model section | | |
| 1.3 | **Least privilege**: `policy-dev.json` lists only the actions your code calls, on your tables and bucket | 4 | `policy-dev.json` against the code | | |

**Subtotal: ___ / 15**

---

## 2. Ingestion and validation (25 pts)

| # | Requirement | Pts | Evidence to look for | Self | Score |
|---|---|---:|---|:--:|:--:|
| 2.1 | **Triggered handler**: `on_file` fires on `.json` objects only, reads and deserialises the object, uses the decoded key | 5 | Code; check: the `.txt` file is ignored | | |
| 2.2 | **Rules R1 to R6** applied per event, with a reason that names the rule; valid events of a partial file kept | 8 | `validate.py`; check: f3 partial 6/6 | | |
| 2.3 | **UTC normalisation**: every stored and returned `access_time` is `...Z`; days are UTC days | 4 | Code; check: A01 on two days, `/events/{id}` | | |
| 2.4 | **File log**: one row per file with status `ok` / `partial` / `rejected`, counts and reasons | 4 | Check: f4 rejected, f1 one row | | |
| 2.5 | **Useful logging** (`app.log`): one line per file with the counts, warnings for rejected files | 4 | Lambda terminal output; code | | |

**Subtotal: ___ / 25**

---

## 3. Robustness (20 pts)

| # | Requirement | Pts | Evidence to look for | Self | Score |
|---|---|---:|---|:--:|:--:|
| 3.1 | **Idempotent**: re-uploaded file, reader retry and an event repeated inside one file create no duplicates; running the check twice gives the same answers | 6 | Check (f1 twice, f6, J10 count); grader repeats C1 and C2 | | |
| 3.2 | **Right errors**: bad data is recorded and returns; infrastructure errors raise (no blanket `except` that hides them) | 5 | Code; grader repeats C3 and C4 | | |
| 3.3 | **Chaos round**: C1 and C4 plus one more, each with a prediction and numbers before and after | 6 | README Chaos round table | | |
| 3.4 | **Nothing lost**: C4 screenshot shows the dead-letter queue and a successful redrive; the queue is empty at submission | 3 | `docs/`; check: DLQ line | | |

**Subtotal: ___ / 20**

---

## 4. API and tests (15 pts)

| # | Requirement | Pts | Evidence to look for | Self | Score |
|---|---|---:|---|:--:|:--:|
| 4.1 | **The five routes follow the contract**: shapes, order, `limit`, 400 and 404 (all live API checks OK) | 8 | `check_project.py` | | |
| 4.2 | **Tests**: at least 8 passing, including one per rule R2 to R6 and one for idempotency; one shown to fail on purpose | 7 | `pytest -q`; Tests section | | |

**Subtotal: ___ / 15**

---

## 5. README, design justification and hygiene (25 pts)

| # | Requirement | Pts | Evidence to look for | Self | Score |
|---|---|---:|---|:--:|:--:|
| 5.1 | **How to run** works from a fresh clone (peer-tested on Thu 03 Dec) | 5 | Grader follows it | | |
| 5.2 | **Architecture** diagram with your names, including the error path | 3 | README / `docs/` | | |
| 5.3 | **Design decisions**: all six answered in your own words with your own numbers (and a cited price for 6) | 6 | README section | | |
| 5.4 | **Data model and API** sections: the key table and one real example per route | 3 | README sections | | |
| 5.5 | **Reflection** (about 150 words) and **Acknowledgements** (help, reused code, AI use and how it was checked) | 3 | README sections | | |
| 5.6 | **Repository hygiene**: work in `project4/` of `ds3022-events`; no `.env`, `.venv/`, `out/`, caches or Chalice deployments committed; `PROGRESS.md` kept; `dp4-submit` tag | 5 | `git ls-files`; `kit/check_project.py` | | |

**Subtotal: ___ / 25**

---

## Total

| Section | Score |
|---|---:|
| 1. Data model and infrastructure | ___ / 15 |
| 2. Ingestion and validation | ___ / 25 |
| 3. Robustness | ___ / 20 |
| 4. API and tests | ___ / 15 |
| 5. README, design justification and hygiene | ___ / 25 |
| **Total** | **___ / 100** |

**Academic integrity.** This is an individual project with open collaboration (see BRIEF.md). Shared code, tests or README text, or undeclared help, are handled under the UVA honor policy. Late submissions (after 23:59 on Thursday 03 December 2026) are penalised under syllabus §3.4.
