"""docify CLI: init, index, check, feature, link, mark-updated."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
import re
from typing import Optional, Literal

import typer

from ..anchors.symbols import find_symbol, language_for
from ..checker.check import Checker
import json
import yaml
from ..core.models import (
    Feature,
    FeatureStatus,
    FileAnchor,
    Priority,
    SymbolAnchor,
    Spec,
    SpecFeatureAction,
    BacklogItem,
)
from ..core.store import Store

app = typer.Typer(name="docify", help="Living feature documentation anchored to code.",
                  no_args_is_help=True)
feature_app = typer.Typer(help="Manage features", no_args_is_help=True)
app.add_typer(feature_app, name="feature")

spec_app = typer.Typer(help="Manage technical specifications", no_args_is_help=True)
app.add_typer(spec_app, name="spec")

backlog_app = typer.Typer(help="Manage backlog/task items", no_args_is_help=True)
app.add_typer(backlog_app, name="backlog")

STATE_STYLE = {
    "fresh": typer.colors.GREEN,
    "stale": typer.colors.YELLOW,
    "broken": typer.colors.RED,
    "unimplemented": typer.colors.BRIGHT_BLACK,
    "unindexed": typer.colors.CYAN,
}


def _store() -> Store:
    return Store(Path.cwd())


def _styled(state: str) -> str:
    return typer.style(state, fg=STATE_STYLE.get(state, typer.colors.WHITE), bold=True)


@app.command()
def init() -> None:
    """Create docs/features, docs/specs, docs/backlog and .docify/config.yaml."""
    store = _store()
    store.init_layout()
    checker = Checker(store)
    if not checker.git.is_repo():
        typer.secho("warning: not a git repository — staleness tracking requires git", fg=typer.colors.YELLOW)
    results, _ = checker.check_all(only_changed=False)
    checker.save_check_to_index(results)
    typer.secho(f"initialized docify in {store.root}", fg=typer.colors.GREEN)
    typer.echo(f"  features dir: {store.config['features_dir']}")
    typer.echo(f"  config:       .docify/config.yaml")


@app.command()
def index(full: bool = typer.Option(False, "--full", help="Reindex everything")) -> None:
    """(Re)build the anchor index: recompute hashes for all features."""
    store = _store()
    checker = Checker(store)
    count = 0
    for feature in store.list_features():
        checker.reindex_feature(feature)
        store.save_feature(feature)
        count += 1
    results, _ = checker.check_all(only_changed=False)
    checker.save_check_to_index(results)
    typer.secho(f"indexed {count} feature(s)", fg=typer.colors.GREEN)


@app.command()
def check(
    ci: bool = typer.Option(False, "--ci", help="Exit non-zero if any feature is stale/broken"),
    fix_anchors: bool = typer.Option(False, "--fix-anchors", help="Apply suggested anchor remaps"),
    full: bool = typer.Option(False, "--full", help="Check all features, ignore incremental cache"),
) -> None:
    """Check documentation staleness against the current code."""
    store = _store()
    checker = Checker(store)
    results, remaps = checker.check_all(only_changed=not full)

    if fix_anchors and remaps:
        applied = checker.apply_remaps(remaps)
        typer.secho(f"applied {applied} anchor remap(s)", fg=typer.colors.CYAN)
        results, remaps = checker.check_all(only_changed=False)

    counts: dict[str, int] = {}
    for r in results:
        state = r.state.value
        counts[state] = counts.get(state, 0) + 1
        typer.echo(f"{_styled(state):<24} {r.feature_id}")
        for ar in r.anchors:
            if ar.detail:
                typer.echo(f"    - {ar.detail}")

    summary = ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))
    typer.echo(f"\n{len(results)} feature(s): {summary or 'none'}")

    problems = counts.get("stale", 0) + counts.get("broken", 0)
    if not ci:
        checker.save_check_to_index(results)
    if ci and problems:
        typer.secho(
            f"\nCI: {problems} feature doc(s) need updating. "
            "Update the docs and run `docify mark-updated <id>`.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)


@feature_app.command("add")
def feature_add(
    feature_id: str = typer.Argument(..., help="Feature id (slug, becomes the filename)"),
    title: str = typer.Option("", "--title"),
    status: FeatureStatus = typer.Option(FeatureStatus.PLANNED, "--status"),
    priority: Priority = typer.Option(Priority.P2, "--priority"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated tags"),
) -> None:
    """Create a new feature doc."""
    store = _store()
    if store.get_feature(feature_id) is not None:
        typer.secho(f"feature `{feature_id}` already exists", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    feature = Feature(
        id=feature_id,
        title=title or feature_id,
        status=status,
        priority=priority,
        tags=[t.strip() for t in tags.split(",")] if tags else [],
        updated_at=date.today().isoformat(),
        body=f"## Что делает\n\n(описание фичи `{feature_id}`)\n",
    )
    path = store.save_feature(feature)
    typer.secho(f"created {path.relative_to(store.root)}", fg=typer.colors.GREEN)


@feature_app.command("list")
def feature_list(
    status: Optional[str] = typer.Option(None, "--status"),
    tag: Optional[str] = typer.Option(None, "--tag"),
) -> None:
    """List features with their check state."""
    store = _store()
    index = store.load_index()
    states = index.get("features", {})
    for f in store.list_features():
        if status and f.status.value != status:
            continue
        if tag and tag not in f.tags:
            continue
        check_state = states.get(f.id, {}).get("state", "?")
        tags = f" [{', '.join(f.tags)}]" if f.tags else ""
        typer.echo(f"{_styled(check_state):<24} {f.id:<28} {f.status.value:<14} {f.title}{tags}")


@feature_app.command("show")
def feature_show(feature_id: str) -> None:
    """Show feature docs, anchors and their current state."""
    store = _store()
    feature = store.get_feature(feature_id)
    if feature is None:
        typer.secho(f"feature `{feature_id}` not found", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    checker = Checker(store)
    result, _ = checker.check_feature(feature, {})
    typer.secho(f"# {feature.title} ({feature.id})", bold=True)
    typer.echo(f"status: {feature.status.value} | priority: {feature.priority.value} | check: {_styled(result.state.value)}")
    if feature.tags:
        typer.echo(f"tags: {', '.join(feature.tags)}")
    typer.echo("\nanchors:")
    if not feature.anchors:
        typer.echo("  (none — feature is unimplemented or not linked)")
    for ar in result.anchors:
        a = ar.anchor
        target = f"{a.path}::{a.symbol}" if isinstance(a, SymbolAnchor) else a.path
        line = f"  {_styled(ar.state.value):<24} {target}"
        typer.echo(line)
        if ar.detail:
            typer.echo(f"      {ar.detail}")
    typer.echo(f"\n{feature.body}")


@feature_app.command("update")
def feature_update(
    feature_id: str,
    status: Optional[FeatureStatus] = typer.Option(None, "--status"),
    priority: Optional[Priority] = typer.Option(None, "--priority"),
    title: Optional[str] = typer.Option(None, "--title"),
) -> None:
    """Update feature fields."""
    store = _store()
    feature = store.get_feature(feature_id)
    if feature is None:
        typer.secho(f"feature `{feature_id}` not found", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    if status is not None:
        feature.status = status
    if priority is not None:
        feature.priority = priority
    if title is not None:
        feature.title = title
    store.save_feature(feature)
    typer.secho(f"updated {feature_id}", fg=typer.colors.GREEN)


@app.command()
def link(
    feature_id: str = typer.Argument(...),
    target: str = typer.Argument(..., help="path/to/file.ts or path/to/file.ts::Qualified.Symbol"),
) -> None:
    """Anchor code to a feature. Symbol anchors: `docify link auth-login src/auth.ts::LoginService.authenticate`."""
    store = _store()
    feature = store.get_feature(feature_id)
    if feature is None:
        typer.secho(f"feature `{feature_id}` not found", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    checker = Checker(store)

    if "::" in target:
        path, symbol = target.split("::", 1)
        if language_for(path) is None:
            typer.secho(f"unsupported language for symbol anchors: {path}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        sym = find_symbol(store.root / path, path, symbol)
        if sym is None:
            typer.secho(f"symbol `{symbol}` not found in {path}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        feature.anchors.append(SymbolAnchor(path=path, symbol=symbol, kind=sym.kind, body_hash=sym.body_hash))
    else:
        blob = checker.git.blob_hash(target)
        if blob is None:
            typer.secho(f"file not found: {target}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        feature.anchors.append(FileAnchor(path=target, blob=blob))

    if feature.status == FeatureStatus.PLANNED:
        feature.status = FeatureStatus.IN_PROGRESS
    store.save_feature(feature)
    typer.secho(f"linked {target} -> {feature_id}", fg=typer.colors.GREEN)


@app.command("mark-updated")
def mark_updated(feature_id: str) -> None:
    """Declare docs up to date: recompute anchor hashes and clear needs-update."""
    store = _store()
    feature = store.get_feature(feature_id)
    if feature is None:
        typer.secho(f"feature `{feature_id}` not found", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    checker = Checker(store)
    checker.reindex_feature(feature)
    if feature.status == FeatureStatus.NEEDS_UPDATE:
        feature.status = FeatureStatus.IMPLEMENTED
    feature.updated_at = date.today().isoformat()
    feature.verified_commit = checker.git.head_commit()
    store.save_feature(feature)
    results, _ = checker.check_all(only_changed=False)
    checker.save_check_to_index(results)
    typer.secho(f"{feature_id}: docs marked up to date", fg=typer.colors.GREEN)


@app.command()
def serve(
    port: int = typer.Option(4321, "--port", help="Port to run the dashboard on"),
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind the dashboard to"),
) -> None:
    """Start the local web dashboard and API server."""
    import uvicorn
    from ..web.app import app as fastapi_app
    typer.echo(f"Starting docify dashboard at http://{host}:{port}")
    uvicorn.run(fastapi_app, host=host, port=port)


@app.command()
def mcp() -> None:
    """Start the MCP server (stdio transport)."""
    from ..mcp.server import mcp as mcp_instance
    mcp_instance.run()


@app.command("install")
def install(
    project: bool = typer.Option(False, "--project", help="Configure MCP for the current project")
) -> None:
    """Configure docify MCP server for Claude and Cursor, and output instructions."""
    store = _store()
    
    # Generate the MCP configuration blocks
    py_path = sys.executable
    bin_dir = Path(py_path).parent
    docify_bin = bin_dir / "docify"
    if not docify_bin.exists():
        docify_bin = Path(sys.argv[0]).resolve()
        
    mcp_config = {
        "command": str(docify_bin),
        "args": ["mcp"],
        "env": {}
    }
    
    config_json = json.dumps({"mcpServers": {"docify": mcp_config}}, indent=2)
    typer.secho("\n--- Claude Desktop config block ---", fg=typer.colors.CYAN)
    typer.echo(config_json)
    
    # Try to write to Claude Desktop config
    claude_config_path = Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
    if claude_config_path.parent.exists():
        try:
            current_config = {}
            if claude_config_path.exists():
                current_config = json.loads(claude_config_path.read_text())
            current_config.setdefault("mcpServers", {})["docify"] = mcp_config
            claude_config_path.write_text(json.dumps(current_config, indent=2))
            typer.secho(f"Successfully configured Claude Desktop at: {claude_config_path}", fg=typer.colors.GREEN)
        except Exception as e:
            typer.secho(f"Failed to auto-configure Claude Desktop: {e}", fg=typer.colors.YELLOW)
    
    if project:
        # Write workflow instructions to CLAUDE.md
        claude_md = store.root / "CLAUDE.md"
        workflow_text = (
            "\n## docify Workflow\n"
            "This project uses docify for feature documentation and staleness checking. "
            "Please follow these guidelines:\n"
            "1. Run `docify check` to see if any feature documentation is stale.\n"
            "2. When modifying code linked to a feature, update its documentation in `docs/features/<feature-id>.md`.\n"
            "3. After updating, run `docify mark-updated <feature-id>` to acknowledge and reset its staleness status.\n"
        )
        if claude_md.exists():
            text = claude_md.read_text()
            if "docify Workflow" not in text:
                claude_md.write_text(text + workflow_text)
                typer.secho(f"Appended docify workflow to CLAUDE.md", fg=typer.colors.GREEN)
        else:
            claude_md.write_text(workflow_text)
            typer.secho(f"Created CLAUDE.md with docify workflow guidelines", fg=typer.colors.GREEN)


@spec_app.command("ingest")
def spec_ingest(
    file_path: str = typer.Argument(..., help="Path to specification markdown file, or '-' for stdin")
) -> None:
    """Ingest a spec file, create new features or mark existing ones as needs-update."""
    store = _store()
    if file_path == "-":
        text = sys.stdin.read()
    else:
        p = Path(file_path)
        if not p.exists():
            typer.secho(f"File not found: {file_path}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        text = p.read_text()
        
    checker = Checker(store)
    
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n?", text, re.DOTALL)
    meta = {}
    body = text
    if match:
        meta = yaml.safe_load(match.group(1)) or {}
        body = text[match.end():]

    spec_id = meta.get("id")
    if not spec_id:
        typer.secho("Error: specification text must contain an `id` in YAML frontmatter.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    parsed_features = []
    for f in meta.get("features", []):
         parsed_features.append(SpecFeatureAction(id=f.get("id"), action=f.get("action", "update")))

    spec = Spec(
        id=spec_id,
        title=meta.get("title", spec_id),
        received_at=meta.get("received_at", date.today().isoformat()),
        source=meta.get("source", "cli"),
        features=parsed_features,
        status=meta.get("status", "open"),
        body=body.strip(),
    )

    store.save_spec(spec)
    typer.secho(f"Ingested specification: {spec.id}", fg=typer.colors.GREEN)

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
                typer.echo(f"  - Created planned feature `{fa.id}`")
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
                typer.echo(f"  - Marked feature `{fa.id}` as needing update")

    # Index
    results, _ = checker.check_all(only_changed=False)
    checker.save_check_to_index(results)


@backlog_app.command("add")
def backlog_add(
    id: str = typer.Argument(..., help="Backlog item unique ID"),
    title: str = typer.Argument(..., help="Backlog item title"),
    type_val: Literal["debt", "growth"] = typer.Option("debt", "--type", help="debt | growth"),
    priority: Priority = typer.Option(Priority.P2, "--priority"),
    features: Optional[str] = typer.Option(None, "--features", help="Comma-separated linked features"),
) -> None:
    """Add an item to the backlog."""
    store = _store()
    item = BacklogItem(
        id=id,
        title=title,
        type=type_val,
        priority=priority,
        features=[f.strip() for f in features.split(",")] if features else [],
        status="open",
        body=f"## Описание\n\n(описание техдолга `{id}`)\n",
    )
    store.save_backlog_item(item)
    typer.secho(f"Created backlog item {id}", fg=typer.colors.GREEN)


@backlog_app.command("list")
def backlog_list() -> None:
    """List all backlog items."""
    store = _store()
    items = store.list_backlog()
    for item in items:
        feats = f" [{', '.join(item.features)}]" if item.features else ""
        typer.echo(f"{item.status:<12} {item.id:<18} {item.type:<8} {item.priority.value:<4} {item.title}{feats}")


@backlog_app.command("done")
def backlog_done(id: str) -> None:
    """Mark a backlog item as resolved/done."""
    store = _store()
    item = store.get_backlog_item(id)
    if item is None:
        typer.secho(f"Backlog item {id} not found", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    item.status = "done"
    store.save_backlog_item(item)
    typer.secho(f"Backlog item {id} marked as done", fg=typer.colors.GREEN)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
