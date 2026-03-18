# China Developer Knowledge Base

针对中国开发者的完整知识库：编码规范、镜像源、SDK、小程序、支付、坐标系、常见坑。

---

## 1. 编码与终端（CRITICAL）

中文 Windows 系统默认 GBK (CP936)，**所有生成的 Python 脚本必须在开头加**：

```python
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
```

**FORBIDDEN — 中文 Windows 下必定崩溃：**
```python
print("✓ 成功")   # UnicodeEncodeError：GBK 无法编码 Unicode 符号
print("❌ 失败")
print("🎉 完成")
```
**改用 ASCII 安全符号：** `[OK]` `[FAIL]` `[DONE]`

**subprocess 同样需要指定编码：**
```python
result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
```

**文件读写：** 始终显式指定 `encoding="utf-8"`；MySQL 用 `CHARACTER SET utf8mb4`；SQLite 用 `PRAGMA encoding = "UTF-8"`

---

## 2. 网络注意事项

- GitHub raw/API 可能超时 → 优先用 Gitee 镜像或本地 clone
- `curl`/`wget` 访问境外 URL 可能超时 → 加 `--connect-timeout 10` + 重试逻辑
- npm 包可能从 GitHub Releases 下载二进制 → 提前配置镜像或手动下载

---

## 3. 镜像源配置

### pip
```bash
# 单次使用
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple <pkg>
# 永久配置（推荐）
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn
# 备用：https://mirrors.aliyun.com/pypi/simple/  https://pypi.doubanio.com/simple/
```

### npm / yarn / pnpm
```bash
npm config set registry https://registry.npmmirror.com
yarn config set registry https://registry.npmmirror.com
pnpm config set registry https://registry.npmmirror.com
# 注意：registry.npm.taobao.org 已失效，必须用 npmmirror.com
```

### Maven（~/.m2/settings.xml 的 mirrors 节）
```xml
<mirror>
  <id>aliyun</id><mirrorOf>*</mirrorOf>
  <url>https://maven.aliyun.com/repository/public</url>
</mirror>
```

### Docker（/etc/docker/daemon.json）
```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
```
重载：`sudo systemctl daemon-reload && sudo systemctl restart docker`

### 其他镜像
```bash
# Go
go env -w GOPROXY=https://goproxy.cn,direct
go env -w GONOSUMCHECK=*

# Cargo (Rust) — ~/.cargo/config.toml
[source.crates-io]
replace-with = "ustc"
[source.ustc]
registry = "sparse+https://mirrors.ustc.edu.cn/crates.io-index/"

# conda
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
conda config --set show_channel_urls yes

# APT (Ubuntu)
sed -i 's|http://archive.ubuntu.com|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list
apt-get update

# yum/dnf (CentOS/Rocky)
sed -i 's|http://mirror.centos.org|https://mirrors.aliyun.com|g' /etc/yum.repos.d/CentOS-Base.repo
yum makecache
```

---

## 4. 微信小程序开发

**框架选择：**
- 原生：WXML + WXSS + JS，最稳定
- uni-app（HBuilderX）：一套代码多端，国内最流行跨端方案
- Taro（React 风格）：适合有 React 背景的团队

**常用 API：**
```js
wx.request({ url, method, data, success, fail })   // 网络请求（需域名白名单）
wx.navigateTo({ url: '/pages/xxx/xxx' })           // 页面跳转（最多10层）
wx.showToast({ title: '成功', icon: 'success' })
wx.setStorageSync(key, value) / wx.getStorageSync(key)
wx.getUserProfile({ desc: '用于完善资料' })         // 2021后替代 getUserInfo
```

**必知限制和坑：**
- 无 DOM/BOM，`window`/`document` 不可用
- 主包限制 2MB，总包限制 20MB，超出必须分包（subpackages）
- 网络域名必须在 mp.weixin.qq.com 控制台配置 request 合法域名
- 图片必须用 `<image>` 组件，不能用 `<img>`
- `wx.request` 不支持 Promise，需自行封装或用 promisify

**云开发（免后端方案）：**
```js
wx.cloud.init({ env: 'your-env-id' })
wx.cloud.callFunction({ name: 'funcName', data: {} })
wx.cloud.database().collection('users').get()
```

---

## 5. 抖音/字节小程序

- 开发工具：字节跳动开发者工具（独立下载，非微信工具）
- 全局对象用 `tt` 替代 `wx`：`tt.request`、`tt.navigateTo`、`tt.showToast`
- uni-app 配置 `"mp-toutiao"` 平台可直接编译为抖音小程序
- 抖音开放平台：open.douyin.com，需企业资质

---

## 6. 短视频 / 音视频开发

**ffmpeg 基础命令：**
```bash
ffmpeg -i input.mp4 -c:v libx264 -crf 23 output.mp4       # 转码
ffmpeg -i input.mp4 -ss 00:00:05 -frames:v 1 thumb.jpg    # 截图
ffmpeg -i input.mp4 -ss 10 -t 30 -c copy clip.mp4         # 剪辑
ffmpeg -i input.mp4 -vn -acodec mp3 audio.mp3             # 提取音频
```

**云视频 SDK：**
```bash
pip install tencentcloud-sdk-python   # 腾讯云点播（vod模块）
pip install aliyun-python-sdk-vod aliyun-python-sdk-core  # 阿里云点播
```
抖音开放平台视频上传：需企业开发者资质，open.douyin.com，使用分片上传接口。

---

## 7. 国内云服务 SDK

### 腾讯云
```bash
pip install tencentcloud-sdk-python   # 全量 SDK
pip install cos-python-sdk-v5         # COS 对象存储专用
```
```python
from tencentcloud.common import credential
cred = credential.Credential("SecretId", "SecretKey")  # 控制台获取
```

### 阿里云
```bash
pip install aliyun-python-sdk-core oss2
```
```python
import oss2
auth = oss2.Auth('AccessKeyId', 'AccessKeySecret')
bucket = oss2.Bucket(auth, 'https://oss-cn-hangzhou.aliyuncs.com', 'bucket-name')
bucket.put_object('remote/path.txt', b'content')
```

### 华为云 / 七牛 / 又拍
```bash
pip install huaweicloudsdkcore huaweicloudsdkobs
pip install qiniu    # 七牛云，常用文件存储
pip install upyun    # 又拍云
```

---

## 8. 支付集成

### 微信支付
```bash
pip install wechatpayv3
```
```python
from wechatpayv3 import WeChatPay, WeChatPayType
wxpay = WeChatPay(
    wechatpay_type=WeChatPayType.MINIPROG,
    mchid='商户号', private_key='私钥内容',
    cert_serial_no='证书序列号', apiv3_key='APIv3密钥',
    appid='小程序appid'
)
# 下单后返回参数传给前端 wx.requestPayment()
```
关键参数：`appid`、`mchid`、`notify_url`、`openid`（小程序必须）

### 支付宝
```bash
pip install alipay-sdk-python
```
```python
from alipay import AliPay
alipay = AliPay(
    appid='your_appid',
    app_notify_url='https://your-domain/notify',
    app_private_key_string=open('private_key.pem').read(),
    alipay_public_key_string=open('alipay_public_key.pem').read(),
)
```

---

## 9. 地图与坐标系（重要！）

**三套坐标系：**
- **WGS-84**：GPS 标准，国际通用
- **GCJ-02（火星坐标）**：中国法定，高德/腾讯/微信地图使用
- **BD-09**：百度地图专用（在 GCJ-02 基础上二次加密）

**规则：在中国境内的地图应用必须使用 GCJ-02，原始 GPS 坐标需转换！**

```bash
pip install coordtransform
```
```python
import coordtransform
lng_gcj, lat_gcj = coordtransform.wgs84_to_gcj02(lng, lat)  # GPS -> 高德/腾讯
lng_bd, lat_bd   = coordtransform.gcj02_to_bd09(lng_gcj, lat_gcj)  # -> 百度
lng_wgs, lat_wgs = coordtransform.gcj02_to_wgs84(lng_gcj, lat_gcj)  # -> 还原GPS
```

**常用地图 API：**
- 高德：amap.com，`jsapi_key` + Web API（geocode、POI、路线规划）
- 腾讯地图：lbs.qq.com，接口格式类似高德
- 百度地图：lbsyun.baidu.com，坐标用 BD-09，注意转换

