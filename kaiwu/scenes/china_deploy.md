# 中国服务器部署场景规范

## 适用场景
在中国大陆服务器（阿里云/腾讯云/华为云）部署应用。

## 关键规范

### 第一步：配置镜像源（必须）
```bash
# pip
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# npm
npm config set registry https://registry.npmmirror.com

# Docker
cat > /etc/docker/daemon.json << 'JSON'
{"registry-mirrors": ["https://docker.mirrors.ustc.edu.cn", "https://hub-mirror.c.163.com"]}
JSON
systemctl daemon-reload && systemctl restart docker
```

### 安全组配置（必须）
部署前在云控制台开放所需端口：
- 80（HTTP）
- 443（HTTPS）  
- 22（SSH，建议改为非标端口）
- 应用端口（如 8000、3000）

### 防火墙配置
```bash
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
ufw enable
```

### HTTPS 证书（必须）
```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d yourdomain.com
# 自动续期
echo "0 0 1 * * certbot renew --quiet" | crontab -
```

### 域名备案
国内服务器部署网站必须备案，否则无法使用80/443端口。
备案期间可先用非标端口测试。

### 进程管理
```bash
# systemd（推荐）
systemctl enable --now myapp.service

# 查看日志
journalctl -u myapp -f
```

### 时区设置
```bash
timedatectl set-timezone Asia/Shanghai
```

### 常见坑
1. 中国服务器无法直接访问 GitHub，需配镜像
2. 新域名解析生效需10分钟到48小时
3. 备案期间不要删服务器，否则重新备案
4. 安全组和防火墙都要开放，两者独立

