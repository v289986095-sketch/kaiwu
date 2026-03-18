# Excel / 电子表格（xlsx）场景规范

## 适用场景
创建、编辑、分析 Excel 文件，数据分析用 pandas，格式化和公式用 openpyxl。

## 快速参考

| 任务类型 | 推荐方式 |
|---------|---------|
| 数据读取 / 分析 | pandas |
| 创建 / 格式化 / 公式 | openpyxl |
| 读取内容 | python -m markitdown spreadsheet.xlsx |

## 核心铁律

**用 Excel 公式，不要在 Python 里算好再硬编码值！**

```python
# 错误做法（硬编码）
sheet['B10'] = sum(values)  # 表格失去动态性

# 正确做法（Excel 公式）
sheet['B10'] = '=SUM(B2:B9)'  # 用户修改数据后自动更新
```

## 核心用法

### 数字格式规范
```python
cell.number_format = '$#,##0'      # 货币
cell.number_format = '(#,##0)'     # 负数用括号
cell.number_format = '0.0%'        # 百分比
```

### 财务模型颜色规范
- 蓝色 = 硬编码输入值
- 黑色 = 公式
- 绿色 = 跨表引用
- 红色 = 外部链接

### 防 #DIV/0! 错误
```
=IF(B2=0, 0, A2/B2)
```

### 跨表引用
正确格式：`Sheet1!A1`，写错格式会产生 #REF! 错误。

## 常见坑
1. Python 算好结果再写入单元格 → 表格不可动态更新，改用 Excel 公式
2. `load_workbook(data_only=True)` 后保存 → 公式永久丢失，只剩缓存值
3. 分母为 0 未加保护 → 出现 #DIV/0! 错误，加 `IF(B2=0, 0, ...)` 判断
4. 跨表引用格式写错 → 出现 #REF! 错误，正确格式：`Sheet1!A1`
5. 列宽未设置 → 内容被截断，用 `sheet.column_dimensions['A'].width = 20`
