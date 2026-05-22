#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JWFileFilter - SRP Refactoring Unit Tests
"""

import unittest
from pathlib import Path
import tempfile
import shutil
import time
from PIL import Image

from file_util import format_file_size
from duplicate_finder import DuplicateFinder
from image_processor import ImageProcessor

class TestFileUtil(unittest.TestCase):
    def test_format_file_size(self):
        self.assertEqual(format_file_size(0), "0 B")
        self.assertEqual(format_file_size(100), "100.0 B")
        self.assertEqual(format_file_size(1024), "1.0 KB")
        self.assertEqual(format_file_size(1024 * 1024), "1.0 MB")
        self.assertEqual(format_file_size(1.5 * 1024 * 1024 * 1024), "1.5 GB")

class TestDuplicateFinder(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.finder = DuplicateFinder()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_find_duplicates(self):
        # Create unique files
        file1 = self.test_dir / "image1.jpg"
        file2 = self.test_dir / "image2.jpg"
        
        file1.write_text("dummy data 1")
        file2.write_text("dummy data 2")
        
        # Set same modification time and size to make them duplicates
        mtime = time.time()
        os.utime(file1, (mtime, mtime))
        os.utime(file2, (mtime, mtime))
        
        # Also create a non-duplicate file
        file3 = self.test_dir / "image3.jpg"
        file3.write_text("different size dummy data")
        
        duplicates = self.finder.find_duplicates(
            dir_path=self.test_dir,
            show_images=True,
            show_videos=False,
            show_others=False,
            recursive=False
        )
        
        self.assertEqual(len(duplicates), 1)
        pair = duplicates[0]
        self.assertTrue((pair[0] == file1 and pair[1] == file2) or (pair[0] == file2 and pair[1] == file1))

    def test_delete_files(self):
        file1 = self.test_dir / "temp_to_delete.txt"
        file1.write_text("delete me")
        
        self.assertTrue(file1.exists())
        self.finder.delete_files([file1])
        self.assertFalse(file1.exists())

class TestImageProcessor(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.img_path = self.test_dir / "test_image.png"
        
        # Create a small PIL image
        img = Image.new("RGB", (200, 100), color="red")
        img.save(self.img_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_load_and_scale_image(self):
        # Scaling down image
        scaled = ImageProcessor.load_and_scale_image(self.img_path, max_width=100, max_height=100)
        self.assertEqual(scaled.size, (100, 50))  # Aspect ratio maintained
        
        # Scaling image that is already smaller than max dimensions should not upscale (limit to scale <= 1.0)
        scaled_no_upscale = ImageProcessor.load_and_scale_image(self.img_path, max_width=400, max_height=400)
        self.assertEqual(scaled_no_upscale.size, (200, 100))

if __name__ == "__main__":
    import os
    unittest.main()
