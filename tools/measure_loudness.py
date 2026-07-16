#!/usr/bin/env python3
"""
Measure the loudness of every clip's own slice (its exact start_time..end_time
range) in sounds.csv, and fill in a gain_db column so every clip lands close
to the same perceived loudness when played back.

This never touches the audio files or re-encodes anything — the gain is
applied live at playback time (see src/audioEngine.js), so this script only
ever rewrites sounds.csv.

Requires ffmpeg on PATH (uses its `loudnorm` filter, EBU R128).

Note: EBU R128 loudness gating wants a few seconds of audio to be reliable.
Very short clips (some single-word variations are well under a second) can
report loud/quiet swings that don't quite match what your ears hear — treat
the numbers as a good starting point, not gospel, and nudge gain_db by hand
in the CSV if a specific button still sounds off.
"""
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "public" / "sounds.csv"
PUBLIC_DIR = ROOT / "public"

TARGET_LUFS = -16.0
MAX_GAIN_DB = 12.0  # clamp so a near-silent/noisy clip doesn't get boosted absurdly


def measure_integrated_loudness(path, start, end):
    # loudnorm prints its JSON summary at info level, so -v error (which we
    # use elsewhere to keep output quiet) would silently swallow it — use
    # -hide_banner/-nostats instead to cut the noise without losing that.
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
        "-ss", start, "-to", end,
        "-af", f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11:print_format=json",
        "-f", "null", "-",
    ]
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
    )
    # The JSON block isn't the last thing printed (ffmpeg logs muxing/timing
    # info after it), so grab the last {...} blob rather than anchoring to EOF.
    matches = re.findall(r"\{[^{}]*\}", proc.stderr)
    if not matches:
        raise RuntimeError(f"couldn't parse loudnorm output:\n{proc.stderr[-500:]}")
    data = json.loads(matches[-1])
    raw = data["input_i"]
    return float(raw) if raw not in ("-inf", "inf", "nan") else -70.0


def main():
    if not CSV_PATH.exists():
        sys.exit(f"{CSV_PATH} not found")

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
    if "gain_db" not in fieldnames:
        fieldnames.append("gain_db")
    rows = list(reader)

    total = len(rows)
    for i, row in enumerate(rows, start=1):
        path = PUBLIC_DIR / row["path_to_file"]
        label = f'{row["name"]} ({row["tab"]})'
        try:
            measured_i = measure_integrated_loudness(path, row["start_time"], row["end_time"])
        except Exception as e:
            print(f"[{i}/{total}] SKIP {label}: {e}", file=sys.stderr)
            continue
        gain_db = max(-MAX_GAIN_DB, min(MAX_GAIN_DB, TARGET_LUFS - measured_i))
        row["gain_db"] = f"{gain_db:.1f}"
        print(f"[{i}/{total}] {label}: measured {measured_i:.1f} LUFS -> gain {gain_db:+.1f}dB")

    with CSV_PATH.open("w", newline="") as f:
        f.writelines(comment_lines)
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nUpdated gain_db for {total} rows in {CSV_PATH}")


if __name__ == "__main__":
    main()
