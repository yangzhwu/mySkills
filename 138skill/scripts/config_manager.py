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
from get_auth_code import get_auth_code, set_preset_auth_code, get_preset_auth_code, PRESET_FILE

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

def ensure_config_dir():
    """确保配置目录存在"""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

def check_config():
    """检查配置文件是否存在且有效（只检查username，密码从preset获取）"""
    if not os.path.exists(CONFIG_FILE):
        return False

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return bool(config.get('username'))
    except:
        return False

def save_config(username):
    """保存配置（密码只从preset_auth.txt读取）"""
    ensure_config_dir()

    config = DEFAULT_CONFIG.copy()
    config['username'] = normalize_username(username)

    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    # 设置文件权限（仅Windows上可读取，Unix系统会限制权限）
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except:
        pass

    print(f"配置已保存到: {CONFIG_FILE}")
    return True


def load_config():
    """加载配置（密码从preset_auth.txt读取）"""
    if not os.path.exists(CONFIG_FILE):
        return None

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
    config['username'] = normalize_username(config.get('username'))

    # 从预设文件获取授权码
    preset_code = get_preset_auth_code()
    if preset_code:
        config['password'] = preset_code

    return config

def show_config():
    """显示当前配置（密码从preset_auth.txt读取）"""
    config = load_config()
    if not config:
        print("未找到配置文件")
        return False

    print("当前配置：")
    print(f"  邮箱账号: {config.get('username', '未设置')}")
    print(f"  授权码: {'已配置' if config.get('password') else '未设置'}（从 preset_auth.txt 读取）")
    print(f"  SMTP服务器: {config.get('smtp_server', 'smtp.139.com')}")
    print(f"  SMTP端口: {config.get('smtp_port', 465)}")
    print(f"  IMAP服务器: {config.get('imap_server', 'imap.139.com')}")
    print(f"  IMAP端口: {config.get('imap_port', 993)}")
    return True

def main():
    parser = argparse.ArgumentParser(description='139邮箱配置管理')
    parser.add_argument('action', choices=['check', 'save', 'show'], help='操作类型')
    parser.add_argument('--username', help='邮箱账号')

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
