import random
import string
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import base64
from config.settings import settings

def generate_captcha(length=4):
    """
    生成验证码图片和文本
    
    Args:
        length (int): 验证码长度，默认为4
        
    Returns:
        tuple: (验证码文本, base64编码的图片)
    """
    # 生成随机验证码文本
    captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    
    # 创建高分辨率图片(2x)，用于抗锯齿后缩放，使文字更圆润
    scale = 2
    width, height = 140, 48
    image = Image.new('RGB', (width * scale, height * scale), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # 使用配置中的TTF字体文件，加大字号
    font_size = 36 * scale
    try:
        font = ImageFont.truetype(settings.TTF_FONT_PATH, font_size)
    except:
        font = ImageFont.load_default()
    
    # 逐字符绘制，带轻微随机旋转，增加辨识度与圆润感
    cursor_x = 14 * scale
    char_spacing = 26 * scale
    for ch in captcha_text:
        # 创建单个字符的临时图层
        char_img = Image.new('RGBA', (font_size + 10, font_size + 10), (255, 255, 255, 0))
        char_draw = ImageDraw.Draw(char_img)
        # 使用 stroke 模拟加粗效果
        text_color = (random.randint(10, 80), random.randint(10, 80), random.randint(10, 80))
        stroke_color = (random.randint(10, 60), random.randint(10, 60), random.randint(10, 60))
        char_draw.text((5, 5), ch, fill=text_color, font=font,
                       stroke_width=3, stroke_fill=stroke_color)
        # 轻微随机旋转 (-8° ~ 8°)
        angle = random.uniform(-8, 8)
        char_img = char_img.rotate(angle, resample=Image.BICUBIC, expand=False)
        # 随机垂直偏移
        y_offset = random.randint(-4 * scale, 4 * scale)
        image.paste(char_img, (int(cursor_x), int((height * scale - font_size) / 2) + y_offset), char_img)
        cursor_x += char_spacing
    
    # 添加贝塞尔曲线干扰线，更柔和
    for _ in range(4):
        points = [(random.randint(0, width * scale), random.randint(0, height * scale)) for _ in range(4)]
        line_color = (random.randint(100, 220), random.randint(100, 220), random.randint(100, 220))
        # 用多段折线模拟曲线
        for i in range(len(points) - 1):
            draw.line([points[i], points[i + 1]], fill=line_color, width=2)
    
    # 添加圆形干扰点，更圆润
    for _ in range(40):
        cx = random.randint(0, width * scale)
        cy = random.randint(0, height * scale)
        r = random.randint(2, 5)
        dot_color = (random.randint(100, 230), random.randint(100, 230), random.randint(100, 230))
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=dot_color)
    
    # 缩放到目标尺寸，使用 LANCZOS 抗锯齿，使文字边缘更圆润平滑
    image = image.resize((width, height), Image.LANCZOS)
    
    # 轻微高斯模糊，进一步柔化边缘
    image = image.filter(ImageFilter.SMOOTH)
    
    # 将图片转换为base64
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return captcha_text, img_str

def verify_captcha(input_captcha, correct_captcha):
    """
    验证验证码
    
    Args:
        input_captcha (str): 用户输入的验证码
        correct_captcha (str): 正确的验证码
        
    Returns:
        bool: 验证结果
    """
    if not input_captcha or not correct_captcha:
        return False
    return input_captcha.lower() == correct_captcha.lower()