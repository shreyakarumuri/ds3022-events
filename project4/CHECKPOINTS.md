# Project 4 checkpoints

Tick them off in your own copy. Add an entry to **PROGRESS.md** (done / next / blocked) at the end of every session and every time you stop working.

## Session 1 · Thu 26 Nov

### Checkpoint A: key design and stack
- [ ] The kit is unzipped into `ds3022-events/project4/`, committed and pushed before you change anything
- [ ] `chalicelib/model.py` docstring: table(s), partition key and sort key **values** for P1, P2 and P3, and the operation (Query or GetItem) for each
- [ ] `template.yaml` changed to your keys; `python kit/stack.py create` prints `CREATE_COMPLETE`
- [ ] README "Data model" section drafted (table, keys, one example item per access pattern)

### Checkpoint B: first events stored
- [ ] `python kit/local_lambda.py` in the Lambda terminal and `python kit/doors.py normal` in the work terminal: the Lambda terminal shows `REPORT ... status: ok`
- [ ] `on_file()` reads the file, rejects non-JSON without raising, writes your item(s), logs the file (TODO B1 to B4)
- [ ] `model.items_for()` written (TODO A2); at least R1 and R2 working
- [ ] API terminal: `chalice local --stage local --port 8000`: `/files` shows your files; one more route answers (P3 is the quickest)

## Session 2 · Mon 30 Nov

### Checkpoint C: all rules, UTC, idempotency
- [ ] R1 to R6 implemented, reasons start with the rule number; `doors.py bad` gives `partial`, 6 rejected
- [ ] Every `access_time` stored in UTC (`...Z`)
- [ ] The same file twice, a reader retry and an event repeated inside one file create no duplicates

### Checkpoint D: chaos round (steps in [CHAOS_CARDS.md](CHAOS_CARDS.md))
- [ ] Card C1 (same file twice) with numbers before and after
- [ ] Card C4 (broken config, dead-letter queue, redrive) with numbers before and after, screenshot of the Lambda terminal in `docs/`
- [ ] At least one of C2, C3, C5, C6
- [ ] "Chaos round" table in README.md

## Between sessions · Tue 01 and Wed 02 Dec (before Session 3)

### Checkpoint E: API and tests
- [ ] The five routes answer as in the contract (BRIEF.md)
- [ ] `python kit/check_project.py`: every live check (files, buildings, after-hours, users, events) is `OK`
- [ ] At least 8 tests pass (`cd access-events`, `pytest -q`), including one per rule and one for idempotency
- [ ] `policy-dev.json`: only the actions your code calls

## Session 3 · Thu 03 Dec

### Checkpoint F: README and submission
- [ ] README complete: every heading, no `TODO` or `(replace` left
- [ ] README peer test done; the one place your reader got stuck is fixed
- [ ] Screenshot of `check_project.py` output in `docs/`
- [ ] `python kit/check_project.py` prints `READY`
- [ ] `RUBRIC.md` Self column filled; everything committed and pushed
- [ ] `git tag dp4-submit` and `git push origin dp4-submit`, **last**
- [ ] Repository link + rubric on the course platform by **23:59**