---

## 10. 国内常用框架速查

| 方向 | 主流选择 |
|------|---------|
| 前端 PC | Vue 3 + Element Plus / Ant Design Vue |
| 前端移动 H5 | Vue 3 + Vant |
| 小程序跨端 | uni-app（最流行）、Taro（React 风格）|
| 后端 Python | FastAPI > Flask > Django |
| 后端 Java | Spring Boot + MyBatis-Plus |
| 后端 Go | Gin + GORM |
| 后端 Node | Express / Koa / NestJS |
| 数据库 | MySQL（主流）、Redis（缓存）、MongoDB（文档）|
| 国产分布式 DB | TiDB、OceanBase（兼容 MySQL 协议）|

---

## 11. 国内代码托管

- **Gitee**（gitee.com）：国内访问快，常用格式：`gitee.com/mirrors/<repo-name>`
- **腾讯 CODING**（coding.net）：企业 DevOps，CI/CD 齐全
- **阿里云 Codeup**（codeup.aliyun.com）：阿里云体系内使用

---

## 12. 数据验证正则（中国特有）

```python
import re

PHONE_RE    = r'^1[3-9]\d{9}$'           # 手机号（11位）
ID_CARD_RE  = r'^\d{17}[\dX]$'           # 身份证（18位，末位可为X）
BANK_CARD_RE= r'^\d{16,19}$'             # 银行卡（还需 Luhn 算法）
USCC_RE     = r'^[0-9A-HJ-NP-RT-UW-Y]{18}$'  # 统一社会信用代码（营业执照）
OPENID_RE   = r'^[a-zA-Z0-9_-]{28}$'    # 微信 openid
POSTCODE_RE = r'^\d{6}$'                  # 邮政编码

def validate_phone(s):    return bool(re.match(PHONE_RE, s))
def validate_id_card(s):  return bool(re.match(ID_CARD_RE, s.upper()))
```

---

## 13. 国内常用 API 服务速查

| 服务类型 | 推荐方案 | 安装 |
|------|------|------|
| 短信 | 腾讯云 SMS | `pip install tencentcloud-sdk-python` |
| 短信备选 | 阿里云 SMS | `pip install aliyun-python-sdk-dysmsapi` |
| OCR | 腾讯云 OCR | tencentcloud SDK，`ocr_client.GeneralBasicOCR` |
| OCR 备选 | 百度 OCR | `pip install baidu-aip` |
| 人脸识别 | 腾讯云 iai | tencentcloud SDK |
| 语音识别 | 腾讯云 ASR / 阿里云 NLS | 按场景选 |
| 推送通知 | 个推 / 极光推送 | `pip install gexin-pusher` |
| 地理编码 | 高德 Web API | HTTP 请求，key 在 console.amap.com 申请 |

---

## 14. A股数据获取与金融计算

### 数据源选择

| 数据源 | 特点 | 安装 |
|------|------|------|
| akshare | 免费、覆盖广、无需 key，首选 | `pip install akshare` |
| tushare | 需注册积分，历史数据完整 | `pip install tushare` |
| baostock | 免费登录，日线/分钟线均有 | `pip install baostock` |
| efinance | 抓取东方财富数据，轻量 | `pip install efinance` |

**注意：yfinance 在中国大陆无法直接获取 A股数据，不要用。**

### akshare 常用接口

```python
import akshare as ak

# 股票日线 K 线（前复权）
df = ak.stock_zh_a_hist(symbol="600519", period="daily",
                         start_date="20230101", end_date="20241231",
                         adjust="qfq")
# 返回列：日期、开盘、收盘、最高、最低、成交量、成交额、振幅、涨跌幅、涨跌额、换手率

# 实时行情（全市场）
df_rt = ak.stock_zh_a_spot_em()

# 指数日线（上证/深证/创业板）
df_idx = ak.stock_index_daily_em(symbol="000001", start_date="20230101", end_date="20241231")

# 财务数据（利润表）
df_profit = ak.stock_financial_benefit_ths(symbol="600519", indicator="按年度")

# 龙虎榜
df_lhb = ak.stock_lhb_detail_em(symbol="600519", start_date="20240101", end_date="20241231")
```

### tushare 常用接口

```python
import tushare as ts
pro = ts.pro_api("your_token")  # token 在 tushare.pro 注册获取

# 日线行情
df = pro.daily(ts_code="600519.SH", start_date="20230101", end_date="20241231")

# 复权因子（前复权需自行计算）
df_adj = pro.adj_factor(ts_code="600519.SH")

# 股票基本信息
df_basic = pro.stock_basic(exchange="SSE", list_status="L")
```

**tushare ts_code 格式：上交所 `.SH`，深交所 `.SZ`，北交所 `.BJ`**

### 技术指标手动实现（不依赖 ta-lib）

```python
import pandas as pd
import numpy as np

def calc_ma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(window=period).mean()

def calc_macd(close: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd_bar = (dif - dea) * 2
    return dif, dea, macd_bar

def calc_rsi(close: pd.Series, period=14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calc_boll(close: pd.Series, period=20, std_dev=2):
    mid = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    return upper, mid, lower

def calc_kdj(high, low, close, n=9, m1=3, m2=3):
    low_n  = low.rolling(window=n).min()
    high_n = high.rolling(window=n).max()
    rsv = (close - low_n) / (high_n - low_n).replace(0, np.nan) * 100
    K = rsv.ewm(com=m1-1, adjust=False).mean()
    D = K.ewm(com=m2-1, adjust=False).mean()
    J = 3 * K - 2 * D
    return K, D, J
```

### 简单回测框架骨架

```python
class Backtest:
    def __init__(self, df: pd.DataFrame, init_cash=100_000):
        self.df = df.copy()
        self.cash = init_cash
        self.position = 0       # 持股数
        self.trades = []
        self.equity_curve = []

    def run(self, strategy_fn):
        """strategy_fn(row, prev_row) -> 'buy' | 'sell' | None"""
        for i in range(1, len(self.df)):
            row, prev = self.df.iloc[i], self.df.iloc[i-1]
            signal = strategy_fn(row, prev)
            price = row["收盘"]
            if signal == "buy" and self.cash >= price * 100:
                shares = int(self.cash // (price * 100)) * 100  # A股最小100股
                self.cash -= shares * price
                self.position += shares
                self.trades.append({"date": row["日期"], "type": "buy", "price": price, "shares": shares})
            elif signal == "sell" and self.position > 0:
                self.cash += self.position * price
                self.trades.append({"date": row["日期"], "type": "sell", "price": price, "shares": self.position})
                self.position = 0
            self.equity_curve.append(self.cash + self.position * price)

    def stats(self):
        curve = pd.Series(self.equity_curve)
        total_return = (curve.iloc[-1] / curve.iloc[0] - 1) * 100
        peak = curve.cummax()
        max_dd = ((curve - peak) / peak).min() * 100
        wins = [t for i, t in enumerate(self.trades) if t["type"] == "sell"
                and t["price"] > self.trades[i-1]["price"]]
        return {
            "total_return_pct": round(total_return, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "trade_count": len([t for t in self.trades if t["type"] == "sell"]),
            "win_rate": round(len(wins) / max(1, len(self.trades)//2) * 100, 1),
        }
```

### 常见坑

- A股最小交易单位是 **100股（1手）**，回测买入量必须取整到100的倍数
- 复权处理：akshare `adjust="qfq"` 前复权，`adjust="hfq"` 后复权，不复权会导致历史指标计算错误
- 涨跌停：A股主板 ±10%，科创板/创业板 ±20%，北交所 ±30%，回测时需过滤涨跌停无法成交的情况
- 交易费用：印花税卖出 0.1%，佣金双向约 0.02%-0.03%，不计入费用会高估收益

---

## 15. 电商数据处理（GMV / 电商指标）

### 核心指标定义（中国电商标准）

```python
# GMV（Gross Merchandise Volume，商品交易总额）
# = 下单金额，含未付款、退款订单；不等于实际收入
gmv = df["order_amount"].sum()

# 实收金额（剔除退款）
actual_revenue = df[df["status"] == "completed"]["order_amount"].sum()

# 客单价（AOV, Average Order Value）
aov = gmv / df["order_id"].nunique()

# UV 转化率
uv_conversion = df["order_id"].nunique() / total_uv * 100

# 复购率
repeat_buyers = df.groupby("user_id")["order_id"].count()
repeat_rate = (repeat_buyers > 1).sum() / repeat_buyers.count() * 100
```

