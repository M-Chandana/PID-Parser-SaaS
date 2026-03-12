import requests
import os
import cv2
import numpy as np

# 1. Create a dummy test image if it doesn't exist
test_img_path = "test_pid.png"
if not os.path.exists(test_img_path):
    # Black background
    img = np.zeros((500, 500, 3), dtype=np.uint8)
    # White background for technical drawing look
    img.fill(255)
    # Draw some "technical" lines
    cv2.line(img, (50, 250), (450, 250), (0, 0, 0), 2) # Horizontal pipe
    cv2.circle(img, (250, 250), 30, (0, 0, 0), 2)     # Valve/Pump symbol
    cv2.imwrite(test_img_path, img)
    print(f"Created dummy test image: {test_img_path}")

# 2. Test /health endpoint
BASE_URL = "http://localhost:8000"
try:
    health = requests.get(f"{BASE_URL}/health")
    print(f"Health Check: {health.json()}")
except:
    print("Service is not running. Start it with: uvicorn app.main:app --reload")

# 3. Test /parse endpoint
if os.path.exists(test_img_path):
    print("Testing /parse endpoint...")
    try:
        with open(test_img_path, "rb") as f:
            files = {"file": (test_img_path, f, "image/png")}
            response = requests.post(f"{BASE_URL}/parse", files=files)
            print("Response Status:", response.status_code)
            if response.status_code == 200:
                print("Response JSON:", response.json())
            else:
                print("Error Details:", response.text)
    except Exception as e:
        print(f"Failed to connect to /parse: {str(e)}")
