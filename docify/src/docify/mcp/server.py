"""MCP server for docify."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional, Literal, Any

import yaml
from mcp.server.fastmcp import FastMCP

from ..core.models import (
    Feature,
    FeatureStatus,
    FileAnchor,
    SymbolAnchor,
    Priority,
    Spec,
    SpecFeatureAction,
    BacklogItem,
)
from ..core.store import Store
from ..checker.check import Checker

mcp = FastMCP("docify", dependencies=["pydantic", "pyyaml", "tree-sitter", "tree-sitter-language-pack"])


def _store() -> Store:
    return Store(Path.cwd())


@mcp.resource("docify://overview")
def get_overview() -> str:
    """Get compact overview of features and their staleness states."""
    store = _store()
    index = store.load_index()
    features = store.list_features()
    states = index.get("features", {})

    lines = ["# docify Project Overview", ""]
    if not features:
        lines.append("No features documented yet. Use `feature add` or `ingest_spec`.")
        return "\n".join(lines)

    lines.append(f"Total features: {len(features)}")
    for f in features:
        state = states.get(f.id, {}).get("state", "unindexed")
        lines.append(f"- **{f.id}** ({f.title}) - Status: `{f.status.value}`, Staleness: `{state}`")

    return "\n".join(lines)


@mcp.prompt("workflow")
def mcp_workflow_prompt() -> str:
    """Prompt workflow guide for agent developers using docify."""
    return """You are developing code in a project that uses docify for living feature documentation.
