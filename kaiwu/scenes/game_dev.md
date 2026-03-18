---
key: game_dev
name: 游戏开发
keywords: [游戏, game, canvas, 小游戏, 游戏开发, phaser, 动画, animation, 碰撞]
---

# 游戏开发规范

## 快速参考
| 任务 | 推荐方案 |
|------|---------|
| 2D 游戏 | Canvas API |
| 游戏框架 | Phaser 3 |
| 物理引擎 | Matter.js |
| 帧循环 | requestAnimationFrame |

## 核心规范

### 游戏主循环
- 必须使用 `requestAnimationFrame`，禁止 `setInterval`/`setTimeout`
- 每帧计算 delta time，物理计算基于 dt 而非帧数
- 分离 update（逻辑）和 render（渲染）

```javascript
let lastTime = 0;

function gameLoop(timestamp) {
    const dt = (timestamp - lastTime) / 1000; // 秒
    lastTime = timestamp;

    update(dt);
    render();

    requestAnimationFrame(gameLoop);
}
requestAnimationFrame(gameLoop);
```

### Delta Time
- 所有运动/动画必须乘以 `dt`
- `position.x += speed * dt`（不是 `position.x += speed`）
- 这样游戏在不同刷新率（60Hz/144Hz）下表现一致
- dt 异常大时（切标签页回来）做截断：`Math.min(dt, 0.1)`

### 状态机
- 游戏全局状态用状态机管理
- 标准状态：`MENU` → `PLAYING` → `PAUSED` → `GAME_OVER`
- 每个状态有独立的 `enter()`、`update(dt)`、`render()`、`exit()` 方法
- 状态切换通过统一接口，不要散落各处

```javascript
const GameState = {
    MENU: 'menu',
    PLAYING: 'playing',
    PAUSED: 'paused',
    GAME_OVER: 'game_over',
};

let currentState = GameState.MENU;

function changeState(newState) {
    states[currentState]?.exit();
    currentState = newState;
    states[currentState]?.enter();
}
```

### 资源预加载
- 所有图片/音频在游戏开始前加载完毕
- 显示加载进度条
- 使用 Promise.all 等待所有资源就绪
- 加载失败提供重试机制

```javascript
function preloadImage(src) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = reject;
        img.src = src;
    });
}
```

### AABB 碰撞检测
- 矩形碰撞（最常用）：检查两个矩形是否重叠
- 碰撞检测在 update 阶段执行，render 之前
- 需要碰撞响应时（弹开/停止），在检测后立即处理

```javascript
function checkCollision(a, b) {
    return (
        a.x < b.x + b.width &&
        a.x + a.width > b.x &&
        a.y < b.y + b.height &&
        a.y + a.height > b.y
    );
}
```

### 输入管理
- 封装 InputManager 类统一处理键盘/鼠标/触摸
- 记录按键状态（isDown/isPressed/isReleased）
- 游戏暂停时停止响应游戏输入
- 支持按键映射配置

```javascript
class InputManager {
    constructor() {
        this.keys = {};
        window.addEventListener('keydown', (e) => { this.keys[e.code] = true; });
        window.addEventListener('keyup', (e) => { this.keys[e.code] = false; });
    }
    isDown(code) { return !!this.keys[code]; }
}
```

### Canvas 渲染
- 每帧开头 `ctx.clearRect(0, 0, canvas.width, canvas.height)` 清屏
- 使用 `ctx.save()` / `ctx.restore()` 管理变换上下文
- Canvas 尺寸用 JS 设置（不用 CSS 缩放，会模糊）
- 支持高 DPI：`canvas.width = width * devicePixelRatio`

### 对象池
- 高频创建/销毁的对象（子弹、粒子）使用对象池
- 池中对象标记 `active` 状态，回收时重置属性
- 避免游戏运行时频繁 GC 导致卡顿

```javascript
class ObjectPool {
    constructor(factory, size = 50) {
        this.pool = Array.from({ length: size }, () => factory());
        this.active = [];
    }
    get() {
        const obj = this.pool.pop() || this.factory();
        this.active.push(obj);
        return obj;
    }
    release(obj) {
        const idx = this.active.indexOf(obj);
        if (idx !== -1) this.active.splice(idx, 1);
        obj.reset();
        this.pool.push(obj);
    }
}
```

## 自检清单
- [ ] 使用 requestAnimationFrame 而非 setInterval
- [ ] 运动计算乘以 delta time
- [ ] 游戏状态用状态机管理
- [ ] 资源在游戏开始前预加载
- [ ] 碰撞检测逻辑正确
- [ ] 输入通过统一 InputManager 处理
- [ ] Canvas 每帧 clearRect 清屏
- [ ] 高频对象使用对象池
