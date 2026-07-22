from app.search.filter import SubsetFilter


class FaceFilter(SubsetFilter):
    kind = "face"
    is_live = False

    def build_predicate(self):
        raise NotImplementedError(
            "FaceFilter requires face detection + embedding (intended SQL: face_similarity >= <threshold>). Not yet implemented."
        )

    def to_spec(self) -> dict:
        return {"kind": "face"}

    @classmethod
    def from_spec(cls, spec: dict) -> "FaceFilter":
        return cls()
