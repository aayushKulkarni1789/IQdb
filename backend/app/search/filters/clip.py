from app.core import clip
from app.models import CLIP_Embedding
from app.search.filter import RankFilter
from sqlalchemy import func, literal, select


class ClipRank(RankFilter):
    kind = "clip"
    is_live = True

    def __init__(self, text: str, weight: float = 1.0) -> None:
        self.text = text
        self.weight = weight

    def to_spec(self) -> dict:
        return {"kind": "clip", "text": self.text, "weight": self.weight}

    @classmethod
    def from_spec(cls, spec: dict) -> "ClipRank":
        return cls(text=spec["text"], weight=float(spec.get("weight", 1.0)))

    def build_rank_cte(self, candidates):
        vec = clip.get_text_embeddings([self.text])[0]
        subq = candidates.subquery()
        distance = CLIP_Embedding.embedding.cosine_distance(vec)
        return select(
            subq.c.id.label("id"),
            func.row_number().over(order_by=distance).label("rank"),
            literal(self.weight).label("weight"),
        ).select_from(subq.join(CLIP_Embedding, CLIP_Embedding.image_id == subq.c.id))
