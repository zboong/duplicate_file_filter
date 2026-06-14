# 📸 Photo Organizer - 사진 정리 규칙서

> **목적**: 사진/동영상 자동 정리 시스템의 모든 규칙을 한 곳에 정리  
> **대상**: 사용자 직접 수정 + AI 참조용

---

## 📁 1. 기본 폴더 구조

```
photo_organizer/
├── core/                    # 공통 로직 (모든 모드에서 재사용)
│   ├── models.py           # 데이터 모델 (PhotoMetadata, PhotoGroup)
│   ├── exif_utils.py       # EXIF 추출
│   ├── renamer.py          # 파일명 생성
│   ├── grouper.py          # 이벤트 그룹핑
│   ├── duplicate_detector.py
│   ├── duplicate_handler.py
│   └── config.py           # 설정 로더
├── cli/                     # CLI 모드
├── gui/                     # GUI 모드 (Tab 3개)
├── config.yaml              # ⚙️ 사용자 설정 파일
└── pyproject.toml
```

---

## 🏷️ 2. 파일명 규칙

### 2.1 통일된 파일명 형식

```
{YYYYMMDD}_{HHMMSS}_{idx}_{imagesource}.{ext}
```

### 2.2 상세 규칙

| 항목 | 규칙 | 예시 |
|------|------|------|
| **날짜** | EXIF DateTimeOriginal 우선, 없으면 파일 수정일 | `20240115` |
| **시간** | EXIF 시간, 없으면 `000000` | `143022` |
| **인덱스(idx)** | 이벤트 내 0부터 시작, 3자리 zero-pad | `000`, `001`, `042` |
| **이미지소스** | EXIF Make/Model 또는 `unknown` | `iPhone15`, `CanonEOSR5`, `unknown` |
| **확장자** | 소문자 통일 | `.jpg`, `.heic`, `.mp4` |

### 2.3 예시

```
20240115_143022_000_iPhone15.jpg
20240115_143025_001_iPhone15.jpg
20240116_092310_000_CanonEOSR5.CR2
20231225_000000_000_unknown.png   ← EXIF 없음
```

---

## 📂 3. 폴더(이벤트) 그룹핑 규칙

### 3.1 그룹핑 기준

- **시간 간격**: `time_gap_hours` (기본: 6시간)
  - 연속 촬영 사진 중 6시간 이상 차이나면 새 이벤트로 분리
- **이벤트명**: `{start_date}_{event_name}` 형식
  - `event_name`은 사용자 정의 또는 기본값 (`event`)

### 3.2 Target 폴더 구조 (최상위: 연도)

```
Target/
├──2019
│  ├──20190618_0705_싱가포르_여행
│  ├──20190901_02_거제_나들이
│  └──20191225_구미_구경
├──2020
│  ├──20200518_0601_
│  └──20201105_서울_구경
└──...
```

### 3.3 폴더명 예시

```
2019/
├──20190618_0705_싱가포르_여행/
│  ├── 20190618_070522_000_iPhone15.jpg
│  └── ...
├──20190901_02_거제_나들이/
│  └── ...
└──20191225_구미_구경/
    └── ...

2020/
├──20200518_0601_/
│  └── ...
└──20201105_서울_구경/
    └── ...
```

### 3.3 설정 (`config.yaml`)

```yaml
grouping:
  time_gap_hours: 6          # 이벤트 분리 기준 시간
  default_event_name: "event"
```

---

## 🔍 4. 중복 파일 감지 규칙

### 4.1 계층적 감지 (3단계)

```
1단계: 파일 크기 비교
   ↓ 일치
2단계: EXIF 메타데이터 비교 (촬영일시 + 모델)
   ↓ 일치
3단계: Perceptual Hash (pHash) 비교 (이미지 유사도)
```

### 4.2 지원 형식

| 유형 | 확장자 |
|------|--------|
| **이미지** | `.jpg`, `.jpeg`, `.png`, `.tiff`, `.heic`, `.raw`, `.cr2`, `.nef` |
| **동영상** | `.mp4`, `.mov`, `.avi`, `.mkv` |

