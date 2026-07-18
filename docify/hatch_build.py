import shutil
import subprocess
from pathlib import Path
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        docify_dir = Path(self.root).resolve()
        project_root = docify_dir.parent
        out_src = project_root / "out"
        out_dst = docify_dir / "src" / "docify" / "web" / "out"

        if not out_src.exists():
            try:
                subprocess.run(["pnpm", "install"], cwd=project_root, check=True)
                subprocess.run(["pnpm", "build"], cwd=project_root, check=True)
            except Exception as e:
                print(f"[docify hatch_build] Warning: failed to build Next.js frontend automatically: {e}")

        if out_src.exists():
            if out_dst.exists():
                shutil.rmtree(out_dst)
            shutil.copytree(out_src, out_dst)
            print(f"[docify hatch_build] Copied Next.js static assets from {out_src} to {out_dst}")