### 大促数据模拟（双十一/618/双十二）

```python
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def gen_promotion_data(n=10000, event="双十一"):
    """生成模拟大促订单数据"""
    categories = ["服装", "电子", "美妆", "食品", "家居", "运动", "图书"]
    provinces  = ["广东", "浙江", "江苏", "上海", "北京", "四川", "湖北",
                  "河南", "山东", "福建", "湖南", "安徽"]
    # 双十一流量分布：0点爆发，10-12点次高峰，20-24点回升
    hour_weights = [15,3,2,2,2,2,3,5,7,8,10,9,7,6,5,5,6,7,8,9,10,11,10,8]

    rng = np.random.default_rng(42)
    hours   = rng.choice(range(24), size=n, p=np.array(hour_weights)/sum(hour_weights))
    cats    = rng.choice(categories, size=n, p=[0.25,0.20,0.18,0.12,0.10,0.08,0.07])
    provs   = rng.choice(provinces, size=n)

    price_map = {"服装":(50,800), "电子":(200,8000), "美妆":(30,500),
                 "食品":(10,200), "家居":(50,2000), "运动":(80,1500), "图书":(20,150)}

    rows = []
    for i in range(n):
        cat = cats[i]
        lo, hi = price_map[cat]
        price = round(rng.uniform(lo, hi), 2)
        qty   = int(rng.choice([1,1,1,2,2,3], p=[0.5,0.2,0.1,0.1,0.05,0.05]))
        rows.append({
            "order_id":  f"DD{i+1:08d}",
            "user_id":   f"U{rng.integers(1, n//3):07d}",
            "category":  cat,
            "province":  provs[i],
            "price":     price,
            "quantity":  qty,
            "amount":    round(price * qty, 2),
            "hour":      int(hours[i]),
            "status":    rng.choice(["completed","refunded"], p=[0.92, 0.08]),
        })
    return pd.DataFrame(rows)
```

### 常用分析聚合

```python
df = gen_promotion_data(10000)

# 1. 各品类 GMV 及占比
gmv_by_cat = (df.groupby("category")["amount"]
               .sum().sort_values(ascending=False)
               .to_frame("gmv")
               .assign(share=lambda x: x["gmv"] / x["gmv"].sum() * 100))

# 2. 每2小时销售额（时段分析）
df["time_slot"] = (df["hour"] // 2 * 2).map(lambda h: f"{h:02d}:00-{h+2:02d}:00")
slot_gmv = df.groupby("time_slot")["amount"].sum().sort_values(ascending=False)

# 3. 各省销量 Top10（ECharts map series 格式）
prov_sales = df.groupby("province")["quantity"].sum().reset_index()
echarts_data = [{"name": r["province"], "value": int(r["quantity"])}
                for _, r in prov_sales.iterrows()]

# 4. 退款率分析
refund_rate = df.groupby("category").apply(
    lambda g: (g["status"] == "refunded").sum() / len(g) * 100
).round(2)
```

### 重要节点日期参考

```python
PROMOTIONS = {
    "618":   {"start": "06-01", "peak": "06-18"},
    "双十一": {"start": "10-31", "peak": "11-11"},
    "双十二": {"start": "12-09", "peak": "12-12"},
    "年货节": {"start": "01-10", "peak": "01-20"},  # 农历前约20天
}
# 大促通常提前10-15天开启预售，当天0点爆发，注意时间戳时区统一用 Asia/Shanghai
```

---

## 16. 中文文本处理与古诗词

### 分词工具选择

```bash
pip install jieba          # 最常用，支持自定义词典
pip install pkuseg         # 北大，分词精度更高，较慢
pip install thulac         # 清华，支持词性标注
pip install hanlp          # 多功能，支持命名实体识别、依存句法
```

### jieba 常用操作

```python
import jieba
import jieba.analyse

# 精确模式（默认）
words = list(jieba.cut("春眠不觉晓，处处闻啼鸟"))

# 全模式（所有可能词组，用于搜索索引）
words_all = list(jieba.cut("白日依山尽，黄河入海流", cut_all=True))

# 搜索引擎模式（细粒度）
words_search = list(jieba.cut_for_search("两岸猿声啼不住，轻舟已过万重山"))

# TF-IDF 关键词提取
keywords = jieba.analyse.extract_tags(text, topK=10, withWeight=True)

# TextRank 关键词（不依赖语料库）
keywords_tr = jieba.analyse.textrank(text, topK=10, withWeight=True)

# 添加自定义词（避免被错误分割）
jieba.add_word("贞观之治")
jieba.add_word("开元盛世")
jieba.load_userdict("custom_dict.txt")  # 每行：词 词频 词性
```

### 古诗词数据集

```python
# chinese-poetry 项目（GitHub: chinese-poetry/chinese-poetry）
# 包含全唐诗、全宋词、论语等，JSON 格式

import json, pathlib

# 假设已下载到本地
def load_tang_poems(data_dir="./chinese-poetry/tang"):
    poems = []
    for f in pathlib.Path(data_dir).glob("poet.tang.*.json"):
        poems.extend(json.loads(f.read_text(encoding="utf-8")))
    return poems
# 每首结构：{"title": str, "author": str, "paragraphs": [str, ...]}

# 快速合并诗句
def poem_to_text(poem: dict) -> str:
    return "".join(poem["paragraphs"])
```

### 从零实现 TF-IDF（古诗词场景）

```python
import math
from collections import Counter

def tokenize_poem(text: str) -> list[str]:
    """古诗词用字级 unigram + bigram 混合"""
    chars   = list(text)                             # 单字
    bigrams = [text[i:i+2] for i in range(len(text)-1)]  # 双字
    return chars + bigrams

def build_tfidf(corpus: list[str]) -> tuple[list[dict], dict]:
    """corpus: 每首诗的全文字符串列表"""
    tokenized = [tokenize_poem(doc) for doc in corpus]
    N = len(corpus)

    # IDF
    doc_freq: dict[str, int] = Counter()
    for tokens in tokenized:
        for t in set(tokens):
            doc_freq[t] += 1
    idf = {t: math.log((N + 1) / (df + 1)) for t, df in doc_freq.items()}

    # TF-IDF 向量（稀疏字典）
    vectors = []
    for tokens in tokenized:
        tf = Counter(tokens)
        total = len(tokens)
        vec = {t: (cnt / total) * idf.get(t, 0) for t, cnt in tf.items()}
        vectors.append(vec)

    return vectors, idf

def cosine_similarity(v1: dict, v2: dict) -> float:
    common = set(v1) & set(v2)
    if not common:
        return 0.0
    dot    = sum(v1[k] * v2[k] for k in common)
    norm1  = math.sqrt(sum(x**2 for x in v1.values()))
    norm2  = math.sqrt(sum(x**2 for x in v2.values()))
    return dot / (norm1 * norm2 + 1e-9)

def query_similar(query: str, corpus: list[str], vectors: list[dict],
                  idf: dict, top_k=5) -> list[tuple[int, float]]:
    q_vec = {}
    tokens = tokenize_poem(query)
    tf = Counter(tokens)
    for t, cnt in tf.items():
        q_vec[t] = (cnt / len(tokens)) * idf.get(t, 0)
    scores = [(i, cosine_similarity(q_vec, v)) for i, v in enumerate(vectors)]
    return sorted(scores, key=lambda x: -x[1])[:top_k]
```

### 中文文本常见坑

- `len("汉字")` 在 Python 3 返回 2（字符数），不是字节数；字节数用 `len("汉字".encode("utf-8"))` = 6
- 繁体/简体转换：`pip install opencc-python-reimplemented`，`opencc.convert(text, config="t2s.json")`
- 全角/半角：数字、字母可能是全角（`１２３` vs `123`），比较前先 `unicodedata.normalize("NFKC", text)`
- 古诗词标点：顿号 `、`、句号 `。`、逗号 `，` 是全角，分词前通常需要去除

---

## 17. 农历与中国节假日

### 农历计算

