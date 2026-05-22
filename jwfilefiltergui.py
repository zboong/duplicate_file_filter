#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JWFileFilter - 사진과 동영상 파일 관리 프로그램
메인 GUI 애플리케이션 (SRP 적용 리팩토링 버전)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from pathlib import Path
from datetime import datetime
from PIL import ImageTk

# 분리된 SRP 모듈 임포트
from file_util import format_file_size
from duplicate_finder import DuplicateFinder
from image_processor import ImageProcessor

class JWFileFilterGUI:
    """
    JWFileFilter의 사용자 인터페이스(UI) 및 상호작용을 담당하는 클래스.
    """
    
    def __init__(self, root):
        self.root = root
        self.root.title("JWFileFilter - 파일 관리자")
        self.root.geometry("1200x800")
        self.root.minsize(1200, 800)
        
        # 현재 작업 디렉토리
        self.current_dir = tk.StringVar(value=os.getcwd())
        
        # 중복 파일 탐색기 인스턴스 생성
        self.finder = DuplicateFinder()
        
        # 중복 파일 관련 변수
        self.duplicate_pairs = []
        self.current_pair_index = 0
        self.selected_for_deletion = set()
        
        self.setup_ui()
        
    def setup_ui(self):
        """UI 구성 요소 설정"""
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 디렉토리 선택 프레임
        dir_frame = ttk.LabelFrame(main_frame, text="디렉토리 선택", padding="5")
        dir_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(dir_frame, text="현재 디렉토리:").grid(row=0, column=0, sticky=tk.W)
        self.dir_entry = ttk.Entry(dir_frame, textvariable=self.current_dir, width=50)
        self.dir_entry.grid(row=0, column=1, padx=(5, 5), sticky=(tk.W, tk.E))
        
        ttk.Button(dir_frame, text="찾아보기", command=self.browse_directory).grid(row=0, column=2)
        
        # 파일 필터 프레임
        filter_frame = ttk.LabelFrame(main_frame, text="파일 필터", padding="5")
        filter_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.show_images = tk.BooleanVar(value=True)
        self.show_videos = tk.BooleanVar(value=True)
        self.show_others = tk.BooleanVar(value=False)
        self.recursive_search = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(filter_frame, text="이미지 파일", variable=self.show_images, 
                       command=self.refresh_file_list).grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(filter_frame, text="동영상 파일", variable=self.show_videos, 
                       command=self.refresh_file_list).grid(row=0, column=1, sticky=tk.W)
        ttk.Checkbutton(filter_frame, text="기타 파일", variable=self.show_others, 
                       command=self.refresh_file_list).grid(row=0, column=2, sticky=tk.W)
        ttk.Checkbutton(filter_frame, text="하위 폴더 포함", variable=self.recursive_search, 
                       command=self.refresh_file_list).grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # 이미지 뷰어 프레임
        image_viewer_frame = ttk.LabelFrame(main_frame, text="중복 파일 이미지 뷰어", padding="10")
        image_viewer_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 이미지 뷰어들을 위한 중앙 정렬 프레임
        viewer_container = tk.Frame(image_viewer_frame)
        viewer_container.grid(row=0, column=0, columnspan=2, pady=10)
        viewer_container.columnconfigure(0, weight=1)
        viewer_container.columnconfigure(1, weight=1)
        
        # 이미지 뷰어들 (더 큰 이미지 표시)
        self.image_viewer1 = tk.Label(
            viewer_container,
            text="이미지 1",
            bg="lightgray",
            relief=tk.SUNKEN,
            anchor=tk.CENTER,
        )
        self.image_viewer1.grid(row=0, column=0, padx=10, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.image_viewer2 = tk.Label(
            viewer_container,
            text="이미지 2",
            bg="lightgray",
            relief=tk.SUNKEN,
            anchor=tk.CENTER,
        )
        self.image_viewer2.grid(row=0, column=1, padx=10, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 체크박스들
        self.checkbox1 = tk.BooleanVar()
        self.checkbox2 = tk.BooleanVar()
        
        checkbox_frame = tk.Frame(image_viewer_frame)
        checkbox_frame.grid(row=1, column=0, columnspan=2, pady=5)
        checkbox_frame.columnconfigure(0, weight=1)
        checkbox_frame.columnconfigure(1, weight=1)
        
        ttk.Checkbutton(checkbox_frame, text="삭제", variable=self.checkbox1).grid(row=0, column=0)
        ttk.Checkbutton(checkbox_frame, text="삭제", variable=self.checkbox2).grid(row=0, column=1)
        
        # 중복 파일 목록 프레임
        duplicate_frame = ttk.LabelFrame(main_frame, text="중복 파일 목록", padding="5")
        duplicate_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 중복 파일 트리뷰
        duplicate_columns = ('파일1', '파일2', '크기', '생성일')
        self.duplicate_tree = ttk.Treeview(duplicate_frame, columns=duplicate_columns, show='headings', height=6)
        
        # 컬럼 설정
        self.duplicate_tree.heading('파일1', text='파일1')
        self.duplicate_tree.heading('파일2', text='파일2')
        self.duplicate_tree.heading('크기', text='크기')
        self.duplicate_tree.heading('생성일', text='생성일')
        
        self.duplicate_tree.column('파일1', width=200)
        self.duplicate_tree.column('파일2', width=200)
        self.duplicate_tree.column('크기', width=100)
        self.duplicate_tree.column('생성일', width=150)
        
        # 중복 파일 스크롤바
        duplicate_scrollbar = ttk.Scrollbar(duplicate_frame, orient=tk.VERTICAL, command=self.duplicate_tree.yview)
        self.duplicate_tree.configure(yscrollcommand=duplicate_scrollbar.set)
        
        self.duplicate_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        duplicate_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 중복 파일 선택 이벤트
        self.duplicate_tree.bind('<<TreeviewSelect>>', self.on_duplicate_select)
        
        # 액션 버튼 프레임
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(action_frame, text="새로고침", command=self.refresh_file_list).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(action_frame, text="중복 파일 검색", command=self.find_duplicates).grid(row=0, column=1, padx=5)
        ttk.Button(action_frame, text="선택된 파일 삭제", command=self.delete_selected_files).grid(row=0, column=2, padx=5)
        
        # 상태바
        self.status_var = tk.StringVar(value="준비")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        # 그리드 가중치 설정
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)  # 중복 파일 목록 프레임
        duplicate_frame.columnconfigure(0, weight=1)
        duplicate_frame.rowconfigure(0, weight=1)
        dir_frame.columnconfigure(1, weight=1)
        
        # 루트 윈도우 그리드 설정
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # 초기 파일 목록 로드
        self.refresh_file_list()
        
    def browse_directory(self):
        """디렉토리 선택 대화상자"""
        directory = filedialog.askdirectory(initialdir=self.current_dir.get())
        if directory:
            self.current_dir.set(directory)
            self.refresh_file_list()
            
    def refresh_file_list(self):
        """파일 목록 새로고침 (기존 동작 호환용 빈 메서드)"""
        pass
    
    def get_selected_files(self):
        """선택된 파일들의 경로 반환 (기존 동작 호환용 빈 메서드)"""
        return []
        
    def find_duplicates(self):
        """중복 파일 검색"""
        try:
            self.status_var.set("중복 파일 검색 중...")
            self.root.update()
            
            current_path = Path(self.current_dir.get())
            if not current_path.exists():
                self.status_var.set("디렉토리가 존재하지 않습니다.")
                return
            
            # DuplicateFinder를 호출하여 파일 스캔 및 비교 수행
            self.duplicate_pairs = self.finder.find_duplicates(
                dir_path=current_path,
                show_images=self.show_images.get(),
                show_videos=self.show_videos.get(),
                show_others=self.show_others.get(),
                recursive=self.recursive_search.get()
            )
            
            # 중복 파일 목록 업데이트
            self.update_duplicate_list()
            
            if self.duplicate_pairs:
                self.status_var.set(f"{len(self.duplicate_pairs)}개의 중복 파일 페어를 찾았습니다.")
                # 첫 번째 페어 표시
                self.current_pair_index = 0
                self.show_current_pair()
            else:
                self.status_var.set("중복 파일을 찾지 못했습니다.")
                self.clear_image_viewers()
                
        except Exception as e:
            self.status_var.set(f"오류: {str(e)}")
            messagebox.showerror("오류", f"중복 파일 검색 중 오류가 발생했습니다:\n{str(e)}")
    
    def update_duplicate_list(self):
        """중복 파일 목록 업데이트"""
        # 기존 항목 제거
        for item in self.duplicate_tree.get_children():
            self.duplicate_tree.delete(item)
        
        # 중복 파일 페어 추가
        for i, (file1, file2) in enumerate(self.duplicate_pairs):
            try:
                stat1 = file1.stat()
                stat2 = file2.stat()
                
                size1 = format_file_size(stat1.st_size)
                size2 = format_file_size(stat2.st_size)
                date1 = datetime.fromtimestamp(stat1.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
                date2 = datetime.fromtimestamp(stat2.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
                
                # 상대 경로로 표시
                try:
                    rel_path1 = file1.relative_to(Path(self.current_dir.get()))
                    rel_path2 = file2.relative_to(Path(self.current_dir.get()))
                except ValueError:
                    rel_path1 = file1.name
                    rel_path2 = file2.name
                
                self.duplicate_tree.insert('', 'end', values=(
                    str(rel_path1), str(rel_path2), size1, date1
                ), tags=(i,))
            except Exception:
                continue
    
    def on_duplicate_select(self, event):
        """중복 파일 목록에서 선택 시"""
        selection = self.duplicate_tree.selection()
        if selection:
            item = selection[0]
            tags = self.duplicate_tree.item(item)['tags']
            if tags:
                self.current_pair_index = int(tags[0])
                self.show_current_pair()
    
    def show_current_pair(self):
        """현재 선택된 페어의 이미지 표시"""
        if not self.duplicate_pairs or self.current_pair_index >= len(self.duplicate_pairs):
            self.clear_image_viewers()
            return
        
        file1, file2 = self.duplicate_pairs[self.current_pair_index]
        self.load_image_to_viewer(file1, self.image_viewer1)
        self.load_image_to_viewer(file2, self.image_viewer2)
        
        # 체크박스 초기화
        self.checkbox1.set(False)
        self.checkbox2.set(False)
    
    def load_image_to_viewer(self, file_path, viewer):
        """이미지를 뷰어에 로드 (보다 크게 표시)"""
        try:
            # ImageProcessor를 호출하여 이미지 로딩 및 리사이즈 수행
            image = ImageProcessor.load_and_scale_image(file_path, max_width=550, max_height=600)
            photo = ImageTk.PhotoImage(image)
            
            viewer.configure(image=photo, text="")
            viewer.image = photo  # 참조 유지
        except Exception:
            viewer.configure(image="", text=f"이미지 로드 실패\n{file_path.name}")
            viewer.image = None
    
    def clear_image_viewers(self):
        """이미지 뷰어 초기화"""
        self.image_viewer1.configure(image="", text="이미지 1")
        self.image_viewer2.configure(image="", text="이미지 2")
        self.image_viewer1.image = None
        self.image_viewer2.image = None
        self.checkbox1.set(False)
        self.checkbox2.set(False)
    
    def delete_selected_files(self):
        """체크된 파일들 삭제"""
        files_to_delete = []
        
        if self.checkbox1.get() and self.duplicate_pairs:
            file1, _ = self.duplicate_pairs[self.current_pair_index]
            files_to_delete.append(file1)
        
        if self.checkbox2.get() and self.duplicate_pairs:
            _, file2 = self.duplicate_pairs[self.current_pair_index]
            files_to_delete.append(file2)
        
        if not files_to_delete:
            messagebox.showwarning("경고", "삭제할 파일을 선택해주세요.")
            return
        
        if messagebox.askyesno("확인", f"{len(files_to_delete)}개 파일을 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다."):
            try:
                # DuplicateFinder를 호출하여 파일 삭제 수행
                self.finder.delete_files(files_to_delete)
                
                # 중복 파일 목록 새로고침
                self.find_duplicates()
                self.status_var.set(f"{len(files_to_delete)}개 파일을 삭제했습니다.")
            except Exception as e:
                messagebox.showerror("오류", f"파일 삭제 중 오류가 발생했습니다:\n{str(e)}")

def main():
    """메인 함수"""
    root = tk.Tk()
    app = JWFileFilterGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
