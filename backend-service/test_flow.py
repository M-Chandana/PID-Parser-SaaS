import requests
import string
import random

BASE_URL = 'http://localhost:5000/api'

def run_test():
    # 1. Create a random user
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    email = f"test_{random_str}@example.com"
    password = "password123"
    
    print(f"Creating user {email}...")
    signup_res = requests.post(f"{BASE_URL}/auth/signup", json={"email": email, "password": password})
    if signup_res.status_code != 201:
        print(f"Signup failed: {signup_res.text}")
        return
    token = signup_res.json()['token']
    print("✅ User created successfully")

    # 2. Check profile
    headers = {"Authorization": f"Bearer {token}"}
    profile_res = requests.get(f"{BASE_URL}/users/me", headers=headers)
    
    profile = profile_res.json()
    print(f"✅ Logged in as: {profile['email']}")
    print(f"✅ Current Plan: {profile['planName']} (Limit: {profile['maxDaily']} per day)")

    # 3. Upload file
    print("📤 Uploading P&ID...")
    file_path = r"c:\Users\chand\Downloads\PID_Parser_proj\ai-service\test_pid.png"
    
    with open(file_path, 'rb') as f:
        files = {'file':('test_pid.png', f, 'image/png')}
        upload_res = requests.post(f"{BASE_URL}/jobs", headers=headers, files=files)
        
    print(f"✅ Upload Response: {upload_res.status_code}")
    print(upload_res.json())

if __name__ == "__main__":
    run_test()
