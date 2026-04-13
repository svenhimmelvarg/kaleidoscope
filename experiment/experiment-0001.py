#!/usr/bin/env python3
"""
experiment-0001.py — Stage 2 parameter sweep for ComfyUI pipeline

Takes a pipeline JSON, generates variants by sweeping Stage 2 parameters
(ClownGuide weight/cutoff, LatentNoised strength, sampler denoise),
and optionally queues them to a running ComfyUI instance.

Usage:
    python3 experiment-0001.py ./pipeline-001.json --limit 5
    python3 experiment-0001.py ./pipeline-001.json --limit 1 --dry-run
    python3 experiment-0001.py ./pipeline-001.json --round 1 --limit 20
    python3 experiment-0001.py ./pipeline-001.json --round 2 --best-denoise 0.55 --best-noise 0.6

Rounds:
    1: Sweep denoise × noise_strength (guide fixed at conservative values)
    2: Sweep guide weight × cutoff (denoise/noise locked from round 1)
    3: Seed robustness check (all params locked, sweep seeds)
    all: Full sweep of all parameters (use --limit to cap)
"""

import argparse
import copy
import itertools
import json
import os
import random
import sys
import time
import urllib.request
import urllib.error
import uuid
import websocket


# =============================================================================
# Stage 2 node IDs — DO NOT TOUCH Stage 1
# =============================================================================
STAGE2_SAMPLER = "72"  # ClownsharKSampler_Beta (stage 2)
STAGE2_GUIDE = "71"  # ClownGuide_Beta (stage 2)
STAGE2_NOISE = "95"  # LatentNoised
STAGE2_SAVE = "77"  # SaveImage output
STAGE1_RESOLUTION = "47"  # FluxResolutionNode
STAGE2_LATENT_SCALE = "87"  # FloatConstant for upscale


# =============================================================================
# Parameter grids per round
# =============================================================================
ROUND_1 = {
    "description": "Sweep denoise × noise_strength (guide at conservative defaults)",
    "fixed": {
        STAGE2_GUIDE: {"weight": 0.15, "cutoff": 0.30},
    },
    "sweep": {
        STAGE2_SAMPLER: {
            "denoise": [0.45, 0.55, 0.65, 0.75, 0.85],
        },
        STAGE2_NOISE: {
            "noise_strength": [0.4, 0.6, 0.8, 1.0],
        },
    },
}

ROUND_2 = {
    "description": "Sweep guide weight × cutoff (denoise/noise locked from round 1)",
    "fixed": {},  # filled in from --best-denoise / --best-noise
    "sweep": {
        STAGE2_GUIDE: {
            "weight": [0.08, 0.12, 0.18, 0.25],
            "cutoff": [0.20, 0.30, 0.40, 0.45],
        },
    },
}

ROUND_3 = {
    "description": "Seed robustness check (all params locked, sweep seeds)",
    "fixed": {},  # filled in from best params
    "sweep": {
        STAGE2_SAMPLER: {
            "seed": list(range(1, 11)),
        },
    },
}

FULL_SWEEP = {
    "description": "Full parameter sweep across all Stage 2 controls",
    "fixed": {},
    "sweep": {
        STAGE2_SAMPLER: {
            "denoise": [0.45, 0.55, 0.65, 0.75, 0.85],
        },
        STAGE2_NOISE: {
            "noise_strength": [0.4, 0.6, 0.8, 1.0],
        },
        STAGE2_GUIDE: {
            "weight": [0.08, 0.15, 0.25],
            "cutoff": [0.20, 0.30, 0.45],
        },
    },
}


def round4_filter(variant):
    try:
        mp = float(variant[STAGE1_RESOLUTION]["inputs"]["megapixel"])
        scale = float(variant[STAGE2_LATENT_SCALE]["inputs"]["value"])
        return 2.5 <= mp * (scale**2) <= 4.0
    except (KeyError, ValueError):
        return True


ROUND_4 = {
    "description": "Megapixel and scale factor sweep (2.5 to 4.0 MP final resolution)",
    "fixed": {},
    "sweep": {
        STAGE1_RESOLUTION: {
            "megapixel": [
                "0.1",
                "0.5",
                "0.75",
                "1.0",
                "1.5",
                "2.0",
                "2.1",
                "2.2",
                "2.3",
                "2.4",
                "2.5",
            ],
        },
        STAGE2_LATENT_SCALE: {
            "value": [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0],
        },
    },
    "filter": round4_filter,
}