### 4.3 중복 처리 옵션

- **삭제**: 사용자가 선택한 파일 삭제
- **이동**: 별도 `duplicates/` 폴더로 이동
- **스킵**: 정리 시 복사 제외

---

## ⚙️ 5. EXIF 추출 규칙

### 5.1 우선순위

1. **DateTimeOriginal** (촬영일시)
2. **CreateDate** (생성일시)
3. **파일 수정일** (EXIF 없을 때 fallback)

### 5.2 추출 필드

- `DateTimeOriginal`
- `Make` + `Model` (카메라 모델)
- `ImageWidth`, `ImageHeight`
- GPS 정보 (선택)

### 5.3 EXIF 없을 때 처리

- 파일 수정일 사용
- `imagesource = "unknown"`
- 시간 = `000000`

---

## 🚀 6. 정리 실행 규칙

### 6.1 동작 모드

| 모드 | 동작 |
|------|------|
| **DRY-RUN** | 실제 복사 없이 미리보기만 |
| **실행** | Target 폴더에 복사 (원본 유지) |

### 6.2 복사 전략

- **복사 방식**: `shutil.copy2()` (메타데이터 보존)
- **충돌 처리**: 파일명에 idx가 있으므로 덮어쓰기 방지
- **원본 보존**: 항상 복사 (삭제 아님)

### 6.3 Target 폴더 구조

```
Target/
├──2019
│  ├──20190618_0705_싱가포르_여행
│  ├──20190901_02_거제_나들이
│  └──20191225_구미_구경
├──2020
│  ├──20200518_0601_제주도_여행
│  └──20201105_서울_구경
└──...
```

---

## 🛠️ 7. 설정 파일 (`config.yaml`) 구조

```yaml
paths:
  source: "~/Pictures"           # 원본 폴더
  target: "~/Pictures_organized" # 정리된 폴더

grouping:
  time_gap_hours: 6
  default_event_name: "event"

renaming:
  format: "{date}_{time}_{idx}_{source}.{ext}"
  idx_padding: 3

duplicate:
  method: "size_exif_phash"      # size | exif | phash | size_exif_phash
  action: "ask"                  # ask | delete | move | skip

extensions:
  image: [".jpg", ".jpeg", ".png", ".heic", ...]
  video: [".mp4", ".mov", ...]
```

---

## 📌 8. 주의사항 및 예외 처리

| 상황 | 처리 방식 |
|------|-----------|
| EXIF 없음 | 파일 수정일 + `unknown` 소스 사용 |
| 같은 시간 다중 촬영 | idx로 구분 (0, 1, 2, ...) |
| 파일명 충돌 | idx 증가로 회피 |
| 지원하지 않는 확장자 | 무시 |
| Target 폴더 없음 | 자동 생성 |

---

## 🔄 9. 워크플로우 요약

```
1. SCAN: Source 폴더 스캔 → EXIF 추출 → PhotoMetadata 리스트 생성
2. GROUP: time_gap 기준으로 PhotoGroup 생성 → 이벤트명 부여
3. PREVIEW: DRY-RUN으로 변경 사항 미리보기
4. EXECUTE: Target에 복사 (통일된 파일명 + 이벤트 폴더)
5. (선택) DUPLICATE: 중복 검색 → 사용자 확인 → 삭제/이동
```

---

## ✏️ 10. 사용자 커스터마이징 포인트

| 항목 | 파일 | 수정 방법 |
|------|------|-----------|
| 파일명 형식 | `core/renamer.py` | `generate_new_filename()` |
| 그룹핑 기준 | `core/grouper.py` | `group_photos_by_time()` |
| EXIF 필드 | `core/exif_utils.py` | `extract_photo_metadata()` |
| 설정값 | `config.yaml` | YAML 직접 편집 |

---

**마지막 업데이트**: 2025-01-XX  
**버전**: v1.0
