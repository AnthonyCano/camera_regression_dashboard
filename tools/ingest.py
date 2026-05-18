import cv2 as cv
import json
import os
from datetime import datetime, timezone

def ingest_runs(run_data_dir="CameraHarness/RunData"):
    runs = []
    frames_covered = []

    # Scan the directory
    if not os.path.exists(run_data_dir):
        print(f"Directory {run_data_dir} does not exist.")
        return

    for filename in os.listdir(run_data_dir):
        if filename.endswith(".json") and not filename.startswith("history_"):
            file_path = os.path.join(run_data_dir, filename)

            # Read each JSON file
            with open(file_path, "r") as f:
                run = json.load(f)

            # Load the sample frame
            frame_filename = run.get("sample_frame")
            if not frame_filename:
                continue

            frame_path = os.path.join(run_data_dir, frame_filename)
            img = cv.imread(frame_path)

            if img is not None:
                # Compute Laplacian variance
                gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
                laplacian = cv.Laplacian(gray, cv.CV_64F)
                laplacian_var = laplacian.var()

                # Add it to the run's metrics
                if "metrics" not in run:
                    run["metrics"] = {}
                run["metrics"]["laplacian_variance"] = laplacian_var

                # Collect all runs
                runs.append(run)
                frames_covered.append(frame_filename)
            else:
                print(f"Warning: Could not read image {frame_path}")

    # Sort by timestamp
    runs.sort(key=lambda x: x.get("timestamp", 0))
    frames_covered.sort()

    # Wrap runs with metadata
    history = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_count": len(runs),
        "frames_covered": frames_covered,
        "runs": runs,
    }

    # Write history with unique filename
    history_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    history_path = os.path.join(run_data_dir, f"history_{history_timestamp}.json")
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)
    print(f"Successfully processed {len(runs)} runs and wrote to {history_path}")

if __name__ == "__main__":
    ingest_runs()
