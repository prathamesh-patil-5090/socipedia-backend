#!/usr/bin/env python3
"""
Quick test to verify image compression works after migration fix
"""
import requests
import json
import random
import string
from PIL import Image

def generate_username():
    return "test_" + ''.join(random.choices(string.ascii_lowercase, k=4))

def create_test_image():
    img = Image.new('RGB', (1500, 1000), color='blue')
    img.save('quick_test.jpg', 'JPEG', quality=100)
    return 'quick_test.jpg'

def test_compression_after_fix():
    BASE_URL = "http://localhost:8000/api"
    
    print("🔧 Testing image compression after migration fix...")
    
    # Create test image
    test_img = create_test_image()
    original_size = os.path.getsize(test_img) / 1024  # KB
    
    # Register user
    username = generate_username()
    register_data = {
        "username": username,
        "password": "testpass",
        "email": f"{username}@test.com",
        "first_name": "Test",
        "last_name": "User"
    }
    
    response = requests.post(f"{BASE_URL}/register/", json=register_data)
    if response.status_code != 201:
        print(f"❌ Registration failed: {response.text}")
        return False
    
    # Login
    login_data = {"username": username, "password": "testpass"}
    response = requests.post(f"{BASE_URL}/login/", json=login_data)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        return False
    
    token = response.json()["access"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test post with image
    with open(test_img, 'rb') as f:
        files = {'picture': f}
        data = {'description': 'Testing compression after migration fix'}
        response = requests.post(f"{BASE_URL}/posts/", files=files, data=data, headers=headers)
    
    if response.status_code == 201:
        post_data = response.json()
        picture_url = post_data.get("picture")
        if picture_url:
            filename = picture_url.split('/')[-1]
            compressed_path = f"public/assets/{filename}"
            if os.path.exists(compressed_path):
                compressed_size = os.path.getsize(compressed_path) / 1024  # KB
                reduction = ((original_size - compressed_size) / original_size) * 100
                print(f"✅ Compression working: {original_size:.1f} KB → {compressed_size:.1f} KB ({reduction:.1f}% reduction)")
                
                # Cleanup
                os.remove(test_img)
                return True
    
    print("❌ Image compression test failed")
    os.remove(test_img)
    return False

if __name__ == "__main__":
    import os
    success = test_compression_after_fix()
    if success:
        print("🎉 Image compression verified working after migration fix!")
    else:
        print("⚠️ Image compression test failed")
