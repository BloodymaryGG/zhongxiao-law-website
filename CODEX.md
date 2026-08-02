# 北京中晓律师事务所官网 — 项目与部署说明

给 Codex（或任何接手的人）快速上手用。**开始改代码前先读一遍**，特别是「部署方式」和「工作流」两节，避免瞎改。

## 项目现状

- 纯静态 HTML 站：**没有** package.json、没有构建步骤；Cloudflare Pages 框架选「无」
- 本地路径：`/Users/cinderella/programs/zhongxiao-law-website/`
- GitHub 仓库：`BloodymaryGG/zhongxiao-law-website`（git push 即自动部署）
- 线上地址：
  - https://zhongxiao-law-website.pages.dev
  - https://zxlawfirm.cn（腾讯云 .cn 域名，已解析到 Cloudflare；境外托管，未做 ICP 备案，属合规状态）
- 页面：`index.html` / `about.html` / `practice.html` / `team.html` / `articles.html` / `contact.html`，文章在 `articles/*.html`
- 表单：`functions/submit.js` 是 Cloudflare Pages Function（在线咨询 → Resend 发邮件）
  - 依赖环境变量：`RESEND_API_KEY` / `TO_EMAIL` / `FROM_EMAIL`
  - 环境变量在 **Cloudflare 控制台** 配置，**不在代码里**（参考 `.env.example` 的说明）
  - 本地无法直接测试邮件发送，改完要 push 到线上验证

## 部署方式

- 托管：Cloudflare Pages，纯静态 HTML，**无构建步骤**，框架选「无」
- **不要引入 npm / 打包工具 / 构建框架**，保持纯静态
- Cloudflare Pages Function 会自动部署 `functions/` 目录，无需额外配置

## 工作流

1. 改完代码 → `git add` + `git commit`
2. `git push`（推送到 main 分支）
3. Cloudflare Pages 自动构建部署（静态文件 + Functions 直接发布）
4. 打开线上地址确认效果（首页、文章页、表单分别验证）

## 已知待办（未做）

- 首页 5 张「即将上线」资讯卡（`coming-soon`）：文章写好后补页面并换回链接
- 隐私政策页面（表单收集个人信息，按《个人信息保护法》建议补）
- 公共样式抽取（现在每页内嵌约 20KB 相同 CSS，可抽成 `style.css`）
- 图片压缩（hero-bg.jpg 650KB 等，可转 WebP）
- sitemap.xml / robots.txt / 404 页面
