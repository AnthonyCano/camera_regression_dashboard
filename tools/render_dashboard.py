import json
import os
import glob
import statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone

RUN_DATA_DIR = "CameraHarness/RunData"
DASHBOARD_DIR = "dashboard"
WINDOW_SIZE = 10
SIGMA_THRESHOLD = 2

METRICS_TO_PLOT = [
    ("jpeg_size_bytes", "JPEG Size (bytes)"),
    ("jpeg_width", "JPEG Width (px)"),
    ("jpeg_height", "JPEG Height (px)"),
    ("exif_iso", "EXIF ISO"),
    ("exif_exposure_time", "EXIF Exposure Time (s)"),
    ("laplacian_variance", "Laplacian Variance (sharpness)"),
]


def load_latest_history():
    history_files = sorted(glob.glob(os.path.join(RUN_DATA_DIR, "history_*.json")))
    if not history_files:
        print("No history files found. Run ingest.py first.")
        return None
    with open(history_files[-1], "r") as f:
        return json.load(f)


def load_regressions():
    path = os.path.join(RUN_DATA_DIR, "regressions.json")
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        data = json.load(f)
    return data.get("regressions", [])


def parse_timestamp(ts):
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H-%M-%SZ")
    except ValueError:
        try:
            return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return None


def compute_baseline_bands(values):
    upper = []
    lower = []
    means = []
    for i in range(len(values)):
        start = max(0, i - WINDOW_SIZE)
        window = values[start:i]
        if len(window) >= 2:
            mean = statistics.mean(window)
            stdev = statistics.stdev(window)
            means.append(mean)
            upper.append(mean + SIGMA_THRESHOLD * stdev)
            lower.append(mean - SIGMA_THRESHOLD * stdev)
        else:
            means.append(None)
            upper.append(None)
            lower.append(None)
    return means, lower, upper


def render_metric_chart(runs, regressions, metric_key, metric_label, output_path):
    timestamps = []
    values = []
    shas = []

    for run in runs:
        val = run.get("metrics", {}).get(metric_key)
        ts = parse_timestamp(run.get("timestamp", ""))
        if val is not None and ts is not None:
            timestamps.append(ts)
            values.append(val)
            shas.append(run.get("git_sha", "?"))

    if not values:
        return False

    # Compute baseline bands
    means, lower_band, upper_band = compute_baseline_bands(values)

    # Find regression points for this metric
    regression_indices = []
    for reg in regressions:
        if reg["metric"] == metric_key:
            for i, sha in enumerate(shas):
                if sha == reg["run_sha"]:
                    regression_indices.append(i)

    fig, ax = plt.subplots(figsize=(10, 4))

    # Plot baseline band (shaded region showing mean ± 2σ)
    band_ts = [timestamps[i] for i in range(len(timestamps)) if means[i] is not None]
    band_upper = [upper_band[i] for i in range(len(timestamps)) if means[i] is not None]
    band_lower = [lower_band[i] for i in range(len(timestamps)) if means[i] is not None]
    band_means = [means[i] for i in range(len(timestamps)) if means[i] is not None]

    if band_ts:
        ax.fill_between(band_ts, band_lower, band_upper, alpha=0.15, color="#3b82f6", label="Baseline ±2σ")
        ax.plot(band_ts, band_means, "--", color="#3b82f6", alpha=0.4, linewidth=1, label="Baseline mean")

    # Plot all points
    ax.plot(timestamps, values, "o-", color="#3b82f6", markersize=6, linewidth=1.5, label="Observed")

    # Overlay regression points in red
    if regression_indices:
        reg_ts = [timestamps[i] for i in regression_indices]
        reg_vals = [values[i] for i in regression_indices]
        ax.scatter(reg_ts, reg_vals, color="#ef4444", s=100, zorder=5, label="Regression", edgecolors="darkred", linewidths=1.5)

    ax.set_title(metric_label, fontsize=14, fontweight="bold")
    ax.set_xlabel("Timestamp")
    ax.set_ylabel(metric_label)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", fontsize=8)

    if len(timestamps) > 1:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
        fig.autofmt_xdate()

    # Add SHA labels below each point
    for i, (t, v, s) in enumerate(zip(timestamps, values, shas)):
        ax.annotate(s[:7], (t, v), textcoords="offset points", xytext=(0, -15),
                    ha="center", fontsize=7, color="gray")

    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return True


def generate_html(chart_files, runs, regressions, dashboard_timestamp):
    total_runs = len(runs)
    total_regressions = len(regressions)
    status = "PASS" if total_regressions == 0 else "FAIL"
    status_color = "#3fb950" if total_regressions == 0 else "#ef4444"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Camera Regression Dashboard</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 1100px;
            margin: 0 auto;
            padding: 20px;
            background: #0d1117;
            color: #c9d1d9;
        }}
        h1 {{
            color: #58a6ff;
            border-bottom: 1px solid #30363d;
            padding-bottom: 12px;
        }}
        .summary {{
            display: flex;
            gap: 16px;
            margin-bottom: 24px;
        }}
        .summary-card {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 16px 24px;
            flex: 1;
            text-align: center;
        }}
        .summary-card .value {{
            font-size: 28px;
            font-weight: bold;
        }}
        .summary-card .label {{
            font-size: 12px;
            color: #484f58;
            margin-top: 4px;
        }}
        .chart {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 20px;
        }}
        .chart img {{
            width: 100%;
            border-radius: 4px;
        }}
        .footer {{
            text-align: center;
            color: #484f58;
            font-size: 12px;
            margin-top: 40px;
        }}
    </style>
</head>
<body>
    <h1>Camera Regression Dashboard</h1>
    <div class="summary">
        <div class="summary-card">
            <div class="value" style="color: {status_color}">{status}</div>
            <div class="label">Status</div>
        </div>
        <div class="summary-card">
            <div class="value">{total_runs}</div>
            <div class="label">Total Runs</div>
        </div>
        <div class="summary-card">
            <div class="value" style="color: {status_color}">{total_regressions}</div>
            <div class="label">Regressions Found</div>
        </div>
    </div>
"""
    for chart in chart_files:
        name = os.path.splitext(os.path.basename(chart))[0].replace("_", " ").title()
        html += f"""    <div class="chart">
        <img src="{os.path.basename(chart)}" alt="{name}">
    </div>
"""

    html += f"""    <div class="footer">
        Generated {dashboard_timestamp} by CameraHarness regression pipeline
    </div>
</body>
</html>"""
    return html


def render_dashboard():
    history = load_latest_history()
    if not history:
        return

    runs = history.get("runs", [])
    if not runs:
        print("No runs found in history.")
        return

    regressions = load_regressions()
    dashboard_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")

    # Timestamped output directory
    output_dir = os.path.join(DASHBOARD_DIR, dashboard_timestamp)
    os.makedirs(output_dir, exist_ok=True)

    chart_files = []
    for metric_key, metric_label in METRICS_TO_PLOT:
        output_path = os.path.join(output_dir, f"{metric_key}.png")
        if render_metric_chart(runs, regressions, metric_key, metric_label, output_path):
            chart_files.append(output_path)
            print(f"  Rendered {metric_key}")

    # Generate HTML
    html = generate_html(chart_files, runs, regressions, dashboard_timestamp)
    html_path = os.path.join(output_dir, "index.html")
    with open(html_path, "w") as f:
        f.write(html)

    print(f"\nDashboard generated: {html_path}")
    print(f"  {len(chart_files)} charts, {len(regressions)} regressions flagged")


if __name__ == "__main__":
    render_dashboard()
