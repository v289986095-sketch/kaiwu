# 微信支付场景规范

## 适用场景
微信支付 V3 API 接入，含 JSAPI、Native、H5、小程序支付。

## 关键规范

### 必须使用官方 SDK
```bash
pip install wechatpayv3
```
不要手拼 RSA 签名，极易出错。

### 核心初始化
```python
from wechatpayv3 import WeChatPay, WeChatPayType

wxpay = WeChatPay(
    wechatpay_type=WeChatPayType.MINIPROG,  # 小程序
    mchid='商户号（10位数字）',
    private_key=open('apiclient_key.pem').read(),
    cert_serial_no='证书序列号（40位十六进制）',
    apiv3_key='APIv3密钥（32位）',
    appid='小程序或公众号 appid',
)
```

### 支付类型对应
- JSAPI：公众号网页内支付，需要 openid
- MINIPROG：小程序支付，需要 openid
- NATIVE：PC 扫码支付，返回二维码 URL
- H5：手机浏览器支付，返回跳转 URL

### 必传字段检查
- JSAPI/小程序：必须传 `payer={'openid': user_openid}`
- openid 必须是该 appid 下的 openid，不同 appid 的 openid 不通用
- notify_url 必须是公网 HTTPS 地址，不能用 localhost

### 回调处理
```python
# 验签并解密回调
result = wxpay.decrypt_callback(
    headers=request.headers,
    body=request.body.decode()
)
# 必须返回成功，否则微信会在24小时内重试
return {'code': 'SUCCESS', 'message': '成功'}
```

### 常见坑
1. 证书文件路径用绝对路径，避免工作目录问题
2. 商户号（mchid）是纯数字，不是 appid
3. 退款需要单独的退款 API，不是直接撤销订单
4. 沙箱环境接口和正式接口地址不同

