#!/usr/bin/env python3
"""为中晓律师事务所公众号生成统一封面图"""
from PIL import Image, ImageDraw, ImageFont
import os

def make_cover(title, subtitle, output_path, font_title_size=36, font_sub_size=22):
    w, h = 900, 500
    img = Image.new('RGB', (w, h), '#0A2647')
    draw = ImageDraw.Draw(img)
    
    # 左侧竖线装饰
    draw.rectangle([(40, 120), (50, 380)], fill='#C0392B')
    
    # 找可用字体
    fonts = [
        '/System/Library/Fonts/Hiragino Sans GB.ttc',
        '/System/Library/Fonts/STHeiti Medium.ttc',
        '/System/Library/Fonts/HelveticaNeue.ttc',
    ]
    font_t = None
    font_s = None
    for fp in fonts:
        try:
            font_t = ImageFont.truetype(fp, font_title_size)
            font_s = ImageFont.truetype(fp, font_sub_size)
            break
        except:
            pass
    if not font_t:
        font_t = ImageFont.load_default()
        font_s = ImageFont.load_default()
    
    # 顶部 LOGO 文字
    draw.text((85, 60), "北京中晓律师事务所", fill='#64B5F6', font=font_s)
    
    # 标题
    lines = []
    remaining = title
    while len(remaining) > 0 and len(lines) < 3:
        if len(remaining) <= 18:
            lines.append(remaining)
            break
        cut = 18
        while cut > 0 and remaining[cut] not in '，。！？、： ':
            cut -= 1
        if cut == 0:
            cut = 18
        lines.append(remaining[:cut])
        remaining = remaining[cut:]
    
    y = 170
    for line in lines:
        draw.text((85, y), line, fill='white', font=font_t)
        y += font_title_size + 8
    
    # 副标题
    if subtitle:
        draw.text((85, y + 10), subtitle, fill='#90CAF9', font=font_s)
    
    # 底部装饰线
    draw.rectangle([(85, 430), (85, 430)], fill='#C0392B')
    draw.text((85, 440), "以法立心 · 向晓而行", fill='#4A6FA5', font=font_s)
    
    img.save(output_path, quality=95)
    print(f"✅ 封面已生成: {output_path}")

if __name__ == '__main__':
    articles = [
        ("中晓律所2026年中总结会：不良资产处置规模再创新高", "上半年累计处置债权本金超12亿元", "cover-midyear.png"),
        ("金融机构不良资产处置实务研讨会圆满举行", "华展资产&中晓律所联合举办", "cover-seminar.png"),
        ("标的额逾2.3亿元！中晓律师团队成功代理金融借款合同纠纷案", "债权本息全额回收", "cover-loan-case.png"),
        ("夫妻共同债务如何认定？最高院最新裁判规则解析", "结合民法典第1064条及最新司法观点", "cover-marital-debt.png"),
        ("法拍房捡漏还是踩坑？不良资产处置十大避坑要点", "起拍价七折的诱惑vs成交即过户的风险", "cover-auction.png"),
        ("担保不是签个字就完事——保证期间与保证方式的法律要点", "保证期间会过期，保证方式决定追偿路径", "cover-guarantee.png"),
    ]
    outdir = "/Users/cinderella/programs/zhongxiao-law-website/articles"
    for title, subtitle, fname in articles:
        make_cover(title, subtitle, os.path.join(outdir, fname))
