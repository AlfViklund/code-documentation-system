"""FastAPI web server backend for docify dashboard."""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path
from typing import Optional, Literal, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from watchfiles import awatch

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

app = FastAPI(title="docify API")

# Enable CORS for Next.js dev server (default port 3000 / 3333)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _store() -> Store:
    return Store(Path.cwd())


# -- API Models --------------------------------------------------------

class FeatureUpsertRequest(BaseModel):
    id: str
    title: str = ""
    status: FeatureStatus = FeatureStatus.PLANNED
    priority: Priority = Priority.P2
    tags: list[str] = Field(default_factory=list)
    body: str = ""


class LinkAnchorsRequest(BaseModel):
    anchors: list[dict] = Field(default_factory=list)


class IngestSpecRequest(BaseModel):
    text: str
    source: Optional[str] = None


# -- Endpoints ---------------------------------------------------------

@app.get("/api/features")
def get_features(status: Optional[str] = None, tag: Optional[str] = None):
    store = _store()
    index = store.load_index()
    states = index.get("features", {})
    results = []

    for f in store.list_features():
        if status and f.status.value != status:
            continue
        if tag and tag not in f.tags:
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
    return results


@app.get("/api/features/{feature_id}")
def get_feature(feature_id: str):
    store = _store()
    feature = store.get_feature(feature_id)
    if feature is None:
        raise HTTPException(status_code=404, detail=f"Feature {feature_id} not found")

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
            anchor_data["body_hash"] = a.body_hash
        else:
            anchor_data["blob"] = getattr(a, "blob", None)
        obj["anchors"].append(anchor_data)

    return obj


@app.post("/api/features")
def upsert_feature(req: FeatureUpsertRequest):
    store = _store()
    feature = store.get_feature(req.id)
    if feature is None:
        feature = Feature(id=req.id)

    feature.title = req.title or req.id
    feature.status = req.status
    feature.priority = req.priority
    feature.tags = req.tags
    if req.body:
        feature.body = req.body

    store.save_feature(feature)
    return {"status": "ok", "message": f"Feature {req.id} saved"}


@app.post("/api/features/{feature_id}/mark-updated")
def mark_feature_updated(feature_id: str):
    store = _store()
    feature = store.get_feature(feature_id)
    if feature is None:
        raise HTTPException(status_code=404, detail=f"Feature {feature_id} not found")

    checker = Checker(store)
    checker.reindex_feature(feature)
    if feature.status == FeatureStatus.NEEDS_UPDATE:
        feature.status = FeatureStatus.IMPLEMENTED
    feature.updated_at = date.today().isoformat()
    feature.verified_commit = checker.git.head_commit()
    store.save_feature(feature)

    results, _ = checker.check_all(only_changed=False)
    checker.save_check_to_index(results)
    return {"status": "ok", "message": f"Feature {feature_id} marked up to date"}


@app.post("/api/features/{feature_id}/link")
def link_code(feature_id: str, req: LinkAnchorsRequest):
    store = _store()
    feature = store.get_feature(feature_id)
    if feature is None:
        raise HTTPException(status_code=404, detail=f"Feature {feature_id} not found")

    checker = Checker(store)
    for a in req.anchors:
        t = a.get("type", "file")
        path = a.get("path")
        if not path:
            continue
        if t == "symbol":
            symbol = a.get("symbol")
            if not symbol:
                continue
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
    checker.reindex_feature(feature)
    results, _ = checker.check_all(only_changed=False)
    checker.save_check_to_index(results)
    return {"status": "ok", "message": f"Linked {len(req.anchors)} anchor(s) to feature {feature_id}"}


@app.get("/api/backlog")
def get_backlog(type: Optional[str] = None, status: Optional[str] = None):
    store = _store()
    items = []
    for item in store.list_backlog():
        if type and item.type != type:
            continue
        if status and item.status != status:
            continue
        items.append(item.model_dump())
    return items


@app.post("/api/backlog")
def upsert_backlog_item(item: BacklogItem):
    store = _store()
    store.save_backlog_item(item)
    return {"status": "ok", "message": f"Backlog item {item.id} saved"}


@app.get("/api/specs")
def get_specs(status: Optional[str] = None):
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
    return specs


@app.get("/api/specs/{spec_id}")
def get_spec(spec_id: str):
    store = _store()
    s = store.get_spec(spec_id)
    if s is None:
        raise HTTPException(status_code=404, detail=f"Spec {spec_id} not found")
    return s.model_dump()


@app.post("/api/specs/ingest")
def ingest_spec(req: IngestSpecRequest):
    store = _store()
    import re
    import yaml
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n?", req.text, re.DOTALL)
    meta = {}
    body = req.text
    if match:
        meta = yaml.safe_load(match.group(1)) or {}
        body = req.text[match.end():]

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

    if not parsed_features:
        body_words = set(re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", req.text.lower()))
        for feat in store.list_features():
            feat_words = {feat.id.lower(), feat.title.lower()} | {t.lower() for t in feat.tags}
            if feat_words & body_words:
                parsed_features.append(SpecFeatureAction(id=feat.id, action="update"))

    spec = Spec(
        id=spec_id,
        title=title,
        received_at=meta.get("received_at", date.today().isoformat()),
        source=req.source or meta.get("source", "web"),
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
    return {"status": "ok", "message": f"Spec {spec_id} ingested"}


@app.get("/api/check")
def check_staleness():
    store = _store()
    checker = Checker(store)
    results, _ = checker.check_all(only_changed=False)
    out = []
    for r in results:
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
    return out


# -- WebSocket for hot reloading ---------------------------------------

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    store = _store()

    # Determine folders to watch
    dirs = [
        str(store.features_dir),
        str(store.specs_dir),
        str(store.backlog_dir),
    ]
    # Check if they exist, create if not
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)

    async def watch_folders():
        try:
            async for changes in awatch(*dirs):
                # Send update message on changes
                await websocket.send_text("reload")
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def send_heartbeat():
        try:
            while True:
                await asyncio.sleep(15)
                await websocket.send_text("ping")
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    watch_task = asyncio.create_task(watch_folders())
    ping_task = asyncio.create_task(send_heartbeat())
    try:
        while True:
            msg = await websocket.receive_text()
            if msg == "pong":
                pass
    except WebSocketDisconnect:
        pass
    finally:
        watch_task.cancel()
        ping_task.cancel()


# Mount Next.js static files if they exist (out directory)
out_path = Path(__file__).parent / "out"
if out_path.exists():
    app.mount("/", StaticFiles(directory=str(out_path), html=True), name="static")
