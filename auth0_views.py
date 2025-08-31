import json
from authlib.integrations.django_client import OAuth
from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse
from urllib.parse import quote_plus, urlencode
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from api.models import User
from api.serializers import UserSerializer
import requests

# Configure OAuth
oauth = OAuth()

oauth.register(
    "auth0",
    client_id=settings.AUTH0_CLIENT_ID,
    client_secret=settings.AUTH0_CLIENT_SECRET,
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f"https://{settings.AUTH0_DOMAIN}/.well-known/openid-configuration",
)

def login(request):
    """Redirect to Auth0 login"""
    return oauth.auth0.authorize_redirect(
        request, request.build_absolute_uri(reverse("auth0_callback"))
    )

def callback(request):
    """Handle Auth0 callback"""
    try:
        token = oauth.auth0.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if user_info:
            # Try to find existing user or create new one
            email = user_info.get('email')
            name = user_info.get('name', '').split(' ')
            first_name = name[0] if name else ''
            last_name = ' '.join(name[1:]) if len(name) > 1 else ''
            username = user_info.get('nickname') or email.split('@')[0]
            
            # Check if user exists
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': username,
                    'first_name': first_name,
                    'last_name': last_name,
                    'is_active': True,
                }
            )
            
            if created:
                # Set random profile stats for new users
                import random
                user.viewed_profile = random.randint(0, 10000)
                user.impressions = random.randint(0, 10000)
                user.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # Store user info in session
            request.session["user"] = token
            request.session["jwt_access"] = access_token
            request.session["jwt_refresh"] = refresh_token
            
            # Redirect to frontend with tokens
            frontend_url = "http://localhost:3001"  # Adjust based on your frontend URL
            return redirect(f"{frontend_url}/?auth0_success=true&access_token={access_token}&refresh_token={refresh_token}")
        
    except Exception as e:
        print(f"Auth0 callback error: {e}")
        # Redirect to frontend with error
        frontend_url = "http://localhost:3001"
        return redirect(f"{frontend_url}/?auth0_error=true")
    
    return redirect("http://localhost:3001")

def logout(request):
    """Clear session and redirect to Auth0 logout"""
    request.session.clear()
    
    return redirect(
        f"https://{settings.AUTH0_DOMAIN}/v2/logout?"
        + urlencode(
            {
                "returnTo": "http://localhost:3001",  # Redirect to your frontend
                "client_id": settings.AUTH0_CLIENT_ID,
            },
            quote_via=quote_plus,
        ),
    )

def index(request):
    """Simple index page for testing Auth0 integration"""
    return render(
        request,
        "index.html",
        context={
            "session": request.session.get("user"),
            "pretty": json.dumps(request.session.get("user"), indent=4),
        },
    )

@api_view(['POST'])
@permission_classes([AllowAny])
def auth0_token_exchange(request):
    """Exchange Auth0 token for user information and JWT tokens"""
    try:
        auth0_token = request.data.get('token')
        
        if not auth0_token:
            return JsonResponse({'error': 'No Auth0 token provided'}, status=400)
        
        # Verify token with Auth0
        headers = {'Authorization': f'Bearer {auth0_token}'}
        response = requests.get(f'https://{settings.AUTH0_DOMAIN}/userinfo', headers=headers)
        
        if response.status_code != 200:
            return JsonResponse({'error': 'Invalid Auth0 token'}, status=400)
        
        user_info = response.json()
        email = user_info.get('email')
        name = user_info.get('name', '').split(' ')
        first_name = name[0] if name else ''
        last_name = ' '.join(name[1:]) if len(name) > 1 else ''
        username = user_info.get('nickname') or email.split('@')[0]
        
        # Get or create user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'is_active': True,
            }
        )
        
        if created:
            import random
            user.viewed_profile = random.randint(0, 10000)
            user.impressions = random.randint(0, 10000)
            user.save()
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return JsonResponse({
            'user': UserSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
