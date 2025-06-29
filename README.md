# Socipedia Django Backend

A full-featured social media backend built with Django REST Framework, featuring automatic image compression, JWT authentication, and comprehensive social media functionality.

## 🚀 Features

- **Authentication**: JWT-based authentication with registration and login
- **User Management**: Custom user model with profile pictures and friend management
- **Posts**: Create, read, update, delete posts with image support
- **Comments**: Full commenting system with like functionality
- **Image Compression**: Automatic image compression for optimal storage and performance
- **Like System**: Like/unlike posts and comments
- **Friend System**: Add/remove friends functionality
- **Image Serving**: Dedicated API for serving images to frontend
- **CORS Support**: Frontend integration ready

## 🔧 Image Compression

All uploaded images are automatically compressed:
- **Profile Pictures**: Max 800x800px, 85% quality
- **Post Images**: Max 1200x1200px, 80% quality
- **Average Compression**: 70-95% size reduction
- **Format Support**: JPEG, PNG with smart format handling

## 📋 API Endpoints

### Authentication
- `POST /api/register/` - User registration
- `POST /api/login/` - User login
- `POST /api/token/refresh/` - Refresh JWT token

### Users
- `GET /api/users/` - List users
- `GET /api/users/{id}/` - Get user details
- `PATCH /api/users/{id}/` - Update user
- `PATCH /api/users/{id}/upload_picture/` - Upload profile picture
- `POST /api/users/{id}/add_friend/` - Add friend
- `POST /api/users/{id}/remove_friend/` - Remove friend

### Posts
- `GET /api/posts/` - List posts
- `POST /api/posts/` - Create post (with image)
- `GET /api/posts/{id}/` - Get post details
- `PATCH /api/posts/{id}/` - Update post
- `PATCH /api/posts/{id}/update_post/` - Custom update (description + image)
- `DELETE /api/posts/{id}/` - Delete post
- `POST /api/posts/{id}/like/` - Like/unlike post

### Comments
- `GET /api/comments/` - List comments
- `POST /api/comments/` - Create comment
- `GET /api/comments/{id}/` - Get comment
- `PATCH /api/comments/{id}/` - Update comment
- `DELETE /api/comments/{id}/` - Delete comment
- `POST /api/comments/{id}/like/` - Like/unlike comment

### Images
- `GET /api/images/{filename}` - Serve images to frontend

## 🛠️ Local Development

### Prerequisites
- Python 3.8+
- pip

### Setup
1. Clone the repository
2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows
   # or
   source venv/bin/activate      # Linux/Mac
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements-local.txt
   ```

4. Run migrations:
   ```bash
   python manage.py migrate
   ```

5. Start development server:
   ```bash
   python manage.py runserver
   ```

The API will be available at `http://localhost:8000/api/`

## 🚀 Deployment (Render)

### Environment Variables
Set these in your Render dashboard:
- `SECRET_KEY` - Django secret key
- `DEBUG` - Set to "False"
- `DATABASE_URL` - PostgreSQL connection string (auto-provided by Render)

### Build Command
```bash
./build.sh
```

### Start Command
```bash
gunicorn socipedia.wsgi:application
```

## 📚 Documentation

- `api-localhost-endpoints.json` - Complete API documentation with curl examples
- `api-endpoints-with-images.json` - Production API endpoints
- `IMAGE_COMPRESSION_IMPLEMENTATION.md` - Detailed image compression guide
- `PATCH_AND_IMAGES_IMPLEMENTATION.md` - PATCH API and image serving guide

## 🔒 Security & Performance

- JWT authentication with refresh tokens
- User ownership validation for all operations
- Automatic image compression (70-95% size reduction)
- CORS properly configured
- Static file serving via Whitenoise
