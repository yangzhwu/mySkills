#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 accessToken 获取 139 邮箱授权码
"""
import hashlib
import json
import os
import sys
import time
import uuid
import base64
from datetime import datetime
from hashlib import sha256 as SHA256
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import configure_console_io

configure_console_io()

# 配置常量
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'token.txt')
API_URL = "http://117.161.135.20:180/keyManage/getAuthCode"
APPID = "100000082"
INTERFACE_VERSION = "1.0"
USER_INFORMATION = "userInformation"
TYPE = "mail"
APPKEY = "894C9B429372943D1CBECC86F0C237A3"
AES_KEY = APPKEY[:16]  # 前16位

# RSA 公钥（用于加密 encryptJson）
RSA_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDxDjWIdgsGAtyUqAo4rc0r4gd66
wzPblqhr6u7+hA9ycERpQWDdwrTA/x8OLvn4NhvwlL13e2M7vDjq2YX6PKHIJ0jC9
31a7ugHmZgCrPEKInigLy3a1NN6BUH+JPevmIi5mmFdpcl8gam+jbJ3mVSDyrz9Z
C+Yfr8bU2jkV2XPwIDAQAB
-----END PUBLIC KEY-----"""


def read_token():
    """从 token.txt 读取 accessToken"""
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(f"Token 文件不存在: {TOKEN_FILE}")

    with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
        token = f.read().strip()

    if not token or token == "请在此文件中填入您的 accessToken":
        raise ValueError("Token 文件中未配置 accessToken")

    return token


def generate_sign(access_token: str, token_type: str, appkey: str) -> str:
    """生成签名: MD5(accessToken + type + appkey)，hex编码"""
    raw = access_token + token_type + appkey
    return hashlib.md5(raw.encode('utf-8')).hexdigest()


def build_request_header():
    """构建请求头"""
    # 17位时间戳格式: yyyyMMddHHmmssSSS
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S") + str(int(datetime.now().microsecond / 1000)).zfill(3)
    return {
        "appid": APPID,
        "timestamp": timestamp,
        "interfaceVersion": INTERFACE_VERSION,
        "traceId": f"trace_{timestamp}_{uuid.uuid4().hex[:5]}"
    }


def rsa_encrypt(data: str) -> str:
    """使用 RSA 公钥加密数据（分段加密，和 Java encryptByPublicKey 一致）"""
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization

    # 加载公钥
    public_key = serialization.load_pem_public_key(
        RSA_PUBLIC_KEY.encode('utf-8'),
        backend=default_backend()
    )

    # RSA 2048 位：Java 中 MAX_ENCRYPT_BLOCK = 117 (RSA/ECB/PKCS1Padding)
    max_encrypt_block = 117

    data_bytes = data.encode('utf-8')

    if len(data_bytes) <= max_encrypt_block:
        # 短数据直接加密
        encrypted = public_key.encrypt(
            data_bytes,
            padding.PKCS1v15()
        )
        return base64.b64encode(encrypted).decode('utf-8')
    else:
        # 长数据分段加密（参考 Java RSAUtils.encryptByPublicKey）
        encrypted_chunks = []
        for i in range(0, len(data_bytes), max_encrypt_block):
            chunk = data_bytes[i:i + max_encrypt_block]
            encrypted = public_key.encrypt(
                chunk,
                padding.PKCS1v15()
            )
            encrypted_chunks.append(encrypted)

        # 合并加密块
        result = b''.join(encrypted_chunks)
        return base64.b64encode(result).decode('utf-8')


def build_request_body(access_token: str) -> dict:
    """构建请求体（JSON格式，encryptJson 只包含 accessToken）"""
    sign = generate_sign(access_token, TYPE, APPKEY)

    # 只加密 accessToken
    biz_data = {
        "accessToken": access_token
    }

    biz_json = json.dumps(biz_data)
    # print(f"待加密数据: {biz_json}", file=sys.stderr)
    # print(f"数据长度: {len(biz_json)}", file=sys.stderr)

    encrypted_json = rsa_encrypt(biz_json)
    # print(f"加密后长度: {len(encrypted_json)}", file=sys.stderr)

    # sign 和 type 放在外层
    return {
        "encryptJson": encrypted_json,
        "userInformation": USER_INFORMATION,
        "type": TYPE,
        "sign": sign
    }


def aes_decrypt(encrypted_data: str) -> str:
    """AES 解密 authCode"""
    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import unpad

        # AES key 必须是16字节
        key = AES_KEY.encode('utf-8')

        # 解密: 先 Base64 解码，再 AES 解密
        encrypted_bytes = base64.b64decode(encrypted_data)

        # IV 为16个零字节
        iv = b'\x00' * 16

        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(encrypted_bytes), AES.block_size)

        return decrypted.decode('utf-8')
    except Exception as e:
        # 如果没有 pycryptodome，尝试用内置库
        return aes_decrypt_fallback(encrypted_data)


def aes_decrypt_fallback(encrypted_data: str) -> str:
    """使用内置库实现 AES 解密（备用）"""
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives import padding
        from cryptography.hazmat.backends import default_backend

        key = AES_KEY.encode('utf-8')
        iv = b'\x00' * 16

        encrypted_bytes = base64.b64decode(encrypted_data)

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded = decryptor.update(encrypted_bytes) + decryptor.finalize()

        # 去除 PKCS5Padding 填充
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded) + unpadder.finalize()

        return data.decode('utf-8')
    except Exception as e:
        raise RuntimeError(f"AES 解密失败: {e}")


def get_auth_code() -> str:
    """
    获取授权码主流程
    1. 读取 token.txt 获取 accessToken
    2. 构建请求并调用 API
    3. 解析响应，解密 authCode
    """
    # print("正在获取授权码...")

    # 1. 读取 token
    access_token = read_token()

    # 2. 构建请求
    headers = build_request_header()
    body = build_request_body(access_token)

    # 3. 发送请求
    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json=body,
            timeout=30
        )
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"API 请求失败: {e}")

    # 4. 解析响应
    try:
        result = response.json()
    except json.JSONDecodeError as e:
        raise RuntimeError(f"响应解析失败: {e}, 内容: {response.text}")

    # print(f"  响应: {json.dumps(result, ensure_ascii=False)[:200]}")

    # 5. 检查结果
    # 响应格式可能是 {"resultCode": "103000", "data": {...}}
    # 或 {"response": {"resultCode": "000000", "data": {...}}}
    result_code = result.get("resultCode") or result.get("response", {}).get("resultCode")
    if result_code not in ("000000", "103000"):
        result_desc = result.get("desc") or result.get("response", {}).get("resultDesc", "未知错误")
        raise RuntimeError(f"API 返回错误: {result_desc}")

    # 6. 获取并解密 authCode
    data = result.get("data") or result.get("response", {}).get("data", {})
    encrypted_auth_code = data.get("authCode")

    if not encrypted_auth_code:
        # 尝试从 result 直接获取
        encrypted_auth_code = result.get("data", {}).get("authCode")

    if not encrypted_auth_code:
        raise RuntimeError("响应中未找到 authCode")

    # print(f"  加密的 authCode: {encrypted_auth_code}")

    # 7. AES 解密
    auth_code = aes_decrypt(encrypted_auth_code)
    # print(f"  解密后的授权码: {auth_code}")

    return auth_code


def main():
    try:
        auth_code = get_auth_code()
        print(auth_code)
        return 0
    except Exception as e:
        print(f"\n错误: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    exit(main())
