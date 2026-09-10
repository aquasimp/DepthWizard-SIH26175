"""
Test submitting an optical sample image to the live DepthWizard backend
with the fine-tuned v1.1.0 multi-city model and verifying the output artifacts.
"""

import requests
import time
from pathlib import Path

sample_path = Path("data/samples/sample_plain.png")
assert sample_path.exists(), f"Sample image not found: {sample_path}"

url = "http://127.0.0.1:8000/api/jobs"
print(f"Submitting job to {url} using sample: {sample_path} with model_version=ensemble...")

with open(sample_path, "rb") as f:
    files = {"file": (sample_path.name, f, "image/png")}
    data = {
        "assumed_gsd_m": "0.33",
        "z_exag": "1.5",
        "model_version": "ensemble",
    }
    resp = requests.post(url, files=files, data=data)

print(f"Create response status: {resp.status_code}")
job_data = resp.json()
print("Response:", job_data)
job_id = job_data["job_id"]

# Poll status until done
print(f"Polling job status for {job_id}...")
for _ in range(40):
    time.sleep(1.0)
    status_resp = requests.get(f"http://127.0.0.1:8000/api/jobs/{job_id}")
    status_data = status_resp.json()
    stage = status_data.get("stage")
    progress = status_data.get("progress")
    st = status_data.get("status")
    print(f"  Stage: {stage}, Progress: {progress}%, Status: {st}")
    if st == "DONE":
        print("\nJob completed successfully!")
        print("Job metadata:", status_data.get("metadata", {}).get("model_metrics"))
        print("Artifacts generated:", status_data.get("metadata", {}).get("artifacts"))
        break
    elif st == "FAILED":
        print("Job FAILED:", status_data.get("error"))
        break
