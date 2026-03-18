# PDF 操作场景规范

## 适用场景
读取、创建、合并、拆分、加水印、加密 PDF 以及对扫描件做 OCR。

## 快速参考

| 任务类型 | 推荐方式 |
|---------|---------|
| 读取 / 分析 | pypdf 或 pdfplumber |
| 提取文字（保留布局） | pdfplumber |
| 提取表格 | pdfplumber `page.extract_tables()` |
| 合并 PDF | pypdf `PdfWriter` + `add_page` |
| 拆分 PDF | 每页单独 `PdfWriter` |
| 创建新 PDF | reportlab（Canvas 或 Platypus） |
| OCR 扫描件 | pdf2image + pytesseract |
| 加水印 | pypdf `merge_page` |
| 加密 | `writer.encrypt("user_pwd", "owner_pwd")` |

## 核心用法

### 提取文字
优先用 `pdfplumber`，它能保留空间布局；`pypdf.extract_text()` 对多栏/表格布局效果差。

### 提取表格
```python
import pdfplumber
with pdfplumber.open("file.pdf") as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
```

### 合并 PDF
```python
from pypdf import PdfWriter, PdfReader
writer = PdfWriter()
for path in pdf_paths:
    reader = PdfReader(path)
    for page in reader.pages:
        writer.add_page(page)
with open("merged.pdf", "wb") as f:
    writer.write(f)
```

### OCR 扫描件
```python
from pdf2image import convert_from_path
import pytesseract
images = convert_from_path("scan.pdf", dpi=300)
text = "\n".join(pytesseract.image_to_string(img, lang="chi_sim+eng") for img in images)
```

### 加密
```python
writer.encrypt(user_password="user_pwd", owner_password="owner_pwd", use_128bit=True)
```

### 解密已加密 PDF（操作前必须先解密）
```bash
qpdf --decrypt input.pdf decrypted.pdf
```

## 常见坑
1. 用 `pypdf.extract_text()` 提取表格 → 格式错乱，表格必须用 `pdfplumber.page.extract_tables()`
2. 扫描 PDF 用文字提取工具 → 返回空字符串，扫描件必须先走 OCR（pdf2image + pytesseract）
3. reportlab 用 Unicode 上下标字符（₀₁²³） → 渲染黑块，改用 `<sub>` / `<super>` XML 标签
4. 大 PDF 一次性全部读入内存 → OOM，用分页处理（逐页迭代 `pdf.pages`）
5. 对加密 PDF 直接操作 → 报错，先用 `qpdf --decrypt` 解密后再处理
