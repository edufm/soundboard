#!/usr/bin/env python3
"""
Auto-generate variation rows (the long-press bubbles) for every top-level
clip in sounds.csv that doesn't already have any.

- Clips between WORD_SPLIT_MIN_S and WORD_SPLIT_MAX_S seconds: split by
  detected word/phrase boundaries, same silence-gap heuristic as
  split_words.py. Long enough to have real internal structure, short enough
  that word-splitting stays meaningful (a full song or a single "ah" don't).
- Everything else: split mechanically into equal-length parts, since a
  silence-based split makes little sense on those. Under HALF_SPLIT_MAX_S
  seconds: 2 halves. Otherwise (both very short and very long clips outside
  the word-split range): 4 quarters.

Clips that already have variations are left untouched — safe to re-run after
generate_csv.py picks up new sounds. Pass --force to also regenerate (and
replace) variations for clips that already have some; a clip that errors out
or yields nothing keeps whatever variations it already had.

New variation rows are left with a blank gain_db (same convention as
split_words.py) — run measure_loudness.py afterwards to fill it in.

Requires ffmpeg on PATH.
"""
import argparse
import array
import csv
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from split_words import SAMPLE_RATE, FRAME_MS, analyze, find_segments, format_time

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "public" / "sounds.csv"
PUBLIC_DIR = ROOT / "public"

WORD_SPLIT_MIN_S = 2.0
WORD_SPLIT_MAX_S = 6.0
HALF_SPLIT_MAX_S = 1.0


def parse_time(s):
    h, m, rest = s.strip().split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def decode_slice_to_pcm(path, start, end):
    """Mono 16-bit PCM samples at SAMPLE_RATE, for just [start, end] of path."""
    cmd = [
        "ffmpeg", "-v", "error", "-i", str(path),
        "-ss", start, "-to", end,
        "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "-",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, check=True)
    return array.array("h", proc.stdout)


def word_split(path, start_str, end_str):
    samples = decode_slice_to_pcm(path, start_str, end_str)
    frame_len = int(SAMPLE_RATE * FRAME_MS / 1000)
    frames = analyze(samples, frame_len)
    # Same "25th percentile of this clip's own frames" heuristic as
    # split_words.py — a fixed offset assumes real silence between words,
    # which short/reverb-heavy meme clips rarely have.
    finite = sorted(f for f in frames if f > -120)
    threshold_db = finite[len(finite) // 4] if finite else -50
    return find_segments(frames, frame_len, threshold_db, 150, 80, 60, len(samples))


def mechanical_split(duration, parts):
    part_len = duration / parts
    return [(i * part_len, (i + 1) * part_len) for i in range(parts)]


def read_rows():
    with CSV_PATH.open(newline="") as f:
        raw_lines = f.readlines()
    header_idx = next(
        i for i, line in enumerate(raw_lines)
        if line.strip() and not line.lstrip().startswith("#")
    )
    comment_lines = raw_lines[:header_idx]
    data_lines = [
        line for line in raw_lines[header_idx:]
        if line.strip() and not line.lstrip().startswith("#")
    ]
    reader = csv.DictReader(data_lines)
    fieldnames = list(reader.fieldnames)
    return comment_lines, fieldnames, list(reader)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Also regenerate variations for clips that already have some",
    )
    args = parser.parse_args()

    if not CSV_PATH.exists():
        sys.exit(f"{CSV_PATH} not found")

    comment_lines, fieldnames, rows = read_rows()
    if "gain_db" not in fieldnames:
        fieldnames.append("gain_db")

    top_level = [r for r in rows if not r.get("parent")]
    existing_variations = [r for r in rows if r.get("parent")]
    has_variations = {(r["parent"], r["tab"]) for r in existing_variations}

    new_variations_by_parent = {}
    total = len(top_level)
    for i, row in enumerate(top_level, start=1):
        key = (row["name"], row["tab"])
        label = f'{row["name"]} ({row["tab"]})'

        if key in has_variations and not args.force:
            print(f"[{i}/{total}] SKIP {label}: already has variations")
            continue

        start_s = parse_time(row["start_time"])
        end_s = parse_time(row["end_time"])
        duration = end_s - start_s
        if duration <= 0:
            print(f"[{i}/{total}] SKIP {label}: non-positive duration", file=sys.stderr)
            continue

        path = PUBLIC_DIR / row["path_to_file"]

        if WORD_SPLIT_MIN_S <= duration <= WORD_SPLIT_MAX_S:
            suffix = "word"
            try:
                offsets = word_split(path, row["start_time"], row["end_time"])
            except Exception as e:
                print(f"[{i}/{total}] SKIP {label}: {e}", file=sys.stderr)
                continue
            if len(offsets) < 2:
                print(f"[{i}/{total}] SKIP {label}: no internal word boundary found")
                continue
        else:
            suffix = "part"
            parts = 2 if duration < HALF_SPLIT_MAX_S else 4
            offsets = mechanical_split(duration, parts)

        variation_rows = [
            {
                "name": f'{row["name"]} - {suffix} {n}',
                "tab": row["tab"],
                "start_time": format_time(start_s + s),
                "end_time": format_time(start_s + e),
                "path_to_file": row["path_to_file"],
                "parent": row["name"],
                "gain_db": "",
            }
            for n, (s, e) in enumerate(offsets, start=1)
        ]
        new_variations_by_parent[key] = variation_rows
        print(f"[{i}/{total}] {label}: {len(variation_rows)} {suffix} segment(s)")

    with CSV_PATH.open("w", newline="") as f:
        f.writelines(comment_lines)
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in top_level:
            writer.writerow({col: row.get(col, "") for col in fieldnames})
            key = (row["name"], row["tab"])
            if key in new_variations_by_parent:
                for v in new_variations_by_parent[key]:
                    writer.writerow({col: v.get(col, "") for col in fieldnames})
            else:
                for v in existing_variations:
                    if v["parent"] == row["name"] and v["tab"] == row["tab"]:
                        writer.writerow({col: v.get(col, "") for col in fieldnames})

    total_new = sum(len(v) for v in new_variations_by_parent.values())
    print(f"\nGenerated {total_new} variation rows across {len(new_variations_by_parent)} clips.")


if __name__ == "__main__":
    main()