```bash
pip install lunardate      # 轻量，纯 Python，支持 1900-2100
pip install ephem          # 天文计算，可精确计算节气
```

```python
from lunardate import LunarDate
from datetime import date

# 公历 -> 农历
today = date.today()
lunar = LunarDate.fromSolarDate(today.year, today.month, today.day)
print(f"农历 {lunar.year}年 {lunar.month}月 {lunar.day}日")
print(f"生肖：{lunar.animal}")   # 鼠牛虎兔龙蛇马羊猴鸡狗猪

# 农历 -> 公历
solar = LunarDate(2025, 1, 1).toSolarDate()   # 2025年春节

# 近年春节公历日期（硬编码更可靠）
SPRING_FESTIVAL = {
    2024: date(2024, 2, 10),
    2025: date(2025, 1, 29),
    2026: date(2026, 2, 17),
    2027: date(2027, 2,  6),
    2028: date(2028, 1, 26),
    2029: date(2029, 2, 13),
    2030: date(2030, 2,  3),
}

# 二十四节气名
SOLAR_TERMS = ["小寒","大寒","立春","雨水","惊蛰","春分",
               "清明","谷雨","立夏","小满","芒种","夏至",
               "小暑","大暑","立秋","处暑","白露","秋分",
               "寒露","霜降","立冬","小雪","大雪","冬至"]
```

### 法定节假日 API

```python
# 推荐：timor.tools 免费节假日 API（无需 key）
import httpx

def is_holiday(date_str: str) -> bool:
    """date_str: YYYY-MM-DD"""
    url = f"https://timor.tech/api/holiday/info/{date_str}"
    r = httpx.get(url, timeout=5)
    data = r.json()
    # type: 0=工作日 1=周末 2=节假日 3=调休补班
    return data["type"]["type"] in (1, 2)

# 获取某年全部节假日安排
def get_holiday_list(year: int) -> dict:
    url = f"https://timor.tech/api/holiday/year/{year}"
    return httpx.get(url, timeout=10).json()
```

### 常见坑

- 法定假日调休：国庆/春节前后常有"调休"工作日，不能简单用周六日判断休息日
- 农历闰月：某些年份有闰月（如闰四月），`lunardate` 会正确处理，手动计算容易出错
- 生肖/干支年：以春节（正月初一）为界，不是以公历1月1日为界

---

## 18. 个人所得税阶梯计算

### 税率表（综合所得，2024年现行）

```python
# 综合所得年度税率表（适用于工资薪金、劳务报酬、稿酬、特许权使用费）
# 应纳税所得额 = 年收入 - 6万元基本减除费用 - 专项扣除 - 专项附加扣除 - 其他扣除
IIT_BRACKETS = [
    # (年应纳税所得额上限, 税率, 速算扣除数)
    (36_000,    0.03,     0),
    (144_000,   0.10,  2_520),
    (300_000,   0.20, 16_920),
    (420_000,   0.25, 31_920),
    (660_000,   0.30, 52_920),
    (960_000,   0.35, 85_920),
    (float("inf"), 0.45, 181_920),
]

def calc_annual_iit(taxable_income: float) -> float:
    """
    计算综合所得年度应纳税额
    taxable_income: 年应纳税所得额（已减去各项扣除后）
    """
    if taxable_income <= 0:
        return 0.0
    for upper, rate, quick_deduction in IIT_BRACKETS:
        if taxable_income <= upper:
            return round(taxable_income * rate - quick_deduction, 2)
    return 0.0  # 不会到达此处
```

### 月度预扣预缴（累计预扣法，企业HR系统常用）

```python
def calc_monthly_withholding(
    cumulative_income: float,      # 本年累计收入
    cumulative_deductions: float,  # 本年累计专项扣除+附加扣除
    prev_tax_withheld: float,      # 本年已预缴税额
    months_elapsed: int,           # 已过月份数（含本月）
) -> float:
    """
    累计预扣法：每月发工资时企业预扣的税额
    基本减除费用：5000元/月 = 60000元/年
    """
    basic_deduction = 5_000 * months_elapsed
    cumulative_taxable = max(0, cumulative_income - basic_deduction - cumulative_deductions)
    cumulative_tax = calc_annual_iit(cumulative_taxable)
    this_month_tax = max(0, cumulative_tax - prev_tax_withheld)
    return round(this_month_tax, 2)
```

### 专项附加扣除（2024年标准）

```python
SPECIAL_ADDITIONAL_DEDUCTIONS = {
    "子女教育":     2_000,   # 元/月/子女（2023年起从1000提至2000）
    "继续教育":       400,   # 元/月（学历教育），技能证书 3600元/年
    "大病医疗":   None,      # 据实扣除，年上限80000元，次年汇算时扣
    "住房贷款利息": 1_000,   # 元/月，首套房，最长240个月
    "住房租金_一线": 1_500,  # 元/月（北京/上海/广州/深圳）
    "住房租金_二线": 1_100,  # 元/月（省会及其他直辖市）
    "住房租金_其他":   800,  # 元/月
    "赡养老人":     3_000,   # 元/月（独生子女），非独生子女分摊不超3000
    "3岁以下婴幼儿照护": 2_000,  # 元/月/子女（2022年新增）
}
```

### 年终奖单独计税（可选优惠政策，2027年12月31日前有效）

```python
# 年终奖单独计税：奖金/12 对应月税率，全额适用该税率
BONUS_BRACKETS = [
    (3_000,    0.03,     0),
    (12_000,   0.10,   210),
    (25_000,   0.20,  1410),
    (35_000,   0.25,  2660),
    (55_000,   0.30,  4410),
    (80_000,   0.35,  7160),
    (float("inf"), 0.45, 15_160),
]

def calc_bonus_tax(bonus: float) -> float:
    """年终奖单独计税（适用条件：全年只能用一次）"""
    monthly = bonus / 12
    for upper, rate, quick_deduction in BONUS_BRACKETS:
        if monthly <= upper:
            return round(bonus * rate - quick_deduction, 2)
    return 0.0

# 注意：存在"多发少得"的临界区间，需规避
# 例：奖金36001元比36000元实际到手更少
BONUS_CLIFF_ZONES = [
    (36_000, 36_000 * 0.10 - 210),   # 跨入10%档
    (144_000, 144_000 * 0.20 - 1410),
    (300_000, 300_000 * 0.25 - 2660),
    (420_000, 420_000 * 0.30 - 4410),
    (660_000, 660_000 * 0.35 - 7160),
    (960_000, 960_000 * 0.45 - 15_160),
]
```

### 社保公积金（一线城市参考，各地比例不同）

```python
# 上海 2024 年参考比例（个人缴纳部分）
SOCIAL_INSURANCE_EMPLOYEE = {
    "养老保险": 0.08,
    "医疗保险": 0.02,
    "失业保险": 0.005,
    # 工伤/生育险：个人不缴纳
}
HOUSING_FUND_RATE = 0.07  # 公积金，5%-12% 各地自定，此为上海最低档

def calc_monthly_social_insurance(gross_salary: float,
                                   base: float = None) -> dict:
    """
    base: 缴费基数（不传则以 gross_salary 为基数）
          实际需在当地上下限之间，超上限按上限，低于下限按下限
    """
    b = base or gross_salary
    result = {k: round(b * r, 2) for k, r in SOCIAL_INSURANCE_EMPLOYEE.items()}
    result["住房公积金"] = round(b * HOUSING_FUND_RATE, 2)
    result["合计"] = round(sum(result.values()), 2)
    return result
```

### 完整税后到手计算

```python
def calc_take_home(gross_monthly: float,
                   special_additional_monthly: float = 0,
                   prev_months_data: list = None) -> dict:
    """
    gross_monthly: 税前月薪
    special_additional_monthly: 本月专项附加扣除合计
    prev_months_data: 前N月的 [gross, special_additional] 列表，用于累计预扣法
    """
    si = calc_monthly_social_insurance(gross_monthly)
    si_total = si["合计"]

    # 累计数据
    prev = prev_months_data or []
    cum_income     = sum(m[0] - calc_monthly_social_insurance(m[0])["合计"] for m in prev) + (gross_monthly - si_total)
    cum_additional = sum(m[1] for m in prev) + special_additional_monthly
    prev_tax       = sum(m[2] for m in prev) if prev and len(prev[0]) > 2 else 0
    months         = len(prev) + 1

    iit = calc_monthly_withholding(cum_income, cum_additional, prev_tax, months)

    return {
        "税前":       gross_monthly,
        "社保公积金": si_total,
        "个税":       iit,
        "税后到手":   round(gross_monthly - si_total - iit, 2),
        "有效税率":   f"{iit / gross_monthly * 100:.1f}%",
    }
```

