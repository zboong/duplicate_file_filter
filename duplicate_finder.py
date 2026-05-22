#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JWFileFilter - Duplicate file detection logic
"""

import os
from pathlib import Path
from collections import defaultdict
from typing import List, Tuple, Set

# Default extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm'}

class DuplicateFinder:
    """
    Handles directory scanning, filtering files by type, and finding duplicate files.
    """
    
    def __init__(self, image_extensions: Set[str] = None, video_extensions: Set[str] = None):
        self.image_extensions = image_extensions if image_extensions is not None else IMAGE_EXTENSIONS
        self.video_extensions = video_extensions if video_extensions is not None else VIDEO_EXTENSIONS

    def find_duplicates(
        self, 
        dir_path: Path, 
        show_images: bool, 
        show_videos: bool, 
        show_others: bool, 
        recursive: bool
    ) -> List[Tuple[Path, Path]]:
        """
        Scan the given directory and find duplicate file pairs.
        
        Args:
            dir_path: Path to the directory to scan.
            show_images: Whether to scan image files.
            show_videos: Whether to scan video files.
            show_others: Whether to scan other file types.
            recursive: Whether to scan subdirectories recursively.
            
        Returns:
            A list of tuples, each containing a pair of Path objects that are duplicate.
        """
        if not dir_path.exists() or not dir_path.is_dir():
            return []

        all_files = []
        search_pattern = '**/*' if recursive else '*'
        
        for file_path in dir_path.glob(search_pattern):
            if not file_path.is_file():
                continue
            
            # Exclude standard environment/configuration folders to prevent performance lags and noise
            try:
                rel_parts = file_path.relative_to(dir_path).parts
                if any(part.startswith('.') or part in ('venv', 'env', 'ENV', '__pycache__', 'node_modules') for part in rel_parts):
                    continue
            except ValueError:
                pass
                
            suffix = file_path.suffix.lower()
            is_image = suffix in self.image_extensions
            is_video = suffix in self.video_extensions
            
            if is_image and show_images:
                all_files.append(file_path)
            elif is_video and show_videos:
                all_files.append(file_path)
            elif not is_image and not is_video and show_others:
                all_files.append(file_path)

        # Group files by size and modification time
        file_groups = defaultdict(list)
        for file_path in all_files:
            try:
                stat = file_path.stat()
                # Group by size and rounded modification time (tolerance: 1s)
                time_key = round(stat.st_mtime)
                key = (stat.st_size, time_key)
                file_groups[key].append(file_path)
            except Exception:
                continue

        # Form duplicate pairs
        duplicate_pairs = []
        for key, files in file_groups.items():
            if len(files) > 1:
                # Create unique pairs from the list of duplicate files
                for i in range(len(files)):
                    for j in range(i + 1, len(files)):
                        duplicate_pairs.append((files[i], files[j]))

        return duplicate_pairs

    def delete_files(self, file_paths: List[Path]) -> None:
        """
        Delete specified files from the filesystem.
        
        Args:
            file_paths: A list of Paths of files to delete.
        """
        for file_path in file_paths:
            if file_path.exists() and file_path.is_file():
                os.remove(file_path)
