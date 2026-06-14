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

# 디자인 색상 상수 정의 (Modern Light 테마)
BG_MAIN = "#F8F9FA"         # 전체 밝은 배경색
BG_CARD = "#FFFFFF"         # 섹션 및 카드의 배경색 (순백색)
BG_DARK = "#E9ECEF"         # 입력창 및 비활성 토글의 배경색 (연한 그레이)
BG_VIEWER = "#F1F3F5"       # 이미지 뷰어의 배경색
FG_MAIN = "#212529"         # 기본 어두운 텍스트 색상
FG_MUTED = "#868E96"        # 부드러운 보조 텍스트 색상
COLOR_ACCENT = "#339AF0"     # 주 포인트 색상 (소프트 블루)
COLOR_ACCENT_HOVER = "#228BE6" # 포인트 색상 호버 시
COLOR_WARNING = "#FA5252"    # 경고/삭제 색상 (소프트 레드)
COLOR_WARNING_HOVER = "#F03E3E" # 경고 색상 호버 시
COLOR_BORDER = "#DEE2E6"     # 카드 테두리 색상
COLOR_BORDER_ACTIVE = "#74C0FC" # 드래그 진입 또는 활성 보더 색상 (연한 블루)

class JWFileFilterGUI:
    """
    JWFileFilter의 현대화된 사용자 인터페이스(UI)를 구성하고 
    Drag & Drop, 스타일 토글, 중복 비교 레이아웃을 바인딩하는 클래스.
    """
    
    def __init__(self, root):
        self.root = root
        self.root.title("JWFileFilter - 중복 파일 관리자")
        self.root.geometry("1280x950")
        self.root.minsize(1200, 850)
        self.root.configure(bg=BG_MAIN)
        
        # 대상 디렉토리 리스트
        self.target_dirs = []
        
        # 중복 파일 탐색기 인스턴스 생성
        self.finder = DuplicateFinder()
        
        # 중복 파일 관련 변수
        self.duplicate_pairs = []
        self.current_pair_index = 0
        
        # 드래그 앤 드롭 테두리 색상 상태
        self.dnd_border_color = COLOR_BORDER
        
        self.setup_ui()
        
        # 키보드 단축키 바인딩
        self.root.bind("<Up>", lambda e: self.navigate_tree(-1))
        self.root.bind("<Down>", lambda e: self.navigate_tree(1))
        self.root.bind("1", lambda e: self.toggle_checkbox(self.checkbox1))
        self.root.bind("2", lambda e: self.toggle_checkbox(self.checkbox2))
        
    def navigate_tree(self, direction):
        """Treeview 아이템 방향키 이동 핸들러"""
        selection = self.duplicate_tree.selection()
        if not selection:
            children = self.duplicate_tree.get_children()
            if children:
                self.duplicate_tree.selection_set(children[0])
                self.on_duplicate_select(None)
            return
            
        current_item = selection[0]
        items = self.duplicate_tree.get_children()
        idx = items.index(current_item)
        
        new_idx = idx + direction
        if 0 <= new_idx < len(items):
            new_item = items[new_idx]
            self.duplicate_tree.selection_set(new_item)
            self.duplicate_tree.see(new_item)
            self.on_duplicate_select(None)

    def toggle_checkbox(self, var):
        """키보드로 삭제 선택 토글"""
        var.set(not var.get())
        
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
        comparison_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
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
        list_card.pack(fill=tk.X, expand=False, pady=(0, 15))
        
        list_title = tk.Label(
            list_card, 
            text="발견된 중복 파일 리스트 (동일 크기 및 타임스탬프 기준)", 
            font=("Segoe UI", 11, "bold"), 
            bg=BG_CARD, 
            fg=FG_MAIN
        )
        list_title.pack(anchor=tk.W, padx=12, pady=(8, 8))
        
        table_container = tk.Frame(list_card, bg=BG_CARD)
        table_container.pack(fill=tk.X, expand=True, padx=10, pady=(0, 10))
        
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
        
        self.duplicate_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 중복 파일 트리뷰 선택 이벤트 바인딩
        self.duplicate_tree.bind('<<TreeviewSelect>>', self.on_duplicate_select)
        
        # ----------------------------------------------------
        # 하단 액션 패널 & 상태 표시 및 로그 구역
        # ----------------------------------------------------
        action_bar = tk.Frame(self.main_container, bg=BG_MAIN)
        action_bar.pack(fill=tk.X, pady=(0, 10))
        
        self.btn_refresh = tk.Button(
            action_bar, text="새로고침", font=("Segoe UI", 10), bg=BG_CARD, fg=FG_MAIN, 
            activebackground=COLOR_BORDER, activeforeground=FG_MAIN, bd=0, padx=20, pady=8, cursor="hand2"
        )
        self.btn_refresh.pack(side=tk.LEFT, padx=(0, 10))
        self.bind_button_hover(self.btn_refresh, BG_CARD, COLOR_BORDER)
        self.btn_refresh.config(command=self.refresh_file_list)

        self.btn_clear = tk.Button(
            action_bar, text="🧹 경로 초기화", font=("Segoe UI", 10), bg=BG_CARD, fg=FG_MAIN, 
            activebackground=COLOR_BORDER, activeforeground=FG_MAIN, bd=0, padx=20, pady=8, cursor="hand2"
        )
        self.btn_clear.pack(side=tk.LEFT, padx=(0, 10))
        self.bind_button_hover(self.btn_clear, BG_CARD, COLOR_BORDER)
        self.btn_clear.config(command=self.clear_target_dirs)
        
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
        
        # 하단 정보 프레임 (진행률 및 로그)
        info_frame = tk.Frame(self.main_container, bg=BG_MAIN)
        info_frame.pack(fill=tk.X, pady=(5, 0))

        # 진행률 표시줄
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(info_frame, variable=self.progress_var, maximum=100, mode='determinate', length=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))

        # 로그 박스 (스크롤 가능한 텍스트 위젯)
        log_frame = tk.Frame(info_frame, bg=BG_DARK, bd=1, relief=tk.FLAT)
        log_frame.pack(fill=tk.X, pady=(0, 5))

        self.log_text = tk.Text(
            log_frame, height=4, font=("Consolas", 9), 
            bg=BG_DARK, fg=FG_MAIN, borderwidth=0, highlightthickness=0
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)
        
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.configure(state="disabled")

        # 상태바
        self.status_var = tk.StringVar(value="준비 완료 - 중복 파일 관리를 시작하려면 폴더를 드래그하거나 클릭하여 설정하세요.")
        status_bar = tk.Label(
            info_frame, 
            textvariable=self.status_var, 
            font=("Segoe UI", 9, "italic"), 
            bg=BG_MAIN, 
            fg=FG_MUTED, 
            anchor=tk.W
        )
        status_bar.pack(fill=tk.X)

        
    def setup_ttk_styles(self):
        """Treeview 라이트 모드 스타일 설정"""
        style = ttk.Style()
        style.theme_use("clam")
        
        # 트리뷰 전체 스타일
        style.configure(
            "Treeview", 
            background=BG_CARD, 
            foreground=FG_MAIN, 
            fieldbackground=BG_CARD, 
            rowheight=28, 
            bordercolor=COLOR_BORDER, 
            borderwidth=1, 
            font=("Segoe UI", 9)
        )
        
        # 선택된 아이템의 테마색 매핑
        style.map(
            "Treeview", 
            background=[("selected", COLOR_ACCENT)], 
            foreground=[("selected", "#FFFFFF")]
        )
        
        # 테이블 헤더 스타일
        style.configure(
            "Treeview.Heading", 
            background=BG_DARK, 
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
        """좌우 대칭 비교 카드 레이아웃 생성 (최적화 버전)"""
        # 상단 정보 구역 (제목 + 상세 정보)
        header_frame = tk.Frame(parent, bg=BG_CARD)
        header_frame.pack(fill=tk.X, padx=12, pady=(10, 5))
        
        title_lbl = tk.Label(
            header_frame, text=f"■ {card_title}", font=("Segoe UI", 11, "bold"), 
            bg=BG_CARD, fg=title_color
        )
        title_lbl.pack(side=tk.LEFT)
        
        # 파일 정보 (사이즈 + 파일명 + 경로) - tk.Text 사용하여 부분 색상 변경 지원
        info_text = tk.Text(
            header_frame, font=("Segoe UI", 11, "bold"), 
            bg=BG_CARD, fg="#000000", height=1, borderwidth=0, highlightthickness=0
        )
        info_text.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
        info_text.tag_configure("diff", foreground=COLOR_WARNING)
        info_text.configure(state="disabled")
        
        # 이미지 뷰어 영역 (가변 높이, 중앙 배치)
        viewer = tk.Label(
            parent, text="이미지 미리보기 없음", font=("Segoe UI", 10), 
            bg=BG_VIEWER, fg=FG_MUTED, relief=tk.FLAT, bd=0
        )
        viewer.pack(fill=tk.BOTH, expand=True, padx=12, pady=0)
        
        # 하단 삭제 토글 버튼
        delete_toggle = tk.Checkbutton(
            parent, text="이 파일 보존 (유지)", variable=checkbox_var, 
            indicatoron=False, font=("Segoe UI", 10, "bold"), bd=1, relief=tk.FLAT, pady=8, cursor="hand2"
        )
        delete_toggle.pack(fill=tk.X, padx=12, pady=(5, 12))
        
        # 인스턴스 참조 바인딩
        if is_left:
            self.card_left_frame = parent
            self.lbl_info1 = info_text
            self.lbl_info1_widget = info_text
            self.title_lbl1 = title_lbl
            self.header_left = header_frame
            self.image_viewer1 = viewer
            self.toggle_delete1 = delete_toggle
            self.configure_toggle_style(
                delete_toggle, checkbox_var, 
                active_bg=COLOR_WARNING, active_fg="#FFFFFF", 
                inactive_bg=BG_DARK, inactive_fg=FG_MAIN, 
                active_text="⚠️ 이 파일 삭제 선택됨", inactive_text="이 파일 보존 (유지)"
            )
            checkbox_var.trace_add("write", lambda *args: self.update_card_bg(True))
        else:
            self.card_right_frame = parent
            self.lbl_info2 = info_text
            self.lbl_info2_widget = info_text
            self.title_lbl2 = title_lbl
            self.header_right = header_frame
            self.image_viewer2 = viewer
            self.toggle_delete2 = delete_toggle
            self.configure_toggle_style(
                delete_toggle, checkbox_var, 
                active_bg=COLOR_WARNING, active_fg="#FFFFFF", 
                inactive_bg=BG_DARK, inactive_fg=FG_MAIN, 
                active_text="⚠️ 이 파일 삭제 선택됨", inactive_text="이 파일 보존 (유지)"
            )
            checkbox_var.trace_add("write", lambda *args: self.update_card_bg(False))

    def update_card_bg(self, is_left):
        """삭제 선택 시 카드 배경색 변경 (연핑크 피드백)"""
        var = self.checkbox1 if is_left else self.checkbox2
        frame = self.card_left_frame if is_left else self.card_right_frame
        header = self.header_left if is_left else self.header_right
        title = self.title_lbl1 if is_left else self.title_lbl2
        info = self.lbl_info1_widget if is_left else self.lbl_info2_widget
        
        # 라이트 테마에 어울리는 부드러운 연핑크(#FFF0F0)
        bg_color = "#FFF0F0" if var.get() else BG_CARD
        
        frame.configure(bg=bg_color)
        header.configure(bg=bg_color)
        title.configure(bg=bg_color)
        info.configure(bg=bg_color)
        
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
            text="📥 여기에 중복 검사할 폴더를 드래그 앤 드롭 하거나 클릭하여 추가 (여러 개 가능)", 
            fill=FG_MAIN, font=("Segoe UI", 11, "bold"), tags="text"
        )
        
        # 경로 요약 표시
        if not self.target_dirs:
            path_text = "선택된 폴더 없음"
        elif len(self.target_dirs) == 1:
            path_text = f"대상 경로: {self.target_dirs[0]}"
        else:
            path_text = f"총 {len(self.target_dirs)}개의 폴더 선택됨: " + ", ".join([Path(p).name for p in self.target_dirs])
            
        if len(path_text) > 85:
            path_text = path_text[:45] + "..." + path_text[-40:]
            
        self.dnd_canvas.create_text(
            w / 2, h / 2 + 15, 
            text=path_text, fill=COLOR_ACCENT if self.target_dirs else FG_MUTED, 
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
        """드롭 발생 시 디렉토리 자동 경로 바인딩 (자동 스캔 제거됨)"""
        self.dnd_border_color = COLOR_BORDER
        try:
            # 드롭된 데이터 파싱 (Tcl 리스트 포맷 고려)
            paths = self.root.tk.splitlist(event.data)
            added = False
            for p in paths:
                path = Path(p)
                if path.is_file():
                    path = path.parent
                    
                if path.is_dir() and str(path) not in self.target_dirs:
                    self.target_dirs.append(str(path))
                    added = True
            
            if added:
                self.draw_dnd_zone()
                self.status_var.set(f"{len(paths)}개의 폴더가 추가되었습니다. '중복 검색 시작' 버튼을 누르세요.")
            elif not paths:
                self.status_var.set("유효하지 않은 폴더 경로입니다.")
        except Exception as e:
            messagebox.showerror("드롭 처리 오류", f"경로를 처리하는 도중 오류가 발생했습니다:\n{str(e)}")

    def browse_directory(self):
        """디렉토리 선택 대화상자 호출"""
        initial_dir = self.target_dirs[-1] if self.target_dirs else os.getcwd()
        directory = filedialog.askdirectory(initialdir=initial_dir)
        if directory and directory not in self.target_dirs:
            self.target_dirs.append(directory)
            self.draw_dnd_zone()
            self.status_var.set("폴더가 추가되었습니다. '중복 검색 시작' 버튼을 누르세요.")
            
    def clear_target_dirs(self):
        """선택된 모든 경로 초기화"""
        self.target_dirs = []
        self.draw_dnd_zone()
        self.status_var.set("대상 경로가 초기화되었습니다.")

    def refresh_file_list(self):
        """파일 목록 및 결과 초기화 후 다시 검색"""
        if self.target_dirs:
            self.find_duplicates()
        else:
            self.status_var.set("먼저 디렉토리를 선택해주세요.")
            
    def get_selected_files(self):
        """호환용 레거시 API 메서드"""
        return []
        
    def find_duplicates(self):
        """중복 파일 검색 로직 실행"""
        try:
            self.status_var.set("스캔 중...")
            self.progress_var.set(0)
            
            # 로그 박스 초기화
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", tk.END)
            self.log_text.insert(tk.END, "스캔을 시작합니다...\n")
            self.log_text.configure(state="disabled")
            self.log_text.see(tk.END)
            
            self.root.update()
            
            if not self.target_dirs:
                self.status_var.set("디렉토리를 선택해주세요.")
                return

            paths = [Path(p) for p in self.target_dirs]
            valid_paths = [p for p in paths if p.exists()]
            
            if not valid_paths:
                self.status_var.set("유효한 디렉토리가 존재하지 않습니다.")
                return
            
            # 스캔 진행률 보고 콜백
            self.files_scanned = 0
            def progress_update(file_path):
                self.files_scanned += 1
                if self.files_scanned % 10 == 0:  # UI 업데이트 빈도 조절
                    self.log_text.configure(state="normal")
                    self.log_text.insert(tk.END, f"스캔 중: {Path(file_path).name}\n")
                    self.log_text.see(tk.END)
                    self.log_text.configure(state="disabled")
                    
                    # 진행률 표시 (정확한 전체 개수를 모르므로 임의의 최대값 대비 비율로 표시하거나 indeterminate 모드로 변경 가능)
                    # 여기서는 간단히 0~100 사이를 순환하도록 하거나 점진적으로 증가하도록 설정
                    self.progress_var.set((self.files_scanned % 1000) / 10) 
                    self.root.update()
            
            # DuplicateFinder를 호출하여 파일 스캔 및 비교 수행
            self.duplicate_pairs = self.finder.find_duplicates(
                dir_paths=valid_paths,
                show_images=self.show_images.get(),
                show_videos=self.show_videos.get(),
                show_others=self.show_others.get(),
                recursive=self.recursive_search.get(),
                progress_callback=progress_update
            )
            
            # 완료 로그
            self.log_text.configure(state="normal")
            self.log_text.insert(tk.END, f"스캔 완료! 총 {self.files_scanned}개 파일 탐색됨.\n")
            self.log_text.see(tk.END)
            self.log_text.configure(state="disabled")
            self.progress_var.set(100)

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
                def get_display_path(file_path):
                    for root in self.target_dirs:
                        try:
                            return file_path.relative_to(Path(root))
                        except ValueError:
                            continue
                    return file_path.name

                rel_path1 = get_display_path(file1)
                rel_path2 = get_display_path(file2)
                
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
        """현재 페어의 상세 텍스트 및 프리뷰 이미지 표시 (Diff 하이라이팅 포함)"""
        if not self.duplicate_pairs or self.current_pair_index >= len(self.duplicate_pairs):
            self.clear_image_viewers()
            return
        
        file1, file2 = self.duplicate_pairs[self.current_pair_index]
        
        if not file1.exists() or not file2.exists():
            self.clear_image_viewers()
            return

        try:
            # 정보 생성: [사이즈]\t[파일명] (경로)
            size1 = format_file_size(file1.stat().st_size)
            info1 = f"{size1}\t{file1.name} ({file1.parent})"
            
            size2 = format_file_size(file2.stat().st_size)
            info2 = f"{size2}\t{file2.name} ({file2.parent})"
            
            # 텍스트 위젯 업데이트 및 차이점 하이라이팅
            self._update_info_text(self.lbl_info1, info1, info2)
            self._update_info_text(self.lbl_info2, info2, info1)
            
            # 뷰어 로드 호출
            self.load_image_to_viewer(file1, self.image_viewer1)
            self.load_image_to_viewer(file2, self.image_viewer2)
            
            # 체크박스(삭제 유무) 토글 변수 초기화
            self.checkbox1.set(False)
            self.checkbox2.set(False)
            
            # 배경색 초기화 (명시적 호출)
            self.update_card_bg(True)
            self.update_card_bg(False)
            
        except Exception as e:
            print(f"Error showing pair: {e}")
            self.clear_image_viewers()

    def _update_info_text(self, text_widget, text, compare_text):
        """두 문자열을 비교하여 다른 문자만 빨간색(diff 태그)으로 표시"""
        text_widget.configure(state="normal")
        text_widget.delete("1.0", tk.END)
        
        # 문자 단위 비교 및 삽입
        for i, char in enumerate(text):
            # 비교 대상보다 길거나 문자가 다르면 diff 태그 적용
            if i >= len(compare_text) or char != compare_text[i]:
                text_widget.insert(tk.END, char, "diff")
            else:
                text_widget.insert(tk.END, char)
        
        text_widget.configure(state="disabled")

    def load_image_to_viewer(self, file_path, viewer):
        """특정 뷰어로 리사이징된 프리뷰 이미지 로드"""
        try:
            # 부모 카드 너비를 고려하여 가로세로 최대 비율 맞춤 조정
            # 뷰어 높이가 늘어났으므로 max_height도 상향 조정
            image = ImageProcessor.load_and_scale_image(file_path, max_width=530, max_height=420)
            photo = ImageTk.PhotoImage(image)
            
            viewer.configure(image=photo, text="")
            viewer.image = photo
        except Exception:
            viewer.configure(image="", text=f"프리뷰 불가능한 파일 유형입니다.\n{file_path.name}")
            viewer.image = None
    
    def clear_image_viewers(self):
        """이미지 및 카드 레이아웃 초기화"""
        if hasattr(self, 'lbl_info1'):
            for widget in [self.lbl_info1, self.lbl_info2]:
                widget.configure(state="normal")
                widget.delete("1.0", tk.END)
                widget.insert("1.0", "파일이 선택되지 않았습니다.")
                widget.configure(state="disabled")
        
        self.image_viewer1.configure(image="", text="이미지 미리보기 없음")
        self.image_viewer2.configure(image="", text="이미지 미리보기 없음")
        self.image_viewer1.image = None
        self.image_viewer2.image = None
        
        self.checkbox1.set(False)
        self.checkbox2.set(False)
        
        if hasattr(self, 'card_left_frame'):
            self.update_card_bg(True)
            self.update_card_bg(False)
    
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
