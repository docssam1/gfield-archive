# GFIELD Thumbnail Pipeline

## 목적
- PDF 첫 페이지를 자동 썸네일(3:4, 300x400)로 생성
- `materials.json`의 `thumbnail_path`를 자동 업데이트

## 준비
```bash
pip install pdf2image pillow
```

Poppler 필요:
- Linux: `sudo apt-get install poppler-utils`
- Windows: Poppler `bin` 경로를 PATH에 추가

## 폴더
- 입력 PDF: `./pdfs/**/*.pdf`
- 출력 썸네일: `./thumbnails/<book_id>.webp`
- 인덱스: `./materials.json`

## 실행
```bash
python tools/generate_thumbnails.py
```

## materials.json 예시
```json
{
  "book_id": "HWSO_26_G_001",
  "display_name": "황소 경시 대비 최상위 수학",
  "thumbnail_path": "thumbnails/HWSO_26_G_001.webp",
  "path": "pdfs/HWSO/HWSO_26_G_001.pdf"
}
```
