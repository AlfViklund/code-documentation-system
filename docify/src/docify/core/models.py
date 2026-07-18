"""Core data models for docify: Feature, Anchor, Spec, BacklogItem."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Optional, Union
from pydantic import BaseModel, Field


class FeatureStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in-progress"
    IMPLEMENTED = "implemented"
    NEEDS_UPDATE = "needs-update"
    DEPRECATED = "deprecated"


class Priority(str, Enum):
    P0 = "p0"
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"


class FileAnchor(BaseModel):
    type: Literal["file"] = "file"
    path: str
    blob: Optional[str] = None  # git blob hash at verified_commit


class SymbolAnchor(BaseModel):
    type: Literal["symbol"] = "symbol"
    path: str
    symbol: str  # qualified name, e.g. "LoginService.authenticate"
    kind: Optional[str] = None  # function | class | method
    body_hash: Optional[str] = None  # sha256 of normalized symbol body


Anchor = Annotated[Union[FileAnchor, SymbolAnchor], Field(discriminator="type")]


class Relation(BaseModel):
    type: Literal["depends-on", "part-of", "supersedes"]
    id: str


class Feature(BaseModel):
    id: str
    title: str = ""
    status: FeatureStatus = FeatureStatus.PLANNED
    priority: Priority = Priority.P2
    tags: list[str] = Field(default_factory=list)
    anchors: list[Anchor] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    specs: list[str] = Field(default_factory=list)
    updated_at: Optional[str] = None  # ISO date
    verified_commit: Optional[str] = None
    body: str = ""  # markdown body (not part of frontmatter)


class AnchorState(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    BROKEN = "broken"
    UNINDEXED = "unindexed"  # anchor exists but has no saved hash yet


class FeatureCheckState(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    BROKEN = "broken"
    UNIMPLEMENTED = "unimplemented"
    EMPTY_BODY = "empty-body"


class AnchorCheckResult(BaseModel):
    anchor: Anchor
    state: AnchorState
    detail: str = ""


class FeatureCheckResult(BaseModel):
    feature_id: str
    state: FeatureCheckState
    anchors: list[AnchorCheckResult] = Field(default_factory=list)

    @staticmethod
    def aggregate(feature: Feature, results: list[AnchorCheckResult]) -> "FeatureCheckResult":
        # Validation for empty/placeholder body in implemented features
        body_text = (feature.body or "").strip()
        is_placeholder = "(описание фичи" in body_text.lower() or "(описание " in body_text.lower()
        if feature.status == FeatureStatus.IMPLEMENTED and (len(body_text) < 80 or is_placeholder):
            state = FeatureCheckState.EMPTY_BODY
        elif not feature.anchors:
            state = FeatureCheckState.UNIMPLEMENTED
        elif any(r.state == AnchorState.BROKEN for r in results):
            state = FeatureCheckState.BROKEN
        elif any(r.state == AnchorState.STALE for r in results):
            state = FeatureCheckState.STALE
        else:
            state = FeatureCheckState.FRESH
        return FeatureCheckResult(feature_id=feature.id, state=state, anchors=results)


class SpecFeatureAction(BaseModel):
    id: str
    action: Literal["create", "update"] = "update"


class Spec(BaseModel):
    id: str
    title: str = ""
    received_at: Optional[str] = None
    source: Optional[str] = None
    features: list[SpecFeatureAction] = Field(default_factory=list)
    status: Literal["open", "in-progress", "done"] = "open"
    body: str = ""


class BacklogItem(BaseModel):
    id: str
    title: str = ""
    type: Literal["debt", "growth"] = "debt"
    priority: Priority = Priority.P2
    features: list[str] = Field(default_factory=list)
    status: Literal["open", "in-progress", "done", "wontfix"] = "open"
    body: str = ""

