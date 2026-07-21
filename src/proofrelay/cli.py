from __future__ import annotations

import argparse
import json
from pathlib import Path

from .live_pipeline import build_live_visual
from .models import ApprovedIncident
from .pipeline import build_preview_bundle


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="proofrelay",
        description="Build a provenance-verified media brief from an approved report.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build", help="build a local preview bundle")
    build.add_argument("incident", type=Path, help="approved incident JSON")
    build.add_argument("--output", type=Path, required=True, help="output directory")
    live = subparsers.add_parser(
        "generate-live",
        help="generate with OpenAI through Genblaze and persist to Backblaze B2",
    )
    live.add_argument("incident", type=Path, help="approved incident JSON")
    live.add_argument("--output", type=Path, required=True, help="local output directory")
    args = parser.parse_args()

    if args.command == "build":
        payload = json.loads(args.incident.read_text(encoding="utf-8"))
        incident = ApprovedIncident.model_validate(payload)
        bundle = build_preview_bundle(incident, args.output)
        print(bundle.model_dump_json(indent=2))
    elif args.command == "generate-live":
        payload = json.loads(args.incident.read_text(encoding="utf-8"))
        incident = ApprovedIncident.model_validate(payload)
        result = build_live_visual(incident, args.output)
        print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
