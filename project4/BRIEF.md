# Data Project 4: Event-Driven Ingestion (brief)

**DS 3022, Fall 2026, UVA in Valencia** · 20% of the course grade · individual project
**Project 4 sessions:** Session 1 (Thu 26 Nov), Session 2 (Mon 30 Nov), Session 3 (Thu 03 Dec). Tue 01 and Wed 02 Dec are for the routes and tests (checkpoint E): Session 3 is only for checking and submitting.
**Due:** Thursday 03 December 2026, 23:59 · **no interview**: you defend your design in writing, in your README

## The story

The university's security office has badge readers on the doors of ten buildings. Every few minutes each reader uploads a JSON file with the swipes it has recorded. The office wants three questions answered within seconds of a file arriving, without anybody running a server that waits all night for files that do not come:

- **P1.** Who went into building B on day D, in time order? (incident reports)
- **P2.** What are the latest N accesses of person U? (a lost or stolen badge)
- **P3.** What exactly happened in event E? (the help desk, and duplicate checks)

They also want a list of **granted accesses after hours** (22:00 to 06:00) per building and day.

This is last year's Project 4 (Prof. Magee's door-access pipeline) on the architecture you built on Mon 23 Nov:

```
kit/doors.py ──► S3 bucket ──ObjectCreated *.json──► on_file() (Lambda, Chalice) ──► DynamoDB (your key design) ──► API
 badge readers      ds3022-access-events              validate, normalise, write          access, file_log             5 routes
                                           on failure: 3 attempts, then the dead-letter queue ──► kit/redrive.py
```

Everything runs on your laptop against the emulator, as in Sessions 20 to 22. `kit/local_lambda.py` plays the Lambda service, `chalice local` serves the API.

## Where your work lives

Your `ds3022-events` repository (from Thu 19 Nov), new folder `project4/` (this kit):

```
ds3022-events/
  s1_dynamodb/  s2_kinesis/  s3_lambda/        (Sessions 20 to 22: the worked examples)
  project4/                                    (Data Project 4: this kit)
    BRIEF.md  CHECKPOINTS.md  CHAOS_CARDS.md  RUBRIC.md
    PROGRESS.md  README.md                     <- you fill these
    template.yaml                              <- you change the keys (checkpoint A)
    access-events/                             <- your Chalice app
      app.py  chalicelib/validate.py  chalicelib/model.py  tests/test_app.py
      .chalice/config.json  .chalice/policy-dev.json
    kit/                                       <- tools, do not edit
      stack.py  local_lambda.py  doors.py  redrive.py  check_project.py
    docs/                                      <- 2 screenshots
    out/                                       (local copies of uploaded files, not committed)
```

Run project commands **from the `project4` folder**, except the two Chalice commands (`chalice local`, `pytest`), which run inside `access-events`. Use the virtual environment of `ds3022-events`; nothing new to install.

Four terminals, named as in Sessions 20 to 22. Activate the `ds3022-events` virtual environment in each one.

| Terminal | Runs | Leave it running? |
|---|---|---|
| **Emulator terminal** | `moto_server -p 9324` | Yes |
| **Lambda terminal** | `python kit/local_lambda.py` (plays the Lambda service; its output is your "CloudWatch Logs") | Yes |
| **API terminal** | inside `access-events`: `chalice local --stage local --port 8000` | Yes (it reloads when you save) |
| **Work terminal** | every other command, from `project4` | It is where you type |

## One file, one event

A file (one reader upload):

```json
{"reader": "A01-23", "uploaded_at": "2026-12-01T08:16:02Z",
 "events": [
   {"event_id": "A01-23-20261201081523-7f3a", "building_code": "A01", "building_door_id": "23",
    "user_identity": "mst3k", "access_time": "2026-12-01T08:15:23Z", "result": "granted"}
 ]}
```

Readers are not perfect. A file can be re-uploaded, a reader can retry by sending the same events in a **new** file, and the same event can even appear **twice in one file**. Some files are not JSON at all.

## The rules (validate.py)

A valid event passes all six rules. Reject an event that breaks any of them and record why; keep the valid events of the same file.

