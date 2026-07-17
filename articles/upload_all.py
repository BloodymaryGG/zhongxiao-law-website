#!/usr/bin/env python3
"""从已存在的文章HTML文件中提取body内容，上传到公众号草稿箱"""
import json, os, re, ssl, urllib.request

CONFIG_PATH = os.path.expanduser("~/.openclaw/workspace/skills/magicx-wechat-publisher/scripts/.wechat-config.json")
with open(CONFIG_PATH) as f:
    cfg = json.load(f)
APPID = cfg["appid"]
SECRET = cfg["secret"]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def http_get(url):
    r = urllib.request.urlopen(url, context=ctx, timeout=10)
    return json.loads(r.read().decode())

def http_post(url, data):
    body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
    r = urllib.request.urlopen(req, context=ctx, timeout=30)
    return json.loads(r.read().decode())

def upload_media(url, filepath):
    boundary = '----' + os.urandom(8).hex()
    filename = os.path.basename(filepath)
    with open(filepath, 'rb') as f:
        file_data = f.read()
    body = b'--' + boundary.encode()
    body += b'\r\nContent-Disposition: form-data; name="media"; filename="' + filename.encode() + b'"'
    body += b'\r\nContent-Type: image/png\r\n\r\n'
    body += file_data
    body += b'\r\n--' + boundary.encode() + b'--\r\n'
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
    r = urllib.request.urlopen(req, context=ctx, timeout=30)
    return json.loads(r.read().decode())

def get_token():
    j = http_get(f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={SECRET}")
    assert "access_token" in j, f"get_token failed: {j}"
    return j["access_token"]

def upload_cover(token, img_path):
    j = upload_media(f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image", img_path)
    assert "media_id" in j, f"upload_cover failed: {j}"
    return j["media_id"]

def create_draft(token, title, content_html, thumb_media_id):
    data = {
        "articles": [{
            "title": title,
            "author": "中晓律师事务所",
            "digest": "",
            "content": content_html,
            "thumb_media_id": thumb_media_id,
            "need_open_comment": 1,
            "only_fans_can_comment": 0,
            "show_cover_pic": 1
        }]
    }
    j = http_post(f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}", data)
    assert "media_id" in j, f"create_draft failed: {j}"
    return j["media_id"]

def extract_article_body(html_path):
    """从article HTML页面提取body内容，转为公众号兼容格式"""
    with open(html_path, encoding='utf-8') as f:
        html = f.read()
    # Extract body content
    m = re.search(r'<div class="article-content">(.*?)</div>\s*<div class="article-footer">', html, re.DOTALL)
    if not m:
        # fallback
        m = re.search(r'<div class="article-content">(.*?)</div>\s*<div', html, re.DOTALL)
    if not m:
        raise Exception(f"Cannot extract body from {html_path}")
    content = m.group(1)
    
    # Convert to inline-style WeChat HTML
    content = re.sub(r'<h2>', '<h2 style="margin:24px 0 12px;font-size:18px;font-weight:700;color:#1a1a1a;">', content)
    content = re.sub(r'<h3>', '<h3 style="margin:20px 0 10px;font-size:16px;font-weight:700;color:#333;">', content)
    content = re.sub(r'<p>', '<p style="margin:3px 0;font-size:16px;line-height:1.75;color:#333;">', content)
    content = re.sub(r'<blockquote>', '<blockquote style="margin:15px 0;padding:12px 16px;background:#f7f8fa;border-left:4px solid #C0392B;font-size:15px;color:#666;line-height:1.6;">', content)
    content = re.sub(r'<ul>', '<ul style="margin:10px 0 10px 1.5em;padding:0;font-size:16px;line-height:1.75;color:#333;">', content)
    content = re.sub(r'<li>', '<li style="margin:6px 0;">', content)
    content = re.sub(r'<ol>', '<ol style="margin:10px 0 10px 1.5em;padding:0;font-size:16px;line-height:1.75;color:#333;">', content)
    content = re.sub(r'<hr>', '<hr style="margin:24px 0;border:none;border-top:1px solid #eee;">', content)
    
    # Remove text-indent from the first paragraph in each section (lead paragraph)
    # Actually, keep it as-is. The WeChat renderer handles it.
    
    # Wrap in container
    result = f'<section style="margin:0 auto;max-width:640px;padding:8px 16px 40px;font-family:-apple-system,BlinkMacSystemFont,\'Helvetica Neue\',\'PingFang SC\',\'Microsoft YaHei\',sans-serif;">\n{content.strip()}\n</section>'
    return result

# Article definitions: (title, html_page_file, cover_file)
ARTICLES = [
    ("中晓律所2026年中总结会：不良资产处置规模再创新高",
     "news-2026-midyear.html", "cover-midyear.png"),
    ("华展资产&中晓律所联合举办金融机构不良资产处置实务研讨会",
     "news-seminar-npl.html", "cover-seminar.png"),
    ("标的额逾2.3亿元！中晓律师团队成功代理金融借款合同纠纷案",
     "news-loan-case.html", "cover-loan-case.png"),
    ("夫妻共同债务如何认定？最高院最新裁判规则实务解析",
     "insight-marital-debt.html", "cover-marital-debt.png"),
    ("法拍房捡漏还是踩坑？不良资产处置十大避坑要点",
     "insight-auction-house.html", "cover-auction.png"),
    ("担保不是签个字就完事——保证期间与保证方式的法律要点",
     "insight-guarantee.html", "cover-guarantee.png"),
]

def main():
    token = get_token()
    print(f"✅ access_token 获取成功")
    
    base_dir = "/Users/cinderella/programs/zhongxiao-law-website/articles"
    
    for i, (title, html_file, cover_file) in enumerate(ARTICLES):
        print(f"\n{'='*55}")
        print(f"[{i+1}/{len(ARTICLES)}] {title}")
        print(f"{'='*55}")
        
        # Extract content
        html_path = os.path.join(base_dir, html_file)
        print(f"  📄 提取正文...")
        try:
            content = extract_article_body(html_path)
            char_count = len(content)
            print(f"  ✅ 内容提取完成 ({char_count} 字符)")
        except Exception as e:
            print(f"  ❌ 提取失败: {e}")
            continue
        
        # Upload cover
        cover_path = os.path.join(base_dir, cover_file)
        print(f"  📤 上传封面...")
        try:
            media_id = upload_cover(token, cover_path)
            print(f"  ✅ 封面上传成功")
        except Exception as e:
            print(f"  ❌ 封面失败: {e}")
            continue
        
        # Create draft
        print(f"  📝 创建草稿...")
        try:
            draft_id = create_draft(token, title, content, media_id)
            print(f"  ✅ 草稿创建成功！")
        except Exception as e:
            print(f"  ❌ 草稿失败: {e}")
            continue
    
    print(f"\n🎉 全部完成！去公众号后台 → 内容与互动 → 草稿箱 查看")

if __name__ == "__main__":
    main()
