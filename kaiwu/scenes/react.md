---
key: react
name: React 组件开发
keywords: [react, 组件, component, tsx, jsx, hooks, shadcn, nextjs]
---

# React 组件开发规范

## 快速参考
| 任务 | 推荐方案 |
|------|---------|
| 样式系统 | CSS 变量 (HSL) + Tailwind |
| 图标 | lucide-react |
| UI 库 | shadcn/ui |
| 状态管理 | useState/useReducer，复杂场景 Zustand |

## 核心规范

### CSS 变量体系
- 使用 HSL 格式定义主题色变量，方便动态切换
- 变量命名：`--primary`、`--secondary`、`--destructive`、`--muted`
- 在 `globals.css` 的 `:root` 和 `.dark` 中分别定义亮/暗色值
- 引用方式：`hsl(var(--primary))`，不要硬编码颜色值

### TypeScript Props 接口
- 每个组件必须定义 Props 接口，命名为 `组件名Props`
- 使用 `interface` 而非 `type`（便于扩展）
- 可选属性用 `?` 标注，必须属性不加
- 导出 Props 接口，方便外部使用

```typescript
interface ButtonProps {
  variant?: 'default' | 'outline' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  loading?: boolean
  children: React.ReactNode
  onClick?: () => void
}
```

### cn() 工具函数
- 使用 `clsx` + `tailwind-merge` 封装 `cn()` 函数
- 所有动态 className 拼接必须走 `cn()`
- 位置：`lib/utils.ts`

### 图标使用
- 统一使用 `lucide-react`，不混用多个图标库
- 图标 size 与文字 size 匹配（text-sm 配 size={16}）
- 图标颜色跟随文字颜色，不单独指定

### 交互状态
- 所有按钮必须处理 `disabled` 和 `loading` 状态
- loading 时显示 Spinner + 文字，禁止重复点击
- disabled 样式：`opacity-50 cursor-not-allowed`

### 无障碍访问
- 所有图标按钮必须加 `aria-label`
- 表单控件绑定 `<label htmlFor>`
- 弹窗使用 `role="dialog"` + `aria-modal="true"`
- 焦点管理：弹窗打开时聚焦首个输入，关闭时恢复

### shadcn/ui 模式
- 组件放 `components/ui/` 目录
- 使用 `cva`（class-variance-authority）管理变体
- 通过 `forwardRef` 暴露 DOM 引用
- Slot 模式支持 `asChild` 属性

### 文件组织
- 一个文件一个组件，文件名与组件名一致
- hooks 放 `hooks/` 目录，以 `use` 开头
- 工具函数放 `lib/` 目录
- 类型定义放 `types/` 目录或组件文件顶部

### 性能注意
- 列表渲染必须加 `key`（用唯一 id，不用 index）
- 昂贵计算用 `useMemo`，回调用 `useCallback`
- 避免在 render 中创建新对象/数组作为 props

## 自检清单
- [ ] 所有组件 Props 都有 TypeScript 接口定义
- [ ] className 拼接使用 cn() 而非模板字符串
- [ ] 按钮有 disabled/loading 状态处理
- [ ] 图标按钮有 aria-label
- [ ] 没有硬编码颜色值，全部走 CSS 变量或 Tailwind
- [ ] 列表渲染有稳定唯一的 key
