"""
TOTP 两步验证（MFA）工具模块
使用 pyotp 和 qrcode 库实现，兼容 Google Authenticator
"""
import pyotp
import qrcode
import base64
from io import BytesIO


def generate_mfa(username: str, title: str = "BlackPotBPanel", interval: int = 30) -> dict:
    """生成 MFA 密钥和二维码

    Args:
        username: 用户名（用于 otpauth URI 中的标识）
        title: 标题（显示在 Authenticator App 中）
        interval: TOTP 刷新间隔（秒），默认 30

    Returns:
        dict: {"secret": "BASE32密钥", "qr_image": "data:image/png;base64,..."}
    """
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret, interval=interval)
    uri = totp.provisioning_uri(username, issuer_name=title)

    img = qrcode.make(uri)
    buf = BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    return {
        "secret": secret,
        "qr_image": f"data:image/png;base64,{qr_b64}"
    }


def verify_code(code: str, secret: str, interval: int = 30) -> bool:
    """验证 TOTP 验证码

    验证当前时间窗口和上一个时间窗口的码（提供时间偏差容差）

    Args:
        code: 用户输入的 6 位验证码
        secret: Base32 密钥
        interval: TOTP 刷新间隔（秒）

    Returns:
        bool: 验证是否通过
    """
    totp = pyotp.TOTP(secret, interval=interval)
    # 验证当前 + 上一个窗口，兼容手机时间偏差
    return totp.verify(code, valid_window=1)
