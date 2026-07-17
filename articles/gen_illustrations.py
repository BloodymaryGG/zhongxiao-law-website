#!/usr/bin/env python3
"""中晓律所公众号文章配图生成器"""
from PIL import Image, ImageDraw, ImageFont
import os

FONT = '/System/Library/Fonts/Hiragino Sans GB.ttc'

def draw_text_center(draw, text, font, fill, y, spacing=0, max_w=700):
    """居中绘制多行文字"""
    lines = []
    for char in text:
        if not lines:
            lines.append(char)
        else:
            test = lines[-1] + char
            bbox = draw.textbbox((0,0), test, font=font)
            if bbox[2] - bbox[0] <= max_w:
                lines[-1] = test
            else:
                lines.append(char)
    total_h = len(lines) * (font.size + spacing) - spacing
    start_y = y - total_h // 2 if total_h < 300 else y
    current_y = start_y
    for line in lines:
        bbox = draw.textbbox((0,0), line, font=font)
        x = (800 - (bbox[2] - bbox[0])) // 2
        draw.text((x, current_y), line, fill=fill, font=font)
        current_y += font.size + spacing

def generate_image(title, subtitle, icon_emoji, bg_color, accent_color, output_path):
    w, h = 800, 500
    img = Image.new('RGB', (w, h), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Accent bar at top
    draw.rectangle([(0, 0), (w, 6)], fill=accent_color)
    
    # Decorative circle in background
    draw.ellipse([(w-180, -80), (w-20, 70)], fill=accent_color[:3] + (20,) if len(accent_color) == 9 else None)
    # Can't use RGBA with RGB, so just draw a subtle shape
    # Try a different approach - lighter shade
    dr = int(accent_color[1:3], 16)
    dg = int(accent_color[3:5], 16)
    db = int(accent_color[5:7], 16)
    lighter = (min(255, dr+60), min(255, dg+60), min(255, db+60))
    
    # Icon area - large centered icon
    font_icon = ImageFont.truetype(FONT, 60)
    font_title = ImageFont.truetype(FONT, 32)
    font_sub = ImageFont.truetype(FONT, 18)
    font_tag = ImageFont.truetype(FONT, 14)
    
    # Draw icon
    bbox = draw.textbbox((0,0), icon_emoji, font=font_icon)
    ix = (w - (bbox[2]-bbox[0])) // 2
    draw.text((ix, 50), icon_emoji, fill='white', font=font_icon)
    
    # Decorative line under icon
    line_y = 130
    draw.rectangle([(w//2-40, line_y), (w//2+40, line_y+3)], fill=accent_color)
    
    # Title
    font_large = ImageFont.truetype(FONT, 30)
    draw_text_center(draw, title, font_large, 'white', 200, spacing=6)
    
    # Subtitle
    if subtitle:
        y_sub = 270 + (len(title) // 20) * 40
        draw_text_center(draw, subtitle, font_sub, '#CCCCCC', y_sub, spacing=4)
    
    # Bottom tag
    tag_text = "北京中晓律师事务所"
    btag = draw.textbbox((0,0), tag_text, font=font_tag)
    draw.text((w - (btag[2]-btag[0]) - 30, h - 40), tag_text, fill='#666666', font=font_tag)
    
    img.save(output_path, quality=95)
    print(f"✅ 配图: {output_path}")

outdir = "/Users/cinderella/programs/zhongxiao-law-website/articles/illustrations"
os.makedirs(outdir, exist_ok=True)

illustrations = [
    ("中晓律所2026年中总结大会", "上半年处置债权超12亿元，同比增长30%", "🏛️", "#0A2647", "#C0392B", "ill-midyear.png"),
    ("金融机构不良资产处置研讨会", "华展资产&中晓律所联合举办", "🤝", "#16213E", "#0EA5E9", "ill-seminar.png"),
    ("逾2.3亿元金融借款合同纠纷案", "债权本息全额回收，胜诉的里程碑", "⚖️", "#1a1a2e", "#F59E0B", "ill-loan-case.png"),
    ("夫妻共同债务如何认定？", "民法典第1064条·最高院裁判规则解析", "💑", "#0F3460", "#10B981", "ill-marital-debt.png"),
    ("法拍房捡漏还是踩坑？", "不良资产处置中的十大避坑要点", "🏠", "#1A1A2E", "#EF4444", "ill-auction.png"),
    ("保证期间与保证方式法律要点", "担保不是签个字就完事", "📜", "#0D1B2A", "#C0392B", "ill-guarantee.png"),
]

for title, sub, icon, bg, accent, fname in illustrations:
    generate_image(title, sub, icon, bg, accent, os.path.join(outdir, fname))

print(f"\n🎉 共 {len(illustrations)} 张配图已生成")
