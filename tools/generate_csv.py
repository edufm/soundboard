#!/usr/bin/env python3
"""
Rebuild sounds.csv's top-level rows from the folders/files under public/sounds
— folder name becomes `tab`, file name (no extension) becomes `name`, and each
row spans the whole file (0 to its duration). Existing variation rows
(non-blank `parent`) are preserved as long as their parent still exists in
the same tab after the rescan; orphaned ones are dropped with a warning.

Requires ffprobe (ships with ffmpeg) on PATH.

Note: re-running this always regenerates top-level `name`s from the current
filenames, so if you hand-edit a top-level row's display name in the CSV,
rename the file itself to match — otherwise the next run overwrites it.

A row's `gain_db` (see tools/measure_loudness.py) is carried over whenever a
row with the same path_to_file + start_time + end_time already existed —
renaming a file breaks that match (its path changes), so a renamed file's
gain_db resets to blank and needs measure_loudness.py run again for it.

Any file whose name contains "musica" (case-insensitive) also gets a second
row in the MUSIC_TAB tab, in addition to its normal folder-based tab — so
songs filed under a mood folder (e.g. Tristeza) still show up under Musicas
too. Files already living directly in MUSIC_TAB aren't duplicated.
"""
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOUNDS_DIR = ROOT / "public" / "sounds"
CSV_PATH = ROOT / "public" / "sounds.csv"
AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}
COLUMNS = ["name", "tab", "start_time", "end_time", "path_to_file", "parent", "gain_db"]
MUSIC_KEYWORD = "musica"
MUSIC_TAB = "Musicas"


def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def get_duration(path):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ]
    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, check=True,
            text=True, encoding="utf-8", errors="replace",
        )
    except FileNotFoundError:
        sys.exit("ffprobe not found on PATH (it ships with ffmpeg) — install ffmpeg first.")
    except subprocess.CalledProcessError as e:
        sys.exit(f"ffprobe failed on {path}: {e}")
    return float(result.stdout.strip())


def scan_folders(gain_lookup):
    rows = []
    for folder in sorted(p for p in SOUNDS_DIR.iterdir() if p.is_dir()):
        tab = folder.name
        for file in sorted(folder.iterdir()):
            if file.suffix.lower() not in AUDIO_EXTENSIONS:
                continue
            duration = get_duration(file)
            start_time = "00:00:00.000"
            end_time = format_time(duration)
            path_to_file = f"sounds/{tab}/{file.name}"
            rows.append({
                "name": file.stem,
                "tab": tab,
                "start_time": start_time,
                "end_time": end_time,
                "path_to_file": path_to_file,
                "parent": "",
                "gain_db": gain_lookup.get((path_to_file, start_time, end_time), ""),
            })
    return rows


def add_music_crosslistings(rows):
    """Duplicate any row whose name contains MUSIC_KEYWORD into MUSIC_TAB too,
    so songs scattered across mood folders are still all reachable from one
    tab, on top of their own."""
    extra = [
        {**row, "tab": MUSIC_TAB}
        for row in rows
        if row["tab"] != MUSIC_TAB and MUSIC_KEYWORD in row["name"].lower()
    ]
    return rows + extra


def read_existing_rows():
    """All data rows from the current sounds.csv, if any."""
    if not CSV_PATH.exists():
        return []
    with CSV_PATH.open(newline="") as f:
        lines = [line for line in f if line.strip() and not line.lstrip().startswith("#")]
    if not lines:
        return []
    return list(csv.DictReader(lines))


def main():
    existing_rows = read_existing_rows()
    # A clip's identity for carrying gain_db forward — renaming a file changes
    # its path_to_file, so a rename always loses the previous measurement.
    gain_lookup = {
        (row["path_to_file"], row["start_time"], row["end_time"]): row["gain_db"]
        for row in existing_rows
        if row.get("gain_db")
    }

    new_rows = scan_folders(gain_lookup)
    if not new_rows:
        sys.exit(f"No audio files found under {SOUNDS_DIR}")
    new_rows = add_music_crosslistings(new_rows)

    names_by_tab = {}
    for row in new_rows:
        names_by_tab.setdefault(row["tab"], set()).add(row["name"])

    kept_variations = []
    for row in existing_rows:
        if not row.get("parent"):
            continue
        if row["parent"] in names_by_tab.get(row["tab"], ()):
            kept_variations.append(row)
        else:
            print(
                f'Dropping orphaned variation "{row["name"]}" '
                f'(parent "{row["parent"]}" not found in tab "{row["tab"]}")',
                file=sys.stderr,
            )

    with CSV_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for row in new_rows:
            writer.writerow(row)
            for variation in kept_variations:
                if variation["parent"] == row["name"] and variation["tab"] == row["tab"]:
                    writer.writerow({col: variation.get(col, "") for col in COLUMNS})

    print(f"Wrote {len(new_rows)} top-level rows and kept {len(kept_variations)} variations to {CSV_PATH}")


if __name__ == "__main__":
    main()
