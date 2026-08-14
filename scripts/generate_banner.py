"""Script to generate a balanced, professional, non-empty repository banner without logos."""

from pathlib import Path
# pyrefly: ignore [missing-import]
from PIL import Image, ImageDraw, ImageFont


def create_banner():
    # Standard 1280 x 640 GitHub Social / OpenGraph banner
    width, height = 1280, 640
    img = Image.new("RGB", (width, height), color="#09090b")
    draw = ImageDraw.Draw(img)

    # Load system TTF fonts
    font_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_regular = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font_mono = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

    font_repo = ImageFont.truetype(font_mono, 22)
    font_title = ImageFont.truetype(font_bold, 86)
    font_subtitle = ImageFont.truetype(font_regular, 28)
    font_badge = ImageFont.truetype(font_mono, 15)
    font_footer = ImageFont.truetype(font_regular, 15)

    # Subtle refined inner border frame
    draw.rectangle([(40, 40), (width - 40, height - 40)], outline="#222226", width=1)
    
    # Corner accent ticks
    tick_len = 12
    draw.line([(40, 40), (40 + tick_len, 40)], fill="#ffffff", width=2)
    draw.line([(40, 40), (40, 40 + tick_len)], fill="#ffffff", width=2)
    draw.line([(width - 40, 40), (width - 40 - tick_len, 40)], fill="#ffffff", width=2)
    draw.line([(width - 40, 40), (width - 40, 40 + tick_len)], fill="#ffffff", width=2)
    draw.line([(40, height - 40), (40 + tick_len, height - 40)], fill="#ffffff", width=2)
    draw.line([(40, height - 40), (40, height - 40 - tick_len)], fill="#ffffff", width=2)
    draw.line([(width - 40, height - 40), (width - 40 - tick_len, height - 40)], fill="#ffffff", width=2)
    draw.line([(width - 40, height - 40), (width - 40, height - 40 - tick_len)], fill="#ffffff", width=2)

    center_x = width // 2

    # 1. Top Repo Pill: "hul0 / findotype"
    repo_text = "hul0 / findotype"
    repo_bbox = font_repo.getbbox(repo_text)
    rw = repo_bbox[2] - repo_bbox[0]
    rh = repo_bbox[3] - repo_bbox[1]
    
    pill_pad_x = 22
    pill_pad_y = 10
    pill_x1 = center_x - (rw // 2) - pill_pad_x
    pill_y1 = 110
    pill_x2 = center_x + (rw // 2) + pill_pad_x
    pill_y2 = pill_y1 + rh + (2 * pill_pad_y)

    draw.rounded_rectangle([(pill_x1, pill_y1), (pill_x2, pill_y2)], radius=6, fill="#141418", outline="#2e2e36", width=1)
    draw.text((center_x - (rw // 2), pill_y1 + pill_pad_y - 1), repo_text, fill="#e4e4e7", font=font_repo)

    # 2. Main Title: "Findotype"
    title_text = "Findotype"
    title_bbox = font_title.getbbox(title_text)
    tw = title_bbox[2] - title_bbox[0]
    title_y = pill_y2 + 35
    draw.text((center_x - (tw // 2), title_y), title_text, fill="#ffffff", font=font_title)

    # 3. Clear Descriptive Subtitle
    sub_text = "Offline Medical Ontology & Clinical Phenotype Engine"
    sub_bbox = font_subtitle.getbbox(sub_text)
    sw = sub_bbox[2] - sub_bbox[0]
    sub_y = title_y + 105
    draw.text((center_x - (sw // 2), sub_y), sub_text, fill="#a1a1aa", font=font_subtitle)

    # 4. Essential Categorical Tags Row
    tags_row_1 = [
        "Python 3.10+",
        "SQLite FTS5",
        "Biomedical Informatics",
    ]
    tags_row_2 = [
        "Disease Ontology (DOID)",
        "Human Phenotype (HPO)",
        "Zero Runtime Dependencies",
    ]

    def draw_tag_row(tags, y_pos):
        total_w = 0
        tag_widths = []
        for tag in tags:
            bbox = font_badge.getbbox(tag)
            w = (bbox[2] - bbox[0]) + 28
            tag_widths.append(w)
            total_w += w
        total_w += (len(tags) - 1) * 12

        start_x = center_x - (total_w // 2)
        cur_x = start_x
        for tag, w in zip(tags, tag_widths):
            draw.rounded_rectangle([(cur_x, y_pos), (cur_x + w, y_pos + 34)], radius=4, fill="#121215", outline="#27272a", width=1)
            bbox = font_badge.getbbox(tag)
            tw = bbox[2] - bbox[0]
            draw.text((cur_x + (w - tw) // 2, y_pos + 9), tag, fill="#d4d4d8", font=font_badge)
            cur_x += w + 12

    tag_y1 = sub_y + 60
    draw_tag_row(tags_row_1, tag_y1)

    tag_y2 = tag_y1 + 46
    draw_tag_row(tags_row_2, tag_y2)

    # 5. Footer Line & Minimalist Meta
    footer_y = height - 70
    draw.line([(100, footer_y - 15), (width - 100, footer_y - 15)], fill="#18181c", width=1)
    
    foot_left = "Open Source  •  GNU AGPL-3.0  •  CC0 Data"
    foot_right = "github.com/hul0/findotype"
    draw.text((100, footer_y), foot_left, fill="#52525b", font=font_footer)
    
    fr_bbox = font_footer.getbbox(foot_right)
    fr_w = fr_bbox[2] - fr_bbox[0]
    draw.text((width - 100 - fr_w, footer_y), foot_right, fill="#52525b", font=font_footer)

    # Save to assets/images/
    out_dir = Path("assets/images")
    out_dir.mkdir(parents=True, exist_ok=True)

    jpeg_path = out_dir / "banner.jpeg"
    jpg_path = out_dir / "banner.jpg"
    img.save(jpeg_path, "JPEG", quality=98, optimize=True)
    img.save(jpg_path, "JPEG", quality=98, optimize=True)

    print(f"Generated clean banner: {jpeg_path}")


if __name__ == "__main__":
    create_banner()