Please adhere to the following workflow:
1. Before changing any code, call `find_features_for_code` with the file paths and symbols you plan to edit.
2. Read the documentation for any affected features using `get_feature` to understand business logic, constraints, and past decisions.
3. Perform your code changes.
4. If your changes affect the feature's behavior or implementation detail, update the markdown content of the feature doc.
5. Once code and documents are aligned, call `mark_updated` to recalculate anchor hashes and resolve the stale state.
6. If you discover technical debt or find unimplemented areas, log them with `upsert_backlog_item`.
"""


@mcp.tool()
def list_features(
    status: Optional[str] = None,
    tag: Optional[str] = None,
    query: Optional[str] = None,
) -> str:
    """List features filtered by status, tag, and search query."""
    store = _store()
    index = store.load_index()
    states = index.get("features", {})
    results = []

    for f in store.list_features():
        if status and f.status.value != status:
            continue
        if tag and tag not in f.tags:
            continue
        if query and (query.lower() not in f.id.lower() and query.lower() not in f.title.lower() and query.lower() not in f.body.lower()):
            continue

        state = states.get(f.id, {}).get("state", "unindexed")
        results.append({
            "id": f.id,
            "title": f.title,
            "status": f.status.value,
            "priority": f.priority.value,
            "tags": f.tags,
            "state": state,
        })
    return json.dumps(results, indent=2, ensure_ascii=False)


@mcp.tool()
def get_feature(id: str) -> str:
    """Retrieve full documentation, code anchors, and check status of a feature."""
    store = _store()
    feature = store.get_feature(id)
    if feature is None:
        return f"Feature `{id}` not found."

    checker = Checker(store)
    result, _ = checker.check_feature(feature)

    obj = {
        "id": feature.id,
        "title": feature.title,
        "status": feature.status.value,
        "priority": feature.priority.value,
        "tags": feature.tags,
        "relations": [r.model_dump() for r in feature.relations],
        "specs": feature.specs,
        "updated_at": feature.updated_at,
        "verified_commit": feature.verified_commit,
        "state": result.state.value,
        "anchors": [],
        "body": feature.body,
    }

    for ar in result.anchors:
        a = ar.anchor
        anchor_data: dict[str, Any] = {
            "type": a.type,
            "path": a.path,
            "state": ar.state.value,
            "detail": ar.detail,
        }
        if isinstance(a, SymbolAnchor):
            anchor_data["symbol"] = a.symbol
            anchor_data["kind"] = a.kind
        obj["anchors"].append(anchor_data)

    return json.dumps(obj, indent=2, ensure_ascii=False)


@mcp.tool()
def find_features_for_code(paths: list[str] | str, symbol: Optional[str] = None) -> str:
    """Reverse search: find which features are mapped to code file paths and optional symbol name."""
    store = _store()
    if isinstance(paths, str):
        path_list = [paths]
    else:
        path_list = paths

    matched = []
    path_set = set(path_list)

    for f in store.list_features():
        has_match = False
        for a in f.anchors:
            if a.path in path_set:
                if symbol:
                    if isinstance(a, SymbolAnchor) and a.symbol == symbol:
                        has_match = True
                        break
                else:
                    has_match = True
                    break
        if has_match:
            matched.append({
                "id": f.id,
                "title": f.title,
                "status": f.status.value,
            })
    return json.dumps(matched, indent=2, ensure_ascii=False)


@mcp.tool()
def check_staleness(scope: Optional[str] = None) -> str:
    """Execute checking for staleness. Returns feature check results."""
    store = _store()
    checker = Checker(store)
    results, _ = checker.check_all(only_changed=False)

    out = []
    for r in results:
        # Check scope filter (if folder path subset)
        if scope:
            feature = store.get_feature(r.feature_id)
            if not feature or not any(scope in a.path for a in feature.anchors):
                continue

        out.append({
            "feature_id": r.feature_id,
            "state": r.state.value,
            "anchors": [
                {
                    "path": ar.anchor.path,
                    "symbol": getattr(ar.anchor, "symbol", None),
                    "state": ar.state.value,
                    "detail": ar.detail,
                }
                for ar in r.anchors
            ]
        })
    return json.dumps(out, indent=2, ensure_ascii=False)


@mcp.tool()
def get_backlog(type: Optional[str] = None, status: Optional[str] = None) -> str:
    """Get all backlog items filtered by type (debt | growth) and status (open | in-progress | done | wontfix)."""
    store = _store()
    items = []
    for item in store.list_backlog():
        if type and item.type != type:
            continue
        if status and item.status != status:
            continue
        items.append(item.model_dump())
    return json.dumps(items, indent=2, ensure_ascii=False)


@mcp.tool()
def list_specs(status: Optional[str] = None) -> str:
    """List specifications filtered by status (open | in-progress | done)."""
    store = _store()
    specs = []
    for s in store.list_specs():
        if status and s.status != status:
            continue
        specs.append({
            "id": s.id,
            "title": s.title,
            "received_at": s.received_at,
            "source": s.source,
            "status": s.status,
            "features": [f.model_dump() for f in s.features],
        })
    return json.dumps(specs, indent=2, ensure_ascii=False)


@mcp.tool()
def get_spec(id: str) -> str:
    """Retrieve full detail of a specific specification."""
    store = _store()
    s = store.get_spec(id)
    if s is None:
        return f"Specification `{id}` not found."
    return json.dumps(s.model_dump(), indent=2, ensure_ascii=False)


@mcp.tool()
def upsert_feature(
    id: str,
    title: str = "",
    status: str = "planned",
    priority: str = "p2",
    tags: Optional[list[str]] = None,
    body: str = "",
) -> str:
    """Create or update a feature."""
    store = _store()
    feature = store.get_feature(id)
    if feature is None:
        feature = Feature(id=id)

    if title:
        feature.title = title
    if status:
        feature.status = FeatureStatus(status)
    if priority:
        feature.priority = Priority(priority)
    if tags is not None:
        feature.tags = tags
    if body:
        feature.body = body

    store.save_feature(feature)
    return f"Feature `{id}` upserted successfully."


@mcp.tool()
def link_code(feature_id: str, anchors: list[dict]) -> str:
    """Link code anchors to a feature. Anchors list keys: type ('file'|'symbol'), path, symbol? (if type is symbol)."""
    store = _store()
    feature = store.get_feature(feature_id)
    if feature is None:
        return f"Feature `{feature_id}` not found."

    checker = Checker(store)
    for a in anchors:
        t = a.get("type", "file")
        path = a.get("path")
        if not path:
            continue
        if t == "symbol":
            symbol = a.get("symbol")
            if not symbol:
                continue
            # Look up symbol hash if file exists
            from ..anchors.symbols import find_symbol
            sym = find_symbol(store.root / path, path, symbol)
            body_hash = sym.body_hash if sym else None
            kind = sym.kind if sym else None
            feature.anchors.append(SymbolAnchor(path=path, symbol=symbol, kind=kind, body_hash=body_hash))
        else:
            blob = checker.git.blob_hash(path)
            feature.anchors.append(FileAnchor(path=path, blob=blob))

    if feature.status == FeatureStatus.PLANNED and feature.anchors:
        feature.status = FeatureStatus.IN_PROGRESS

    store.save_feature(feature)
    # Index to update index.json
    checker.reindex_feature(feature)
    results, _ = checker.check_all(only_changed=False)
    checker.save_check_to_index(results)

    return f"Linked {len(anchors)} anchor(s) to feature `{feature_id}`."


@mcp.tool()
def mark_updated(feature_id: str) -> str:
    """Declare documentation for feature up to date. Recomputes anchor hashes."""
    store = _store()
    feature = store.get_feature(feature_id)
    if feature is None:
        return f"Feature `{feature_id}` not found."

    checker = Checker(store)
    checker.reindex_feature(feature)
    if feature.status == FeatureStatus.NEEDS_UPDATE:
        feature.status = FeatureStatus.IMPLEMENTED
    feature.updated_at = date.today().isoformat()
    feature.verified_commit = checker.git.head_commit()
    store.save_feature(feature)

    results, _ = checker.check_all(only_changed=False)
    checker.save_check_to_index(results)
    return f"Feature `{feature_id}` marked up to date."


@mcp.tool()
def ingest_spec(text: str, source: Optional[str] = None) -> str:
    """Ingest a specification. Accepts raw markdown or markdown with YAML frontmatter.

    Creates docs/specs/<spec_id>.md, and updates actioned features (creates planned, updates implemented to needs-update).
    """
    store = _store()
    import re
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n?", text, re.DOTALL)
    meta = {}
    body = text
    if match:
        meta = yaml.safe_load(match.group(1)) or {}
        body = text[match.end():]

    spec_id = meta.get("id")
    title = meta.get("title")
    if not title:
        first_line = body.strip().splitlines()[0] if body.strip() else "Untitled Spec"
        title = re.sub(r"^#+\s*", "", first_line).strip()

    if not spec_id:
        spec_id = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "spec-ingested"

    parsed_features = []
    for f in meta.get("features", []):
        parsed_features.append(SpecFeatureAction(id=f.get("id"), action=f.get("action", "update")))

    # Auto-matching heuristic if features list is empty
    if not parsed_features:
        body_words = set(re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", text.lower()))
        for feat in store.list_features():
            feat_words = {feat.id.lower(), feat.title.lower()} | {t.lower() for t in feat.tags}
            if feat_words & body_words:
                parsed_features.append(SpecFeatureAction(id=feat.id, action="update"))

    spec = Spec(
        id=spec_id,
        title=title,
        received_at=meta.get("received_at", date.today().isoformat()),
        source=source or meta.get("source", "mcp"),
        features=parsed_features,
        status=meta.get("status", "open"),
        body=body,
    )
    store.save_spec(spec)

    # Process features actions
    for fa in spec.features:
        f = store.get_feature(fa.id)
        if fa.action == "create":
            if f is None:
                new_f = Feature(
                    id=fa.id,
                    title=fa.id,
                    status=FeatureStatus.PLANNED,
                    specs=[spec.id],
                    body=f"## Что делает\n\n(создано по спеке `{spec.id}`)\n",
                )
                store.save_feature(new_f)
            else:
                if spec.id not in f.specs:
                    f.specs.append(spec.id)
                    store.save_feature(f)
        elif fa.action == "update":
            if f is not None:
                f.status = FeatureStatus.NEEDS_UPDATE
                if spec.id not in f.specs:
                    f.specs.append(spec.id)
                store.save_feature(f)

    # Index
    checker = Checker(store)
    results, _ = checker.check_all(only_changed=False)
    checker.save_check_to_index(results)

    return f"Ingested spec `{spec.id}`. Feature files updated accordingly."


@mcp.tool()
def upsert_backlog_item(
    id: str,
    title: str = "",
    type: Literal["debt", "growth"] = "debt",
    priority: str = "p2",
    features: Optional[list[str]] = None,
    status: Literal["open", "in-progress", "done", "wontfix"] = "open",
    body: str = "",
) -> str:
    """Create or update a backlog item."""
    store = _store()
    item = store.get_backlog_item(id)
    if item is None:
        item = BacklogItem(id=id)

    if title:
        item.title = title
    if type:
        item.type = type
    if priority:
        item.priority = Priority(priority)
    if features is not None:
        item.features = features
    if status:
        item.status = status
    if body:
        item.body = body

    store.save_backlog_item(item)
    return f"Backlog item `{id}` upserted successfully."


if __name__ == "__main__":
    mcp.run()
