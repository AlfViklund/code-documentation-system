"""Git operations: blob hashes, changed files, rename detection."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


class GitRepo:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def _run(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout

    def is_repo(self) -> bool:
        try:
            self._run("rev-parse", "--git-dir")
            return True
        except (RuntimeError, FileNotFoundError):
            return False

    def head_commit(self) -> Optional[str]:
        try:
            return self._run("rev-parse", "HEAD").strip()
        except RuntimeError:
            return None  # empty repo, no commits yet

    def blob_hash(self, path: str) -> Optional[str]:
        """Blob hash of the file's *current on-disk* content (not what's committed)."""
        file_path = self.root / path
        if not file_path.exists():
            return None
        result = subprocess.run(
            ["git", "hash-object", str(file_path)],
            cwd=self.root,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()

    def changed_files(self, since_commit: Optional[str]) -> Optional[set[str]]:
        """Files changed since a commit (committed + staged + unstaged + untracked).
        Returns None when incremental detection is impossible (full scan needed)."""
        if not since_commit:
            return None
        changed: set[str] = set()
        try:
            diff = self._run("diff", "--name-only", "-M", f"{since_commit}..HEAD")
            changed.update(line for line in diff.splitlines() if line)
        except RuntimeError:
            return None  # commit unknown (rebase, shallow clone) -> full scan
        status = self._run("status", "--porcelain", "--find-renames")
        for line in status.splitlines():
            entry = line[3:].strip()
            if " -> " in entry:
                old, new = entry.split(" -> ", 1)
                changed.update((old.strip('"'), new.strip('"')))
            elif entry:
                changed.add(entry.strip('"'))
        return changed

    def detect_renames(self, since_commit: str) -> dict[str, str]:
        """Map of old_path -> new_path for renames since a commit."""
        renames: dict[str, str] = {}
        try:
            out = self._run(
                "diff", "--name-status", "-M", f"{since_commit}..HEAD"
            )
            for line in out.splitlines():
                parts = line.split("\t")
                if parts and parts[0].startswith("R") and len(parts) == 3:
                    renames[parts[1]] = parts[2]
        except RuntimeError:
            pass

        try:
            status = self._run("status", "--porcelain", "--find-renames")
            for line in status.splitlines():
                entry = line[3:].strip()
                if " -> " in entry:
                    old, new = entry.split(" -> ", 1)
                    renames[old.strip('"')] = new.strip('"')
        except RuntimeError:
            pass

        return renames
