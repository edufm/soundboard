#!/usr/bin/env python3
"""
Detect word/phrase-level segments in an audio file by finding gaps of
silence, and print them as ready-to-paste sounds.csv rows.

No pip packages needed — only requires `ffmpeg` on PATH, used solely to
decode the input into raw PCM. Silence detection itself is plain Python
(short-time RMS energy in dBFS, same idea pydub's detect_nonsilent uses).

This is a heuristic, not a transcription tool: it can't tell a word from a
cough, and plosives/breaths can confuse it. Always eyeball the printed
timestamps (or listen to the clips in the app) before trusting them.

Example:
    python3 tools/split_words.py "public/sounds/Frases/Ai Pai Para.mp3"
    python3 tools/split_words.py "public/sounds/Frases/Ai Pai Para.mp3" \\
        --min-silence-ms 200 --pad-ms 80
"""
import argparse
import array
import math
import subprocess
import sys
from pathlib import Path

SAMPLE_RATE = 16000  # downsample everything to this rate for analysis
FRAME_MS = 20


def decode_to_pcm(path):
    """Shell out to ffmpeg to get mono 16-bit PCM samples at SAMPLE_RATE."""
    cmd = [
        "ffmpeg", "-v", "error", "-i", str(path),
        "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "-",
    ]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, check=True)
    except FileNotFoundError:
        sys.exit("ffmpeg not found on PATH — install it first (e.g. `sudo apt-get install ffmpeg`).")
    except subprocess.CalledProcessError as e:
        sys.exit(f"ffmpeg failed to decode {path}: {e}")
    return array.array("h", proc.stdout)


def frame_dbfs(samples, start, end):
    n = end - start
    if n <= 0:
        return -120.0
    total = sum(samples[i] * samples[i] for i in range(start, end))
    rms = math.sqrt(total / n)
    if rms <= 0:
        return -120.0
    return 20 * math.log10(rms / 32768)


def analyze(samples, frame_len):
    return [
        frame_dbfs(samples, start, min(start + frame_len, len(samples)))
        for start in range(0, len(samples), frame_len)
    ]


def find_segments(frames, frame_len, threshold_db, min_silence_ms, min_word_ms, pad_ms, total_samples):
    frame_ms = frame_len / SAMPLE_RATE * 1000
    min_silence_frames = max(1, round(min_silence_ms / frame_ms))
    min_word_frames = max(1, round(min_word_ms / frame_ms))

    is_loud = [f >= threshold_db for f in frames]

    # Merge consecutive "loud" frames into raw segments (frame index ranges).
    raw_segments = []
    start = None
    for i, loud in enumerate(is_loud):
        if loud and start is None:
            start = i
        elif not loud and start is not None:
            raw_segments.append((start, i))
            start = None
    if start is not None:
        raw_segments.append((start, len(is_loud)))

    # A silence gap shorter than min_silence_frames doesn't count as a word
    # boundary (e.g. the brief stop before a hard consonant) — merge across it.
    merged = []
    for seg in raw_segments:
        if merged and seg[0] - merged[-1][1] < min_silence_frames:
            merged[-1] = (merged[-1][0], seg[1])
        else:
            merged.append(list(seg))

    # Drop segments too short to be a real word (clicks, breaths).
    merged = [s for s in merged if s[1] - s[0] >= min_word_frames]

    pad_samples = int(SAMPLE_RATE * pad_ms / 1000)
    results = []
    for s, e in merged:
        start_sample = max(0, s * frame_len - pad_samples)
        end_sample = min(total_samples, e * frame_len + pad_samples)
        results.append((start_sample / SAMPLE_RATE, end_sample / SAMPLE_RATE))
    return results


def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def default_path_to_file(audio_path):
    """Path relative to public/, matching sounds.csv's path_to_file convention."""
    parts = audio_path.resolve().parts
    if "public" in parts:
        idx = parts.index("public")
        return "/".join(parts[idx + 1 :])
    return f"sounds/{audio_path.name}"


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("audio_file", help="Path to the audio file to analyze")
    parser.add_argument(
        "--threshold-db", type=float, default=None,
        help="Absolute dBFS above which audio counts as speech. Default: this "
        "file's own 25th-percentile frame energy.",
    )
    parser.add_argument(
        "--min-silence-ms", type=int, default=150,
        help="Silence shorter than this is NOT a word boundary (default: 150ms)",
    )
    parser.add_argument(
        "--min-word-ms", type=int, default=80,
        help="Segments shorter than this are dropped as noise (default: 80ms)",
    )
    parser.add_argument(
        "--pad-ms", type=int, default=60,
        help="Padding added before/after each detected word (default: 60ms)",
    )
    parser.add_argument("--tab", default="Frases", help="tab column for the generated rows")
    parser.add_argument(
        "--parent", help="parent column value (default: the file's name without extension)"
    )
    parser.add_argument(
        "--path-to-file",
        help="path_to_file value to print (default: derived from the input path, relative to public/)",
    )
    parser.add_argument(
        "--append-to", type=Path,
        help="Append the generated rows straight to this CSV file instead of only printing them",
    )
    args = parser.parse_args()

    audio_path = Path(args.audio_file)
    samples = decode_to_pcm(audio_path)
    frame_len = int(SAMPLE_RATE * FRAME_MS / 1000)
    frames = analyze(samples, frame_len)

    if args.threshold_db is not None:
        threshold_db = args.threshold_db
    else:
        # A fixed offset below the average (e.g. pydub's "avg - 16dB" default)
        # assumes real silence between words. Short, already-trimmed clips —
        # especially memes with background music/reverb — rarely have that,
        # so the 25th percentile of this file's own frame energies (i.e.
        # "quieter than 3/4 of the clip") tracks its actual noise floor much
        # more reliably in practice.
        finite = sorted(f for f in frames if f > -120)
        threshold_db = finite[len(finite) // 4] if finite else -50

    segments = find_segments(
        frames, frame_len, threshold_db,
        args.min_silence_ms, args.min_word_ms, args.pad_ms, len(samples),
    )

    if not segments:
        sys.exit(f"No segments found above {threshold_db:.1f} dBFS — try a lower --threshold-db.")

    if len(segments) < 2:
        print(
            f"Only the whole clip was found for {audio_path.name} (no internal word "
            "boundary) — nothing useful to add as a variation, skipping.",
            file=sys.stderr,
        )
        return

    parent = args.parent or audio_path.stem
    path_to_file = args.path_to_file or default_path_to_file(audio_path)

    rows = [
        f"{parent} - word {i},{args.tab},{format_time(start)},{format_time(end)},{path_to_file},{parent}"
        for i, (start, end) in enumerate(segments, start=1)
    ]

    print(f"# {len(segments)} segments found (threshold {threshold_db:.1f} dBFS) — review before trusting!")
    print(f"# make sure a top-level row with name={parent} (parent blank) already exists in tab={args.tab}")
    for row in rows:
        print(row)

    if args.append_to:
        with args.append_to.open("a") as f:
            f.write("\n".join(rows) + "\n")
        print(f"\nAppended {len(rows)} rows to {args.append_to}", file=sys.stderr)


if __name__ == "__main__":
    main()
