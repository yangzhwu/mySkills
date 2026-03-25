#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
139邮箱共享连接辅助模块
默认使用兼容 139 服务器的 TLS 配置。
"""
import os
import smtplib
import ssl
import subprocess
import sys

import imapclient

from common import normalize_username

# 获取脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GET_AUTH_CODE_SCRIPT = os.path.join(SCRIPT_DIR, 'get_auth_code.py')


def get_auth_code_from_token():
    """通过 token.txt 获取授权码"""
    try:
        result = subprocess.run(
            [sys.executable, GET_AUTH_CODE_SCRIPT],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=SCRIPT_DIR
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())

        # 从输出中提取授权码（最后一行）
        output_lines = result.stdout.strip().split('\n')
        auth_code = output_lines[-1] if output_lines else None

        if not auth_code:
            raise RuntimeError("未能获取授权码")

        return auth_code
    except subprocess.TimeoutExpired:
        raise RuntimeError("获取授权码超时")
    except Exception as e:
        raise RuntimeError(f"获取授权码失败: {e}")


def build_compatible_ssl_context():
    """兼容 139 服务器的 TLS 上下文。"""
    ssl_context = ssl._create_unverified_context()
    ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')
    return ssl_context


def get_login_credentials(config):
    """获取登录凭据（通过 token 动态获取授权码）"""
    username = normalize_username(config.get('username'))
    # 从 token 动态获取授权码
    password = get_auth_code_from_token()
    return username, password


def connect_imap(config, timeout=None):
    """连接并登录 IMAP，默认使用兼容模式。"""
    username, password = get_login_credentials(config)
    server = imapclient.IMAPClient(
        config['imap_server'],
        port=config['imap_port'],
        ssl=True,
        ssl_context=build_compatible_ssl_context(),
        timeout=timeout,
    )
    server.login(username, password)
    return server


def connect_smtp(config, timeout=10):
    """连接并登录 SMTP，默认使用兼容模式。"""
    username, password = get_login_credentials(config)
    server = smtplib.SMTP_SSL(
        config['smtp_server'],
        config['smtp_port'],
        context=build_compatible_ssl_context(),
        timeout=timeout,
    )
    server.login(username, password)
    return server
