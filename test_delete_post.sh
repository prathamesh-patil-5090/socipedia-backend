#!/bin/bash

# Test script to verify post deletion functionality

echo "Testing post deletion functionality..."

# Assuming you have a test post ID and valid token
# Replace these with actual values for testing

POST_ID="your_post_id_here"
TOKEN="your_token_here"

echo "Attempting to delete post with ID: $POST_ID"

# Test the delete endpoint
curl -X DELETE \
  "http://localhost:8000/api/posts/$POST_ID/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -v

echo "Delete test completed."
