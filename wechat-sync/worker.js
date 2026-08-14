/**
 * 微信公众号文章自动同步 → GitHub 仓库（触发 Cloudflare Pages 自动部署）
 *
 * 功能：
 *   1. 定时调用微信官方接口，获取公众号"发布"的新文章（freepublish）
 *   2. 为新文章生成网站文章页 articles/wechat-*.html（沿用站点现有紫色系模板）
 *   3. 更新 articles/wechat-index.json（已同步清单，同时充当"状态存储"）
 *   4. 更新 articles/wechat.html（自动文章列表页）
 *   5. 提交到 GitHub main 分支 → Cloudflare Pages 自动部署
 *
 * 环境变量（在 Cloudflare Worker 设置中配置）：
 *   WECHAT_APPID   文本（AppID，非机密）
 *   WECHAT_SECRET  密钥（AppSecret）
 *   GITHUB_TOKEN   密钥（GitHub Personal Access Token，勾选 repo 权限）
 *   GITHUB_REPO    文本，默认 BloodymaryGG/zhongxiao-law-website
 *   GITHUB_BRANCH  文本，默认 main
 *   SYNC_TOKEN     可选，手动触发时的访问口令（x-sync-token 请求头）
 */

const GITHUB_API = 'https://api.github.com';
const WECHAT_API = 'https://api.weixin.qq.com';

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(runSync(env).then(r => console.log('wechat-sync:', JSON.stringify(r))));
  },
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname !== '/sync') {
      return new Response('not found', { status: 404 });
    }
    if (env.SYNC_TOKEN && request.headers.get('x-sync-token') !== env.SYNC_TOKEN) {
      return new Response('forbidden', { status: 403 });
    }
    const result = await runSync(env);
    return new Response(JSON.stringify(result, null, 2), {
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
    });
  },
};

async function runSync(env) {
  const out = { ok: false, published: 0, newArticles: [], errors: [] };
  try {
    const token = await getAccessToken(env.WECHAT_APPID, env.WECHAT_SECRET);
    const published = await listPublished(token);
    out.published = published.length;

    const state = await readState(env);
    const seen = new Set(state.map(a => a.id));
    const fresh = published.filter(a => !seen.has(a.id));

    if (fresh.length === 0) {
      out.ok = true;
      out.message = '没有新文章';
      return out;
    }

    for (const art of fresh) {
      await putFile(env, `articles/${art.fileName}`, buildArticlePage(art));
      seen.add(art.id);
      state.push({
        id: art.id,
        title: art.title,
        date: art.date,
        wechatUrl: art.wechatUrl,
        page: art.pageUrl,
      });
      out.newArticles.push(art.title);
    }

    await putFile(env, 'articles/wechat-index.json', JSON.stringify(state, null, 2));
    await putFile(env, 'articles/wechat.html', buildListPage(state));
    out.ok = true;
    return out;
  } catch (e) {
    out.errors.push(String((e && e.message) || e));
    return out;
  }
}

/* ============ 微信接口 ============ */

async function getAccessToken(appid, secret) {
  const url = `${WECHAT_API}/cgi-bin/token?grant_type=client_credential&appid=${encodeURIComponent(appid)}&secret=${encodeURIComponent(secret)}`;
  const res = await fetch(url);
  const data = await res.json();
  if (!data.access_token) {
    throw new Error(`微信 access_token 获取失败: ${JSON.stringify(data)}`);
  }
  return data.access_token;
}

async function listPublished(token) {
  const articles = [];
  for (let offset = 0; offset < 100; offset += 20) {
    const res = await fetch(
      `${WECHAT_API}/cgi-bin/freepublish/batchget?access_token=${token}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ offset, count: 20, no_content: 0 }),
      }
    );
    const data = await res.json();
    if (data.errcode) {
      throw new Error(`微信 freepublish 接口错误: ${JSON.stringify(data)}`);
    }
    for (const item of data.item || []) {
      const recordId = String(item.article_id || '');
      const date = formatDate(item.update_time);
      const newsItems = (item.content && item.content.news_item) || [];
      newsItems.forEach((news, i) => {
        const id = `${recordId}-${i + 1}`;
        const fileName = `wechat-${sanitizeFile(recordId)}-${i + 1}.html`;
        articles.push({
          id,
          fileName,
          title: news.title || '未命名文章',
          digest: news.digest || '',
          content: news.content || '',
          date,
          wechatUrl: news.url || '',
          pageUrl: `https://zxlawfirm.cn/articles/${fileName}`,
        });
      });
    }
    if (!data.item || data.item.length < 20) break;
  }
  return articles;
}

