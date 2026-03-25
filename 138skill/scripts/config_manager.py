#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
139邮箱配置管理器
"""
import json
import os
import argparse
import sys

from common import configure_console_io, normalize_username

configure_console_io()

CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
CONFIG_FILE = os.path.join(CONFIG_DIR, '139mail.conf')

DEFAULT_CONFIG = {
    "username": "",
    "smtp_server": "smtp.139.com",
    "smtp_port": 465,
    "imap_server": "imap.139.com",
    "imap_port": 993
}

# token 文件路径
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'token.txt')

def ensure_config_dir():
    """确保配置目录存在"""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

def check_config():
    """检查配置文件是否存在且有效（需要 username 和 token.txt）"""
    if not os.path.exists(CONFIG_FILE):
        return False

    # 检查 token.txt 是否存在
    if not os.path.exists(TOKEN_FILE):
        return False

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return bool(config.get('username'))
    except:
        return False

def save_config(username):
    """保存配置（不需要保存授权码，通过 token.txt 动态获取）"""
    ensure_config_dir()

    config = DEFAULT_CONFIG.copy()
    config['username'] = normalize_username(username)

    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    # 设置文件权限
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except:
        pass

    print(f"配置已保存到: {CONFIG_FILE}")
    print(f"请确保 token.txt 已配置 accessToken")
    return True

def load_config():
    """加载配置"""
    if not os.path.exists(CONFIG_FILE):
        return None
    
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
    config['username'] = normalize_username(config.get('username'))
    return config

def show_config():
    """显示当前配置"""
    config = load_config()
    if not config:
        print("未找到配置文件")
        return False

    # 检查 token 状态
    token_status = "已配置" if os.path.exists(TOKEN_FILE) else "未配置"

    print("当前配置：")
    print(f"  邮箱账号: {config.get('username', '未设置')}")
    print(f"  Token: {token_status} (通过 token.txt 动态获取授权码)")
    print(f"  SMTP服务器: {config.get('smtp_server', 'smtp.139.com')}")
    print(f"  SMTP端口: {config.get('smtp_port', 465)}")
    print(f"  IMAP服务器: {config.get('imap_server', 'imap.139.com')}")
    print(f"  IMAP端口: {config.get('imap_port', 993)}")
    return True

def main():
    parser = argparse.ArgumentParser(description='139邮箱配置管理')
    parser.add_argument('action', choices=['check', 'save', 'show'], help='操作类型')
    parser.add_argument('--username', help='邮箱账号（如 13800138000@139.com）')

    args = parser.parse_args()

    if args.action == 'check':
        if check_config():
            print("已配置")
            return 0
        else:
            print("未配置")
            return 1

    elif args.action == 'save':
        if not args.username:
            print("错误：需要提供 --username")
            return 1

        save_config(args.username)
        return 0

    elif args.action == 'show':
        show_config()
        return 0

if __name__ == '__main__':
    exit(main())
