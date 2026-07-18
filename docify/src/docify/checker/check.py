"""Staleness checker: compares saved anchor hashes with the current repo state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..anchors.gitops import GitRepo
from ..anchors.symbols import find_by_body_hash, find_symbol
from ..core.models import (
    Anchor,
    AnchorCheckResult,
    AnchorState,
    Feature,
    FeatureCheckResult,
    FileAnchor,
    SymbolAnchor,
)
from ..core.store import Store


@dataclass
class RemapSuggestion:
    feature_id: str
    anchor: Anchor
    new_path: Optional[str] = None
    new_symbol: Optional[str] = None


class Checker:
    def __init__(self, store: Store):
        self.store = store
        self.git = GitRepo(store.root)

    def check_anchor(self, anchor: Anchor, renames: dict[str, str]) -> tuple[AnchorCheckResult, Optional[RemapSuggestion]]:
        path = renames.get(anchor.path, anchor.path)
        remap: Optional[RemapSuggestion] = None
        abs_path = self.store.root / path

        if isinstance(anchor, FileAnchor):
            current = self.git.blob_hash(path)
            if current is None:
                return AnchorCheckResult(anchor=anchor, state=AnchorState.BROKEN,
                                         detail=f"file not found: {path}"), None
            if anchor.blob is None:
                return AnchorCheckResult(anchor=anchor, state=AnchorState.UNINDEXED,
                                         detail="no saved hash — run `docify index`"), None
            if current == anchor.blob:
                state, detail = AnchorState.FRESH, ""
            else:
                state, detail = AnchorState.STALE, f"file content changed: {path}"
            if path != anchor.path:
                remap = RemapSuggestion(feature_id="", anchor=anchor, new_path=path)
            return AnchorCheckResult(anchor=anchor, state=state, detail=detail), remap

        # SymbolAnchor
        if not abs_path.exists():
            return AnchorCheckResult(anchor=anchor, state=AnchorState.BROKEN,
                                     detail=f"file not found: {path}"), None
        sym = find_symbol(abs_path, path, anchor.symbol)
        if sym is None:
            # symbol gone — try body-hash remap (rename detection)
            if anchor.body_hash:
                candidate = find_by_body_hash(abs_path, path, anchor.body_hash)
                if candidate is not None:
                    remap = RemapSuggestion(feature_id="", anchor=anchor,
                                            new_path=path, new_symbol=candidate.qualified_name)
                    return AnchorCheckResult(
                        anchor=anchor, state=AnchorState.BROKEN,
                        detail=f"symbol renamed? found identical body as `{candidate.qualified_name}` "
                               f"(run `docify check --fix-anchors`)"), remap
            return AnchorCheckResult(anchor=anchor, state=AnchorState.BROKEN,
                                     detail=f"symbol not found: {anchor.symbol} in {path}"), None
        if anchor.body_hash is None:
            return AnchorCheckResult(anchor=anchor, state=AnchorState.UNINDEXED,
                                     detail="no saved hash — run `docify index`"), None
        if sym.body_hash == anchor.body_hash:
            state, detail = AnchorState.FRESH, ""
        else:
            state, detail = AnchorState.STALE, f"body of `{anchor.symbol}` changed (lines {sym.start_line}-{sym.end_line})"
        if path != anchor.path:
            remap = RemapSuggestion(feature_id="", anchor=anchor, new_path=path)
        return AnchorCheckResult(anchor=anchor, state=state, detail=detail), remap

    def get_renames(self) -> dict[str, str]:
        """Retrieve git file renames since the last indexed commit."""
        index = self.store.load_index()
        last_commit = index.get("last_indexed_commit")
        return self.git.detect_renames(last_commit) if last_commit else {}

    def check_feature(self, feature: Feature, renames: Optional[dict[str, str]] = None) -> tuple[FeatureCheckResult, list[RemapSuggestion]]:
        if renames is None:
            renames = self.get_renames()
        results: list[AnchorCheckResult] = []
        remaps: list[RemapSuggestion] = []
        for anchor in feature.anchors:
            result, remap = self.check_anchor(anchor, renames)
            results.append(result)
            if remap is not None:
                remap.feature_id = feature.id
                remaps.append(remap)
        return FeatureCheckResult.aggregate(feature, results), remaps

    def check_all(self, only_changed: bool = True) -> tuple[list[FeatureCheckResult], list[RemapSuggestion]]:
        index = self.store.load_index()
        last_commit = index.get("last_indexed_commit")
        changed = self.git.changed_files(last_commit) if only_changed else None
        renames = self.git.detect_renames(last_commit) if last_commit else {}

        results: list[FeatureCheckResult] = []
        all_remaps: list[RemapSuggestion] = []
        for feature in self.store.list_features():
            anchor_paths = {a.path for a in feature.anchors}
            anchor_paths |= {renames.get(p, p) for p in anchor_paths}
            if changed is not None and anchor_paths and not (anchor_paths & changed):
                # untouched since last index -> trust cached freshness
                cached = index.get("features", {}).get(feature.id)
                if cached and cached.get("state") == "fresh":
                    results.append(FeatureCheckResult(feature_id=feature.id, state="fresh"))
                    continue
            result, remaps = self.check_feature(feature, renames)
            results.append(result)
            all_remaps.extend(remaps)
        return results, all_remaps

    def apply_remaps(self, remaps: list[RemapSuggestion]) -> int:
        """Rewrite anchors in feature files according to remap suggestions."""
        applied = 0
        by_feature: dict[str, list[RemapSuggestion]] = {}
        for r in remaps:
            by_feature.setdefault(r.feature_id, []).append(r)
        for feature_id, feature_remaps in by_feature.items():
            feature = self.store.get_feature(feature_id)
            if feature is None:
                continue
            for r in feature_remaps:
                for anchor in feature.anchors:
                    if anchor.path == r.anchor.path and (
                        isinstance(anchor, FileAnchor)
                        or (isinstance(anchor, SymbolAnchor)
                            and isinstance(r.anchor, SymbolAnchor)
                            and anchor.symbol == r.anchor.symbol)
                    ):
                        if r.new_path:
                            anchor.path = r.new_path
                        if r.new_symbol and isinstance(anchor, SymbolAnchor):
                            anchor.symbol = r.new_symbol
                        applied += 1
            self.store.save_feature(feature)
        return applied

    def reindex_feature(self, feature: Feature) -> Feature:
        """Recompute and persist anchor hashes: 'the docs are now up to date'."""
        for anchor in feature.anchors:
            abs_path = self.store.root / anchor.path
            if isinstance(anchor, FileAnchor):
                anchor.blob = self.git.blob_hash(anchor.path)
            else:
                sym = find_symbol(abs_path, anchor.path, anchor.symbol)
                if sym is not None:
                    anchor.body_hash = sym.body_hash
                    if anchor.kind is None:
                        anchor.kind = sym.kind
        return feature

    def save_check_to_index(self, results: list[FeatureCheckResult]) -> None:
        index = self.store.load_index()
        index["last_indexed_commit"] = self.git.head_commit()
        index["features"] = {
            r.feature_id: {"state": r.state.value if hasattr(r.state, "value") else str(r.state)}
            for r in results
        }
        self.store.save_index(index)
