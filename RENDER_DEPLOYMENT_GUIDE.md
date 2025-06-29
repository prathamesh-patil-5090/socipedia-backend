# Render Deployment Checklist - Socipedia Backend

## ✅ Pre-Deployment Checklist

### 1. Code Preparation ✅ COMPLETED
- [x] All test files removed
- [x] Images and unnecessary files cleaned up
- [x] __pycache__ files removed
- [x] Code committed and pushed to GitHub
- [x] README.md updated with comprehensive documentation
- [x] .gitignore properly configured

### 2. Required Files ✅ VERIFIED
- [x] `requirements.txt` - Production dependencies
- [x] `build.sh` - Render build script
- [x] `manage.py` - Django management
- [x] `public/assets/.gitkeep` - Assets directory structure
- [x] All migration files included

## 🚀 Render Deployment Steps

### 1. Create New Web Service
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository: `socipedia-backend`
4. Select the repository

### 2. Configure Service Settings
```
Name: socipedia-backend
Environment: Python 3
Region: Choose closest to your users
Branch: main
Root Directory: (leave empty)
```

### 3. Build & Deploy Settings
```
Build Command: ./build.sh
Start Command: gunicorn socipedia.wsgi:application
```

### 4. Environment Variables
Add these in Render dashboard:
```
SECRET_KEY=<generate-a-strong-secret-key>
DEBUG=False
ALLOWED_HOSTS=<your-render-url>.onrender.com
```

**To generate SECRET_KEY:**
```python
import secrets
print(secrets.token_urlsafe(50))
```

### 5. Database Configuration
- Render will automatically provide `DATABASE_URL` for PostgreSQL
- Your settings.py is already configured to use it

### 6. Auto-Deploy Settings
- [x] Enable "Auto-Deploy" for automatic deployments on git push

## 📋 Post-Deployment Verification

### 1. Check Deployment Status
- Monitor build logs in Render dashboard
- Ensure build completes successfully
- Check that service starts without errors

### 2. Test API Endpoints
Once deployed, test these endpoints:
```bash
# Health check
curl https://your-app.onrender.com/api/

# Registration
curl -X POST https://your-app.onrender.com/api/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123", "email": "test@example.com", "first_name": "Test", "last_name": "User"}'

# Login
curl -X POST https://your-app.onrender.com/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'
```

### 3. Test Image Functionality
- Test image upload (should compress automatically)
- Test image serving API
- Verify images are stored correctly

## 🔧 Important Notes

### Build Process
The `build.sh` script will:
1. Install dependencies from `requirements.txt`
2. Collect static files
3. Run database migrations
4. Create superuser (optional)

### Image Storage
- Images will be stored in the file system on Render
- For production scale, consider using cloud storage (AWS S3, etc.)
- Current setup works well for small to medium applications

### Environment Variables Detail
```bash
SECRET_KEY=your-django-secret-key-here
DEBUG=False
DATABASE_URL=postgresql://... (auto-provided by Render)
ALLOWED_HOSTS=your-app-name.onrender.com
```

## 🎯 Expected Features After Deployment

✅ **Authentication System**
- User registration with automatic profile stats
- JWT login with access/refresh tokens
- Token refresh functionality

✅ **Image Compression**
- Automatic compression on upload
- Profile pictures: 800x800px @ 85% quality
- Post images: 1200x1200px @ 80% quality
- 70-95% size reduction

✅ **Full CRUD Operations**
- Users, Posts, Comments management
- Like/unlike functionality
- Friend system

✅ **API Features**
- PATCH API for posts (multiple endpoints)
- Image serving API for frontend
- CORS support for web applications

## 🚨 Troubleshooting

### Common Issues:
1. **Build fails with "No module named 'api.image_utils'"**: ✅ FIXED
   - This was resolved by updating migration file 0004
   - Image compression still works via model save() method
   
2. **Build fails**: Check build.sh permissions and requirements.txt
3. **Database errors**: Ensure migrations are included
4. **Static files**: Whitenoise is configured in settings.py
5. **Image uploads**: Check MEDIA settings and file permissions

### Logs Location:
- Build logs: Render dashboard → Service → Events
- Runtime logs: Render dashboard → Service → Logs

## 🎉 Success Confirmation

Your deployment is successful when:
- ✅ Build completes without errors
- ✅ Service starts and shows "Live"
- ✅ API endpoints respond correctly
- ✅ Image upload and compression works
- ✅ Database operations function properly

---

**Your Socipedia Django Backend is now ready for production! 🚀**
