"""Print, write, or verify the checked-in OpenAPI snapshot.

In Windows PowerShell, generate in the mounted backend directory and copy the file
to avoid shell code-page conversions of Vietnamese descriptions:
    docker compose exec api python -m app.tools.openapi_snapshot --write /app/backend/openapi.generated.json
    Copy-Item backend/openapi.generated.json docs/openapi.json -Force
    Remove-Item backend/openapi.generated.json
    docker compose exec api python -m app.tools.openapi_snapshot --check
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_PATH = REPOSITORY_ROOT / "docs" / "openapi.json"


def render_openapi() -> str:
    """Return stable, UTF-8 JSON for the current FastAPI application schema."""
    from app.main import app

    return (
        json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )


def check_snapshot() -> int:
    """Return nonzero if the checked-in contract differs from the app."""
    if not SNAPSHOT_PATH.is_file():
        print(f"OpenAPI snapshot is missing: {SNAPSHOT_PATH}", file=sys.stderr)
        print("Generate it with --write and commit the result.", file=sys.stderr)
        return 1

    expected = render_openapi()
    actual = SNAPSHOT_PATH.read_text(encoding="utf-8-sig")
    if actual == expected:
        print("OpenAPI snapshot matches the application.")
        return 0

    print(
        "OpenAPI contract changed; review and update docs/openapi.json:",
        file=sys.stderr,
    )
    diff = difflib.unified_diff(
        actual.splitlines(keepends=True),
        expected.splitlines(keepends=True),
        fromfile="docs/openapi.json (committed)",
        tofile="docs/openapi.json (generated)",
    )
    sys.stderr.writelines(diff)
    return 1


def write_snapshot(path: Path) -> int:
    """Write generated UTF-8 JSON to a caller-selected mounted path."""
    path.write_text(render_openapi(), encoding="utf-8")
    print(f"Wrote OpenAPI snapshot to {path}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--stdout", action="store_true", help="write the generated JSON to stdout"
    )
    mode.add_argument(
        "--check", action="store_true", help="compare against docs/openapi.json"
    )
    mode.add_argument(
        "--write",
        type=Path,
        metavar="PATH",
        help="write generated UTF-8 JSON to PATH",
    )
    args = parser.parse_args()
    if args.stdout:
        sys.stdout.write(render_openapi())
        return 0
    if args.write:
        return write_snapshot(args.write)
    return check_snapshot()


if __name__ == "__main__":
    raise SystemExit(main())
