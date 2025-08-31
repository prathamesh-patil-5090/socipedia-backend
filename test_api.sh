#!/bin/bash

echo "Testing Django API login and posts..."

# Test login
echo "1. Testing login..."
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser1", "password": "testpassword"}')

echo "Login response:"
echo "$LOGIN_RESPONSE" | python -m json.tool

# Extract token
TOKEN=$(echo "$LOGIN_RESPONSE" | python -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('token', ''))
except:
    pass
")

if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
    echo ""
    echo "2. Token obtained: ${TOKEN:0:30}..."
    
    echo ""
    echo "3. Testing posts endpoint..."
    POSTS_RESPONSE=$(curl -s -X GET http://localhost:8000/api/posts/ \
      -H "Authorization: Bearer $TOKEN")
    
    echo "Posts response:"
    echo "$POSTS_RESPONSE" | python -m json.tool
else
    echo "Failed to get token!"
fi
