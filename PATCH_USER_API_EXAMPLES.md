# PATCH API - User Update Examples

## ✅ **What CAN be updated via PATCH API:**

### 1. **Basic Text Fields Update**
```bash
curl -X PATCH http://localhost:8000/api/users/4/ \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Updated",
    "last_name": "NewLastName",
    "location": "New Location",
    "occupation": "Senior Developer"
  }'
```

### 2. **Complete Profile Update (All Editable Fields)**
```bash
curl -X PATCH http://localhost:8000/api/users/4/ \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Updated",
    "last_name": "User",
    "email": "test1@example.com",
    "username": "testuser1",
    "location": "New Location",
    "occupation": "Full Stack Developer"
  }'
```

### 3. **Update with Profile Picture**
```bash
curl -X PATCH http://localhost:8000/api/users/4/ \
  -H "Authorization: Bearer <your_access_token>" \
  -F "first_name=Updated" \
  -F "last_name=User" \
  -F "email=test1@example.com" \
  -F "location=New Location" \
  -F "occupation=Developer" \
  -F "picture=@/path/to/your/image.jpg"
```

### 4. **Update Friends List**
```bash
curl -X PATCH http://localhost:8000/api/users/4/ \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "friends": [1, 2, 3, 5]
  }'
```

### 5. **Partial Update (Only Specific Fields)**
```bash
curl -X PATCH http://localhost:8000/api/users/4/ \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Updated",
    "location": "New Location"
  }'
```

## ❌ **Fields that CANNOT be updated via PATCH:**

- **`picture_path`** - Automatically generated from picture URL
- **`viewed_profile`** - System managed counter
- **`impressions`** - System managed counter  
- **`password`** - Use separate password change endpoint for security

## 📝 **Response Format:**

When successful, you'll get the updated user object:
```json
{
  "id": 4,
  "first_name": "Updated",
  "last_name": "User", 
  "email": "test1@example.com",
  "username": "testuser1",
  "picture": "http://localhost:8000/media/testuser1_image.jpg",
  "picture_path": "/media/testuser1_image.jpg", 
  "friends": [1, 2, 3],
  "location": "New Location",
  "occupation": "Developer",
  "viewed_profile": 1234,
  "impressions": 5678
}
```

## 🔐 **Authentication:**

All PATCH requests require a valid JWT access token in the Authorization header:
```
Authorization: Bearer <your_access_token>
```

Get your token by logging in:
```bash
curl -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser1", "password": "testpassword"}'
```
