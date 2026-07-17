#!/usr/bin/env python3
"""完整版：提取正文 + 插入配图 + 上传封面 + 创建草稿，一次完成"""
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

def upload_file(url, filepath, field="media"):
    boundary = '----' + os.urandom(8).hex()
    filename = os.path.basename(filepath)
    with open(filepath, 'rb') as f:
        file_data = f.read()
    body = b'--' + boundary.encode()
    body += b'\r\nContent-Disposition: form-data; name="' + field.encode() + b'"; filename="' + filename.encode() + b'"'
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
    j = upload_file(f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image", img_path)
    assert "media_id" in j, f"upload_cover failed: {j}"
    return j["media_id"]

def upload_article_image(token, img_path):
    """上传配图到微信图床，返回可直接引用的URL"""
    j = upload_file(f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={token}", img_path, "media")
    assert "url" in j, f"upload_article_image failed: {j}"
    return j["url"]

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

def extract_and_convert(html_path, image_urls):
    """提取文章body，插入配图，转公众号格式"""
    with open(html_path, encoding='utf-8') as f:
        html = f.read()
    
    # Extract body
    m = re.search(r'<div class="article-content">(.*?)</div>\s*<div class="article-footer">', html, re.DOTALL)
    if not m:
        m = re.search(r'<div class="article-content">(.*?)</div>', html, re.DOTALL)
    assert m, f"Cannot extract body from {html_path}"
    content = m.group(1)
    
    # Insert image after each h2 (but not the last one, and not the disclaimer)
    for img_url in image_urls:
        img_tag = f'\n<p style="margin:15px auto;text-align:center;"><img src="{img_url}" alt="" style="width:100%;max-width:100%;border-radius:6px;"></p>\n'
        # Insert after first h2
        content = re.sub(r'(</h2>)', r'\1' + img_tag, content, count=1)
    
    # Convert to inline styles
    content = re.sub(r'<h2>', '<h2 style="margin:24px 0 12px;font-size:18px;font-weight:700;color:#1a1a1a;">', content)
    content = re.sub(r'<h3>', '<h3 style="margin:20px 0 10px;font-size:16px;font-weight:700;color:#333;">', content)
    content = re.sub(r'<p>', '<p style="margin:3px 0;font-size:16px;line-height:1.75;color:#333;">', content)
    content = re.sub(r'<blockquote>', '<blockquote style="margin:15px 0;padding:12px 16px;background:#f7f8fa;border-left:4px solid #C0392B;font-size:15px;color:#666;line-height:1.6;">', content)
    content = re.sub(r'<ul>', '<ul style="margin:10px 0 10px 1.5em;padding:0;font-size:16px;line-height:1.75;color:#333;">', content)
    content = re.sub(r'<li>', '<li style="margin:6px 0;">', content)
    content = re.sub(r'<ol>', '<ol style="margin:10px 0 10px 1.5em;padding:0;font-size:16px;line-height:1.75;color:#333;">', content)
    content = re.sub(r'<hr>', '<hr style="margin:24px 0;border:none;border-top:1px solid #eee;">', content)
    
    # Remove text-indent from first p after each h2 (lead sentences)
    content = re.sub(r'(<h2[^>]*>.*?</h2>)\s*<p style="margin:3px 0;font-size:16px;line-height:1.75;color:#333;">', 
                     r'\1<p style="margin:3px 0;font-size:16px;line-height:1.75;color:#333;text-indent:0;">', content)
    
    result = f'<section style="margin:0 auto;max-width:640px;padding:8px 16px 40px;font-family:-apple-system,BlinkMacSystemFont,\'Helvetica Neue\',\'PingFang SC\',\'Microsoft YaHei\',sans-serif;">\n{content.strip()}\n</section>'
    return result

# ===== Articles =====
ILL_DIR = "/Users/cinderella/programs/zhongxiao-law-website/articles/illustrations"
HTML_DIR = "/Users/cinderella/programs/zhongxiao-law-website/articles"

ARTICLES = [
    ("中晓律所2026年中总结会：不良资产处置规模再创新高",
     "news-2026-midyear.html",
     "cover-midyear.png",
     ["ill-midyear.png"]),
    ("华展资产&中晓律所联合举办金融机构不良资产处置实务研讨会",
     "news-seminar-npl.html",
     "cover-seminar.png",
     ["ill-seminar.png"]),
    ("标的额逾2.3亿元！中晓律师团队成功代理金融借款合同纠纷案",
     "news-loan-case.html",
     "cover-loan-case.png",
     ["ill-loan-case.png"]),
    ("夫妻共同债务如何认定？最高院最新裁判规则实务解析",
     "insight-marital-debt.html",
     "cover-marital-debt.png",
     ["ill-marital-debt.png"]),
    ("法拍房捡漏还是踩坑？不良资产处置十大避坑要点",
     "insight-auction-house.html",
     "cover-auction.png",
     ["ill-auction.png"]),
    ("担保不是签个字就完事——保证期间与保证方式的法律要点",
     "insight-guarantee.html",
     "cover-guarantee.png",
     ["ill-guarantee.png"]),
]

def main():
    token = get_token()
    print(f"✅ access_token 获取成功")

    # Step 1: Upload all illustrations first
    ill_urls = {}
    for title, _, _, ill_files in ARTICLES:
        for ill_file in ill_files:
            ill_path = os.path.join(ILL_DIR, ill_file)
            if ill_file not in ill_urls:
                print(f"  📤 上传配图: {ill_file}...")
                url = upload_article_image(token, ill_path)
                ill_urls[ill_file] = url
                print(f"     ✅ URL: {url[:60]}...")
    
    print(f"\n{'='*55}")
    print("开始创建草稿（含配图）")
    
    for i, (title, html_file, cover_file, ill_files) in enumerate(ARTICLES):
        print(f"\n{'='*55}")
        print(f"[{i+1}/{len(ARTICLES)}] {title}")
        print(f"{'='*55}")
        
        # Get illustration URLs for this article
        img_urls = [ill_urls[f] for f in ill_files]
        
        # Extract + convert + insert images
        html_path = os.path.join(HTML_DIR, html_file)
        print(f"  📄 提取正文 + 插入配图...")
        try:
            content = extract_and_convert(html_path, img_urls)
            print(f"  ✅ 完成 ({len(content)} 字符)")
        except Exception as e:
            print(f"  ❌ 提取失败: {e}")
            continue
        
        # Upload cover
        cover_path = os.path.join(HTML_DIR, cover_file)
        print(f"  📤 上传封面...")
        try:
            media_id = upload_cover(token, cover_path)
            print(f"  ✅ OK")
        except Exception as e:
            print(f"  ❌ 封面失败: {e}")
            continue
        
        # Create draft
        print(f"  📝 创建草稿...")
        try:
            draft_id = create_draft(token, title, content, media_id)
            print(f"  ✅ 草稿ID: {draft_id}")
        except Exception as e:
            print(f"  ❌ 草稿失败: {e}")
    
    print(f"\n🎉 全部完成！公众号后台 → 内容与互动 → 草稿箱")

if __name__ == "__main__":
    main()