/* ============ GitHub ============ */

async function gh(env, path, options = {}) {
  const res = await fetch(`${GITHUB_API}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: 'application/vnd.github+json',
      'User-Agent': 'zhongxiao-wechat-sync',
      ...(options.headers || {}),
    },
  });
  return res;
}

async function readState(env) {
  const branch = env.GITHUB_BRANCH || 'main';
  const res = await gh(
    env,
    `/repos/${env.GITHUB_REPO}/contents/articles/wechat-index.json?ref=${branch}`
  );
  if (res.status === 404) return [];
  if (!res.ok) throw new Error(`读取已同步清单失败: ${res.status}`);
  const data = await res.json();
  const text = decodeBase64(data.content);
  try {
    const arr = JSON.parse(text);
    return Array.isArray(arr) ? arr : [];
  } catch (e) {
    return [];
  }
}

async function putFile(env, path, content) {
  const branch = env.GITHUB_BRANCH || 'main';
  const repo = env.GITHUB_REPO;
  // 获取已有文件 sha（用于更新）
  let sha = null;
  const existRes = await gh(env, `/repos/${repo}/contents/${path}?ref=${branch}`);
  if (existRes.ok) {
    const existData = await existRes.json();
    sha = existData.sha || null;
  }
  const body = {
    message: `chore: 同步微信公众号文章 ${path}`,
    content: toBase64(content),
    branch,
  };
  if (sha) body.sha = sha;
  const res = await gh(env, `/repos/${repo}/contents/${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`提交 ${path} 失败: ${res.status} ${text.slice(0, 200)}`);
  }
}

function toBase64(str) {
  const bytes = new TextEncoder().encode(str);
  let bin = '';
  bytes.forEach(b => (bin += String.fromCharCode(b)));
  return btoa(bin);
}

function decodeBase64(b64) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new TextDecoder().decode(bytes);
}

/* ============ 工具 ============ */

function sanitizeFile(s) {
  return (s || '').replace(/[^A-Za-z0-9_-]/g, '');
}

function formatDate(ts) {
  if (!ts) return '';
  const d = new Date(ts * 1000 + 8 * 3600 * 1000);
  return `${d.getUTCFullYear()}年${d.getUTCMonth() + 1}月${d.getUTCDate()}日`;
}

