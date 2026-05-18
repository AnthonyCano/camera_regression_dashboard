# CLAUDE.md

This file gives Claude Code the context it needs to be useful in this repo. Keep it short, accurate, and updated as the project evolves.

## Project: Camera Quality Regression Dashboard

A portfolio project demonstrating SDET skills for Apple's Camera API Quality Engineering team (Software Development Engineer in Test - Camera API, Camera & Photos). The system is a **macOS CLI tool** that captures measurements from a camera via AVFoundation, then detects regressions in those metrics over time using a rolling statistical baseline.

**Target role:** SDET on Apple's Camera Software team. The role emphasizes API test development, CI systems, test frameworks & tools, and debugging across API/OS/device boundaries. This project demonstrates all four.

**Goal:** show end-to-end ownership of a camera quality test pipeline — CLI capture harness, metric ingestion, regression detection, and CI-published dashboard.

## Architecture

Three independent components communicating via JSON files in `runs/`:

1. **`CameraHarness/`** — Swift Package Manager executable (macOS CLI tool). Exercises `AVCaptureSession` against a fixed test scene using the Mac's built-in camera and writes per-run metrics + a sample JPEG to disk.
2. **`tools/`** — Python scripts. Ingest run JSONs, compute image-based metrics (Laplacian variance), detect regressions against a rolling baseline, render a static matplotlib dashboard.
3. **`.github/workflows/ci.yml`** — Runs the Python pipeline on every push, uploads `dashboard/` as a build artifact.

### Why a CLI tool, not an iOS app

The job description emphasizes "test frameworks & tools" running "24x7 in lab" — that's CLI tools on a Mac controlling cameras, not GUI apps. A CLI tool also:
- Runs in CI and lab environments without a display
- Can be scripted and composed with other tools
- Demonstrates the kind of tooling Apple's Camera QE team actually builds

### Phased approach

- **Phase 1 (MVP):** macOS CLI using the built-in webcam via AVFoundation
- **Phase 2 (stretch):** Continuity Camera support — the iPhone appears as an `AVCaptureDevice` on macOS, same CLI code, just a different device identifier. No iOS app needed.

## Repo layout

```
camera-regression-dashboard/
├── CameraHarness/              # Swift Package Manager executable
│   ├── Package.swift           # SPM manifest, macOS .v13+, executableTarget
│   ├── Sources/
│   │   ├── CaptureRunner.swift # the capture sequence
│   │   ├── MetricsLogger.swift # JSON emission
│   │   └── TestScene.swift     # scene config constants
├── tools/
│   ├── ingest.py               # runs/*.json -> runs/history.json (+ Laplacian variance)
│   ├── detect_regressions.py   # rolling baseline + 2-sigma check -> runs/regressions.json
│   ├── render_dashboard.py     # matplotlib PNGs + dashboard/index.html
│   └── synthetic_regression.py # injects a fake regression for the demo
├── runs/                       # JSON artifacts + sample frames, git-tracked
├── dashboard/                  # generated output, gitignored
└── .github/workflows/ci.yml
```

## Build and run

```bash
cd CameraHarness
swift build
.build/debug/CameraHarness
```

No Xcode project required. SourceKit-LSP provides autocomplete in any editor with Swift support.

## Metrics captured per run

Every run produces one JSON file `runs/<timestamp>_<git_sha>.json` with this schema:

```json
{
  "timestamp": "2026-05-14T10:30:00Z",
  "git_sha": "abc123",
  "device": "Built-in FaceTime HD Camera",
  "os_version": "macOS 15.3",
  "metrics": {
    "session_startup_ms": 142,
    "jpeg_size_bytes": 2847291,
    "jpeg_width": 4032,
    "jpeg_height": 3024,
    "exif_iso": 100,
    "exif_exposure_time": 0.0166
  },
  "sample_frame": "frame_abc123.jpg"
}
```

`laplacian_variance` (sharpness score) is added by `tools/ingest.py` — the Swift side does not compute it.

**Stretch metrics** (add only after MVP is working):
- `focus_lock_ms` — time from session start to focus locked
- `exposure_convergence_ms` — time from session start to exposure stabilized

## Conventions

- **Python**: 3.12, standard library + `opencv-python`, `numpy`, `matplotlib`. No other deps without a reason.
- **Swift**: native AVFoundation only. No third-party SDKs. Built with Swift Package Manager.
- **JSON files are the contract** between Swift and Python. Schema changes require updating both sides AND any historical runs (or bumping a schema version field).
- **Idempotency**: every Python script must be safe to re-run. No destructive operations on `runs/`.
- **No secrets in the repo.** The git SHA is injected at build time; do not hardcode device identifiers or user data.

## Regression detection

Implemented in `tools/detect_regressions.py`:

- For each metric, maintain a **trailing** rolling window of the last N=10 runs *excluding the current point* (a regression must not contaminate its own baseline).
- Flag any value more than **2-sigma** from the rolling mean.
- If history has fewer than 5 prior runs for a metric, skip detection — insufficient signal.
- Output: `runs/regressions.json` listing `(metric, run_sha, observed_value, expected_range)` tuples.

The 2-sigma threshold and N=10 window are starting points, not tuned values. Document any changes in the PR description.

## Test scene constraints

The captured scene must be identical between runs for metrics to be meaningful:

- Camera position is fixed (laptop stays put, or external webcam is mounted).
- Test chart or static high-contrast image is fixed (wall-mounted or second monitor at fixed brightness).
- Ambient lighting kept consistent — don't capture runs at different times of day without noting it.

If the scene changes, start a new history file. Don't mix scenes in one baseline.

## What "done" looks like for the weekend MVP

Minimum viable scope, in priority order:
1. Swift CLI harness captures session startup latency, JPEG size, EXIF data, and a sample frame.
2. Python ingest computes Laplacian variance and builds `history.json`.
3. Regression detector flags 2-sigma outliers.
4. Dashboard renders one PNG per metric with flagged points in red.
5. `synthetic_regression.py` demonstrates the detector catching an injected 30% JPEG-size drop.
6. CI workflow runs steps 2-4 on every push and uploads the dashboard.

Focus-lock and exposure-convergence timings are stretch goals — they're the fiddliest to time correctly and should be cut first if time runs short.

## Known limitations (document honestly in README)

- Single test scene, single device — no cross-device or cross-scene comparison.
- 2-sigma threshold is untuned.
- Built-in webcam has limited control compared to iPhone camera hardware.
- Continuity Camera integration (iPhone as capture device) is a stretch goal.

## How Claude Code should help

- **The user writes the code.** Provide guidance, review, and debugging help — not implementations.
- **Default to small, focused edits.** This is a portfolio project; clarity beats cleverness.
- **Match the existing style** in each language (Swift idioms in `CameraHarness/`, straightforward procedural Python in `tools/`).
- **When changing the JSON schema, update both Swift and Python in the same change** and call it out explicitly.
- **Don't add dependencies** without asking. The dep list is intentionally short.
- **When in doubt about a camera concept** (exposure values, EXIF tags, JPEG vs HEIF tradeoffs), prefer Apple's AVFoundation documentation over generic web sources.
- **Preserve the "interview story" framing** in the README — the synthetic regression demo is the centerpiece and should not be removed or buried.
- **Frame everything through the lens of the SDET role** — this project demonstrates test tooling, CI, API validation, and quality engineering, not app development.
