# Photo Organizer

NAS 기반 개인 파일 자동 정리 시스템 (V1: CLI + Core)

## 목표

- EXIF/파일명 기반 이벤트 단위 폴더링
- 파일명 통일: `{YYYYMMDD}_{HHMMSS}_{idx}_{imagesource}.{ext}`
- 계층적 중복 감지 (파일크기 → EXIF → perceptual hash)
- Docker + Task Scheduler로 NAS 자동화

## 구조

```
photo_organizer/
├── core/           # 공통 로직 (CLI, GUI, NAS 모두 재사용)
├── cli/            # CLI 정리 도구
├── config.yaml     # 설정
└── pyproject.toml
```

## 다음 단계

1. core/models.py - 데이터 모델
2. core/exif_utils.py - EXIF 추출
3. core/renamer.py - 파일명 통일
4. core/duplicate_detector.py - 중복 감지
5. core/grouper.py - 이벤트 그룹핑
6. cli/main.py - CLI 진입점
```