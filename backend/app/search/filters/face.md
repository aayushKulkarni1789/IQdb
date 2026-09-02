# Face Filter (kind: `face`) — Subset Filter (stub, not live)

## What it does
Reserved face filter that will subset by detected faces / face similarity. Intended SQL is `face_similarity >= <threshold>` against a face embedding store. Currently `is_live = False` and `build_predicate` raises `NotImplementedError`.

## How to use
Not available via tools. Spec shape is reserved; adding it now returns a 501 from the tool layer. No live tool is exposed for `face`.

**Spec format:** `{"kind": "face"}`

**Example:** `{"kind": "face"}`

## When to use
Do not use. Planned for future "photos containing this person" queries. Until live, use `clip` for people descriptions.
