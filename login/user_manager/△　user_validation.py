# user_manager/user_validation.py
import re
from user_manager.config import REQUIRED_FIELDS, MIN_PASSWORD_LENGTH, MYNUMBER_LENGTH

def validate_required_fields(data: dict) -> bool:
    for field in REQUIRED_FIELDS:
        if field not in data or not data[field]:
            raise ValueError(f"必須フィールドが不足しています: {field}")
    return True

def validate_email(email: str) -> bool:
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(pattern, email):
        raise ValueError("不正なメールアドレスです")
    return True

def validate_mynumber(mynumber: str) -> bool:
    if len(mynumber) != MYNUMBER_LENGTH or not mynumber.isdigit():
        raise ValueError("不正なマイナンバーです")
    return True

def validate_password(password: str) -> bool:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError("パスワードは最低でも {} 文字必要です".format(MIN_PASSWORD_LENGTH))
    return True
