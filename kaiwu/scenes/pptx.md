# PPT / 演示文稿（pptx）场景规范

## 适用场景
创建或编辑 .pptx 演示文稿，从头创建用 pptxgenjs（Node.js），编辑已有文件用 python-pptx。

## 快速参考

| 任务类型 | 推荐方式 |
|---------|---------|
| 从头创建 PPT | pptxgenjs（Node.js）或 python-pptx |
| 编辑已有 pptx | python-pptx |
| 读取 / 分析内容 | python -m markitdown presentation.pptx |

## 设计规范（必须遵守）

- **配色方案**：选一个大胆的配色，且必须适合主题内容，不能套用通用蓝。主色占 60-70% 视觉权重，搭配 1-2 个配色和 1 个强调色
- **深浅结构**：深色背景用于标题页和结尾页，浅色用于内容页，形成深-浅-深的三明治结构
- **视觉元素**：每张幻灯片必须有视觉元素（图片/图表/图标/形状），纯文字幻灯片令人遗忘
- **字体规范**：标题 36-44pt bold，正文 14-16pt，不要默认用 Arial
- **绝对禁止**：绝不在标题下加装饰横线，这是 AI 生成幻灯片的标志性缺陷
- **布局多样性**：不要每张幻灯片用同一个布局，变化使用两列/图标行/网格/全图背景等

## 核心用法

### 从头创建（pptxgenjs）
```js
const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";

const slide = pptx.addSlide();
slide.addText("标题文字", {
  x: 0.5, y: 1.5, w: 9, h: 1.5,
  fontSize: 40, bold: true, color: "FFFFFF",
  align: "center"
});
slide.background = { color: "1a1a2e" };

await pptx.writeFile({ fileName: "output.pptx" });
```

### 内容检查
```bash
python -m markitdown output.pptx
```

## 常见坑
1. 每张幻灯片用相同布局 → 演示单调，变化使用两列/图标行/网格/全图背景等
2. 标题下加装饰横线 → AI 生成痕迹，改用空白分隔或背景色块区分
3. 默认蓝色配色（#0070C0） → 与主题内容无关，根据主题选择匹配的颜色体系
4. 生成后不做视觉 QA → 元素重叠或文字溢出边界，必须转图检查
5. 纯文字幻灯片（无任何视觉元素） → 必须加图标、数据图表或配图
