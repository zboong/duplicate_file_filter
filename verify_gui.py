#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration test to programmatically verify JWFileFilterGUI and SRP modules.
"""

import tkinter as tk
import tempfile
from pathlib import Path
import os
import shutil
import time
from PIL import Image

from jwfilefiltergui import JWFileFilterGUI

def test_gui_integration():
    print("Starting integration test...")
    # 1. Create a temporary directory
    temp_dir = Path(tempfile.mkdtemp())
    print(f"Temporary test directory: {temp_dir}")
    
    try:
        # 2. Create dummy image files (duplicate size and time)
        img1 = temp_dir / "photo1.jpg"
        img2 = temp_dir / "photo2.jpg"
        img3 = temp_dir / "photo3.jpg" # Unique image
        
        # Save actual small images so PIL can load them
        image_data = Image.new("RGB", (100, 100), color="blue")
        image_data.save(img1)
        image_data.save(img2)
        
        image_data_large = Image.new("RGB", (200, 200), color="green")
        image_data_large.save(img3)
        
        # Match size and modification time for img1 and img2
        mtime = time.time()
        os.utime(img1, (mtime, mtime))
        os.utime(img2, (mtime, mtime))
        
        print("Created test image files:")
        print(f" - {img1.name} (size: {img1.stat().st_size}, mtime: {img1.stat().st_mtime})")
        print(f" - {img2.name} (size: {img2.stat().st_size}, mtime: {img2.stat().st_mtime})")
        print(f" - {img3.name} (size: {img3.stat().st_size}, mtime: {img3.stat().st_mtime})")
        
        # 3. Instantiate Tk and the GUI class
        root = tk.Tk()
        # Withdraw the root window so it doesn't pop up on the screen during tests
        root.withdraw()
        
        app = JWFileFilterGUI(root)
        
        # Set the directory in the GUI
        app.current_dir.set(str(temp_dir))
        print(f"Set current directory in GUI: {app.current_dir.get()}")
        
        # Set filters
        app.show_images.set(True)
        app.show_videos.set(False)
        app.show_others.set(False)
        app.recursive_search.set(False)
        
        # 4. Simulate clicking "중복 파일 검색"
        print("Simulating duplicate search...")
        app.find_duplicates()
        
        # 5. Verify duplicates were found
        print(f"Status bar message: {app.status_var.get()}")
        print(f"Number of duplicate pairs found: {len(app.duplicate_pairs)}")
        assert len(app.duplicate_pairs) == 1, "Should find exactly 1 duplicate pair"
        
        # Verify treeview entries
        tree_children = app.duplicate_tree.get_children()
        print(f"Treeview entries count: {len(tree_children)}")
        assert len(tree_children) == 1, "Treeview should show 1 entry"
        
        # 6. Simulate selection of duplicate pair
        print("Simulating selection of the duplicate pair...")
        app.duplicate_tree.selection_set(tree_children[0])
        # Trigger event handler manually
        app.on_duplicate_select(None)
        
        # Verify images loaded in viewer labels
        print("Verifying image viewers...")
        assert app.image_viewer1.image is not None, "Image viewer 1 should have loaded photo1"
        assert app.image_viewer2.image is not None, "Image viewer 2 should have loaded photo2"
        print("Images successfully loaded into both viewers!")
        
        # 7. Simulate checking delete box for photo1 (checkbox1)
        print("Selecting photo1 for deletion...")
        app.checkbox1.set(True)
        app.checkbox2.set(False)
        
        # Mock messagebox.askyesno to automatically return True
        old_askyesno = tk.messagebox.askyesno
        tk.messagebox.askyesno = lambda title, message: True
        
        # Simulate clicking "선택된 파일 삭제"
        print("Simulating deletion of selected files...")
        app.delete_selected_files()
        
        # Restore messagebox
        tk.messagebox.askyesno = old_askyesno
        
        # 8. Verify photo1 was deleted, and duplicate list was updated (should be empty now)
        print("Verifying deletion outcome...")
        assert not img1.exists(), "photo1.jpg should be deleted"
        assert img2.exists(), "photo2.jpg should still exist"
        assert img3.exists(), "photo3.jpg should still exist"
        print("File deletion verified successfully!")
        
        # Verify duplicates updated
        print(f"Remaining duplicate pairs: {len(app.duplicate_pairs)}")
        assert len(app.duplicate_pairs) == 0, "No duplicate pairs should remain"
        assert len(app.duplicate_tree.get_children()) == 0, "Treeview should be empty"
        
        print("\nINTEGRATION TEST PASSED SUCCESSFULLY! The GUI and business logic work perfectly.")
        
        # Clean up Tk
        root.destroy()
        
    finally:
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_gui_integration()
