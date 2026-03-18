---
key: data_analysis
name: 数据分析
keywords: [pandas, 数据分析, 分析, dataframe, excel, csv, 数据处理, 统计]
---

# 数据分析规范

## 快速参考
| 任务 | 推荐方案 |
|------|---------|
| 数据读取 | pd.read_csv / pd.read_excel |
| 数据清洗 | pandas 链式操作 |
| 可视化 | matplotlib + seaborn |
| 大文件 | chunksize 分块读取 |

## 核心规范

### 数据读取
- 始终指定 `encoding` 参数（中文数据常见 `gbk`/`utf-8-sig`/`utf-8`）
- 大文件用 `chunksize` 分块处理，避免内存溢出
- 读取后立即检查 `df.shape`、`df.dtypes`、`df.head()`

```python
df = pd.read_csv('data.csv', encoding='utf-8-sig', chunksize=10000)

# 或一次性读取
df = pd.read_csv('data.csv', encoding='utf-8')
print(f'数据形状: {df.shape}')
print(f'列类型:\n{df.dtypes}')
```

### 空值处理
- 先检查空值分布：`df.isnull().sum()`
- 不要无脑 `dropna()`，先分析空值占比和含义
- 数值列空值：根据业务决定填充（均值/中位数/0）
- 分类列空值：填充为"未知"或单独类别
- 记录处理前后行数变化

```python
null_stats = df.isnull().sum()
print(f'空值统计:\n{null_stats[null_stats > 0]}')

# 明确决策后再处理
df['age'] = df['age'].fillna(df['age'].median())
df['category'] = df['category'].fillna('未知')
```

### 类型安全
- 字符串转数值：`pd.to_numeric(col, errors='coerce')`
- 字符串转日期：`pd.to_datetime(col, errors='coerce', format='%Y-%m-%d')`
- 转换后检查 NaT/NaN 数量（`errors='coerce'` 会静默转 NaN）
- 不要直接 `int()` 或 `float()` 转换，会因脏数据报错

### 内存优化
- `int64` → `int32`（值范围允许时）
- 低基数字符串列（<500种）→ `category` 类型
- 用 `df.info(memory_usage='deep')` 查看真实内存占用

```python
df['status'] = df['status'].astype('category')
df['count'] = pd.to_numeric(df['count'], downcast='integer')
```

### SettingWithCopyWarning 预防
- 从 DataFrame 切片后立即 `.copy()`
- 不要对切片结果直接赋值
- 使用 `.loc[]` 进行条件赋值

```python
# 正确
subset = df[df['age'] > 18].copy()
subset['label'] = 'adult'

# 正确
df.loc[df['age'] > 18, 'label'] = 'adult'

# 错误 - 触发警告
subset = df[df['age'] > 18]
subset['label'] = 'adult'
```

### matplotlib 中文支持
- 必须设置中文字体，否则中文显示方框
- Windows：SimHei；macOS：PingFang SC；Linux：WenQuanYi

```python
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei', 'PingFang SC', 'WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus'] = False
```

### 输出文件
- CSV 输出用 `encoding='utf-8-sig'`（Excel 兼容 BOM 头）
- Excel 输出用 `openpyxl` 引擎
- 输出前打印摘要信息（行数、列数、文件大小）
- `index=False` 除非索引有业务含义

```python
df.to_csv('output.csv', encoding='utf-8-sig', index=False)
```

## 自检清单
- [ ] read_csv/read_excel 指定了 encoding
- [ ] 空值处理前先分析了分布
- [ ] 类型转换用 pd.to_numeric/pd.to_datetime
- [ ] 切片后使用了 .copy()
- [ ] matplotlib 设置了中文字体
- [ ] 输出 CSV 用 utf-8-sig 编码
- [ ] 处理前后打印了数据形状变化
