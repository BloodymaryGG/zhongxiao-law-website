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

## 内容与风格约定（改之前必看）

- **联系方式已全面更新**：全站邮箱统一为 `myq@zhongxiaolaw.com`（11 处），电话 `13522711878`（14 处）；旧邮箱 `534818861@qq.com` 已无残留。新增内容保持一致，**不要用旧邮箱**。表单收件人 `TO_EMAIL` 也是 `myq@zhongxiaolaw.com`
- **文章与封面**：`articles/` 下有 6 篇文章 + 1 个模板（`template.html`）+ 33 张封面图。新增文章需配套封面图，命名沿用 `cover-*.png` 风格
- **`qrcode.jpg` 是公众号二维码**，6 个页面全部引用，不要误删或改路径
- **生产环境变量在 Cloudflare 控制台**（不在代码里）。`FROM_EMAIL` 目前可能仍是 Resend 的占位符 `onboarding@resend.dev`，属正常，**不要当成 bug 去修**；`TO_EMAIL` 已是 `myq@zhongxiaolaw.com`
- **风格约束**：最近一次大改版是"华城风格"卡片布局，改样式前先看现有页面，保持视觉统一，别自由发挥

## 备注

- 域名 `zxlawfirm.cn` 已购买并解析到 Cloudflare（线上已验证可访问）；早期备注里"域名还没买"的说法已过时
- ICP 备案：境外托管（Cloudflare Pages）不需要备案，属合规状态，不用管

## 已知待办（未做）

- 首页 5 张「即将上线」资讯卡（`coming-soon`）：文章写好后补页面并换回链接
- 隐私政策页面（表单收集个人信息，按《个人信息保护法》建议补）
- 公共样式抽取（现在每页内嵌约 20KB 相同 CSS，可抽成 `style.css`）
- 图片压缩（hero-bg.jpg 650KB 等，可转 WebP）
- sitemap.xml / robots.txt / 404 页面
