# CLIP Filter (kind: `clip`) — Rank Filter

## What it does
Semantic ranking filter that scores images by cosine similarity between a text query embedding and stored CLIP embeddings. Implemented as a `RankFilter` that contributes a ranked CTE fused by Reciprocal Rank Fusion (RRF, `k=60`) at finalize time. Does not narrow the candidate set alone; it orders candidates.

## How to use
Call the `add_clip_filter` tool with the spec fields. The tool validates via `ClipRankSpec` (`extra="ignore"` — unknown fields are dropped).

**Spec format:** `{"kind": "clip", "text": "<search query>", "weight": <float, default 1.0>}`

**Example:** `{"kind": "clip", "text": "a photo of a cat", "weight": 1.0}`

**Fields:**
- `text` (required, str): natural-language description of desired visual content.
- `weight` (optional, float, default 1.0): RRF weight; higher values increase influence when multiple rank filters are fused.

Validation errors return an actionable 422-style message with `Problems:`, `Expected format:`, and `Example:`.

## When to use
Use when the user describes visual semantics — objects, scenes, styles, activities, or free-form image content (e.g., "sunset over mountains", "a cat sitting on a couch"). Prefer this over `datetime` for content queries. Can be used multiple times; multiple `clip` filters are fused via RRF.
