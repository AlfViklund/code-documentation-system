"""Reading and writing docify data: feature markdown files with YAML frontmatter,
config, and the derived index cache."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

import yaml

from .models import Feature, Spec, BacklogItem

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)

DEFAULT_CONFIG = {
    "features_dir": "docs/features",
    "specs_dir": "docs/specs",
    "backlog_dir": "docs/backlog",
    "ignore": ["node_modules/**", ".git/**", ".docify/**", "dist/**", ".next/**"],
}


class Store:
    """Filesystem access rooted at the repository root."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.docify_dir = self.root / ".docify"
        self.config = self._load_config()

    # -- config / index -------------------------------------------------

    def _load_config(self) -> dict[str, Any]:
        cfg_path = self.docify_dir / "config.yaml"
        cfg = dict(DEFAULT_CONFIG)
        if cfg_path.exists():
            loaded = yaml.safe_load(cfg_path.read_text()) or {}
            cfg.update(loaded)
        return cfg

    def init_layout(self) -> None:
        (self.root / self.config["features_dir"]).mkdir(parents=True, exist_ok=True)
        (self.root / self.config["specs_dir"]).mkdir(parents=True, exist_ok=True)
        (self.root / self.config["backlog_dir"]).mkdir(parents=True, exist_ok=True)
        self.docify_dir.mkdir(exist_ok=True)
        cfg_path = self.docify_dir / "config.yaml"
        if not cfg_path.exists():
            cfg_path.write_text(yaml.safe_dump(DEFAULT_CONFIG, sort_keys=False, allow_unicode=True))

    @property
    def index_path(self) -> Path:
        return self.docify_dir / "index.json"

    def load_index(self) -> dict[str, Any]:
        if self.index_path.exists():
            return json.loads(self.index_path.read_text())
        return {"last_indexed_commit": None, "features": {}}

    def save_index(self, index: dict[str, Any]) -> None:
        self.docify_dir.mkdir(exist_ok=True)
        self.index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False))

    # -- features --------------------------------------------------------

    @property
    def features_dir(self) -> Path:
        return self.root / self.config["features_dir"]

    def feature_path(self, feature_id: str) -> Path:
        return self.features_dir / f"{feature_id}.md"

    def list_features(self) -> list[Feature]:
        if not self.features_dir.exists():
            return []
        features = []
        for path in sorted(self.features_dir.glob("*.md")):
            features.append(self.load_feature_file(path))
        return features

    def get_feature(self, feature_id: str) -> Optional[Feature]:
        path = self.feature_path(feature_id)
        if not path.exists():
            return None
        return self.load_feature_file(path)

    def load_feature_file(self, path: Path) -> Feature:
        text = path.read_text()
        match = FRONTMATTER_RE.match(text)
        meta: dict[str, Any] = {}
        body = text
        if match:
            meta = yaml.safe_load(match.group(1)) or {}
            body = text[match.end():]
        meta.setdefault("id", path.stem)
        meta["body"] = body.strip()
        return Feature.model_validate(meta)

    def save_feature(self, feature: Feature) -> Path:
        meta = feature.model_dump(mode="json", exclude={"body"}, exclude_none=True)
        # drop empty collections for cleaner frontmatter
        meta = {k: v for k, v in meta.items() if v not in ([], {}, "")}
        frontmatter = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
        content = f"---\n{frontmatter}\n---\n\n{feature.body.strip()}\n"
        path = self.feature_path(feature.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    # -- specs -------------------------------------------------------------

    @property
    def specs_dir(self) -> Path:
        return self.root / self.config["specs_dir"]

    def spec_path(self, spec_id: str) -> Path:
        return self.specs_dir / f"{spec_id}.md"

    def list_specs(self) -> list[Spec]:
        if not self.specs_dir.exists():
            return []
        specs = []
        for path in sorted(self.specs_dir.glob("*.md")):
            specs.append(self.load_spec_file(path))
        return specs

    def get_spec(self, spec_id: str) -> Optional[Spec]:
        path = self.spec_path(spec_id)
        if not path.exists():
            return None
        return self.load_spec_file(path)

    def load_spec_file(self, path: Path) -> Spec:
        from .models import Spec
        text = path.read_text()
        match = FRONTMATTER_RE.match(text)
        meta: dict[str, Any] = {}
        body = text
        if match:
            meta = yaml.safe_load(match.group(1)) or {}
            body = text[match.end():]
        meta.setdefault("id", path.stem)
        meta["body"] = body.strip()
        return Spec.model_validate(meta)

    def save_spec(self, spec: Spec) -> Path:
        meta = spec.model_dump(mode="json", exclude={"body"}, exclude_none=True)
        meta = {k: v for k, v in meta.items() if v not in ([], {}, "")}
        frontmatter = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
        content = f"---\n{frontmatter}\n---\n\n{spec.body.strip()}\n"
        path = self.spec_path(spec.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    # -- backlog -----------------------------------------------------------

    @property
    def backlog_dir(self) -> Path:
        return self.root / self.config["backlog_dir"]

    def backlog_path(self, item_id: str) -> Path:
        return self.backlog_dir / f"{item_id}.md"

    def list_backlog(self) -> list[BacklogItem]:
        if not self.backlog_dir.exists():
            return []
        items = []
        for path in sorted(self.backlog_dir.glob("*.md")):
            items.append(self.load_backlog_file(path))
        return items

    def get_backlog_item(self, item_id: str) -> Optional[BacklogItem]:
        path = self.backlog_path(item_id)
        if not path.exists():
            return None
        return self.load_backlog_file(path)

    def load_backlog_file(self, path: Path) -> BacklogItem:
        from .models import BacklogItem
        text = path.read_text()
        match = FRONTMATTER_RE.match(text)
        meta: dict[str, Any] = {}
        body = text
        if match:
            meta = yaml.safe_load(match.group(1)) or {}
            body = text[match.end():]
        meta.setdefault("id", path.stem)
        meta["body"] = body.strip()
        return BacklogItem.model_validate(meta)

    def save_backlog_item(self, item: BacklogItem) -> Path:
        meta = item.model_dump(mode="json", exclude={"body"}, exclude_none=True)
        meta = {k: v for k, v in meta.items() if v not in ([], {}, "")}
        frontmatter = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
        content = f"---\n{frontmatter}\n---\n\n{item.body.strip()}\n"
        path = self.backlog_path(item.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

