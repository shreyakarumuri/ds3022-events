"""Your key design: how one event becomes DynamoDB item(s), and the keys each route queries.

The three access patterns (BRIEF.md) must each be answered by a Query or a GetItem,
never a Scan:
  P1  every access to building B on UTC day D, oldest first
  P2  the latest N accesses of user U, newest first
  P3  one event by its event_id

Write your design here first (it becomes "Data model" in your README):
  TODO A1: table(s), partition key and sort key values for P1, P2 and P3
"""
FIELDS = ["event_id", "building_code", "building_door_id", "user_identity", "access_time", "result"]


def items_for(event):
    """TODO A2: the item(s) to write for one valid, normalised event.
    Writing the same event again must produce exactly the same keys (idempotent)."""
    raise NotImplementedError("items_for")


def public(item):
    """The event as the API returns it: the six FIELDS only, without your key attributes."""
    return {f: item[f] for f in FIELDS if f in item}
