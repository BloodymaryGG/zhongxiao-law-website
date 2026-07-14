# 北京中晓律师事务所 — 官方网站

## 部署流程

### 1. 买域名
在 https://buy.cloud.tencent.com/domain/cart 挑选域名，付款后会进入备案流程。
备案需要公司主体信息，腾讯云会引导你完成。

### 2. 将代码上传到 GitHub
```bash
cd /Users/cinderella/programs/zhongxiao-law-website
git init
git add .
git commit -m "init: 中晓律师事务所官网"
# 在 GitHub 上新建仓库后执行：
git remote add origin https://github.com/你的用户名/zhongxiao-law-website.git
git push -u origin main
```

### 3. 关联 Cloudflare Pages
1. 注册/登录 [Cloudflare](https://dash.cloudflare.com)
2. 进入 **Pages** → **连接到 Git**
3. 授权 GitHub，选中 `zhongxiao-law-website` 仓库
4. 构建设置：框架 = **无**（纯静态 HTML）
5. 部署！几秒钟后就有 `你的项目.pages.dev` 域名可以访问

### 4. 绑定自定义域名
1. 在 Cloudflare Pages 项目设置 → **自定义域**
2. 输入你在腾讯云买的域名
3. Cloudflare 会自动配置 DNS
4. 等待 SSL 证书下发（几分钟）
5. ✅ 上线！

### 5. 修改内容
需要改文案、联系方式、律师信息时，直接告诉我，我来改代码。
你也可以用任何文本编辑器打开 `index.html` 修改。

### 目录结构
```
└── index.html          # 首页（单页全包含）
└── README.md           # 本文件
```

### 后续可扩展
- 单独的「团队详情」「案例展示」等子页面
- 微信公众号文章自动同步到官网
- 在线咨询表单接入企业微信/邮件通知
- 百度统计/SEO 优化
