---
key: dataviz
name: 数据可视化
keywords: [图表, chart, 可视化, echarts, chartjs, dashboard, 仪表盘, 看板, 数据展示]
---

# 数据可视化规范

## 快速参考
| 任务 | 推荐方案 |
|------|---------|
| 轻量图表 | Chart.js（CDN 即用） |
| 复杂交互 | ECharts（中文生态好） |
| 数据看板 | KPI卡片 + 主图 + 辅图 布局 |

## 核心规范

### 标准调色板
- 主色序列：`['#6366f1', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444']`
- 背景色：`rgba` 版本降低到 0.1 透明度做填充区域
- 同一图表颜色不超过 6 种，超出用灰色归入"其他"
- 对比场景用互补色（如 #10b981 正面 / #ef4444 负面）

### Chart.js 配置模板
```javascript
{
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom', labels: { padding: 20, usePointStyle: true } },
    tooltip: { mode: 'index', intersect: false }
  },
  elements: {
    line: { tension: 0.4, borderWidth: 2 },
    bar: { borderRadius: 6 },
    point: { radius: 0, hoverRadius: 5 }
  },
  scales: {
    y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
    x: { grid: { display: false } }
  }
}
```

### ECharts 配置要点
- `grid: { containLabel: true, left: 20, right: 20, top: 40, bottom: 20 }`
- `tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } }`
- `xAxis.axisLabel.rotate`：标签过长时旋转 30-45 度
- 必须监听 `window.resize` 调用 `chart.resize()`

### 看板布局
- 顶部：KPI 卡片行（3-5 个），每个卡片包含标题、数值、变化率
- 中部：主图表区域（占 60% 高度），用折线/柱状图
- 底部或侧边：辅助图表（饼图、排名表）
- 卡片间距 gap-6，外层 max-w-7xl mx-auto

### KPI 卡片设计
- 数值用 text-3xl font-bold，变化率用带颜色的小字
- 正增长 text-emerald-600 ▲，负增长 text-red-500 ▼
- 卡片背景 bg-white，左侧可加彩色边条

### 容器高度
- 必须为图表容器设置明确高度（不能依赖内容撑开）
- 主图：`h-[400px]` 或 `min-height: 400px`
- 辅图：`h-[300px]`
- KPI 卡片：自适应，不设固定高度

### 数字格式化
- 千位分隔符：`num.toLocaleString('zh-CN')`
- 大数缩写：万/亿（10000 → 1万，100000000 → 1亿）
- 百分比保留 1 位小数：`(val * 100).toFixed(1) + '%'`
- 金额加 ¥ 前缀

### 数据加载
- 图表区域在数据加载时显示骨架屏或 loading 动画
- 空数据状态：显示"暂无数据"插图，不留空白
- 错误状态：显示重试按钮

## 自检清单
- [ ] 所有图表容器有明确高度
- [ ] 调色板统一，未超过 6 色
- [ ] 数字有千位分隔和单位
- [ ] 图表 responsive 已启用
- [ ] 窗口 resize 时图表自适应
- [ ] 空数据和加载中状态已处理
