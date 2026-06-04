"""
Image optimization utilities for the Foodgram application.
Handles image compression, format conversion, and optimization.
"""

from PIL import Image
import os
from django.conf import settings


def optimize_uploaded_image(image_file, max_width=1200, max_height=1200, quality=85):
    """
    Optimize uploaded images by:
    - Resizing to max dimensions
    - Compressing to reduce file size
    - Converting to efficient format
    
    Args:
        image_file: The image file to optimize
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels
        quality: JPEG quality (1-100)
    
    Returns:
        Optimized image file
    """
    try:
        img = Image.open(image_file)
        
        # Convert RGBA to RGB if needed (for JPEG)
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img
        
        # Resize while maintaining aspect ratio
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Save optimized image
        img.save(image_file, 'JPEG', quality=quality, optimize=True)
        
        return image_file
    except Exception as e:
        print(f"Error optimizing image: {e}")
        return image_file


def get_image_dimensions(image_path):
    """
    Get image dimensions for template rendering.
    
    Args:
        image_path: Path to the image
    
    Returns:
        Tuple of (width, height) or (250, 250) as default
    """
    try:
        if not image_path:
            return (250, 250)
        
        img = Image.open(image_path)
        return img.size
    except Exception:
        return (250, 250)


def get_responsive_image_srcset(image_url, base_name="recipe"):
    """
    Generate responsive image srcset for multiple resolutions.
    
    Args:
        image_url: The base image URL
        base_name: Name for generating different sizes
    
    Returns:
        Dictionary with srcset information
    """
    if not image_url:
        return None
    
    return {
        'src': image_url,
        'srcset': f"{image_url} 1x, {image_url}?w=500 1.5x, {image_url}?w=400 2x"
    }
