import csv
from pathlib import Path

for exp_dir in Path("experiments").iterdir():
    if not exp_dir.is_dir():
        continue
    chunks_csv = exp_dir / "chunks.csv"
    if not chunks_csv.exists():
        continue

    csv.field_size_limit(int(1e9))
    with open(chunks_csv, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    lengths = sorted(len(r["text"]) for r in rows)
    print(f"\n{exp_dir.name}: {len(rows)} chunks")
    print(f"  min={lengths[0]:5d}  max={lengths[-1]:5d}  med={lengths[len(lengths)//2]:5d}")

    short100 = sum(1 for l in lengths if l < 100)
    print(f"  <100 chars: {short100:4d} ({short100/len(lengths)*100:.1f}%)")

    tiny50 = sum(1 for l in lengths if l < 50)
    print(f"  <50 chars:  {tiny50:4d} ({tiny50/len(lengths)*100:.1f}%)")

    tiny20 = sum(1 for l in lengths if l < 20)
    print(f"  <20 chars:  {tiny20:4d} ({tiny20/len(lengths)*100:.1f}%)")

    for r in rows:
        if len(r["text"]) < 20:
            print(f"  [{len(r['text'])} chars] {r['text'][:80]!r}")
