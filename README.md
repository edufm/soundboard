# Soundboard

A browser soundboard built with React + Vite. Effects (echo, distortion,
reverb, speed) apply globally via the Web Audio API; tabs and buttons are
driven by `public/sounds.csv`. Buttons can also have variations (different
clips of the same underlying audio) revealed with a long press.

## Running it

```
npm install
npm run dev
```

## Adding your own sounds

1. Drop an audio file (`.mp3`, `.wav`, `.ogg`) into `public/sounds/`.
2. Add a row to `public/sounds.csv` with columns:

   | column | meaning |
   |---|---|
   | `name` | Text shown on the button |
   | `tab` | Tab this button belongs to (new tab names create new tabs automatically) |
   | `start_time` | Where the clip starts, `hh:mm:ss.mmm` (any number of decimal digits works) |
   | `end_time` | Where the clip stops, same format |
   | `path_to_file` | Path to the audio file, relative to `public/`, e.g. `sounds/my-clip.mp3` |
   | `parent` | Optional. Blank = a normal top-level button. Otherwise, the `name` of the button this row is a variation of (see below) |
   | `gain_db` | Optional. A volume adjustment in dB applied at playback (see "Leveling volume across clips" below). Blank = 0dB, no change |

3. Reload the browser tab (the CSV is only read once on page load, so edits
   need a manual refresh — the dev server itself doesn't need restarting).

Lines starting with `#` are ignored, so you can comment out example rows
instead of deleting them.

## Variations (long-press)

A single audio file can back several clips — the whole clip, just one
sentence, a single word, an alternate cut, etc. Give the "main" clip a normal
row with `parent` blank, then add one row per variation with `parent` set to
that main clip's `name` (must be in the same `tab`). For example, in the
sample CSV, `Full Sentence` has three word-level variations pointing at
`parent=Full Sentence`.

In the app: a short tap always plays the button's own (main) clip. If it has
variations, press and hold (~0.45s) to pop open small bubbles arranged around
the button, one per variation — tap a bubble to play that variation. Tap
anywhere else (or press Escape) to close the bubbles without playing
anything. Only one level of nesting is supported — a variation can't have its
own sub-variations.

## Populating sounds.csv from public/sounds

`tools/generate_csv.py` scans `public/sounds/<Tab>/<file>` and (re)writes
`sounds.csv`'s top-level rows: folder name → `tab`, file name (no extension)
→ `name`, each row spanning the whole file. Needs `ffprobe` (ships with
ffmpeg) on PATH.

```
python3 tools/generate_csv.py
```

Safe to re-run after adding/removing sound files — it preserves any
variation rows (`parent` set) and any `gain_db` already measured for a clip,
as long as that clip's file wasn't renamed (renaming changes `path_to_file`,
so the old measurement can't be matched up and resets to blank).

## Generating word/phrase variations automatically

`tools/split_words.py` detects word-level segments in an audio file by
looking for gaps of silence, and prints `sounds.csv`-ready rows for each one
(as `parent=<file name>` variations). It only needs `ffmpeg` on PATH — no pip
packages required.

```
python3 tools/split_words.py "public/sounds/Frases/Ai Pai Para.mp3"
```

Tune it if the split looks wrong: `--min-silence-ms` (bigger = fewer, longer
words), `--pad-ms` (more headroom around each word), `--threshold-db`
(lower = more sensitive to quiet speech). Pass `--append-to public/sounds.csv`
to write the rows directly instead of just printing them. It's a heuristic
(short-time energy, not real speech detection), so always sanity-check the
result — a top-level row for the file must already exist in `sounds.csv`
with `parent` blank before its word-variations will show up as bubbles.

Tested against some of the real `Frases/` clips: it splits cleanly when a
phrase has actual gaps between words, but clips spoken fast with no real
pause, or with continuous background music/reverb under the whole clip,
often come back as a single segment — there's no silence for it to find.
That's a limit of energy-based detection, not a bug; those files are better
left as single buttons (or split by ear/manually, not word-by-word).

## Leveling volume across clips

Clips from different sources rarely have the same volume — some are much
louder or quieter than others. `tools/measure_loudness.py` measures every
row's own clip slice (its exact `start_time`..`end_time` range, not just the
whole file) using `ffmpeg`'s `loudnorm` filter (EBU R128, the same standard
Spotify/YouTube use), and fills in `gain_db` so everything lands close to a
common target loudness (-16 LUFS by default).

```
python3 tools/measure_loudness.py
```

This never touches or re-encodes the audio files — it only rewrites
`sounds.csv`. The gain is applied live at playback time as a plain
`GainNode` multiplier (see `src/audioEngine.js`), which costs essentially
nothing, so there's no meaningful runtime overhead to worry about. Gain is
clamped to ±12dB so a near-silent or corrupted clip doesn't get boosted into
noise. Re-run it any time after adding sounds or re-running
`generate_csv.py` (takes well under a minute for ~130 clips) — rows that
already have a `gain_db` just get re-measured and overwritten with the same
process. EBU R128 gating wants a few seconds of audio to be fully reliable,
so very short single-word clips can occasionally read louder/quieter than
they sound — nudge `gain_db` by hand in the CSV if one still sounds off.

## Effects

The top bar has four global Web Audio sliders, applied to every sound
regardless of which button triggered it:

- **Echo** — delay + feedback loop
- **Distortion** — wave-shaping curve
- **Reverb** — convolution with a synthetically generated impulse response
  (no external IR file needed)
- **Speed** — playback rate (0.5x–2x); like changing a tape's speed, this
  also shifts pitch

Multiple sounds can overlap — clicking a button never stops another one
that's already playing, so you can layer/spam sounds like a real soundboard.

## Known limitations

- CSV parsing is hand-rolled and doesn't support commas or quotes inside
  field values (fine for short names/paths).
- Missing/broken audio files don't crash the app — the button just shows an
  error state (border + tooltip) and logs a warning to the console.
- Variations are one level deep only; a variation's own `parent` value is
  ignored if it points at another variation.
