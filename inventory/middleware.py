# middleware.py - Custom Django Middleware Examples

from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class UserActivityMiddleware(MiddlewareMixin):
    """Track user activity and update last_seen timestamp"""
    
    def process_request(self, request):
        if request.user.is_authenticated:
            # Update user's last activity
            request.user.last_seen = timezone.now()
            request.user.save(update_fields=['last_seen'])
        return None

class AdminOnlyAccessMiddleware(MiddlewareMixin):
    """Restrict certain URLs to admin users only"""
    
    ADMIN_ONLY_URLS = [
        '/manage/',
        '/reports/',
        '/admin/',
    ]
    
    def process_request(self, request):
        # Check if the request path starts with any admin-only URL
        for admin_url in self.ADMIN_ONLY_URLS:
            if request.path.startswith(admin_url):
                if not request.user.is_authenticated:
                    messages.error(request, 'Please login to access this page.')
                    return redirect('login')
                elif request.user.role != 'admin':
                    messages.error(request, 'Admin access required.')
                    return redirect('dashboard')
        return None

class RequestLoggingMiddleware(MiddlewareMixin):
    """Log all requests for debugging/monitoring"""
    
    def process_request(self, request):
        logger.info(f"Request: {request.method} {request.path} from {request.META.get('REMOTE_ADDR')}")
        return None
    
    def process_response(self, request, response):
        logger.info(f"Response: {response.status_code} for {request.path}")
        return response

class MaintenanceModeMiddleware(MiddlewareMixin):
    """Put site in maintenance mode"""
    
    def process_request(self, request):
        if getattr(settings, 'MAINTENANCE_MODE', False):
            if not request.user.is_staff:
                from django.http import HttpResponse
                return HttpResponse(
                    "Site is under maintenance. Please try again later.",
                    status=503
                )
        return None

# Add to settings.py:
# MIDDLEWARE = [
#     'django.middleware.security.SecurityMiddleware',
#     'inventory.middleware.UserActivityMiddleware',  # Custom
#     'inventory.middleware.AdminOnlyAccessMiddleware',  # Custom
#     'django.contrib.sessions.middleware.SessionMiddleware',
#     # ... other middleware
# ]
