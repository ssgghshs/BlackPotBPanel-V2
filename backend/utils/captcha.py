import random
import string
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import base64

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
    
    # 创建图片
    width, height = 120, 40
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # 尝试使用系统字体，如果失败则使用默认字体
    try:
        # 在Windows系统上尝试使用arial字体
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        try:
            # 在Linux/Mac系统上尝试使用DejaVuSans字体
            font = ImageFont.truetype("/opt/blackpotbpanel-v2/app/backend/data/ttf/DejaVuSans.ttf", 24)
        except:
            # 使用默认字体
            font = ImageFont.load_default()
    
    # 绘制验证码文本
    text_width = draw.textlength(captcha_text, font=font)
    text_height = 30  # 近似值
    x = (width - text_width) / 2
    y = (height - text_height) / 2
    draw.text((x, y), captcha_text, fill=(0, 0, 0), font=font)
    
    # 添加干扰线
    for _ in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)), width=1)
    
    # 添加干扰点
    for _ in range(30):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    
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