### 常见坑

- 个税按**自然年度**累计，1月税少、12月税多（累计预扣法效应），年终汇算清缴多退少补
- 劳务报酬预扣税率：800元以下免税，800-4000元扣800后×20%，4000元以上×(1-20%)后×20%，与工资薪金税率表**不同**
- 稿酬所得：预扣时按应纳税所得额×70%计入综合所得
- 年终奖"临界值陷阱"需在HR系统中做提示，避免员工实际少拿

---

## 19. 中国互联网核心法规速查

### 必须遵守的核心法规

| 法规名称 | 施行时间 | 核心约束 | 适用场景 |
|------|------|------|------|
| 《网络安全法》 | 2017-06 | 数据本地化、网络实名制、等保 | 所有互联网产品 |
| 《数据安全法》 | 2021-09 | 数据分类分级、重要数据出境限制 | 数据处理业务 |
| 《个人信息保护法（PIPL）》 | 2021-11 | 知情同意、最小必要、跨境传输 | 收集用户信息 |
| 《网络信息内容生态治理规定》 | 2020-03 | 内容审核义务、禁止信息列表 | UGC平台 |
| 《互联网信息服务算法推荐管理规定》 | 2022-03 | 算法备案、禁止利用算法操纵 | 推荐系统 |
| 《互联网信息服务深度合成管理规定》 | 2023-01 | AI生成内容标识、备案 | AIGC产品 |
| 《生成式人工智能服务管理暂行办法》 | 2023-08 | AIGC备案、内容安全 | AI对话/生成产品 |
| 《网络数据安全管理条例》 | 2025-01 | 细化数据分类标准、境外提供数据 | 数据出海 |

### 个人信息保护法（PIPL）开发合规要点

```
必须做到：
1. 隐私政策：首次收集前展示，用户主动同意（不得预勾选）
2. 最小必要原则：只收集实现功能必需的信息，拒绝授权不得拒绝提供基本服务
3. 单独同意：敏感信息（生物识别、位置、健康、金融、未成年人）需单独弹窗授权
4. 用户权利：须提供查询、复制、更正、删除、注销账号的入口（通常在"设置-账号安全"）
5. 数据跨境：向境外提供个人信息需通过安全评估/标准合同/认证之一

敏感个人信息（需单独同意）：
- 生物识别（人脸、指纹、声纹）
- 宗教信仰、特定身份
- 医疗健康
- 金融账户
- 行踪轨迹
- 不满14周岁未成年人信息
```

### 等保（网络安全等级保护）

```
等级划分：
- 一级：一般系统，自主保护
- 二级：重要系统，需备案 + 年度自查（大多数商业App需达到）
- 三级：重要信息系统，需备案 + 年度测评（金融/医疗/政务系统）
- 四/五级：涉及国家安全，不对外公开

二级常见技术要求（开发侧）：
□ 用户鉴别：密码复杂度要求，失败锁定（≥6位，连续失败5次锁定）
□ 最小权限：账号权限分离，禁止共用超级账号
□ 审计日志：用户操作、管理操作日志留存≥6个月
□ 通信加密：全程 HTTPS，禁止 HTTP 明文传输敏感信息
□ 数据备份：重要数据异地备份
```

### ICP 备案与许可证

```
必须备案/许可的情形：

ICP备案（工信部）：
- 面向中国大陆用户的网站/App → 必须备案，未备案域名被屏蔽
- 备案主体：企业或个人，需实名
- 时间：通常15-20个工作日

增值电信业务许可证（ICP证）：
- 提供信息服务（内容平台、社区、搜索）→ 需ICP证
- 提供网络接入→ 需ISP证

专项许可（按业务类型）：
- 在线教育：网络出版服务许可证（新闻出版总署）
- 直播/短视频：《信息网络传播视听节目许可证》（广电总局）
- 新闻资讯：互联网新闻信息服务许可证（网信办）
- 金融/支付：支付业务许可证（央行）/ 网络小贷牌照
- 医疗健康：互联网医疗许可（卫健委）
- 地图导航：测绘资质证书（自然资源部）
```

### AIGC 产品合规要点（2023年起）

```
生成式AI服务需做到：
1. 备案：在网信办完成算法备案（算法推荐/深度合成/生成式AI三类）
2. 内容标识：AI生成的图片/视频/音频需加水印或元数据标识
3. 训练数据：使用有合法来源的训练数据，不得侵犯知识产权
4. 禁止生成内容：颠覆政权、恐怖主义、歧视、色情、虚假信息
5. 用户实名：提供服务需核验用户真实身份

AIGC 水印推荐实现：
- 图片：隐写水印（不可见）+ 右下角可见标识"AI生成"
- 视频：每帧元数据注入 + 片尾字幕
```

### 未成年人保护（重点）

```python
# 相关法规：《未成年人网络保护条例》（2024-01施行）

MINOR_RULES = {
    "实名认证": "必须核验真实年龄，不得允许未成年人注册成年账号",
    "游戏时长限制": {
        "工作日": "1.5小时/天",
        "节假日": "3小时/天",
        "禁止时段": "22:00-08:00",
    },
    "消费限制": {
        "8岁以下": "不得提供付费服务",
        "8-16岁": "单次≤50元，每月≤200元",
        "16-18岁": "单次≤100元，每月≤400元",
    },
    "内容分级": "须对内容分级，向未成年人屏蔽不适宜内容",
    "青少年模式": "App须提供青少年模式，该模式下限制功能和时长",
}
```

### 数据跨境传输合规路径

```
三种合法路径（满足一种即可）：

1. 安全评估（数据量大/重要数据必须走此路径）：
   - 向境外提供重要数据
   - 处理100万人以上个人信息的处理者向境外提供
   - 累计向境外提供10万人以上个人信息
   申请机构：国家互联网信息办公室

2. 个人信息保护认证：
   - 由专业机构（CCRC等）认证
   - 适合集团内部跨境数据流动

3. 标准合同（SCCs）：
   - 与境外接收方签署网信办发布的标准合同
   - 适合中小企业、数据量不大的场景
   - 需向省级网信部门备案

注意：不满足以上任一路径，不得向境外提供个人信息
```

### 禁止/限制内容清单（开发内容审核时参考）

```python
# 《网络信息内容生态治理规定》第六条 — 禁止发布
FORBIDDEN_CONTENT = [
    "危害国家安全、荣誉和利益",
    "煽动颠覆国家政权、推翻社会主义制度",
    "宣扬恐怖主义、极端主义",
    "宣扬民族仇恨、民族歧视",
    "传播暴力、淫秽色情信息",
    "散布谣言、虚假信息",
    "侵害他人名誉、隐私、知识产权",
]

# 第七条 — 不得生产、复制、发布（负面清单）
DISCOURAGED_CONTENT = [
    "使用夸张标题，内容与标题严重不符",
    "炒作绯闻、丑闻、劣迹",
    "不当评述自然灾害、重大事故等灾难",
    "带有性暗示、性挑逗的低俗内容",
    "利用未成年人牟利的",
    "宣扬八卦、低俗、炫富",
]
```

### 常见合规坑

- **隐私政策必须可点击**：App 首次启动时隐私弹窗内的"隐私政策"必须是可跳转链接，纯文字描述不合规
- **权限申请时机**：不得在启动时批量申请所有权限，必须在用到该功能时才申请对应权限
- **账号注销**：必须提供注销功能，注销后15天内完成数据删除（不得仅做逻辑删除后长期保留）
- **Cookie 弹窗**：境内产品通常不需要 GDPR 式 Cookie 弹窗，但 PIPL 要求对 Cookie 等自动化手段收集信息告知用户
- **境外 SDK 合规**：集成 Firebase/Admob/AppsFlyer 等境外 SDK 时，需评估其数据收集是否合规，部分SDK可能将数据传至境外
- **实名制**：游戏/直播/社区类 App 必须后台核验真实身份（对接公安网或第三方实名服务），不能仅靠用户自填

