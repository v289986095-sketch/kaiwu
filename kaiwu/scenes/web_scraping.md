---
key: web_scraping
name: 网页爬虫
keywords: [爬虫, 抓取, scraping, crawler, 采集, requests, beautifulsoup, playwright, 爬取]
---

# 网页爬虫规范

## 快速参考
| 任务 | 推荐方案 |
|------|---------|
| 静态页面 | requests + BeautifulSoup |
| 动态页面 | playwright |
| 数据提取 | CSS 选择器 / XPath |
| 反爬应对 | 随机延迟 + UA 轮换 |

## 核心规范

### 必须设置 User-Agent
- 每个请求携带真实浏览器 UA，不用默认的 python-requests
- 准备 3-5 个 UA 轮换使用
- 同时设置 `Accept` 和 `Accept-Language` 头

```python
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}
```

### 重试机制
- 使用 `requests.adapters.HTTPAdapter` 配置自动重试
- 重试次数 3 次，退避因子 0.5
- 针对 500/502/503/504 状态码重试

```python
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retry))
session.mount('http://', HTTPAdapter(max_retries=retry))
```

### 超时设置
- 每个请求必须设置 `timeout=10`（秒）
- 连接超时和读取超时可分开：`timeout=(5, 10)`
- 没有 timeout 的请求可能无限挂起

### 请求频率控制
- 每次请求间随机延迟 1-3 秒：`time.sleep(random.uniform(1, 3))`
- 对同一域名不要并发请求
- 遵守 robots.txt（至少检查一下）
- 如遇 429 状态码，指数退避等待

### 元素提取安全
- `find()` / `select_one()` 结果可能为 None，必须检查
- 提取文本用 `.get_text(strip=True)`
- 提取属性用 `.get('href', '')`，不要直接 `['href']`
- 链式查找分步做，每步检查 None

```python
# 正确
item = soup.select_one('.product-card')
if item:
    title_el = item.select_one('.title')
    title = title_el.get_text(strip=True) if title_el else '未知'
    link = item.select_one('a')
    href = link.get('href', '') if link else ''

# 错误 - 可能 NoneType 报错
title = soup.select_one('.product-card .title').text
```

### 数据存储
- 使用追加模式写文件（`mode='a'`），防止中断丢失数据
- 每采集一批数据立即写入，不要全部存内存
- CSV 第一次写入包含表头，后续 `header=False`
- 文件编码 `utf-8-sig`

```python
df_batch.to_csv('output.csv', mode='a', header=not os.path.exists('output.csv'),
                index=False, encoding='utf-8-sig')
```

### Playwright 降级方案
- requests 拿不到内容时（JS 渲染页面），切换 playwright
- 使用无头模式 `headless=True`
- 等待目标元素出现再提取：`page.wait_for_selector('.target')`
- 用完关闭浏览器释放资源

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, timeout=15000)
    page.wait_for_selector('.content')
    html = page.content()
    browser.close()
```

### 异常与日志
- 单条数据抓取失败不中断全流程，记录跳过
- 定期输出进度（每 50 条打印一次）
- 记录失败 URL 到单独文件，便于补抓

## 自检清单
- [ ] 所有请求设置了 User-Agent
- [ ] 所有请求设置了 timeout
- [ ] 请求间有随机延迟
- [ ] find()/select_one() 结果检查了 None
- [ ] 数据追加模式写入文件
- [ ] 失败请求有重试机制
- [ ] 异常不中断主循环
