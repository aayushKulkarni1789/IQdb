from pathlib import Path
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, literal, select

from app.core import clip
from app.models import CLIP_Embedding
from app.search.filter import FilterKind, RankFilter

# Description is authored in clip.md alongside this module so prompt
# content stays in sync with filter semantics.
try:
    _CLIP_DESCRIPTION = Path(__file__).with_suffix(".md").read_text(encoding="utf-8")
except FileNotFoundError:
    _CLIP_DESCRIPTION = ""


class ClipRankSpec(BaseModel):
    # Pydantic spec model for the CLIP rank filter (design D6). Unknown extra
    # fields are ignored so clients can send richer bodies safely.
    model_config = ConfigDict(extra="ignore")

    kind: Literal[FilterKind.CLIP] = FilterKind.CLIP
    text: str
    weight: float = 1.0


class ClipRank(RankFilter):
    kind = FilterKind.CLIP
    is_live = True
    spec_model = ClipRankSpec
    SPEC_FORMAT: ClassVar[str] = (
        '{"kind": "clip", "text": "<search query>", "weight": <float, default 1.0>}'
    )
    SPEC_EXAMPLE: ClassVar[dict] = {"kind": "clip", "text": "a photo of a cat", "weight": 1.0}
    DESCRIPTION: ClassVar[str] = _CLIP_DESCRIPTION

    def __init__(self, text: str, weight: float = 1.0) -> None:
        self.text = text
        self.weight = weight

    def to_spec(self) -> dict:
        return {"kind": str(FilterKind.CLIP), "text": self.text, "weight": self.weight}

    @classmethod
    def from_spec(cls, spec_model: ClipRankSpec) -> "ClipRank":
        return cls(text=spec_model.text, weight=spec_model.weight)

    def build_rank_cte(self, candidates):
        vec = clip.get_text_embeddings([self.text])[0]
        subq = candidates.subquery()
        distance = CLIP_Embedding.embedding.cosine_distance(vec)
        return select(
            subq.c.id.label("id"),
            func.row_number().over(order_by=distance).label("rank"),
            literal(self.weight).label("weight"),
        ).select_from(subq.join(CLIP_Embedding, CLIP_Embedding.image_id == subq.c.id))