---

## 20. 中国手机号段与运营商识别

### 号段总表

```python
# 中国手机号：11位，1开头，第2位3-9
# 号段会随工信部分配持续新增，以下为截至目前的主要号段

CARRIER_SEGMENTS = {
    "中国移动": {
        "常规": ["134","135","136","137","138","139",
                 "150","151","152","157","158","159",
                 "178","182","183","184","187","188",
                 "195","197","198"],
        "虚拟运营商": ["165","1703","1705","1706"],
        "物联网": ["1440","148","1847"],
    },
    "中国联通": {
        "常规": ["130","131","132","155","156",
                 "175","176","185","186","196"],
        "虚拟运营商": ["167","1704","1707","1708","1709","171"],
        "物联网": ["1460","146"],
    },
    "中国电信": {
        "常规": ["133","149","153","173","174",
                 "177","180","181","189","190","191","193","199"],
        "虚拟运营商": ["162","1700","1701","1702"],
        "物联网": ["1410","141"],
    },
    "中国广电": {
        "常规": ["192"],
    },
}
```

### 运营商识别函数

```python
import re

def identify_carrier(phone: str) -> dict:
    """识别手机号运营商和号段类型

    Returns:
        {"carrier": "中国移动", "type": "常规", "valid": True}
        或 {"carrier": "未知", "type": "", "valid": False}
    """
    phone = phone.strip().replace(" ", "").replace("-", "")

    # 去掉国际区号前缀
    if phone.startswith("+86"):
        phone = phone[3:]
    elif phone.startswith("86") and len(phone) == 13:
        phone = phone[2:]

    if not re.match(r'^1[3-9]\d{9}$', phone):
        return {"carrier": "未知", "type": "", "valid": False}

    for carrier, segments in CARRIER_SEGMENTS.items():
        for seg_type, prefixes in segments.items():
            for prefix in prefixes:
                if phone.startswith(prefix):
                    return {"carrier": carrier, "type": seg_type, "valid": True}

    return {"carrier": "未知（号段未收录）", "type": "", "valid": True}


# 批量识别示例
def batch_identify(phones: list[str]) -> dict:
    """统计一批手机号的运营商分布"""
    from collections import Counter
    results = [identify_carrier(p) for p in phones]
    carrier_dist = Counter(r["carrier"] for r in results if r["valid"])
    type_dist = Counter(r["type"] for r in results if r["valid"])
    invalid = sum(1 for r in results if not r["valid"])
    return {
        "total": len(phones),
        "invalid": invalid,
        "carrier_distribution": dict(carrier_dist),
        "type_distribution": dict(type_dist),
    }
```

### 精确号段正则（比简单 `1[3-9]` 更准确）

```python
# 按运营商分组的正则（用于表单验证、短信通道选择等）
MOBILE_RE  = r'^1(?:3[4-9]|5[0-27-9]|7[8]|8[2-478]|9[578]|65)\d{8}$'
UNICOM_RE  = r'^1(?:3[0-2]|5[56]|7[56]|8[56]|96|67|71)\d{8}$'
TELECOM_RE = r'^1(?:33|49|53|7[347]|8[019]|9[01399]|62)\d{8}$'
BROADNET_RE= r'^192\d{8}$'

# 宽松验证（推荐，兼容未来新号段）
PHONE_LOOSE_RE = r'^1[3-9]\d{9}$'

# 严格验证（精确到3位前缀，需定期更新）
PHONE_STRICT_RE = r'^1(?:3\d|4[014-9]|5[0-35-9]|6[2567]|7[0-8]|8[0-9]|9[0-35-9])\d{8}$'
```

### 虚拟运营商与物联网卡识别

```python
def is_virtual_carrier(phone: str) -> bool:
    """判断是否虚拟运营商号码（常用于风控拦截）"""
    virtual_prefixes = [
        "162","165","167","170","171",
        "1700","1701","1702","1703","1704","1705","1706","1707","1708","1709",
    ]
    phone = phone.lstrip("+86").lstrip("86")
    return any(phone.startswith(p) for p in virtual_prefixes)


def is_iot_card(phone: str) -> bool:
    """判断是否物联网卡（不能收短信验证码）"""
    iot_prefixes = ["1440","1410","1460","141","146","148","1847","149"]
    phone = phone.lstrip("+86").lstrip("86")
    return any(phone.startswith(p) for p in iot_prefixes)
```

### 常见坑

- **虚拟运营商号段**：170/171 等号段被大量用于诈骗/垃圾短信，部分平台风控会拦截，注册场景慎重对待
- **物联网卡**：144/146/148 等号段是物联网卡，无法接收短信验证码，不能用于用户注册
- **携号转网**：号段不再严格对应运营商，精确判断需调用运营商 API 或第三方服务（如聚合数据、阿里云号码百科）
- **新号段**：工信部持续分配新号段，硬编码号段表需定期更新，宽松正则 `1[3-9]` 更稳妥
- **国际格式**：`+8613812345678` 或 `008613812345678`，存储建议统一去掉前缀存 11 位
- **短信通道**：不同运营商的短信通道费率不同，批量发送前可按运营商分组走不同通道

---

## 21. 麻将番数计算（国标 / 各地方言规则）

### 国标麻将（GB/T 标准，81 番种）

```python
"""
国标麻将（中国体育总局竞赛规则）：
- 基础分 8 番起和
- 81 种番种，分 1~88 番
- 不计原则：高番包含低番时，低番不重复计
"""

# ── 牌面表示 ──────────────────────────────────────────────────────

# 万(m) 条/索(s) 饼/筒(p) 字牌(z)
# 1m~9m  1s~9s  1p~9p  1z~7z(东南西北中发白)
# 示例手牌: ["1m","2m","3m","4s","5s","6s","7p","8p","9p","1z","1z","1z","2z","2z"]

WINDS  = {"1z":"东","2z":"南","3z":"西","4z":"北"}
DRAGONS= {"5z":"中","6z":"发","7z":"白"}
HONORS = {**WINDS, **DRAGONS}

SUIT_NAMES = {"m": "万", "s": "条", "p": "饼"}


def parse_hand(hand_str: str) -> list[str]:
    """解析简写手牌: '123m456s789p111z' → ['1m','2m','3m',...]"""
    tiles = []
    nums = []
    for ch in hand_str:
        if ch.isdigit():
            nums.append(ch)
        elif ch in ('m', 's', 'p', 'z'):
            tiles.extend(f"{n}{ch}" for n in nums)
            nums = []
    return tiles


# ── 基础判定工具 ─────────────────────────────────────────────────

def is_honor(tile: str) -> bool:
    return tile.endswith('z')

def is_terminal(tile: str) -> bool:
    """是否幺九牌（1或9的数牌 + 字牌）"""
    return is_honor(tile) or tile[0] in ('1', '9')

def is_simple(tile: str) -> bool:
    """是否中张（2-8的数牌）"""
    return not is_honor(tile) and tile[0] in '2345678'

def tile_suit(tile: str) -> str:
    return tile[-1]

def tile_num(tile: str) -> int:
    return int(tile[0]) if not is_honor(tile) else 0


def group_by_suit(tiles: list[str]) -> dict[str, list[int]]:
    """按花色分组，返回 {'m': [1,2,3], 's': [4,5,6], ...}"""
    groups: dict[str, list[int]] = {}
    for t in tiles:
        s = tile_suit(t)
        groups.setdefault(s, []).append(tile_num(t) if s != 'z' else int(t[0]))
    for v in groups.values():
        v.sort()
    return groups
```

### 国标番种表（核心番种）

