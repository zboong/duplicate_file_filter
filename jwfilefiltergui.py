#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JWFileFilter - 사진과 동영상 파일 관리 프로그램
메인 GUI 애플리케이션 (Modern UI/UX 및 Drag & Drop 탑재 버전)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from pathlib import Path
from datetime import datetime
from PIL import ImageTk

# TkinterDnD 의존성 불러오기
from tkinterdnd2 import DND_FILES, TkinterDnD

# 분리된 SRP 모듈 임포트
from file_util import format_file_size
from duplicate_finder import DuplicateFinder
from image_processor import ImageProcessor

# 디자인 색상 상수 정의
BG_MAIN = "#1A1B26"         # 전체 어두운 배경색 (Tokyo Night 테마 계열)
BG_CARD = "#24283B"         # 섹션 및 카드의 배경색
BG_DARK = "#1F2335"         # 입력창 및 비활성 토글의 배경색
BG_VIEWER = "#15161E"       # 이미지 뷰어의 어두운 배경색
FG_MAIN = "#C0CAF5"         # 기본 밝은 텍스트 색상
FG_MUTED = "#565F89"        # 어두운 보조 텍스트 색상
COLOR_ACCENT = "#7AA2F7"     # 주 포인트 색상 (소프트 블루)
COLOR_ACCENT_HOVER = "#89DDFF" # 포인트 색상 호버 시
COLOR_WARNING = "#F7768E"    # 경고/삭제 색상 (소프트 레드)
COLOR_WARNING_HOVER = "#FF9E9E" # 경고 색상 호버 시
COLOR_BORDER = "#414868"     # 카드 테두리 색상
COLOR_BORDER_ACTIVE = "#BB9AF7" # 드래그 진입 또는 활성 보더 색상 (소프트 퍼플)