function esc(s) {
  return String(s || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function sanitizeHtml(html) {
  return String(html || '')
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, '')
    .replace(/(href|src)\s*=\s*("|')javascript:[^"']*("|')/gi, '');
}

/* ============ 页面模板 ============ */

function buildArticlePage(art) {
  const content = sanitizeHtml(art.content);
  const backLink = 'https://zxlawfirm.cn/articles/wechat.html';
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${esc(art.title)} — 北京中晓律师事务所</title>
    <meta name="description" content="${esc(art.digest)}">
    <link rel="icon" type="image/png" href="../favicon.png">
    <link rel="canonical" href="${art.pageUrl}">
    <style>
:root {
  --color-primary: #291943;
  --color-primary-hover: #3d2663;
  --color-secondary: #881C3C;
  --color-accent: #CB6172;
  --color-muted: #9C8BA7;
  --color-bg-main: #F9F8FA;
  --color-card-bg: #FFFFFF;
  --color-text-primary: #1D132D;
  --color-text-secondary: #635773;
  --color-border: rgba(156, 139, 167, 0.2);
}
        body { font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif; color: #1D132D; background: #fff; line-height: 1.6; }
        a { text-decoration: none; color: #881C3C; }
        a:hover { color: #6E1630; }
        .header { position: fixed; top: 0; left: 0; right: 0; z-index: 100; background: rgba(255,255,255,0.97); backdrop-filter: blur(10px); border-bottom: 1px solid #E7E2EE; height: 76px; }
        .header-inner { max-width: 1200px; margin: 0 auto; padding: 0 24px; display: flex; align-items: center; justify-content: space-between; height: 76px; }
        .logo { display: flex; align-items: center; gap: 12px; }
        .logo-img { height: 46px; width: auto; border-radius: 4px; }
        .logo-text { font-size: 20px; font-weight: 700; color: #1D132D; letter-spacing: 2px; }
        .logo-sub { font-size: 11px; color: #9C8BA7; letter-spacing: 1px; margin-top: 2px; }
        .nav { display: flex; gap: 4px; }
        .nav a { padding: 8px 18px; font-size: 15px; color: #635773; border-radius: 6px; transition: all 0.2s; position: relative; }
        .nav a:hover { color: #881C3C; background: rgba(136,28,60,0.06); }
        .article-container { max-width: 800px; margin: 100px auto 60px; padding: 0 24px; }
        .article-header { margin-bottom: 40px; }
        .article-category { display: inline-block; font-size: 13px; color: #881C3C; font-weight: 600; margin-bottom: 12px; letter-spacing: 2px; }
        .article-title { font-size: 32px; font-weight: 700; color: #1D132D; line-height: 1.3; margin-bottom: 16px; }
        .article-meta { font-size: 14px; color: #9C8BA7; margin-bottom: 32px; padding-bottom: 24px; border-bottom: 1px solid #E7E2EE; }
        .article-content { font-size: 16px; line-height: 2; color: #635773; }
        .article-content h2 { font-size: 22px; font-weight: 700; color: #1D132D; margin: 40px 0 16px; padding-left: 14px; border-left: 4px solid #881C3C; }
        .article-content h3 { font-size: 18px; font-weight: 700; color: #1D132D; margin: 28px 0 12px; }
        .article-content p { margin-bottom: 16px; }
        .article-content blockquote { margin: 20px 0; padding: 16px 20px; background: #F9F8FA; border-left: 4px solid #881C3C; border-radius: 4px; color: #635773; font-size: 15px; }
        .article-content img { max-width: 100%; height: auto; border-radius: 8px; }
        .article-content ul, .article-content ol { margin: 16px 0 16px 2em; }
        .article-content li { margin-bottom: 8px; }
        .article-footer { margin-top: 48px; padding-top: 24px; border-top: 1px solid #E7E2EE; }
        .article-footer .back-link { display: inline-flex; align-items: center; gap: 6px; color: #881C3C; font-weight: 600; font-size: 15px; }
        .article-footer .back-link:hover { color: #6E1630; }
        .disclaimer { margin-top: 24px; padding: 16px 20px; background: #F9F8FA; border-radius: 8px; font-size: 13px; color: #9C8BA7; line-height: 1.6; }
        .footer { background: #291943; color: #fff; padding: 40px 0 24px; margin-top: 60px; }
        .footer-inner { max-width: 1200px; margin: 0 auto; padding: 0 24px; text-align: center; font-size: 13px; color: rgba(255,255,255,0.4); }
        @media (max-width: 768px) {
            .article-title { font-size: 24px; }
            .article-content { font-size: 15px; }
            .article-container { margin-top: 80px; }
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="../index.html" class="logo">
                <img src="../logo.png" alt="中晓律师事务所" class="logo-img">
                <div>
                    <div class="logo-text">中晓律师事务所</div>
                    <div class="logo-sub">ZHONGXIAO LAW FIRM</div>
                </div>
            </a>
            <nav class="nav">
                <a href="../index.html">首页</a>
                <a href="../articles.html">律所资讯</a>
                <a href="../index.html#contact">联系我们</a>
            </nav>
        </div>
    </header>

    <div class="article-container">
        <div class="article-header">
            <div class="article-category">微信公众号文章</div>
            <h1 class="article-title">${esc(art.title)}</h1>
            <div class="article-meta">${esc(art.date)} | 北京中晓律师事务所</div>
        </div>
        <div class="article-content">
${content}
        </div>
        <div class="article-footer">
            <a href="${backLink}" class="back-link">← 返回微信公众号文章列表</a>
            ${art.wechatUrl ? `<p style="margin-top:12px;"><a href="${esc(art.wechatUrl)}">查看微信公众号原文 →</a></p>` : ''}
            <div class="disclaimer">
                <strong>免责声明：</strong>本文内容仅供一般参考，不构成法律意见。具体法律问题请咨询专业律师。
            </div>
        </div>
    </div>

    <footer class="footer">
        <div class="footer-inner">
            <p>© 2026 北京中晓律师事务所 All Rights Reserved</p>
        </div>
    </footer>
</body>
</html>`;
}

function buildListPage(state) {
  const items = state
    .slice()
    .reverse()
    .map(
      a => `<li>
            <a href="${a.page}">${esc(a.title)}</a>
            <span class="meta">${esc(a.date)}${a.wechatUrl ? ` · <a href="${esc(a.wechatUrl)}">微信原文</a>` : ''}</span>
          </li>`
    )
    .join('\n');
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>微信公众号文章 — 北京中晓律师事务所</title>
    <meta name="description" content="北京中晓律师事务所微信公众号文章汇总。">
    <link rel="icon" type="image/png" href="../favicon.png">
    <link rel="canonical" href="https://zxlawfirm.cn/articles/wechat.html">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif; color: #1D132D; background: #fff; line-height: 1.6; }
        a { text-decoration: none; color: #881C3C; }
        .header { position: fixed; top: 0; left: 0; right: 0; z-index: 100; background: rgba(255,255,255,0.97); backdrop-filter: blur(10px); border-bottom: 1px solid #E7E2EE; height: 76px; }
        .header-inner { max-width: 1200px; margin: 0 auto; padding: 0 24px; display: flex; align-items: center; justify-content: space-between; height: 76px; }
        .logo { display: flex; align-items: center; gap: 12px; }
        .logo-img { height: 46px; width: auto; border-radius: 4px; }
        .logo-text { font-size: 20px; font-weight: 700; color: #1D132D; letter-spacing: 2px; }
        .logo-sub { font-size: 11px; color: #9C8BA7; letter-spacing: 1px; margin-top: 2px; }
        .nav { display: flex; gap: 4px; }
        .nav a { padding: 8px 18px; font-size: 15px; color: #635773; border-radius: 6px; transition: all 0.2s; }
        .nav a:hover { color: #881C3C; background: rgba(136,28,60,0.06); }
        .page-header { margin-top: 76px; padding: 90px 0 50px; background: linear-gradient(135deg, #291943, #3D2663); color: #fff; text-align: center; }
        .page-header h2 { font-size: 32px; font-weight: 300; letter-spacing: 6px; margin-bottom: 10px; }
        .page-header .en-sub { font-size: 13px; color: rgba(255,255,255,0.35); letter-spacing: 4px; }
        .page-header .divider { width: 40px; height: 2px; background: #881C3C; margin: 18px auto 0; }
        .list { max-width: 800px; margin: 0 auto; padding: 48px 24px 80px; }
        .list ul { list-style: none; }
        .list li { padding: 18px 4px; border-bottom: 1px solid #E7E2EE; display: flex; justify-content: space-between; align-items: baseline; gap: 16px; flex-wrap: wrap; }
        .list li a { font-size: 16px; color: #1D132D; }
        .list li a:hover { color: #881C3C; }
        .list .meta { font-size: 13px; color: #9C8BA7; white-space: nowrap; }
        .footer { background: #291943; color: #fff; padding: 40px 0 24px; }
        .footer-inner { max-width: 1200px; margin: 0 auto; padding: 0 24px; text-align: center; font-size: 13px; color: rgba(255,255,255,0.4); }
        @media (max-width: 768px) {
            .list li { flex-direction: column; gap: 4px; }
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="../index.html" class="logo">
                <img src="../logo.png" alt="中晓律师事务所" class="logo-img">
                <div>
                    <div class="logo-text">中晓律师事务所</div>
                    <div class="logo-sub">ZHONGXIAO LAW FIRM</div>
                </div>
            </a>
            <nav class="nav">
                <a href="../index.html">首页</a>
                <a href="../articles.html">律所资讯</a>
                <a href="../index.html#contact">联系我们</a>
            </nav>
        </div>
    </header>
    <section class="page-header">
        <h2>微信公众号文章</h2>
        <div class="en-sub">WECHAT ARTICLES</div>
        <div class="divider"></div>
    </section>
    <div class="list">
        ${items ? `<ul>${items}</ul>` : '<p style="color:#9C8BA7;">暂无文章</p>'}
    </div>
    <footer class="footer">
        <div class="footer-inner">
            <p>© 2026 北京中晓律师事务所 All Rights Reserved</p>
        </div>
    </footer>
</body>
</html>`;
}
