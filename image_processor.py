#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JWFileFilter - Image processing utilities
"""

from pathlib import Path
from PIL import Image

class ImageProcessor:
    """
    Handles image loading and scaling operations.
    """
    
    @staticmethod
    def load_and_scale_image(file_path: Path, max_width: int, max_height: int) -> Image.Image:
        """
        Open an image file and scale it to fit within maximum dimensions
        while preserving the original aspect ratio.
        
        Args:
            file_path: Path to the image file.
            max_width: Maximum allowed width for the scaled image.
            max_height: Maximum allowed height for the scaled image.
            
        Returns:
            A scaled PIL.Image object.
        """
        image = Image.open(file_path)
        img_width, img_height = image.size
        
        # Calculate scale factor to maintain aspect ratio
        scale = min(max_width / img_width, max_height / img_height, 1.0)
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        # Resize utilizing high-quality Lanczos resampling
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