| Rule | An event is valid only if |
|---|---|
| **R1** | all six fields are present and not empty |
| **R2** | `building_code` is one of `A01 B02 C03 D04 E05 F06 G07 H08 I09 J10` |
| **R3** | `building_door_id` is a whole number from 10 to 69 (sent as text, e.g. `"23"`) |
| **R4** | `user_identity` is a computing ID: 2-3 letters, 1 digit, 1-3 letters (`^[a-z]{2,3}[0-9][a-z]{1,3}$`) |
| **R5** | `access_time` is ISO 8601 **with a time zone**, and not more than 5 minutes in the future |
| **R6** | `result` is `granted` or `denied` |

Store and return every `access_time` **in UTC**, as `YYYY-MM-DDTHH:MM:SSZ`. "Day D" and "after hours" are UTC too. Example: `2026-11-16T00:30:00+01:00` is stored as `2026-11-15T23:30:00Z` and belongs to 15 November.

## The API contract

`kit/check_project.py` calls these exactly. Every event in a response has the six fields above and nothing else.

| Route | Returns |
|---|---|
| `GET /buildings/{code}/access?date=YYYY-MM-DD` | `{"building_code", "date", "count", "events": [...]}`, oldest first. **400** without a valid `date` |
| `GET /buildings/{code}/after-hours?date=YYYY-MM-DD` | Same shape: only `granted` events between 22:00 and 06:00 UTC on that day, oldest first |
| `GET /users/{user}/access?limit=N` | `{"user_identity", "count", "events": [...]}`, newest first, `limit` default 10, at most 100 |
| `GET /events/{event_id}` | The event object. **404** if there is no such event |
| `GET /files` | Given in the kit: one row per file `{"file_key", "processed_at", "status", "valid", "rejected", "reasons"}`, newest first. `status` is `ok`, `partial` (some events rejected) or `rejected` (no valid events, or not JSON) |

## Minimum requirements

1. **Event-driven.** Events reach DynamoDB only through `on_file()`, triggered by `s3:ObjectCreated` on `.json` objects. A pipeline that reads the bucket in a loop, or writes from `doors.py`, is capped at 60/100.
2. **Your key design.** P1, P2 and P3 are each answered by a Query or a GetItem on keys you designed, never a Scan (`/files` may Scan its small table). Deployed from your `template.yaml`.
3. **Valid data only, normalised.** Rules R1 to R6; times in UTC; bad events counted with a reason in `file_log`.
4. **Idempotent.** Re-uploads, reader retries and repeated events never create duplicates.
5. **Right errors.** Bad data is recorded and the function returns; an infrastructure error raises (so it is retried and lands in the dead-letter queue). Nothing is lost after `kit/redrive.py --go`.
6. **The five routes** answer exactly as in the contract (`check_project.py` passes all API checks).
7. **At least 8 passing tests** (`pytest -q` in `access-events`), including one per rule and one for idempotency.
8. **README.md** (template in this folder) complete: Data model, Design decisions, Chaos round, API, Tests, Reflection, Acknowledgements.

## Working alone, together

Same rules as Project 3. This is an **individual** project: your own repository, key design, code and README.

- You **may** debug together, compare ideas about keys in general, share tips and explain things to each other.
- You **may not** share code files, tests or README text, or submit work you cannot explain in writing.
- Name everyone who helped you, and any AI assistance (what for, and how you checked it), in **Acknowledgements**. Naming help never costs points; hiding it does.

## How to submit (by 23:59, Thursday 03 December)

1. With the emulator, Lambda and API terminals running: `python kit/check_project.py` prints `READY`.
2. Fill the **Self** column of `RUBRIC.md`, commit and push.
3. Tag the version you submit, last of all:
   ```
   git tag dp4-submit
   git push origin dp4-submit
   ```
4. On the course platform: the link to your `ds3022-events` repository + your completed rubric.

If your repository is private, add the instructor as a collaborator. The grader checks out `dp4-submit`, follows your README (emulator, stack, `local_lambda.py`, `chalice local`), runs `kit/check_project.py` and `pytest`, uploads files with `kit/doors.py`, and reads your code, design decisions and chaos round. Late work is penalised under syllabus §3.4.

## On real AWS (not required)

The same code deploys to AWS: deploy `template.yaml` with CloudFormation, set a globally unique bucket name in the `dev` stage of `.chalice/config.json` and in `policy-dev.json`, then `chalice deploy --stage dev`. You do not need an AWS account for this project.
