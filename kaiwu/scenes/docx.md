# Word 文档（docx）生成场景规范

## 适用场景
用 Python 生成或修改 Word 文档。

## 推荐库
```bash
pip install python-docx
```

## 核心用法

### 创建文档
```python
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()

# 标题
doc.add_heading('报告标题', level=1)

# 段落
p = doc.add_paragraph('正文内容')
p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY  # 两端对齐

# 加粗/字体
run = p.add_run('加粗文字')
run.bold = True
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(0xFF, 0, 0)  # 红色

# 表格
table = doc.add_table(rows=3, cols=3, style='Table Grid')
table.cell(0, 0).text = '表头'

# 图片
doc.add_picture('image.png', width=Inches(4))

doc.save('output.docx')
```

### 中文注意事项
- 字体用宋体/微软雅黑：`run.font.name = '宋体'`
- 文档默认字体在 styles 里设置
- 表格中文对齐可能需要手动设置

### 常见坑
1. 修改现有文档用 `Document('existing.docx')` 而非 `Document()`
2. 图片路径用绝对路径
3. 表格合并单元格：`cell.merge(other_cell)`

