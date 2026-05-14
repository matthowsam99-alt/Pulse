"""
Pulse Australia — Main pipeline runner
Runs all fetchers, normalises output, generates manifest.
Usage: python run_pipeline.py [--source rba|abs|all]
"""

import json
import os
import sys
import argparse
from datetime import datetime

# Add project root to path
ROOT = os.path.dirname(__file__)
sys.path.insert(0, ROOT)

from pipeline.fetchers.rba import run_all as run_rba
from pipeline.fetchers.abs import run_all as run_abs
from pipeline.fetchers.health import run_all as run_health
from pipeline.schema import INDICATOR_REGISTRY, CATEGORIES

PROCESSED_DIR = os.path.join(ROOT, "data", "processed")
OUTPUT_DIR = os.path.join(ROOT, "data", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_manifest():
    """
    Generate a manifest.json listing all available indicators,
    their metadata, and whether data exists for them.
    This is what the front-end loads first to build the toggle panel.
    """
    manifest = {
        "version": "1.0",
        "generated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "categories": CATEGORIES,
        "indicators": []
    }

    for meta in INDICATOR_REGISTRY:
        indicator_id = meta["id"]
        data_path = os.path.join(PROCESSED_DIR, f"{indicator_id}.json")

        entry = {**meta, "available": False, "last_updated": None, "data_points": 0}

        if os.path.exists(data_path):
            try:
                with open(data_path) as f:
                    data = json.load(f)
                entry["available"] = True
                entry["last_updated"] = data.get("last_updated")
                entry["data_points"] = len(data.get("series", []))
                entry["first_year"] = data.get("first_year")
                entry["source"] = data.get("source")
                entry["description"] = data.get("description")
                entry["frequency"] = data.get("frequency")
            except Exception as e:
                print(f"  ✗ Error reading {indicator_id}: {e}")

        manifest["indicators"].append(entry)

    out_path = os.path.join(OUTPUT_DIR, "manifest.json")
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)

    available = sum(1 for i in manifest["indicators"] if i["available"])
    print(f"\n📋 Manifest generated: {available}/{len(INDICATOR_REGISTRY)} indicators available")
    return out_path


def copy_to_output():
    """Copy all processed JSON files to the output directory for CDN serving."""
    count = 0
    for fname in os.listdir(PROCESSED_DIR):
        if fname.endswith(".json"):
            src = os.path.join(PROCESSED_DIR, fname)
            dst = os.path.join(OUTPUT_DIR, fname)
            with open(src) as f:
                data = json.load(f)
            with open(dst, "w") as f:
                json.dump(data, f)  # compact for CDN
            count += 1

    # Also copy events
    events_src = os.path.join(ROOT, "data", "events.json")
    if os.path.exists(events_src):
        with open(events_src) as f:
            events = json.load(f)
        with open(os.path.join(OUTPUT_DIR, "events.json"), "w") as f:
            json.dump(events, f)

    print(f"📦 Copied {count} indicator files + events to output/")


def print_summary():
    """Print a summary of what's been fetched."""
    print("\n" + "="*60)
    print("PULSE AUSTRALIA — PIPELINE SUMMARY")
    print("="*60)

    by_category = {}
    for meta in INDICATOR_REGISTRY:
        cat = meta["category"]
        if cat not in by_category:
            by_category[cat] = {"total": 0, "available": 0}
        by_category[cat]["total"] += 1
        data_path = os.path.join(PROCESSED_DIR, f"{meta['id']}.json")
        if os.path.exists(data_path):
            by_category[cat]["available"] += 1

    for cat, counts in by_category.items():
        label = CATEGORIES.get(cat, {}).get("label", cat)
        bar = "█" * counts["available"] + "░" * (counts["total"] - counts["available"])
        print(f"  {label:<15} {bar}  {counts['available']}/{counts['total']}")

    total_available = sum(c["available"] for c in by_category.values())
    total = sum(c["total"] for c in by_category.values())
    print(f"\n  Total: {total_available}/{total} indicators fetched")
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Pulse Australia data pipeline")
    parser.add_argument("--source", choices=["rba", "abs", "all"], default="all")
    args = parser.parse_args()

    print("\n🇦🇺 PULSE AUSTRALIA — Data Pipeline")
    print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    if args.source in ("rba", "all"):
        run_rba()

    if args.source in ("abs", "all"):
        run_abs()

    run_health()  # AIHW health indicators (hardcoded from published reports)

    copy_to_output()
    generate_manifest()
    print_summary()

    print("✅ Pipeline complete. Output ready in data/output/\n")


if __name__ == "__main__":
    main()
