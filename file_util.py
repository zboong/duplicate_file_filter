#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JWFileFilter - Utility functions for file operations
"""

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in bytes to a human-readable string.
    
    Args:
        size_bytes: The file size in bytes.
        
    Returns:
        A human-readable string representation of the file size (e.g. "1.5 MB").
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"
