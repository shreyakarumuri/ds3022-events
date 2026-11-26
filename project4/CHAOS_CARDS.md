# Chaos round (Project 4 Session 2 · Mon 30 Nov)

Break your own pipeline on purpose, then explain what happened. **C1 and C4 are compulsory**; do at least one more. Every card goes into the Chaos round table of your README.

## How to run a card

1. **Predict.** Before you type anything, write in your README what you expect (counts, status, Lambda terminal lines).
2. **Do.** Run the steps. The emulator terminal (`moto_server -p 9324`), the Lambda terminal (`python kit/local_lambda.py`) and the API terminal (`chalice local --stage local --port 8000`) must be running.
3. **Observe.** Write the numbers before and after. Useful numbers: the `count` of `/buildings/<code>/access?date=<day>`, the number of rows in `/files` and the row of your file, the `REPORT` / `ERROR` / `GAVE UP` lines in the Lambda terminal.
4. **Explain.** Two or three sentences: why did it happen, and which line of your code makes it so?

`doors.py` prints the key of every file it uploads (`Uploaded s3://ds3022-access-events/uploads/...`): copy it exactly when a card needs it. The day for `/buildings/...` is the UTC date of the events (the `access_time` in the file, also in `out/`).

## C1 · The same file twice (compulsory)

1. `python kit/doors.py normal --files 1` and note the key, the building and the date.
2. Note the count for that building and day, and the number of rows in `/files`.
3. `python kit/doors.py again <key>`.
4. Look at the Lambda terminal, the building count, `/files`.

**Expected:** a second `REPORT` for the same key; the building count does not change; `/files` still has one row for that key, with a new `processed_at`.

## C2 · A reader retries (same events, new file name)

1. Take the key from C1. `python kit/doors.py retry <key>`.
2. Compare the building count and `/files`.

**Expected:** one new row in `/files` (a different file, `status: ok`); the building count does not change. Explain which part of your keys makes this true: the file name is new, the events are not.

## C3 · Bad rows and a file that is not JSON

1. `python kit/doors.py bad` (10 good events + 6 bad ones, one per rule).
2. `python kit/doors.py broken`.
3. Read both rows in `/files` and the Lambda terminal lines.

**Expected:** `bad`: `partial`, 10 valid, 6 rejected, a reason for each rule. `broken`: `rejected`, `attempt 1` only, no retries. Explain why retrying the broken file would be useless.

## C4 · Broken configuration, dead-letter queue, redrive (compulsory)

1. In the Lambda terminal, stop `local_lambda.py` (Ctrl+C). In `access-events/.chalice/config.json`, stage `local`, change `"ACCESS_TABLE": "access"` to `"acess"`. Start `local_lambda.py` again.
2. `python kit/doors.py normal --files 2`. Wait about 30 seconds and watch the Lambda terminal.
3. `python kit/redrive.py` (shows what waits in the dead-letter queue).
4. Fix the name, restart `local_lambda.py`, then `python kit/redrive.py --go`.
5. Take a screenshot of the Lambda terminal showing the `ERROR` lines, `GAVE UP` and the final `REPORT ... ok` lines: save it in `docs/`.

**Expected:** `ResourceNotFoundException`, attempts 1, 2 and 3 about 10 seconds apart, `GAVE UP ... event sent to access-file-dlq` for both files; `redrive.py` lists them; after the fix and `--go`, two `REPORT ... status: ok`. Explain why this error must raise (and the one in C3 must not), and what would have happened without a dead-letter queue.

## C5 · A burst of 200 files

1. Note the number of rows in `/files`.
2. `python kit/doors.py burst --files 200`. Time how long until `/files` has 200 more rows.
3. Check `python kit/redrive.py` (nothing should be waiting).

**Expected:** about 2 seconds to upload, a few seconds to process (tested: 200 files in about 6 s, 20 ms per file on average, the first one slower). Explain what AWS would do differently (many copies of your function at once) and what that means for DynamoDB and for cost.

## C6 · Late events

1. `python kit/doors.py late --hours 30` (the events happened about 30 hours ago and arrive now).
2. Query the building for **yesterday's** UTC date and for today's.

**Expected:** the events appear under yesterday, not today. Explain event time vs arrival time (Thu 22 Oct and Mon 02 Nov) and why your key design puts them in the right place without any special code.

## Example README row

| Card | Prediction | What I did | Numbers before → after | Explanation |
|---|---|---|---|---|
| C1 Same file twice | Count unchanged, one file row | `doors.py normal --files 1`, then `again uploads/J10-26/...json` | J10 on 2026-12-03: 41 → 41; `/files` rows 12 → 12; Lambda terminal: 2 REPORTs | My keys are built from `event_id` and `access_time`, so the second run writes the same keys and overwrites. `file_log` is keyed by the file name, so its row is replaced too. |
