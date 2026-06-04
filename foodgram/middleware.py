"""
Middleware for optimizing image and media file serving.
Adds cache control headers for static and media files.
"""

import re
from django.utils.cache import patch_cache_control


class CacheControlMiddleware:
    """
    Add cache control headers to responses for static files and media.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Media file extensions to cache
        self.cacheable_extensions = (
            '.jpg', '.jpeg', '.png', '.gif', '.webp',  # images
            '.css', '.js',  # stylesheets and scripts
            '.woff', '.woff2', '.ttf', '.eot',  # fonts
        )
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Check if this is a media or static file
        path = request.path.lower()
        
        if any(path.endswith(ext) for ext in self.cacheable_extensions):
            # Cache static/media files for 30 days (2592000 seconds)
            if path.startswith('/media/'):
                patch_cache_control(
                    response,
                    max_age=2592000,  # 30 days
                    public=True
                )
            elif path.startswith('/static/'):
                patch_cache_control(
                    response,
                    max_age=31536000,  # 1 year for static files
                    public=True,
                    immutable=True
                )
        
        return response
