#!/bin/bash

echo "Testing Django API pagination..."

# Test posts without authentication (should work due to IsAuthenticatedOrReadOnly)
echo "1. Testing posts pagination - Page 1..."
curl -s "http://localhost:8000/api/posts/?page=1&limit=5" \
  -H "Content-Type: application/json" | python -m json.tool

echo -e "\n\n2. Testing posts pagination - Page 2..."
curl -s "http://localhost:8000/api/posts/?page=2&limit=5" \
  -H "Content-Type: application/json" | python -m json.tool

echo -e "\n\n3. Testing posts with default pagination..."
curl -s "http://localhost:8000/api/posts/" \
  -H "Content-Type: application/json" | python -m json.tool
