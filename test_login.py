#!/usr/bin/env python
import os
import sys
import django

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socipedia.settings')
django.setup()

from django.contrib.auth import authenticate
from api.models import User
from api.serializers import UserSerializer
from rest_framework_simplejwt.tokens import RefreshToken

def test_login():
    print("Testing login functionality...")
    
    # Check if user exists
    try:
        user = User.objects.get(username='testuser1')
        print(f"✅ User found: {user.username} (ID: {user.id})")
        print(f"✅ User is active: {user.is_active}")
        print(f"✅ Password check: {user.check_password('testpassword')}")
    except User.DoesNotExist:
        print("❌ User 'testuser1' does not exist")
        return
    
    # Test authentication
    auth_user = authenticate(username='testuser1', password='testpassword')
    if auth_user:
        print(f"✅ Authentication successful: {auth_user.username}")
        
        # Test JWT token generation
        try:
            refresh = RefreshToken.for_user(auth_user)
            access_token = str(refresh.access_token)
            print(f"✅ JWT token generated successfully")
            print(f"Access token (first 30 chars): {access_token[:30]}...")
            
            # Test serializer
            serializer = UserSerializer(auth_user)
            print(f"✅ User serialization successful")
            print(f"Serialized data keys: {list(serializer.data.keys())}")
            
            # Print expected response
            response_data = {
                'user': serializer.data,
                'token': access_token,
                'refresh': str(refresh),
                'access': access_token,
            }
            print(f"✅ Expected response structure ready")
            
        except Exception as e:
            print(f"❌ JWT/Serialization error: {e}")
    else:
        print("❌ Authentication failed")

if __name__ == "__main__":
    test_login()