def build_variants(pipeline, round_config):
    """
    Generate all parameter combinations from a round config.
    Returns list of (params_dict, modified_pipeline) tuples.
    """
    # Apply fixed overrides
    base = copy.deepcopy(pipeline)
    for node_id, params in round_config["fixed"].items():
        for key, val in params.items():
            base[node_id]["inputs"][key] = val

    # Collect all sweep axes: list of (node_id, param_name, values)
    axes = []
    for node_id, params in round_config["sweep"].items():
        for param_name, values in params.items():
            axes.append((node_id, param_name, values))

    if not axes:
        return [({}, base)]

    # Build cartesian product
    axis_values = [a[2] for a in axes]
    axis_keys = [(a[0], a[1]) for a in axes]

    variants = []
    for combo in itertools.product(*axis_values):
        variant = copy.deepcopy(base)
        params_record = {}

        for (node_id, param_name), value in zip(axis_keys, combo):
            variant[node_id]["inputs"][param_name] = value
            node_title = variant[node_id].get("_meta", {}).get("title", node_id)
            params_record[f"{node_title}.{param_name}"] = value

        if "filter" in round_config and not round_config["filter"](variant):
            continue

        variants.append((params_record, variant))

    return variants


def set_output_prefix(pipeline, run_id, experiment_name="experiment-0001"):
    """Set the SaveImage filename prefix to include run ID."""
    if STAGE2_SAVE in pipeline:
        pipeline[STAGE2_SAVE]["inputs"]["filename_prefix"] = (
            f"experiments/{experiment_name}/run_{run_id:04d}"
        )
    return pipeline


