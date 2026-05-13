"""
Always run this before pushing to GitHub.
Rebuilds manifest.json from scratch from all processed indicator files.
Prevents the manifest from ever getting out of sync with actual data.
"""
import json, shutil, os, sys

sys.path.insert(0, os.path.dirname(__file__))
from pipeline.schema import CATEGORIES

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), 'data', 'processed')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'data', 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

manifest = {
    "version": "1.0",
    "generated": __import__('datetime').datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "categories": CATEGORIES,
    "indicators": []
}

count = 0
for fname in sorted(os.listdir(PROCESSED_DIR)):
    if not fname.endswith('.json'):
        continue
    src = os.path.join(PROCESSED_DIR, fname)
    dst = os.path.join(OUTPUT_DIR, fname)
    shutil.copy(src, dst)
    with open(src) as f:
        data = json.load(f)
    manifest["indicators"].append({
        "id": data["id"],
        "label": data["label"],
        "category": data["category"],
        "unit": data["unit"],
        "unit_label": data["unit_label"],
        "available": True,
        "last_updated": data.get("last_updated"),
        "data_points": len(data.get("series", [])),
        "first_year": data.get("first_year"),
        "source": data.get("source"),
        "description": data.get("description"),
        "frequency": data.get("frequency"),
    })
    count += 1

with open(os.path.join(OUTPUT_DIR, 'manifest.json'), 'w') as f:
    json.dump(manifest, f, indent=2)

shutil.copy('data/events.json', os.path.join(OUTPUT_DIR, 'events.json'))

print(f"✅ Manifest rebuilt: {len(manifest['indicators'])} indicators, {count} JSON files copied to output/")
