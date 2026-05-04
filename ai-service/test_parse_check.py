#!/usr/bin/env python3
"""
Test script to validate POST /parse response:
1. graph_data contains non-empty nodes and edges
2. Artifact PNGs are distinct (different SHA256)
3. line_detections count matches geometry_summary.total_lines
"""
import requests
import hashlib
import sys
import os
import json

BASE = "http://127.0.0.1:8000"
API_KEY = "pid-parser-internal-secret-2026"
PDF = "PID-010.pdf"

def fail(msg, code=1):
    print(f"FAIL: {msg}")
    sys.exit(code)

def pass_check(msg):
    print(f"✓ OK: {msg}")

# Check if PID-010.pdf exists
if not os.path.exists(PDF):
    fail(f"{PDF} not found in current directory")

# POST /parse
print(f"Posting {PDF} to {BASE}/parse...")
with open(PDF, "rb") as f:
    r = requests.post(
        f"{BASE}/parse",
        headers={"X-API-Key": API_KEY},
        files={"file": (PDF, f, "application/pdf")}
    )

if r.status_code != 200:
    fail(f"POST /parse returned {r.status_code}: {r.text}")

data = r.json()
job_id = data.get("job_id", "unknown")
print(f"Job ID: {job_id}\n")

# 1) Graph data non-empty
print("Test 1: graph_data contains nodes and edges")
nodes = data.get("graph_data", {}).get("nodes", [])
edges = data.get("graph_data", {}).get("edges", [])

if not nodes:
    fail("graph_data.nodes is empty")
if not edges:
    fail("graph_data.edges is empty")

pass_check(f"graph_data has {len(nodes)} nodes and {len(edges)} edges")

# 2) Artifact PNGs are distinct
print("\nTest 2: Artifact PNGs are distinct")
artifacts = data.get("artifacts", {})
model_keys = ["model1", "model2", "model3"]
hashes = {}

for k in model_keys:
    if k not in artifacts:
        fail(f"artifact '{k}' missing from response")
    
    artifact_path = artifacts[k]
    url = f"{BASE}/artifacts/{artifact_path}"
    print(f"  Downloading {k} from {url}...")
    
    rr = requests.get(url)
    if rr.status_code != 200:
        fail(f"Failed to download artifact '{k}' at {url} (status {rr.status_code})")
    
    content = rr.content
    sha256_hash = hashlib.sha256(content).hexdigest()
    hashes[k] = sha256_hash
    print(f"    SHA256: {sha256_hash[:16]}...")

# Check if all hashes are unique
unique_hashes = set(hashes.values())
if len(unique_hashes) < len(model_keys):
    fail(f"Model artifact images are NOT distinct. Hashes: {hashes}")

pass_check(f"All {len(model_keys)} model artifacts have unique SHA256 hashes")

# 3) Line detections vs geometry_summary
print("\nTest 3: line_detections count matches geometry_summary.total_lines")
lines_count = len(data.get("line_detections", []))
total_lines = data.get("geometry_summary", {}).get("total_lines", None)

if total_lines is None:
    fail("geometry_summary.total_lines is missing")

if lines_count != total_lines:
    fail(f"Mismatch: line_detections length ({lines_count}) != geometry_summary.total_lines ({total_lines})")

pass_check(f"line_detections ({lines_count}) matches total_lines ({total_lines})")

print("\n" + "="*60)
print("ALL CHECKS PASSED ✓")
print("="*60)
