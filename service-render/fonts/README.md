# UPDATE ME — bundle real font files here

Download these from [Google Fonts / Noto](https://fonts.google.com/noto) and
place them in this folder with exactly these filenames (referenced by
`app/config.py:SCRIPT_FONT_MAP`):

- `NotoSansTamil-Regular.ttf`
- `NotoSansTelugu-Regular.ttf`
- `NotoSansDevanagari-Regular.ttf` (used for both `hi` and `mr`)
- `NotoSansGujarati-Regular.ttf`
- `NotoSansKannada-Regular.ttf`
- `NotoSansMalayalam-Regular.ttf`
- `NotoSansGurmukhi-Regular.ttf`
- `NotoSansBengali-Regular.ttf`
- `NotoNastaliqUrdu-Regular.ttf`

Without these files, `/render` raises `FileNotFoundError` (see
`app/rendering.py`) rather than silently falling back to a system font —
silent fallback risks wrong/missing glyphs for the exact accuracy-critical
text this product depends on (spec Section 0).
