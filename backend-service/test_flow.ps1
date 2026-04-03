$ErrorActionPreference = "Stop"

# 1. Create a fresh test user
$userEmail = "pro_user_" + (Get-Random) + "@example.com"
$signup = Invoke-RestMethod -Uri "http://localhost:5000/api/auth/signup" -Method Post -Body (@{
    email = $userEmail
    password = "password123"
} | ConvertTo-Json) -ContentType "application/json"

$token = $signup.token
Write-Host "✅ User created successfully!"

# 2. Check the user's plan and daily limit
$profile = Invoke-RestMethod -Uri "http://localhost:5000/api/users/me" -Method Get -Headers @{ Authorization = "Bearer $token" }
Write-Host "✅ Logged in as: $($profile.email)"
Write-Host "✅ Current Plan: $($profile.planName) (Limit: $($profile.maxDaily) per day)"

# 3. Upload a file to see the Quota Bouncer in action
Write-Host "📤 Uploading P&ID..."
$filePath = "c:\Users\chand\Downloads\PID_Parser_proj\ai-service\test_pid.png"
curl.exe -H "Authorization: Bearer $token" -F "file=@$filePath" http://localhost:5000/api/jobs
