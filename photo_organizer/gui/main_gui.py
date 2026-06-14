#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Photo Organizer GUI - Tab 기반 통합 인터페이스
- Tab 1: 정리 (Organizer) - EXIF 그룹핑 + 통일 파일명 Copy
- Tab 2: 중복 관리 (Duplicates) - 기존 JWFileFilter 스타일 비교/삭제
- Tab 3: 설정 (Settings)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import sys
import threading
import queue

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import load_config, Config
from core.models import PhotoMetadata, PhotoGroup
from core.exif_utils import extract_photo_metadata
from core.renamer import generate_new_filename
from core.grouper import group_photos_by_time, assign_event_names
from core.duplicate_detector import detect_all_duplicates
from core.duplicate_handler import organize_duplicates, get_duplicate_summary
import shutil

# Import DuplicateFinder from existing JWFileFilter logic
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from duplicate_finder import DuplicateFinder, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
    HAS_DUPLICATE_FINDER = True
except ImportError:
    HAS_DUPLICATE_FINDER = False


class PhotoOrganizerGUI:
    """Main GUI application with Tab-based interface."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Photo Organizer - NAS 사진 정리 도구")
        self.root.geometry("1200x900")
        self.root.minsize(1100, 800)
        
        self.config = load_config()
        self.photos = []
        self.groups = []
        self.duplicates = []
        
        self.setup_ui()
    
    def setup_ui(self):
        """Create main tabbed interface."""
        # Notebook (Tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Organizer
        self.tab_organizer = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_organizer, text="  📁  사진 정리  ")
        self.setup_organizer_tab()
        
        # Tab 2: Duplicates
        self.tab_duplicates = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_duplicates, text="  🔍  중복 관리  ")
        self.setup_duplicates_tab()
        
        # Tab 3: Settings
        self.tab_settings = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_settings, text="  ⚙️  설정  ")
        self.setup_settings_tab()
        
        # Status bar
        self.status_var = tk.StringVar(value="준비 완료")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    # ============================================================
    # TAB 1: Organizer
    # ============================================================
    def setup_organizer_tab(self):
        frame = self.tab_organizer
        
        # Source / Target selection
        path_frame = ttk.LabelFrame(frame, text="경로 설정", padding=10)
        path_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(path_frame, text="Source (원본):").grid(row=0, column=0, sticky=tk.W)
        self.source_var = tk.StringVar(value=str(self.config.paths.source))
        ttk.Entry(path_frame, textvariable=self.source_var, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(path_frame, text="찾아보기", command=self.browse_source).grid(row=0, column=2)
        
        ttk.Label(path_frame, text="Target (정리됨):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.target_var = tk.StringVar(value=str(self.config.paths.target))
        ttk.Entry(path_frame, textvariable=self.target_var, width=60).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(path_frame, text="찾아보기", command=self.browse_target).grid(row=1, column=2, pady=5)
        
        # Options
        opt_frame = ttk.LabelFrame(frame, text="옵션", padding=10)
        opt_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.dry_run_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="Dry-run (실제 복사하지 않음)", variable=self.dry_run_var).pack(side=tk.LEFT)
        
        self.recursive_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="하위 폴더 포함", variable=self.recursive_var).pack(side=tk.LEFT, padx=20)
        
        ttk.Label(opt_frame, text="이벤트 시간 간격 (시간):").pack(side=tk.LEFT, padx=10)
        self.time_gap_var = tk.IntVar(value=self.config.grouping.time_gap_hours)
        ttk.Spinbox(opt_frame, from_=1, to=72, textvariable=self.time_gap_var, width=5).pack(side=tk.LEFT)
        
        # Action buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="SCAN", command=self.preview_organize).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="🚀 정리 실행", command=self.run_organize).pack(side=tk.LEFT, padx=10)
        
        # Preview text
        preview_frame = ttk.LabelFrame(frame, text="정리 미리보기", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.preview_text = tk.Text(preview_frame, height=20, font=("Consolas", 10))
        self.preview_text.pack(fill=tk.BOTH, expand=True)
    
    def browse_source(self):
        path = filedialog.askdirectory(title="Source 폴더 선택")
        if path:
            self.source_var.set(path)
    
    def browse_target(self):
        path = filedialog.askdirectory(title="Target 폴더 선택")
        if path:
            self.target_var.set(path)
    
    def preview_organize(self):
        source = Path(self.source_var.get())
        if not source.exists():
            messagebox.showerror("오류", "Source 경로가 존재하지 않습니다.")
            return
        
        self.preview_text.delete("1.0", tk.END)
        
        # 1. Disable main window and show loading overlay
        self.root.attributes('-disabled', 1)
        self.loading_win = tk.Toplevel(self.root)
        self.loading_win.geometry("300x100")
        self.loading_win.title("Loading")
        self.loading_win.transient(self.root)
        self.loading_win.grab_set() # Modal
        
        ttk.Label(self.loading_win, text="스캔 중...", font=("Segoe UI", 14)).pack(pady=20)
        self.progress_label = ttk.Label(self.loading_win, text="파일 목록 생성 중...")
        self.progress_label.pack()
        
        # 2. Start thread
        self.scan_queue = queue.Queue()
        thread = threading.Thread(target=self._scan_worker, args=(source, self.recursive_var.get()), daemon=True)
        thread.start()
        
        # 3. Check queue periodically
        self.root.after(100, self._check_scan_queue)
    
    def run_organize(self):
        if not self.groups:
            messagebox.showwarning("경고", "먼저 '스캔 및 그룹핑 미리보기'를 실행하세요.")
            return
        
        target = Path(self.target_var.get())
        dry_run = self.dry_run_var.get()
        
        if not dry_run:
            if not messagebox.askyesno("확인", "실제 파일을 복사합니다. 계속하시겠습니까?"):
                return
        
        # 1. Preview summary
        total_photos = sum(len(g.photos) for g in self.groups)
        summary = f"\n=== \uc815리 \uacc4획 ===\n"
        summary += f"이벤트: {len(self.groups)}개\n"
        summary += f"총 사진: {total_photos}장\n"
        summary += f"Target: {target}\n"
        if dry_run:
            summary += "\n[DRY-RUN] \uc2e4제 복사는 수행되지 않습니다.\n"
        
        self.preview_text.insert(tk.END, summary)
        
        if not dry_run:
            if not messagebox.askyesno("확인", f"{len(self.groups)}개 이벤트, {total_photos}장을 Target에 복사합니다.\n\uacc4속하시겠습니까?"):
                self.preview_text.insert(tk.END, "\n\ucde8소되었습니다.\n")
                return
        
        # 2. Actual Copy (or Dry-run simulation)
        copied = 0
        self.status_var.set("복사 시작...")
        
        for group in self.groups:
            event_dir = target / group.folder_name
            if not dry_run:
                event_dir.mkdir(parents=True, exist_ok=True)
            
            for i, photo in enumerate(group.photos):
                new_name = generate_new_filename(photo, idx=i)
                dest = event_dir / new_name
                
                if dry_run:
                    self.preview_text.insert(tk.END, f"[DRY] {photo.file_path.name} -> {dest}\n")
                else:
                    try:
                        shutil.copy2(photo.file_path, dest)
                        copied += 1
                        if copied % 10 == 0:
                            self.status_var.set(f"{copied}장 복사 완료...")
                            self.root.update()
                    except Exception as e:
                        self.preview_text.insert(tk.END, f"[ERROR] {photo.file_path.name}: {e}\n")
        
        if dry_run:
            self.status_var.set(f"[DRY-RUN] {total_photos}장 복사 계획 완료")
        else:
            self.status_var.set(f"✅ {copied}장 복사 완료")
    
    def scan_photos(self, source_dir: Path, recursive: bool):
        IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.tiff', '.heic'}
        photos = []
        pattern = '**/*' if recursive else '*'
        for file_path in source_dir.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in IMAGE_EXTS:
                meta = extract_photo_metadata(file_path)
                if meta:
                    photos.append(meta)
        return photos

    def _scan_worker(self, source, recursive):
        """Worker thread for scanning."""
        try:
            photos = self.scan_photos(source, recursive)
            self.scan_queue.put(("done", photos))
        except Exception as e:
            self.scan_queue.put(("error", str(e)))

    def _check_scan_queue(self):
        """Check the queue for results from the worker thread."""
        try:
            msg, data = self.scan_queue.get_nowait()
            if msg == "done":
                self.photos = data
                self.status_var.set(f"스캔 완료: {len(self.photos)}장 발견. 그룹핑 중...")
                self.root.update_idletasks()
                self.preview_text.insert(tk.END, f"총 {len(self.photos)}장 발견\n\n")
                
                all_groups = group_photos_by_time(self.photos, self.time_gap_var.get())
                assign_event_names(all_groups, self.config.grouping.default_event_name)
                
                # event_name이 있는 그룹만 필터링하여 self.groups에 저장
                self.groups = [g for g in all_groups if g.event_name and g.start_date]
                for group in self.groups[:10]:
                    self.preview_text.insert(tk.END, f"📁 {group.folder_name} ({len(group.photos)}장)\n")
                    for i, photo in enumerate(group.photos[:3]):
                        new_name = generate_new_filename(photo, idx=i)
                        self.preview_text.insert(tk.END, f"   {photo.file_path.name} → {new_name}\n")
                    if len(group.photos) > 3:
                        self.preview_text.insert(tk.END, f"   ... 외 {len(group.photos)-3}장\n")
                    self.preview_text.insert(tk.END, "\n")
                
                if len(self.groups) > 10:
                    self.preview_text.insert(tk.END, f"... 외 {len(self.groups)-10}개 이벤트\n")
                
                self.status_var.set(f"그룹핑 완료: {len(self.groups)}개 이벤트")
                
            elif msg == "error":
                messagebox.showerror("오류", data)
            
            # Cleanup
            self.loading_win.destroy()
            self.root.attributes('-disabled', 0)
            
        except queue.Empty:
            self.root.after(100, self._check_scan_queue)
    
        # ============================================================
    # TAB 2: Duplicates (Based on duplicate_finder.py)
    # ============================================================
    def setup_duplicates_tab(self):
        frame = self.tab_duplicates
        
        # Path selection
        path_frame = ttk.LabelFrame(frame, text="대상 폴더", padding=10)
        path_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.dup_dirs = []
        self.dup_dir_var = tk.StringVar(value="선택된 폴더 없음")
        ttk.Label(path_frame, textvariable=self.dup_dir_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="폴더 추가", command=self.add_dup_dir).pack(side=tk.LEFT, padx=5)
        ttk.Button(path_frame, text="초기화", command=self.clear_dup_dirs).pack(side=tk.LEFT)
        
        # Filters
        filter_frame = ttk.LabelFrame(frame, text="필터", padding=10)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.show_images = tk.BooleanVar(value=True)
        self.show_videos = tk.BooleanVar(value=True)
        self.show_others = tk.BooleanVar(value=False)
        self.recursive = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(filter_frame, text="이미지", variable=self.show_images).pack(side=tk.LEFT)
        ttk.Checkbutton(filter_frame, text="동영상", variable=self.show_videos).pack(side=tk.LEFT, padx=10)
        ttk.Checkbutton(filter_frame, text="기타", variable=self.show_others).pack(side=tk.LEFT)
        ttk.Checkbutton(filter_frame, text="하위폴더 포함", variable=self.recursive).pack(side=tk.RIGHT)
        
        # Action
        action_frame = ttk.Frame(frame)
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(action_frame, text="🔍 중복 검색", command=self.find_duplicates_gui).pack(side=tk.LEFT)
        ttk.Button(action_frame, text="🗑️ 선택 삭제", command=self.delete_selected_duplicates).pack(side=tk.RIGHT)
        
        # Results
        result_frame = ttk.LabelFrame(frame, text="중복 파일 목록", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ('파일1', '파일2', '크기')
        self.dup_tree = ttk.Treeview(result_frame, columns=columns, show='headings', height=15)
        self.dup_tree.heading('파일1', text='파일 A')
        self.dup_tree.heading('파일2', text='파일 B')
        self.dup_tree.heading('크기', text='크기')
        self.dup_tree.pack(fill=tk.BOTH, expand=True)
        
        self.dup_pairs = []
    
    def add_dup_dir(self):
        path = filedialog.askdirectory()
        if path and path not in self.dup_dirs:
            self.dup_dirs.append(path)
            self.dup_dir_var.set("; ".join([Path(p).name for p in self.dup_dirs]))
    
    def clear_dup_dirs(self):
        self.dup_dirs = []
        self.dup_dir_var.set("선택된 폴더 없음")
    
    def find_duplicates_gui(self):
        if not self.dup_dirs:
            messagebox.showwarning("경고", "폴더를 선택하세요.")
            return
        
        if not HAS_DUPLICATE_FINDER:
            messagebox.showerror("오류", "duplicate_finder.py를 찾을 수 없습니다.")
            return
        
        self.status_var.set("중복 검색 중...")
        self.dup_tree.delete(*self.dup_tree.get_children())
        
        finder = DuplicateFinder()
        paths = [Path(p) for p in self.dup_dirs]
        
        self.dup_pairs = finder.find_duplicates(
            dir_paths=paths,
            show_images=self.show_images.get(),
            show_videos=self.show_videos.get(),
            show_others=self.show_others.get(),
            recursive=self.recursive.get()
        )
        
        for i, (f1, f2) in enumerate(self.dup_pairs[:500]):  # Limit to 500 for performance
            try:
                size = f1.stat().st_size
                self.dup_tree.insert('', 'end', values=(f1.name, f2.name, f"{size//1024} KB"), tags=(i,))
            except:
                continue
        
        self.status_var.set(f"{len(self.dup_pairs)}개 중복 발견")
    
    def delete_selected_duplicates(self):
        selection = self.dup_tree.selection()
        if not selection:
            messagebox.showwarning("경고", "삭제할 항목을 선택하세요.")
            return
        
        if not messagebox.askyesno("확인", "선택한 파일을 삭제하시겠습니까?"):
            return
        
        # TODO: Implement actual deletion using finder.delete_files
        for item in selection:
            self.dup_tree.delete(item)
        self.status_var.set("삭제 완료 (구현 필요)")
    
    # ============================================================
    # TAB 3: Settings
    # ============================================================
    def setup_settings_tab(self):
        frame = self.tab_settings
        ttk.Label(frame, text="config.yaml 편집 (추후 구현)", padding=20).pack()


def main():
    root = tk.Tk()
    app = PhotoOrganizerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()