#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
139邮箱共享连接辅助模块
默认使用兼容 139 服务器的 TLS 配置。
"""
import smtplib
import ssl

import imapclient

from common import normalize_username


def build_compatible_ssl_context():
    """兼容 139 服务器的 TLS 上下文。"""
    ssl_context = ssl._create_unverified_context()
    ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')
    return ssl_context


def get_login_credentials(config):
    """获取规范化后的登录凭据。"""
    return normalize_username(config.get('username')), config.get('password')


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
