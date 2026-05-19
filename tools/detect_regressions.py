import json
import os
import glob
import statistics
from datetime import datetime, timezone

WINDOW_SIZE = 10
SIGMA_THRESHOLD = 2
MIN_HISTORY = 5

METRICS_TO_CHECK = [
    "jpeg_size_bytes",
    "jpeg_width",
    "jpeg_height",
    "exif_iso",
    "exif_exposure_time",
    "laplacian_variance",
]


def load_latest_history(run_data_dir):
    history_files = sorted(glob.glob(os.path.join(run_data_dir, "history_*.json")))
    if not history_files:
        print("No history files found. Run ingest.py first.")
        return None
    latest = history_files[-1]
    with open(latest, "r") as f:
        return json.load(f)


def detect_regressions(run_data_dir="CameraHarness/RunData"):
    history = load_latest_history(run_data_dir)
    if not history:
        return

    runs = history.get("runs", [])
    if len(runs) < MIN_HISTORY:
        print(f"Only {len(runs)} runs found. Need at least {MIN_HISTORY} for regression detection.")
        return

    regressions = []

    for i, current_run in enumerate(runs):
        current_metrics = current_run.get("metrics", {})
        current_sha = current_run.get("git_sha", "unknown")
        current_timestamp = current_run.get("timestamp", "unknown")

        # Build the baseline from the previous N runs, excluding the current one
        baseline_start = max(0, i - WINDOW_SIZE)
        baseline_runs = runs[baseline_start:i]

        if len(baseline_runs) < MIN_HISTORY:
            continue

        for metric in METRICS_TO_CHECK:
            current_value = current_metrics.get(metric)
            if current_value is None:
                continue

            baseline_values = []
            for br in baseline_runs:
                val = br.get("metrics", {}).get(metric)
                if val is not None:
                    baseline_values.append(val)

            if len(baseline_values) < MIN_HISTORY:
                continue

            mean = statistics.mean(baseline_values)
            stdev = statistics.stdev(baseline_values)

            # If stdev is 0 the metric is perfectly stable, skip
            if stdev == 0:
                continue

            deviation = abs(current_value - mean) / stdev

            if deviation > SIGMA_THRESHOLD:
                direction = "above" if current_value > mean else "below"
                regressions.append({
                    "metric": metric,
                    "run_sha": current_sha,
                    "run_timestamp": current_timestamp,
                    "observed_value": current_value,
                    "baseline_mean": round(mean, 4),
                    "baseline_stdev": round(stdev, 4),
                    "deviation_sigma": round(deviation, 2),
                    "direction": direction,
                    "expected_range": [
                        round(mean - SIGMA_THRESHOLD * stdev, 4),
                        round(mean + SIGMA_THRESHOLD * stdev, 4),
                    ],
                })

    # Write regressions output
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sigma_threshold": SIGMA_THRESHOLD,
        "window_size": WINDOW_SIZE,
        "regressions_found": len(regressions),
        "regressions": regressions,
    }

    output_path = os.path.join(run_data_dir, "regressions.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    if regressions:
        print(f"Found {len(regressions)} regression(s):")
        for r in regressions:
            print(f"  {r['metric']} in {r['run_sha']}: {r['observed_value']} "
                  f"({r['deviation_sigma']}σ {r['direction']}, "
                  f"expected {r['expected_range'][0]} - {r['expected_range'][1]})")
    else:
        print("No regressions detected.")


if __name__ == "__main__":
    detect_regressions()
