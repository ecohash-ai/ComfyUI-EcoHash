#!/usr/bin/env python3
"""Exercise the dedicated image nodes directly against a real inference service.

Configure ECOHASH_DEDICATED_* or [dedicated] in config.ini first. No keys or URLs
are accepted as CLI arguments. This calls the same node methods as ComfyUI, but
does not launch or validate the ComfyUI workflow executor.
"""

import argparse
from pathlib import Path
import sys
import tempfile

# Permit execution from any working directory without installing this custom node.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ecohash import client, conversions
from ecohash_nodes.image_nodes import EcoHashDedicatedImageEdit, EcoHashDedicatedImageGenerate, SIZES


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Exact deployed generation model ID")
    parser.add_argument("--edit-model", help="Also test image editing with this deployed model ID")
    parser.add_argument("--connection", default="dedicated", help="Saved connection ID (default: dedicated)")
    parser.add_argument("--edit-connection", help="Connection ID for editing (default: same as generation)")
    parser.add_argument("--prompt", default="a small red apple on a plain white background, product photo")
    parser.add_argument("--edit-prompt", default="make the apple bright green")
    parser.add_argument("--size", choices=SIZES, default="512x512")
    parser.add_argument("--width", type=int, default=1024, help="Width when size=custom")
    parser.add_argument("--height", type=int, default=1024, help="Height when size=custom")
    parser.add_argument("--steps", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    if not 0 <= args.steps <= 100 or not -1 <= args.seed <= 2**31 - 1:
        parser.error("steps must be 0..100 and seed must be -1..2147483647")

    output_dir = args.output_dir or Path(tempfile.mkdtemp(prefix="ecohash-dedicated-smoke-"))
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        (image,) = EcoHashDedicatedImageGenerate().generate(
            args.model, args.prompt, args.size, args.steps, args.seed,
            width=args.width, height=args.height, connection=args.connection,
        )
        path = output_dir / "generated.png"
        path.write_bytes(conversions.image_tensor_to_png_bytes(image))
        print(f"PASS generation: {image.shape[2]}x{image.shape[1]} -> {path}")
        if args.edit_model:
            (edited,) = EcoHashDedicatedImageEdit().edit(image, args.edit_model, args.edit_prompt, "auto", connection=args.edit_connection or args.connection)
            path = output_dir / "edited.png"
            path.write_bytes(conversions.image_tensor_to_png_bytes(edited))
            print(f"PASS editing: {edited.shape[2]}x{edited.shape[1]} -> {path}")
    except (client.EcoHashError, OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