class JWFileFilterGUI:
    """
    JWFileFilter의 현대화된 사용자 인터페이스(UI)를 구성하고 
    Drag & Drop, 스타일 토글, 중복 비교 레이아웃을 바인딩하는 클래스.
    """
    
    def __init__(self, root):
        self.root = root
        self.root.title("JWFileFilter - 중복 파일 관리자")
        self.root.geometry("1200x900")
        self.root.minsize(1200, 850)
        self.root.configure(bg=BG_MAIN)
        
        # 현재 작업 디렉토리
        self.current_dir = tk.StringVar(value=os.getcwd())
        
        # 중복 파일 탐색기 인스턴스 생성
        self.finder = DuplicateFinder()
        
        # 중복 파일 관련 변수
        self.duplicate_pairs = []
        self.current_pair_index = 0
        
        # 드래그 앤 드롭 테두리 색상 상태
        self.dnd_border_color = COLOR_BORDER
        
        self.setup_ui()
        
    def setup_ui(self):
        """UI 및 스타일 레이아웃 구성"""
        # 1. ttk 스타일 정의 (Treeview 다크테마 개편용)
        self.setup_ttk_styles()
        
        # 메인 컨테이너 프레임
        self.main_container = tk.Frame(self.root, bg=BG_MAIN, padx=15, pady=15)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # ----------------------------------------------------
        # 헤더 & Drag & Drop Zone 영역
        # ----------------------------------------------------
        header_frame = tk.Frame(self.main_container, bg=BG_MAIN)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 타이틀 및 서브타이틀
        title_label = tk.Label(
            header_frame, 
            text="JWFileFilter", 
            font=("Segoe UI", 20, "bold"), 
            bg=BG_MAIN, 
            fg=COLOR_ACCENT
        )
        title_label.pack(anchor=tk.W)
        
        subtitle_label = tk.Label(
            header_frame, 
            text="사진 및 동영상 중복 파일 클리너 • 디렉토리를 드래그하여 바로 탐색하세요", 
            font=("Segoe UI", 10), 
            bg=BG_MAIN, 
            fg=FG_MUTED
        )
        subtitle_label.pack(anchor=tk.W, pady=(2, 10))
        
        # Drag & Drop Zone (Canvas로 대쉬 보더 카드 구현)
        self.dnd_canvas = tk.Canvas(
            header_frame, 
            height=90, 
            bg=BG_DARK, 
            bd=0, 
            highlightthickness=0, 
            cursor="hand2"
        )
        self.dnd_canvas.pack(fill=tk.X, expand=True)
        
        # 드래그 앤 드롭 이벤트 바인딩
        self.dnd_canvas.drop_target_register(DND_FILES)
        self.dnd_canvas.dnd_bind('<<Drop>>', self.handle_drop)
        self.dnd_canvas.dnd_bind('<<DragEnter>>', self.handle_drag_enter)
        self.dnd_canvas.dnd_bind('<<DragLeave>>', self.handle_drag_leave)
        
        # 클릭 시 디렉토리 찾아보기 실행
        self.dnd_canvas.bind("<Button-1>", lambda e: self.browse_directory())
        self.dnd_canvas.bind("<Configure>", self.draw_dnd_zone)
        
        # ----------------------------------------------------
        # 파일 필터 영역 (버튼형 체크박스 토글 카드)
        # ----------------------------------------------------
        filter_card = tk.Frame(self.main_container, bg=BG_CARD, bd=1, highlightbackground=COLOR_BORDER, highlightthickness=1)
        filter_card.pack(fill=tk.X, pady=(0, 15), ipady=8, ipadx=10)
        
        filter_title = tk.Label(
            filter_card, 
            text="검색 필터 옵션", 
            font=("Segoe UI", 11, "bold"), 
            bg=BG_CARD, 
            fg=FG_MAIN
        )
        filter_title.pack(anchor=tk.W, padx=12, pady=(8, 8))
        
        filter_btn_frame = tk.Frame(filter_card, bg=BG_CARD)
        filter_btn_frame.pack(fill=tk.X, padx=10)
        
        self.show_images = tk.BooleanVar(value=True)
        self.show_videos = tk.BooleanVar(value=True)
        self.show_others = tk.BooleanVar(value=False)
        self.recursive_search = tk.BooleanVar(value=False)
        
        # 버튼 스타일 체크박스 (indicatoron=False)
        self.chk_images = tk.Checkbutton(
            filter_btn_frame, text="이미지 파일 포함 (.jpg, .png 등)", variable=self.show_images, 
            indicatoron=False, font=("Segoe UI", 10), bd=1, relief=tk.FLAT, padx=12, pady=6, cursor="hand2"
        )
        self.chk_images.pack(side=tk.LEFT, padx=5)
        self.configure_toggle_style(self.chk_images, self.show_images, active_bg=COLOR_ACCENT, active_fg=BG_MAIN, inactive_bg=BG_DARK, inactive_fg=FG_MUTED)
        
        self.chk_videos = tk.Checkbutton(
            filter_btn_frame, text="동영상 파일 포함 (.mp4, .mov 등)", variable=self.show_videos, 
            indicatoron=False, font=("Segoe UI", 10), bd=1, relief=tk.FLAT, padx=12, pady=6, cursor="hand2"
        )
        self.chk_videos.pack(side=tk.LEFT, padx=5)
        self.configure_toggle_style(self.chk_videos, self.show_videos, active_bg=COLOR_ACCENT, active_fg=BG_MAIN, inactive_bg=BG_DARK, inactive_fg=FG_MUTED)
        
        self.chk_others = tk.Checkbutton(
            filter_btn_frame, text="기타 파일 포함", variable=self.show_others, 
            indicatoron=False, font=("Segoe UI", 10), bd=1, relief=tk.FLAT, padx=12, pady=6, cursor="hand2"
        )
        self.chk_others.pack(side=tk.LEFT, padx=5)
        self.configure_toggle_style(self.chk_others, self.show_others, active_bg=COLOR_ACCENT, active_fg=BG_MAIN, inactive_bg=BG_DARK, inactive_fg=FG_MUTED)
        
        self.chk_recursive = tk.Checkbutton(
            filter_btn_frame, text="하위 폴더 깊은 탐색 (Recursive)", variable=self.recursive_search, 
            indicatoron=False, font=("Segoe UI", 10), bd=1, relief=tk.FLAT, padx=12, pady=6, cursor="hand2"
        )
        self.chk_recursive.pack(side=tk.RIGHT, padx=5)
        self.configure_toggle_style(self.chk_recursive, self.recursive_search, active_bg=COLOR_BORDER_ACTIVE, active_fg=BG_MAIN, inactive_bg=BG_DARK, inactive_fg=FG_MUTED)
        
        # ----------------------------------------------------
        # 중복 이미지 비교 구역 (좌/우 명확하게 분할된 카드 레이아웃)
        # ----------------------------------------------------
        comparison_frame = tk.Frame(self.main_container, bg=BG_MAIN)
        comparison_frame.pack(fill=tk.X, pady=(0, 15))
        comparison_frame.columnconfigure(0, weight=1)
        comparison_frame.columnconfigure(1, weight=1)
        
        # 체크박스 변수 정의
        self.checkbox1 = tk.BooleanVar()
        self.checkbox2 = tk.BooleanVar()
        
        # 좌측 비교 카드
        self.card_left = tk.Frame(comparison_frame, bg=BG_CARD, bd=1, highlightbackground=COLOR_BORDER, highlightthickness=1)
        self.card_left.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        self.setup_comparison_card(self.card_left, "비교 대상 파일 A", COLOR_ACCENT, self.checkbox1, is_left=True)
        
        # 우측 비교 카드
        self.card_right = tk.Frame(comparison_frame, bg=BG_CARD, bd=1, highlightbackground=COLOR_BORDER, highlightthickness=1)
        self.card_right.grid(row=0, column=1, padx=(8, 0), sticky="nsew")
        self.setup_comparison_card(self.card_right, "비교 대상 파일 B", COLOR_BORDER_ACTIVE, self.checkbox2, is_left=False)
        
        # ----------------------------------------------------
        # 중복 파일 목록 테이블 구역 (다크테마 Treeview)
        # ----------------------------------------------------
        list_card = tk.Frame(self.main_container, bg=BG_CARD, bd=1, highlightbackground=COLOR_BORDER, highlightthickness=1)
        list_card.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        list_title = tk.Label(
            list_card, 
            text="발견된 중복 파일 리스트 (동일 크기 및 타임스탬프 기준)", 
            font=("Segoe UI", 11, "bold"), 
            bg=BG_CARD, 
            fg=FG_MAIN
        )
        list_title.pack(anchor=tk.W, padx=12, pady=(8, 8))
        
        table_container = tk.Frame(list_card, bg=BG_CARD)
        table_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        duplicate_columns = ('파일1', '파일2', '크기', '생성일')
        self.duplicate_tree = ttk.Treeview(table_container, columns=duplicate_columns, show='headings', height=5)
        
        # 컬럼 및 헤더 바인딩
        self.duplicate_tree.heading('파일1', text='비교 파일 A')
        self.duplicate_tree.heading('파일2', text='비교 파일 B')
        self.duplicate_tree.heading('크기', text='파일 크기')
        self.duplicate_tree.heading('생성일', text='타임스탬프')
        
        self.duplicate_tree.column('파일1', width=350, anchor=tk.W)
        self.duplicate_tree.column('파일2', width=350, anchor=tk.W)
        self.duplicate_tree.column('크기', width=100, anchor=tk.CENTER)
        self.duplicate_tree.column('생성일', width=180, anchor=tk.CENTER)
        
        # 스크롤바 바인딩
        tree_scrollbar = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.duplicate_tree.yview)
        self.duplicate_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.duplicate_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 중복 파일 트리뷰 선택 이벤트 바인딩
        self.duplicate_tree.bind('<<TreeviewSelect>>', self.on_duplicate_select)
        
        # ----------------------------------------------------
        # 하단 액션 패널 & 상태 표시 바
        # ----------------------------------------------------
        action_bar = tk.Frame(self.main_container, bg=BG_MAIN)
        action_bar.pack(fill=tk.X, pady=(0, 5))
        
        self.btn_refresh = tk.Button(
            action_bar, text="새로고침", font=("Segoe UI", 10), bg=BG_CARD, fg=FG_MAIN, 
            activebackground=COLOR_BORDER, activeforeground=FG_MAIN, bd=0, padx=20, pady=8, cursor="hand2"
        )
        self.btn_refresh.pack(side=tk.LEFT, padx=(0, 10))
        self.bind_button_hover(self.btn_refresh, BG_CARD, COLOR_BORDER)
        self.btn_refresh.config(command=self.refresh_file_list)
        
        self.btn_search = tk.Button(
            action_bar, text="🔍 중복 파일 검색 시작", font=("Segoe UI", 10, "bold"), bg=COLOR_ACCENT, fg=BG_MAIN, 
            activebackground=COLOR_ACCENT_HOVER, activeforeground=BG_MAIN, bd=0, padx=25, pady=8, cursor="hand2"
        )
        self.btn_search.pack(side=tk.LEFT)
        self.bind_button_hover(self.btn_search, COLOR_ACCENT, COLOR_ACCENT_HOVER)
        self.btn_search.config(command=self.find_duplicates)
        
        self.btn_delete = tk.Button(
            action_bar, text="🗑️ 선택된 파일 영구 삭제", font=("Segoe UI", 10, "bold"), bg=COLOR_WARNING, fg=BG_MAIN, 
            activebackground=COLOR_WARNING_HOVER, activeforeground=BG_MAIN, bd=0, padx=25, pady=8, cursor="hand2"
        )
        self.btn_delete.pack(side=tk.RIGHT)
        self.bind_button_hover(self.btn_delete, COLOR_WARNING, COLOR_WARNING_HOVER)
        self.btn_delete.config(command=self.delete_selected_files)
        
        # 상태바
        self.status_var = tk.StringVar(value="준비 완료 - 중복 파일 관리를 시작하려면 폴더를 드래그하거나 클릭하여 설정하세요.")
        status_bar = tk.Label(
            self.main_container, 
            textvariable=self.status_var, 
            font=("Segoe UI", 9, "italic"), 
            bg=BG_MAIN, 
            fg=FG_MUTED, 
            anchor=tk.W
        )
        status_bar.pack(fill=tk.X, pady=(8, 0))
        
    def setup_ttk_styles(self):
        """Treeview 다크 모드 룩앤필 설정"""
        style = ttk.Style()
        style.theme_use("clam")
        
        # 트리뷰 전체 스타일
        style.configure(
            "Treeview", 
            background=BG_DARK, 
            foreground=FG_MAIN, 
            fieldbackground=BG_DARK, 
            rowheight=28, 
            bordercolor=COLOR_BORDER, 
            borderwidth=1, 
            font=("Segoe UI", 9)
        )
        
        # 선택된 아이템의 테마색 매핑
        style.map(
            "Treeview", 
            background=[("selected", COLOR_ACCENT)], 
            foreground=[("selected", BG_MAIN)]
        )
        
        # 테이블 헤더 스타일
        style.configure(
            "Treeview.Heading", 
            background=BG_CARD, 
            foreground=FG_MAIN, 
            font=("Segoe UI", 9, "bold"), 
            bordercolor=COLOR_BORDER, 
            borderwidth=1
        )
        style.map(
            "Treeview.Heading", 
            background=[("active", COLOR_BORDER)], 
            foreground=[("active", COLOR_ACCENT)]
        )
        
    def setup_comparison_card(self, parent, card_title, title_color, checkbox_var, is_left):
        """좌우 대칭 비교 카드 레이아웃 생성"""
        # 헤더 라벨
        header_lbl = tk.Label(
            parent, text=card_title, font=("Segoe UI", 10, "bold"), 
            bg=BG_CARD, fg=title_color
        )
        header_lbl.pack(anchor=tk.W, padx=12, pady=(10, 2))
        
        # 파일명 및 상세 경로 표시 라벨
        name_var = tk.StringVar(value="-")
        path_var = tk.StringVar(value="파일이 선택되지 않았습니다.")
        
        name_lbl = tk.Label(
            parent, textvariable=name_var, font=("Segoe UI", 12, "bold"), 
            bg=BG_CARD, fg=FG_MAIN, anchor=tk.W
        )
        name_lbl.pack(fill=tk.X, padx=12, pady=(2, 0))
        
        path_lbl = tk.Label(
            parent, textvariable=path_var, font=("Segoe UI", 9), 
            bg=BG_CARD, fg=FG_MUTED, anchor=tk.W
        )
        path_lbl.pack(fill=tk.X, padx=12, pady=(0, 6))
        
        # 이미지 뷰어 영역 (어둡게 설정하여 명확한 좌우 비교 가능)
        viewer = tk.Label(
            parent, text="이미지 미리보기 없음", font=("Segoe UI", 10), 
            bg=BG_VIEWER, fg=FG_MUTED, relief=tk.FLAT, bd=0, height=13
        )
        viewer.pack(fill=tk.X, padx=12, pady=6)
        
        # 체크박스 토글 버튼 (indicatoron=False)
        delete_toggle = tk.Checkbutton(
            parent, text="이 파일 보존 (유지)", variable=checkbox_var, 
            indicatoron=False, font=("Segoe UI", 10, "bold"), bd=1, relief=tk.FLAT, pady=6, cursor="hand2"
        )
        delete_toggle.pack(fill=tk.X, padx=12, pady=(8, 12))
        
        # 인스턴스 참조 바인딩
        if is_left:
            self.lbl_name1 = name_var
            self.lbl_path1 = path_var
            self.image_viewer1 = viewer
            self.toggle_delete1 = delete_toggle
            self.configure_toggle_style(
                delete_toggle, checkbox_var, 
                active_bg=COLOR_WARNING, active_fg=BG_MAIN, 
                inactive_bg=BG_DARK, inactive_fg=FG_MAIN, 
                active_text="⚠️ 이 파일 삭제 선택됨", inactive_text="이 파일 보존 (유지)"
            )
        else:
            self.lbl_name2 = name_var
            self.lbl_path2 = path_var
            self.image_viewer2 = viewer
            self.toggle_delete2 = delete_toggle
            self.configure_toggle_style(
                delete_toggle, checkbox_var, 
                active_bg=COLOR_WARNING, active_fg=BG_MAIN, 
                inactive_bg=BG_DARK, inactive_fg=FG_MAIN, 
                active_text="⚠️ 이 파일 삭제 선택됨", inactive_text="이 파일 보존 (유지)"
            )
            
    def configure_toggle_style(self, btn, var, active_bg, active_fg, inactive_bg, inactive_fg, active_text=None, inactive_text=None):
        """체크박스 토글 시 색상 및 텍스트 상태 변경 핸들러"""
        def update_style(*args):
            try:
                if var.get():
                    btn.config(
                        bg=active_bg, fg=active_fg, 
                        activebackground=active_bg, activeforeground=active_fg
                    )
                    if active_text:
                        btn.config(text=active_text)
                else:
                    btn.config(
                        bg=inactive_bg, fg=inactive_fg, 
                        activebackground=inactive_bg, activeforeground=inactive_fg
                    )
                    if inactive_text:
                        btn.config(text=inactive_text)
            except tk.TclError:
                pass
                
        var.trace_add("write", update_style)
        update_style()
        
    def bind_button_hover(self, btn, normal_bg, hover_bg):
        """마우스 오버 효과 추가"""
        btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg))
        btn.bind("<Leave>", lambda e: btn.config(bg=normal_bg))
        
    def draw_dnd_zone(self, event=None):
        """Drag & Drop 영역 캔버스 그리기 (대쉬 라인 및 반응형 텍스트)"""
        w = self.dnd_canvas.winfo_width()
        h = self.dnd_canvas.winfo_height()
        if w < 10 or h < 10:
            return
            
        self.dnd_canvas.delete("all")
        
        # 테두리 대쉬 사각형 드로잉
        self.dnd_canvas.create_rectangle(
            8, 8, w - 8, h - 8, 
            dash=(6, 4), outline=self.dnd_border_color, width=2, tags="border"
        )
        
        # 중앙 메시지 아이콘 및 문구
        self.dnd_canvas.create_text(
            w / 2, h / 2 - 12, 
            text="📥 여기에 중복 검사할 폴더를 드래그 앤 드롭 하거나 클릭하여 찾아보기", 
            fill=FG_MAIN, font=("Segoe UI", 11, "bold"), tags="text"
        )
        
        # 경로 요약 표시
        path_text = f"현재 설정된 대상 경로: {self.current_dir.get()}"
        if len(path_text) > 85:
            path_text = path_text[:45] + "..." + path_text[-40:]
            
        self.dnd_canvas.create_text(
            w / 2, h / 2 + 15, 
            text=path_text, fill=COLOR_ACCENT if self.current_dir.get() else FG_MUTED, 
            font=("Segoe UI", 9), tags="subtext"
        )
        
    def handle_drag_enter(self, event):
        """드래그 진입 시 보더 하이라이트 피드백"""
        self.dnd_border_color = COLOR_BORDER_ACTIVE
        self.draw_dnd_zone()
        
    def handle_drag_leave(self, event):
        """드래그 탈출 시 보더 초기화"""
        self.dnd_border_color = COLOR_BORDER
        self.draw_dnd_zone()
        
    def handle_drop(self, event):
        """드롭 발생 시 디렉토리 자동 경로 바인딩 및 즉시 검색"""
        self.dnd_border_color = COLOR_BORDER
        try:
            # 드롭된 데이터 파싱 (Tcl 리스트 포맷 고려)
            paths = self.root.tk.splitlist(event.data)
            if paths:
                path = Path(paths[0])
                if path.is_file():
                    path = path.parent
                    
                if path.is_dir():
                    self.current_dir.set(str(path))
                    self.draw_dnd_zone()
                    self.find_duplicates()
                else:
                    self.status_var.set("유효하지 않은 폴더 경로입니다.")
        except Exception as e:
            messagebox.showerror("드롭 처리 오류", f"경로를 처리하는 도중 오류가 발생했습니다:\n{str(e)}")

    def browse_directory(self):
        """디렉토리 선택 대화상자 호출"""
        directory = filedialog.askdirectory(initialdir=self.current_dir.get())
        if directory:
            self.current_dir.set(directory)
            self.draw_dnd_zone()
            self.find_duplicates()
            
    def refresh_file_list(self):
        """파일 목록 및 결과 초기화 후 다시 검색"""
        if self.current_dir.get():
            self.find_duplicates()
        else:
            self.status_var.set("먼저 디렉토리를 선택해주세요.")
            
    def get_selected_files(self):
        """호환용 레거시 API 메서드"""
        return []
        
    def find_duplicates(self):
        """중복 파일 검색 로직 실행"""
        try:
            self.status_var.set("중복 파일 탐색 스캔을 활성화하는 중...")
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
                self.status_var.set(f"탐색 완료: {len(self.duplicate_pairs)}개의 중복 파일 페어를 검출했습니다.")
                self.current_pair_index = 0
                self.show_current_pair()
            else:
                self.status_var.set("중복 파일 검출 사항이 존재하지 않습니다.")
                self.clear_image_viewers()
                
        except Exception as e:
            self.status_var.set(f"검색 실패: {str(e)}")
            messagebox.showerror("오류", f"중복 파일 검색 중 오류가 발생했습니다:\n{str(e)}")
    
    def update_duplicate_list(self):
        """중복 파일 목록 Treeview 바인딩"""
        # 기존 항목 제거
        for item in self.duplicate_tree.get_children():
            self.duplicate_tree.delete(item)
        
        # 중복 파일 페어 추가
        for i, (file1, file2) in enumerate(self.duplicate_pairs):
            try:
                stat1 = file1.stat()
                stat2 = file2.stat()
                
                size1 = format_file_size(stat1.st_size)
                date1 = datetime.fromtimestamp(stat1.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
                
                # 상대 경로로 텍스트 축소 변환
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
        """Treeview 아이템 더블클릭/선택 연동"""
        selection = self.duplicate_tree.selection()
        if selection:
            item = selection[0]
            tags = self.duplicate_tree.item(item)['tags']
            if tags:
                self.current_pair_index = int(tags[0])
                self.show_current_pair()
    
    def show_current_pair(self):
        """현재 페어의 상세 텍스트 및 프리뷰 이미지 표시"""
        if not self.duplicate_pairs or self.current_pair_index >= len(self.duplicate_pairs):
            self.clear_image_viewers()
            return
        
        file1, file2 = self.duplicate_pairs[self.current_pair_index]
        
        # 좌우 카드 상단 텍스트 정보 매핑
        self.lbl_name1.set(file1.name)
        self.lbl_path1.set(f"크기: {format_file_size(file1.stat().st_size)} | 경로: {file1.parent}")
        
        self.lbl_name2.set(file2.name)
        self.lbl_path2.set(f"크기: {format_file_size(file2.stat().st_size)} | 경로: {file2.parent}")
        
        # 뷰어 로드 호출
        self.load_image_to_viewer(file1, self.image_viewer1)
        self.load_image_to_viewer(file2, self.image_viewer2)
        
        # 체크박스(삭제 유무) 토글 변수 초기화
        self.checkbox1.set(False)
        self.checkbox2.set(False)
    
    def load_image_to_viewer(self, file_path, viewer):
        """특정 뷰어로 리사이징된 프리뷰 이미지 로드"""
        try:
            # 부모 카드 너비를 고려하여 가로세로 최대 비율 맞춤 조정
            image = ImageProcessor.load_and_scale_image(file_path, max_width=530, max_height=360)
            photo = ImageTk.PhotoImage(image)
            
            viewer.configure(image=photo, text="")
            viewer.image = photo
        except Exception:
            viewer.configure(image="", text=f"프리뷰 불가능한 파일 유형입니다.\n{file_path.name}")
            viewer.image = None
    
    def clear_image_viewers(self):
        """이미지 및 카드 레이아웃 초기화"""
        self.lbl_name1.set("-")
        self.lbl_path1.set("파일이 선택되지 않았습니다.")
        self.lbl_name2.set("-")
        self.lbl_path2.set("파일이 선택되지 않았습니다.")
        
        self.image_viewer1.configure(image="", text="이미지 미리보기 없음")
        self.image_viewer2.configure(image="", text="이미지 미리보기 없음")
        self.image_viewer1.image = None
        self.image_viewer2.image = None
        
        self.checkbox1.set(False)
        self.checkbox2.set(False)
    
    def delete_selected_files(self):
        """체크 처리된 파일 목록 영구 삭제 연산"""
        files_to_delete = []
        
        if self.checkbox1.get() and self.duplicate_pairs:
            file1, _ = self.duplicate_pairs[self.current_pair_index]
            files_to_delete.append(file1)
        
        if self.checkbox2.get() and self.duplicate_pairs:
            _, file2 = self.duplicate_pairs[self.current_pair_index]
            files_to_delete.append(file2)
        
        if not files_to_delete:
            messagebox.showwarning("경고", "비교 카드 하단의 '삭제 선택됨' 토글을 1개 이상 활성화한 후 클릭하세요.")
            return
        
        names = "\n".join([f"- {f.name}" for f in files_to_delete])
        if messagebox.askyesno("확인", f"선택한 {len(files_to_delete)}개 파일을 삭제하시겠습니까?\n\n{names}\n\n이 작업은 복구가 불가능합니다."):
            try:
                # DuplicateFinder를 호출하여 파일 삭제 수행
                self.finder.delete_files(files_to_delete)
                
                # 중복 파일 목록 다시 탐색
                self.find_duplicates()
                self.status_var.set(f"삭제 완료: {len(files_to_delete)}개의 중복 의심 파일을 제거했습니다.")
            except Exception as e:
                messagebox.showerror("오류", f"파일 삭제 중 오류가 발생했습니다:\n{str(e)}")

def main():
    """메인 실행 핸들러"""
    root = TkinterDnD.Tk()
    app = JWFileFilterGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
