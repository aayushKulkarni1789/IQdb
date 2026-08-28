from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict

from app.search.filter import FilterKind, SubsetFilter


class FaceFilterSpec(BaseModel):
    # Spec shape reserved for the future face implementation; only the kind
    # field is required today (design D6).
    model_config = ConfigDict(extra="ignore")

    kind: Literal[FilterKind.FACE] = FilterKind.FACE


class FaceFilter(SubsetFilter):
    kind = FilterKind.FACE
    is_live = False
    spec_model = FaceFilterSpec
    SPEC_FORMAT: ClassVar[str] = '{"kind": "face"}'
    SPEC_EXAMPLE: ClassVar[dict] = {"kind": "face"}

    def build_predicate(self):
        raise NotImplementedError(
            "FaceFilter requires face detection + embedding (intended SQL: face_similarity >= <threshold>). Not yet implemented."
        )

    def to_spec(self) -> dict:
        return {"kind": str(FilterKind.FACE)}

    @classmethod
    def from_spec(cls, spec_model: FaceFilterSpec) -> "FaceFilter":
        return cls()