```python
# 番种定义（部分核心番种，完整版 81 种）
# 格式: (番数, 名称, 判定函数名, 说明)

GUOBIAO_FAN_TABLE = [
    # ── 88 番 ──
    (88, "大四喜",     "四个风牌刻子/杠"),
    (88, "大三元",     "中发白三组刻子/杠"),
    (88, "绿一色",     "仅由 23468s + 发 组成"),
    (88, "九莲宝灯",   "同花色 1112345678999 + 任意同花色"),
    (88, "四杠",       "4个杠"),
    (88, "连七对",     "同花色连续7个对子"),
    (88, "十三幺",     "13种幺九各一张 + 任一幺九做将"),

    # ── 64 番 ──
    (64, "清幺九",     "全由幺九牌(19+字)的刻子和将组成"),
    (64, "小四喜",     "三组风牌刻子 + 一组风牌做将"),
    (64, "小三元",     "两组箭牌刻子 + 一组箭牌做将"),
    (64, "字一色",     "全由字牌组成"),
    (64, "四暗刻",     "4组暗刻（不含明刻和杠）"),
    (64, "一色双龙会", "同花色 123+789 各两组 + 5做将"),

    # ── 48 番 ──
    (48, "一色四同顺", "同花色同一顺子4组"),
    (48, "一色四节高", "同花色4组依次递增的刻子"),

    # ── 32 番 ──
    (32, "一色四步高", "同花色4组步长相同的顺子"),
    (32, "三杠",       "3个杠"),
    (32, "混幺九",     "全由幺九牌组成（含顺子中的19）"),

    # ── 24 番 ──
    (24, "七对",       "7个对子"),
    (24, "七星不靠",   "东南西北中发白各一 + 三花色不靠"),
    (24, "全双刻",     "所有刻子和将均为偶数牌"),
    (24, "清一色",     "同一花色数牌"),
    (24, "一色三同顺", "同花色同一顺子3组"),
    (24, "一色三节高", "同花色3组依次递增的刻子"),
    (24, "全大",       "全由789数牌组成"),
    (24, "全中",       "全由456数牌组成"),
    (24, "全小",       "全由123数牌组成"),

    # ── 16 番 ──
    (16, "清龙",       "同花色 123+456+789"),
    (16, "一色三步高", "同花色3组步长相同的顺子"),
    (16, "三暗刻",     "3组暗刻"),
    (16, "天听",       "庄家第一巡即报听"),

    # ── 12 番 ──
    (12, "大于五",     "所有数牌 >= 6"),
    (12, "小于五",     "所有数牌 <= 4"),
    (12, "三风刻",     "3组风牌刻子"),

    # ── 8 番 ──
    (8,  "妙手回春", "摸最后一张牌自摸和"),
    (8,  "海底捞月", "吃最后一张打出的牌和"),
    (8,  "杠上开花", "开杠后补摸的牌自摸和"),
    (8,  "抢杠和",   "他家加杠时抢和"),
    (8,  "混一色",   "一种花色数牌 + 字牌"),

    # ── 6 番 ──
    (6,  "碰碰和",   "4组刻子/杠 + 将"),
    (6,  "全求人",   "全靠吃碰明杠，单钓他家"),
    (6,  "五门齐",   "万条饼风箭五种都有"),
    (6,  "双暗杠",   "2个暗杠"),
    (6,  "双箭刻",   "2组箭牌（中发白）刻子"),

    # ── 4 番 ──
    (4,  "全带幺",   "每组面子和将都含幺九牌"),
    (4,  "不求人",   "没有吃碰明杠，自摸和"),
    (4,  "双明杠",   "2个明杠"),
    (4,  "和绝张",   "和牌是该牌的最后一张"),

    # ── 2 番 ──
    (2,  "箭刻",     "中/发/白的刻子"),
    (2,  "门风刻",   "自己门风的刻子"),
    (2,  "圈风刻",   "当前圈风的刻子"),
    (2,  "平和",     "4组顺子 + 数牌做将，不含字牌"),
    (2,  "四归一",   "4张相同牌分在不同面子和将中"),
    (2,  "断幺",     "没有幺九牌（全是中张）"),
    (2,  "双暗刻",   "2组暗刻"),
    (2,  "暗杠",     "1个暗杠"),

    # ── 1 番 ──
    (1,  "一般高",   "同花色两组相同顺子"),
    (1,  "连六",     "同花色两组相连顺子 (123+456 或 456+789)"),
    (1,  "老少副",   "同花色 123+789"),
    (1,  "幺九刻",   "含19的刻子或字牌刻子"),
    (1,  "明杠",     "1个明杠"),
    (1,  "边张",     "和 12X 的3 或 X89 的7"),
    (1,  "坎张",     "和 X_X 中间那张"),
    (1,  "单钓将",   "只差将牌"),
    (1,  "自摸",     "自己摸牌和"),
]

def lookup_fan(name: str) -> int:
    """查询番种的番数"""
    for fan, n, _ in GUOBIAO_FAN_TABLE:
        if n == name:
            return fan
    return 0
```

### 和牌拆解（通用算法骨架）

```python
from collections import Counter
from itertools import combinations

def can_win(tiles: list[str]) -> bool:
    """判断14张牌是否能和（3n+2结构 或 七对 或 十三幺）"""
    if len(tiles) != 14:
        return False
    return _check_regular(tiles) or _check_seven_pairs(tiles) or _check_thirteen_orphans(tiles)


def _check_seven_pairs(tiles: list[str]) -> bool:
    cnt = Counter(tiles)
    return len(cnt) == 7 and all(v == 2 for v in cnt.values())


def _check_thirteen_orphans(tiles: list[str]) -> bool:
    required = {"1m","9m","1s","9s","1p","9p","1z","2z","3z","4z","5z","6z","7z"}
    hand_set = set(tiles)
    if not required.issubset(hand_set):
        return False
    cnt = Counter(tiles)
    return any(cnt[t] >= 2 for t in required)


def _check_regular(tiles: list[str]) -> bool:
    """标准和牌：4组面子(顺子/刻子) + 1对将"""
    cnt = Counter(tiles)
    # 尝试每种牌做将
    for pair_tile in set(tiles):
        if cnt[pair_tile] < 2:
            continue
        remaining = list(tiles)
        remaining.remove(pair_tile)
        remaining.remove(pair_tile)
        if _extract_melds(Counter(remaining)):
            return True
    return False


def _extract_melds(cnt: Counter) -> bool:
    """递归拆面子（刻子优先尝试+顺子优先尝试，取并集）"""
    if sum(cnt.values()) == 0:
        return True

    # 取第一张未处理的牌
    tile = min((t for t in cnt if cnt[t] > 0),
               key=lambda t: (t[-1], t[0]))

    # 尝试刻子
    if cnt[tile] >= 3:
        cnt[tile] -= 3
        if _extract_melds(cnt):
            cnt[tile] += 3
            return True
        cnt[tile] += 3

    # 尝试顺子（仅数牌）
    if not is_honor(tile):
        suit = tile_suit(tile)
        num = tile_num(tile)
        t2 = f"{num+1}{suit}"
        t3 = f"{num+2}{suit}"
        if num <= 7 and cnt.get(t2, 0) > 0 and cnt.get(t3, 0) > 0:
            cnt[tile] -= 1
            cnt[t2] -= 1
            cnt[t3] -= 1
            if _extract_melds(cnt):
                cnt[tile] += 1
                cnt[t2] += 1
                cnt[t3] += 1
                return True
            cnt[tile] += 1
            cnt[t2] += 1
            cnt[t3] += 1

    return False
```

### 各地方言规则速查

