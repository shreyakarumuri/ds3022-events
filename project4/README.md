# TODO: your project title

**Author:** TODO
**DS 3022 Data Project 4, Fall 2026**

> There is no interview for this project: this README is where you explain and defend your pipeline. Fill in the title, your name and every italic placeholder, then delete this note. Keep the headings: `kit/check_project.py` looks for them.

## How to run

_(replace: the exact commands, in order, from a fresh clone of your repository. A classmate will follow them on Thu 03 Dec without asking you. Include the virtual environment, the four terminals (emulator, `kit/stack.py create`, `kit/local_lambda.py`, `chalice local`), uploading files with `kit/doors.py`, the check and the tests:)_

```bash
cd project4
python kit/check_project.py
```

## Architecture

_(replace: a diagram (an image in docs/ or a text diagram) of reader files → bucket → trigger → `on_file` → your table(s) → routes, plus the error path (retries, dead-letter queue, redrive). Use your own names.)_

## Data model

_(replace: your table(s) and keys. For each access pattern: the partition key value, the sort key value, the operation (Query or GetItem) and one example item. Example layout:)_

| Pattern | Table | Partition key | Sort key | Operation |
|---|---|---|---|---|
| P1 building + day | TODO | TODO | TODO | TODO |
| P2 user, newest first | TODO | TODO | TODO | TODO |
| P3 one event | TODO | TODO | TODO | TODO |

## Design decisions

Answer each in 2-4 sentences, in your own words, with your own numbers.

1. **Keys.** _(replace: why these keys answer P1, P2 and P3 without a Scan. What does a write cost (how many items per event), and why is that worth it? Why was the starting key (event_key + access_time) not enough?)_
2. **Hot partitions.** _(replace: which partition gets the most writes at 08:30 on a Monday? What would you change if the university had 100 times more readers?)_
3. **Idempotency.** _(replace: what makes two events "the same"? What happens, item by item, on a re-uploaded file, a reader retry and an event repeated inside one file?)_
4. **Data errors vs infrastructure errors.** _(replace: which problems you record and return, which you let raise, and why. Give one example of each from your chaos round.)_
5. **Time.** _(replace: why you store UTC, what happens to an event at 00:30+01:00, and how late events (card C6) end up on the right day.)_
6. **Cost and limits.** _(replace: at 1 million events a day in files of 50 events, about how many Lambda invocations a month, and what they cost (use the AWS pricing page; cite it). How many DynamoDB writes does your design make, and what do they cost on demand? When would you stop using Lambda for this?)_

## Chaos round

| Card | Prediction | What I did | Numbers before → after | Explanation |
|---|---|---|---|---|
| C1 Same file twice | TODO | TODO | TODO | TODO |
| C4 Broken config, DLQ, redrive | TODO | TODO | TODO | TODO |
| TODO (C2, C3, C5 or C6) | TODO | TODO | TODO | TODO |

![Lambda terminal during card C4](docs/TODO.png)

## API

_(replace: one example call and a shortened response for each of the five routes, taken from your own running API.)_

## Tests

_(replace: how to run them, how many there are, what they cover (one line per test or group), and one test you made fail on purpose to prove it can fail.)_

![check_project.py output](docs/TODO.png)

## Reflection

_(replace: about 150 words, first person. What did you learn about event-driven and serverless systems that you did not know before Thu 19 Nov? Compare this pipeline with Project 2 or Project 3: when would you choose each style?)_

## Acknowledgements

_(replace: everyone who helped you and how (classmates, instructor, online sources), code you reused (for example from s3_lambda/ in this repository), and any AI assistance: what for, and how you checked the result. Write "None" if there is nothing to declare.)_
