# 微信公众号文章自动同步（Cloudflare Worker）

定时把公众号「发布」的新文章自动同步到网站，提交 GitHub 后由 Cloudflare Pages 自动部署。

## 部署步骤（约 5 分钟）

1. 打开 Cloudflare 控制台 → **Workers & Pages → 创建 Worker**（名称如 `wechat-sync`）
2. 把 [`worker.js`](./worker.js) 全文粘贴进编辑器 → **保存并部署**
3. **设置 → 变量**，添加：

   | 变量 | 类型 | 说明 |
   |------|------|------|
   | `WECHAT_APPID` | 文本 | 公众号 AppID |
   | `WECHAT_SECRET` | 密钥 | 公众号 AppSecret |
   | `GITHUB_TOKEN` | 密钥 | GitHub Personal Access Token（勾选 repo） |
   | `GITHUB_REPO` | 文本 | 默认 `BloodymaryGG/zhongxiao-law-website`，可不填 |
   | `GITHUB_BRANCH` | 文本 | 默认 `main`，可不填 |
   | `SYNC_TOKEN` | 文本 | 可选，手动触发口令（`x-sync-token` 请求头） |

4. **触发器 → Cron 触发器 → 添加**：`*/15 * * * *`（每 15 分钟）
5. 手动测试：`curl -X POST https://<你的worker>.workers.dev/sync`（若设置了 SYNC_TOKEN，加请求头 `x-sync-token: <口令>`）

环境变量改动后需**重新部署 Worker** 才生效。

## 工作方式

- 调用微信 `freepublish` 接口拉取「已发布」文章（含正文 HTML）
- 新文章 → 生成 `articles/wechat-*.html` 文章页（沿用站点紫色系模板）
- 更新 `articles/wechat-index.json`（已同步清单，兼作去重状态）
- 更新 `articles/wechat.html`（自动文章列表页）
- 全部提交 GitHub main 分支 → Pages 自动部署

## ⚠️ 重要：微信「发布」与「群发」的区别

- **发布**：文章发到公众号主页，不推送通知粉丝。`freepublish` 接口能查到，**自动同步只认这个**。
- **群发**：会推送消息通知所有粉丝。**官方接口没有群发记录列表**，自动同步拿不到。

**以后发新文章请统一用「发布」，不要用「群发」**，否则同步不到。
已群发的旧文章：把链接发给 Codex，手动导入一次即可。

## 已知边界

- 文章图片沿用微信图床（mmbiz.qpic.cn）链接，未做本地化
- 首页资讯区和 `articles.html` 暂未自动接入，需要时人工加链接，或后续升级为自动生成
- 微信 access_token 有效期 2 小时，由 Worker 每次运行自动获取，无需缓存