```python
# 中国各地麻将规则差异巨大，以下为常见地方规则的核心差异

LOCAL_RULES = {
    "四川麻将（血战到底）": {
        "牌数": "108张（去掉字牌，只有万条饼）",
        "核心规则": [
            "缺一门：必须打掉一个花色才能和",
            "血战到底：一人和牌后剩余玩家继续打",
            "自摸加底：自摸额外加底分",
            "刮风下雨：明杠（刮风）点杠者付，暗杠（下雨）三家付",
            "查花猪：结束时没有缺一门的罚分",
            "查大叫：结束时没有听牌的罚分",
        ],
        "常见番种": {
            "根": "手中有4张相同牌（每根翻一倍）",
            "清一色": "同一花色，翻倍",
            "对对胡/碰碰和": "全刻子，翻倍",
            "金钩钓": "4组刻子+单钓，大番",
            "十八罗汉": "4杠+单钓",
            "清龙": "同花色123+456+789",
        },
        "计分": "底分 × 2^(番数) ，自摸三家付，点炮点炮者付",
    },

    "广东麻将（推倒和/鸡平和）": {
        "牌数": "136张（含字牌，部分玩法含花牌144张）",
        "核心规则": [
            "推倒和：无番数限制，能和就和",
            "鸡平和：最小和牌形式，底分",
            "爆和（自摸）：自摸翻倍",
            "抢杠和：他家加杠时可和",
            "一炮多响：多人同时和，放炮者都赔",
        ],
        "常见番种": {
            "平和": "基础和牌",
            "自摸": "翻倍",
            "清一色": "大番",
            "混一色": "中番",
            "对对和": "中番",
            "大三元/小三元": "大番",
            "十三幺": "最大番",
        },
    },

    "杭州麻将": {
        "牌数": "136张（含字牌）",
        "核心规则": [
            "财神（百搭）：翻开的牌的下一张为财神（万能替代）",
            "爆头/爆杠：杠上开花特殊计分",
            "边卡钓：边张、坎张、单钓加分",
            "包三家：某些大牌型由特定玩家包赔",
        ],
    },

    "武汉麻将（开口翻）": {
        "牌数": "108张（去字牌）+ 部分含赖子",
        "核心规则": [
            "开口翻：每吃/碰/杠一次底分翻一倍",
            "赖子：每局翻出一张赖子（万能牌）",
            "红中赖子杠：红中当赖子时的特殊规则",
        ],
    },

    "长沙麻将": {
        "牌数": "108张（去字牌）",
        "核心规则": [
            "需缺一门",
            "小胡可以不和（放弃小胡追大胡）",
            "六六顺：6对以上特殊牌型",
            "节节高：连续递增的刻子",
        ],
    },

    "东北麻将": {
        "牌数": "136张（含字牌）",
        "核心规则": [
            "宝牌：每局翻宝，持有宝牌加番",
            "夹（坎张）：额外加番",
            "飘：底分倍数的额外约定",
            "手把一：手中只剩一张牌时和",
        ],
    },
}
```

### 麻将番数计算器骨架

```python
def calc_fan_guobiao(
    hand: list[str],
    melds: list[dict] = None,
    win_tile: str = "",
    is_self_draw: bool = False,
    seat_wind: str = "1z",
    round_wind: str = "1z",
) -> dict:
    """国标麻将番数计算骨架

    Args:
        hand: 暗手牌列表
        melds: 明牌面子 [{"type":"chi/pon/kan","tiles":[...]}, ...]
        win_tile: 和的那张牌
        is_self_draw: 是否自摸
        seat_wind: 门风 (1z东 2z南 3z西 4z北)
        round_wind: 圈风

    Returns:
        {"total_fan": 总番数, "fan_list": [(番数,番名), ...], "valid": 是否满8番}
    """
    melds = melds or []
    all_tiles = hand + [t for m in melds for t in m["tiles"]]

    fan_list = []

    # ── 自摸 ──
    if is_self_draw:
        fan_list.append((1, "自摸"))

    # ── 风牌刻判定 ──
    pon_tiles = _get_pon_tiles(hand, melds)
    for pt in pon_tiles:
        if pt == seat_wind:
            fan_list.append((2, "门风刻"))
        if pt == round_wind:
            fan_list.append((2, "圈风刻"))
        if pt in DRAGONS:
            fan_list.append((2, "箭刻"))

    # ── 和牌方式 ──
    if win_tile:
        wait_type = _classify_wait(hand, win_tile)
        if wait_type == "edge":
            fan_list.append((1, "边张"))
        elif wait_type == "middle":
            fan_list.append((1, "坎张"))
        elif wait_type == "single":
            fan_list.append((1, "单钓将"))

    # ── 断幺 ──
    if all(is_simple(t) for t in all_tiles):
        fan_list.append((2, "断幺"))

    # ── 平和 ──
    if _is_pinhu(hand, melds):
        fan_list.append((2, "平和"))

    # ── 清一色 / 混一色 ──
    suits = set(tile_suit(t) for t in all_tiles)
    num_suits = suits - {'z'}
    has_honor = 'z' in suits
    if len(num_suits) == 1 and not has_honor:
        fan_list.append((24, "清一色"))
    elif len(num_suits) == 1 and has_honor:
        fan_list.append((8, "混一色"))

    # ── 碰碰和 ──
    if _is_all_pons(hand, melds):
        fan_list.append((6, "碰碰和"))

    # ── 七对 ──
    if _check_seven_pairs(all_tiles):
        fan_list.append((24, "七对"))

    # ── 十三幺 ──
    if _check_thirteen_orphans(all_tiles):
        fan_list.append((88, "十三幺"))

    # ... 其余番种判定按 GUOBIAO_FAN_TABLE 逐项实现

    # ── 不计原则：高番覆盖低番 ──
    fan_list = _apply_exclusion_rules(fan_list)

    total = sum(f for f, _ in fan_list)
    return {
        "total_fan": total,
        "fan_list": fan_list,
        "valid": total >= 8,  # 国标最低 8 番起和
    }


def _get_pon_tiles(hand, melds):
    """提取所有刻子/杠的牌"""
    cnt = Counter(hand)
    pons = [t for t, c in cnt.items() if c >= 3]
    for m in melds:
        if m["type"] in ("pon", "kan"):
            pons.append(m["tiles"][0])
    return pons


def _classify_wait(hand, win_tile):
    """判断听牌形式：边张/坎张/单钓"""
    # 简化版：实际需考虑所有可能的拆法
    return "normal"


def _is_pinhu(hand, melds):
    """判断平和：4顺子+数牌将，无字牌"""
    return False  # 需完整实现


def _is_all_pons(hand, melds):
    """判断碰碰和：全刻子"""
    return False  # 需完整实现


def _apply_exclusion_rules(fan_list):
    """不计原则：高番包含低番时去除低番"""
    # 例：清一色(24) 包含 混一色(8)，不重复计
    EXCLUSIONS = {
        "清一色": {"混一色"},
        "碰碰和": {"双暗刻", "幺九刻"},
        "七对":   {"门前清", "单钓将"},
        "十三幺": {"五门齐", "门前清", "单钓将", "混幺九"},
    }
    names = {n for _, n in fan_list}
    excluded = set()
    for n in names:
        excluded |= EXCLUSIONS.get(n, set())
    return [(f, n) for f, n in fan_list if n not in excluded]
```

### 四川麻将计分示例

```python
def calc_sichuan(
    fan_names: list[str],
    base_score: int = 1,
    is_self_draw: bool = False,
    gen_count: int = 0,
) -> dict:
    """四川麻将（血战到底）计分

    Args:
        fan_names: 番种名称列表（如 ["清一色", "对对胡"]）
        base_score: 底分
        is_self_draw: 是否自摸
        gen_count: 根的数量（4张相同牌的组数）

    Returns:
        {"per_player": 每人付分, "total": 总得分, "breakdown": 明细}
    """
    SICHUAN_FAN = {
        "平胡":   0,  # 基础和牌
        "对对胡": 1,
        "清一色": 1,
        "七对":   1,
        "金钩钓": 2,
        "清对":   2,  # 清一色 + 对对胡
        "将对":   2,  # 全258对对胡
        "清七对": 2,  # 清一色 + 七对
        "龙七对": 2,  # 七对中含一个4张（豪华七对）
        "清龙七对": 3,
        "十八罗汉": 3,
    }

    fan_total = sum(SICHUAN_FAN.get(f, 0) for f in fan_names)
    fan_total += gen_count  # 每根翻一倍

    score = base_score * (2 ** fan_total)

    if is_self_draw:
        return {
            "per_player": score,
            "total": score * 3,
            "breakdown": f"底分{base_score} × 2^{fan_total} = {score}/人 × 3人",
        }
    else:
        return {
            "per_player": score,
            "total": score,
            "breakdown": f"底分{base_score} × 2^{fan_total} = {score}，点炮者付",
        }
```

### 常见坑

- **各地规则差异极大**：开发麻将游戏/计分器前必须确认具体地区规则，不存在"通用麻将"
- **国标 vs 地方**：国标 81 番种，8 番起和；地方规则往往更简单但计分方式不同（翻倍制 vs 累加制）
- **赖子/百搭**：杭州、武汉等地有赖子（万能替代牌），和牌判定需特殊处理
- **一炮多响**：广东等地允许多人同时和同一张牌，服务端需处理并发结算
- **牌墙剩余**：不同规则对"流局"的牌墙剩余张数规定不同（通常留14~20张）
- **花牌**：部分规则含春夏秋冬梅兰竹菊 8 张花牌，摸到即补牌，计分时额外加番