def queue_to_comfyui(pipeline, server="127.0.0.1:8188"):
    """Queue a pipeline to a running ComfyUI instance and wait for it to finish."""
    client_id = str(uuid.uuid4())
    payload = json.dumps({"prompt": pipeline, "client_id": client_id}).encode("utf-8")
    req = urllib.request.Request(
        f"http://{server}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        prompt_id = result.get("prompt_id")

        if prompt_id:
            ws_url = f"ws://{server}/ws?clientId={client_id}"
            ws = websocket.create_connection(ws_url, timeout=300)
            while True:
                out = ws.recv()
                if isinstance(out, str):
                    message = json.loads(out)
                    if (
                        message.get("type") == "executing"
                        and message.get("data", {}).get("node") is None
                    ):
                        break
            ws.close()

        return result
    except urllib.error.URLError as e:
        print(f"  [ERROR] Could not connect to ComfyUI at {server}: {e}")
        return None
    except Exception as e:
        print(f"  [ERROR] Queue failed: {e}")
        return None


def save_variant_json(pipeline, output_dir, run_id):
    """Save a variant pipeline JSON for manual loading."""
    path = os.path.join(output_dir, f"run_{run_id:04d}.json")
    with open(path, "w") as f:
        json.dump(pipeline, f, indent=2)
    return path


def main():
    parser = argparse.ArgumentParser(description="Stage 2 parameter sweep for ComfyUI pipeline")
    parser.add_argument("pipeline", help="Path to pipeline JSON file")
    parser.add_argument(
        "--round",
        type=str,
        default="1",
        choices=["1", "2", "3", "4", "all"],
        help="Which experiment round to run (default: 1)",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Max number of variants to generate/queue"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Save JSONs but don't queue to ComfyUI"
    )
    parser.add_argument(
        "--server",
        default="127.0.0.1:8188",
        help="ComfyUI server address (default: 127.0.0.1:8188)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to save variant JSONs (default: ./experiments/<round>)",
    )
    parser.add_argument("--shuffle", action="store_true", help="Randomize the order of variants")

    # Round 2 inputs: lock in best values from round 1
    parser.add_argument(
        "--best-denoise",
        type=float,
        default=None,
        help="Best denoise from round 1 (required for round 2+)",
    )
    parser.add_argument(
        "--best-noise",
        type=float,
        default=None,
        help="Best noise_strength from round 1 (required for round 2+)",
    )

    # Round 3 inputs: lock in best values from round 2
    parser.add_argument(
        "--best-weight",
        type=float,
        default=None,
        help="Best guide weight from round 2 (required for round 3)",
    )
    parser.add_argument(
        "--best-cutoff",
        type=float,
        default=None,
        help="Best guide cutoff from round 2 (required for round 3)",
    )

    # Round 4 inputs: lock in best seed from round 3
    parser.add_argument(
        "--best-seed",
        type=int,
        default=None,
        help="Best seed from round 3 (required for round 4)",
    )

    args = parser.parse_args()

    # Load pipeline
    with open(args.pipeline) as f:
        pipeline = json.load(f)

    # Select round config
    if args.round == "1":
        config = copy.deepcopy(ROUND_1)
    elif args.round == "2":
        if args.best_denoise is None or args.best_noise is None:
            print("ERROR: Round 2 requires --best-denoise and --best-noise from round 1")
            sys.exit(1)
        config = copy.deepcopy(ROUND_2)
        config["fixed"][STAGE2_SAMPLER] = {"denoise": args.best_denoise}
        config["fixed"][STAGE2_NOISE] = {"noise_strength": args.best_noise}
    elif args.round == "3":
        if any(
            v is None
            for v in [args.best_denoise, args.best_noise, args.best_weight, args.best_cutoff]
        ):
            print(
                "ERROR: Round 3 requires --best-denoise, --best-noise, --best-weight, --best-cutoff"
            )
            sys.exit(1)
        config = copy.deepcopy(ROUND_3)
        config["fixed"][STAGE2_SAMPLER] = {"denoise": args.best_denoise}
        config["fixed"][STAGE2_NOISE] = {"noise_strength": args.best_noise}
        config["fixed"][STAGE2_GUIDE] = {
            "weight": args.best_weight,
            "cutoff": args.best_cutoff,
        }
    elif args.round == "4":
        if any(
            v is None
            for v in [
                args.best_denoise,
                args.best_noise,
                args.best_weight,
                args.best_cutoff,
                args.best_seed,
            ]
        ):
            print(
                "ERROR: Round 4 requires --best-denoise, --best-noise, --best-weight, --best-cutoff, --best-seed"
            )
            sys.exit(1)
        config = copy.deepcopy(ROUND_4)
        config["fixed"][STAGE2_SAMPLER] = {"denoise": args.best_denoise, "seed": args.best_seed}
        config["fixed"][STAGE2_NOISE] = {"noise_strength": args.best_noise}
        config["fixed"][STAGE2_GUIDE] = {
            "weight": args.best_weight,
            "cutoff": args.best_cutoff,
        }
    else:
        config = copy.deepcopy(FULL_SWEEP)

    # Build variants
    variants = build_variants(pipeline, config)

    if args.shuffle:
        random.shuffle(variants)

    if args.limit is not None:
        variants = variants[: args.limit]

    # Output directory
    output_dir = args.output_dir or f"./experiments/round_{args.round}"
    os.makedirs(output_dir, exist_ok=True)

    # Print experiment summary
    total = len(variants)
    est_time = total * 5
    print(f"{'=' * 60}")
    print(f"  Experiment: Stage 2 Parameter Sweep")
    print(f"  Round: {args.round} — {config['description']}")
    print(f"  Variants: {total}")
    print(f"  Est. time: {est_time}s (~{est_time / 60:.1f} min)")
    print(f"  Output: {output_dir}")
    print(f"  Mode: {'DRY RUN (save only)' if args.dry_run else f'Queue to {args.server}'}")
    print(f"{'=' * 60}")

    if config["fixed"]:
        print(f"\n  Fixed parameters:")
        for node_id, params in config["fixed"].items():
            node_title = pipeline.get(node_id, {}).get("_meta", {}).get("title", node_id)
            for k, v in params.items():
                print(f"    {node_title}.{k} = {v}")

    print(f"\n  Sweep axes:")
    for node_id, params in config["sweep"].items():
        node_title = pipeline.get(node_id, {}).get("_meta", {}).get("title", node_id)
        for k, v in params.items():
            print(f"    {node_title}.{k} = {v}")
    print()

    # Save manifest
    manifest = {
        "round": args.round,
        "description": config["description"],
        "total_variants": total,
        "runs": [],
    }

    # Run
    for i, (params, variant) in enumerate(variants):
        run_id = i + 1
        variant = set_output_prefix(variant, run_id)
        json_path = save_variant_json(variant, output_dir, run_id)

        param_str = " | ".join(f"{k}={v}" for k, v in params.items())
        print(f"  [{run_id:3d}/{total}] {param_str}")

        manifest["runs"].append(
            {
                "run_id": run_id,
                "params": params,
                "json_path": json_path,
            }
        )

        if not args.dry_run:
            result = queue_to_comfyui(variant, args.server)
            if result:
                prompt_id = result.get("prompt_id", "unknown")
                print(f"           queued: {prompt_id}")
            else:
                print(f"           FAILED to queue")
            # Small delay to avoid overwhelming the server
            time.sleep(0.5)

    # Save manifest
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"  Done. {total} variants {'saved' if args.dry_run else 'queued'}.")
    print(f"  Manifest: {manifest_path}")
    print(f"  Images will save to: experiments/experiment-0001/run_XXXX")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
