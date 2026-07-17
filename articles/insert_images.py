#!/usr/bin/env python3
"""上传配图到微信图床 + 更新草稿插入图片"""
import json, os, re, ssl, urllib.request, urllib.parse

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

def get_token():
    j = http_get(f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={SECRET}")
    assert "access_token" in j, f"get_token failed: {j}"
    return j["access_token"]

def http_post(url, data):
    body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
    r = urllib.request.urlopen(req, context=ctx, timeout=30)
    return json.loads(r.read().decode())

def upload_article_image(token, img_path):
    """上传文章配图到微信（返回可用的图床URL）"""
    boundary = '----' + os.urandom(8).hex()
    filename = os.path.basename(img_path)
    with open(img_path, 'rb') as f:
        file_data = f.read()
    body = b'--' + boundary.encode()
    body += b'\r\nContent-Disposition: form-data; name="media"; filename="' + filename.encode() + b'"'
    body += b'\r\nContent-Type: image/png\r\n\r\n'
    body += file_data
    body += b'\r\n--' + boundary.encode() + b'--\r\n'
    req = urllib.request.Request(
        f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={token}",
        data=body,
        headers={'Content-Type': 'multipart/form-data; boundary=' + boundary}
    )
    r = urllib.request.urlopen(req, context=ctx, timeout=30)
    j = json.loads(r.read().decode())
    assert "url" in j, f"upload article image failed: {j}"
    return j["url"]

def update_draft(token, media_id, title, content_html):
    """更新已有草稿"""
    data = {
        "media_id": media_id,
        "index": 0,
        "articles": {
            "title": title,
            "author": "中晓律师事务所",
            "digest": "",
            "content": content_html,
            "need_open_comment": 1,
            "only_fans_can_comment": 0,
            "show_cover_pic": 1
        }
    }
    j = http_post(f"https://api.weixin.qq.com/cgi-bin/draft/update?access_token={token}", data)
    if "errcode" in j and j["errcode"] != 0:
        raise Exception(f"update_draft failed: {j}")
    return j

def get_draft(token, media_id):
    """获取草稿内容"""
    data = {"media_id": media_id}
    url = f"https://api.weixin.qq.com/cgi-bin/draft/get?access_token={token}"
    j = http_post(url, data)
    assert "news_item" in j, f"get_draft failed: {j}"
    return j["news_item"][0]

# Articles: (draft_media_id, title, ill_image_paths, insert_after_keywords)
# I need the draft media_ids from the previous upload
# From the previous output:
DRAFT_ARTICLES = [
    # article 1 - midyear meeting
    ("_LMvIB_MctHyZLPqm248EKV4QwsWeBj-kIU2CiHEkEEFTSRFsr5R3ILAYGwHma1O",
     "中晓律所2026年中总结会：不良资产处置规模再创新高",
     ["ill-midyear.png"],
     ["半年成绩单：数字见证专业力量"]),
    # article 2 - seminar
    ("_LMvIB_MctHyZLPqm248EBb3ojsnC4GiVb8m3RNBUkTvxbAlIpta5SRCguq3DrEj",
     "华展资产&中晓律所联合举办金融机构不良资产处置实务研讨会",
     ["ill-seminar.png"],
     ["行业变局下的新挑战"]),
    # article 3 - loan case
    ("_LMvIB_MctHyZLPqm248EE-VCqzw2d20RSw38f4F-yGlRzLM3l_Dm_4vWEpj5iZc",
     "标的额逾2.3亿元！中晓律师团队成功代理金融借款合同纠纷案",
     ["ill-loan-case.png"],
     ["案件背景"]),
    # article 4 - marital debt
    ("_LMvIB_MctHyZLPqm248EGqqKIDjOTdc4sylYtB7EuWvapr3mhDcLXsCQ6RA1xGV",
     "夫妻共同债务如何认定？最高院最新裁判规则实务解析",
     ["ill-marital-debt.png"],
     ["法律框架"]),
    # article 5 - auction house
    ("_LMvIB_MctHyZLPqm248EA1j57nIZWOsUIqRNrQlk3R5nZpI1U-Oeajc81y7uo1r", 
     "法拍房捡漏还是踩坑？不良资产处置十大避坑要点",
     ["ill-auction.png"],
     ["第一坑"]),
    # article 6 - guarantee
    ("_LMvIB_MctHyZLPqm248EAga9CZ2Mo95yimh2Wly0ADoElH24dtf2B27E6JGeJJz",
     "担保不是签个字就完事——保证期间与保证方式的法律要点",
     ["ill-guarantee.png"],
     ["二、保证方式"]),
]

def main():
    token = get_token()
    print(f"✅ access_token 获取成功")
    
    base = "/Users/cinderella/programs/zhongxiao-law-website/articles/illustrations"
    
    for i, (draft_id, title, ill_files, keywords) in enumerate(DRAFT_ARTICLES):
        print(f"\n{'='*55}")
        print(f"[{i+1}/6] {title}")
        print(f"{'='*55}")
        
        # 1. Upload illustration images
        img_urls = []
        for ill_file in ill_files:
            ill_path = os.path.join(base, ill_file)
            print(f"  📤 上传配图: {ill_file}...")
            try:
                url = upload_article_image(token, ill_path)
                print(f"  ✅ 图床URL: {url[:60]}...")
                img_urls.append(url)
            except Exception as e:
                print(f"  ❌ 配图上传递失败: {e}")
                continue
        
        # 2. Get existing draft content
        print(f"  📄 读取草稿内容...")
        try:
            draft = get_draft(token, draft_id)
            content = draft["content"]
            print(f"  ✅ 草稿内容 {len(content)} 字符")
        except Exception as e:
            print(f"  ❌ 读取失败: {e}")
            continue
        
        # 3. Insert images after keywords
        for idx, keyword in enumerate(keywords):
            if idx < len(img_urls):
                img_html = f'<p style="margin:15px 0;text-align:center;"><img src="{img_urls[idx]}" alt="配图" style="width:100%;max-width:100%;border-radius:8px;"></p>'
                # Find the keyword and insert image after it
                replacement = keyword + '</h2>' + img_html + '</h2>'
                # Actually we need to insert after the h2 tag that contains the keyword
                pattern = re.escape(keyword) + r'</h2>'
                new_content = re.sub(pattern, keyword + '</h2>\n' + img_html, content, count=1)
                if new_content != content:
                    print(f"  ✅ 图片已插入: {keyword}")
                    content = new_content
                else:
                    # Try without h2
                    pattern2 = re.escape(keyword)
                    new_content = re.sub(pattern2, keyword + '\n' + img_html, content, count=1)
                    if new_content != content:
                        print(f"  ✅ 图片已插入(文本匹配): {keyword}")
                        content = new_content
                    else:
                        print(f"  ⚠️ 未找到插入点: {keyword}")
        
        # 4. Update the draft
        print(f"  📝 更新草稿...")
        try:
            result = update_draft(token, draft_id, title, content)
            print(f"  ✅ 草稿更新成功！")
        except Exception as e:
            print(f"  ❌ 更新失败: {e}")
    
    print(f"\n🎉 全部完成！公众号后台 → 内容与互动 → 草稿箱 查看配图效果")

if __name__ == "__main__":
    main()
