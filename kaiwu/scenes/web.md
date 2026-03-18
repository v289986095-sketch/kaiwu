---
key: web
name: 网页/前端生成
keywords: [网页, html, 页面, landing, 前端, tailwind, css, website, 网站]
---

# 网页/前端生成规范

## 快速参考
| 任务 | 推荐方案 |
|------|---------|
| 静态页面 | HTML + Tailwind CDN |
| 响应式布局 | Grid + Flexbox |
| 动画 | CSS transition + transform |

## 核心规范

### 设计先行
- 先明确风格方向（配色/字体/布局），不要上来就写代码
- 选择有个性的字体（不要默认 Inter/Arial/Roboto）
- 大胆配色，避免全灰单调

### 配色与字体
- 主色系统一（推荐 indigo/blue #6366f1），中性色 slate
- 页面背景 #f8fafc，文字 slate-800/slate-600
- 标题 font-semibold 或 font-bold，正文 text-sm 或 text-base

### 间距与圆角
- 所有间距使用 8px 倍数（p-4 / p-6 / p-8 / gap-6）
- 卡片 rounded-xl，按钮 rounded-lg，小标签 rounded-full

### 布局
- 外层容器 max-w-7xl mx-auto px-4
- 卡片统一 bg-white border border-slate-200 shadow-sm
- 响应式网格：grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6

### 导航栏
- sticky top-0 z-10 backdrop-blur bg-white/80 border-b border-slate-200

### 按钮样式
- 主按钮：bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors
- 次按钮：border border-slate-300 text-slate-700 hover:bg-slate-50

### CDN 引入
- <head> 中引入 Tailwind CDN（script src cdn.tailwindcss.com）
- Font Awesome 6.5（cdnjs）

### 交互细节
- 所有可点击元素加 cursor-pointer 和 hover 状态
- 卡片加 hover:shadow-md transition-shadow

## 自检清单
- [ ] 页面标题/卡片标题风格统一
- [ ] 全局只用 2-3 个主色
- [ ] 移动端（<768px）布局正确
- [ ] 所有按钮和链接有 hover 状态
- [ ] 已引入 Tailwind CDN 和图标库
