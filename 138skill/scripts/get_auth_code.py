#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取授权码模块
支持从预置文件读取和服务端接口获取
"""
import os
import json

# 获取 skill 根目录
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRESET_FILE = os.path.join(SKILL_DIR, 'config', 'preset_auth.txt')
CONFIG_FILE = os.path.join(SKILL_DIR, 'config', '139mail.conf')


def get_auth_code_from_preset():
    """从预置文件中读取授权码"""
    if not os.path.exists(PRESET_FILE):
        return None

    with open(PRESET_FILE, 'r', encoding='utf-8') as f:
        code = f.read().strip()

    return code if code else None


def get_auth_code_from_service(username):
    """
    从服务端接口获取授权码
    TODO: 接口完成后实现具体的调用逻辑
    """
    # TODO: 实现服务端接口调用
    # 示例:
    # import requests
    # response = requests.post('http://your-api/get_auth_code', json={'username': username})
    # return response.json().get('auth_code')
    raise NotImplementedError("服务端接口尚未完成，请使用预置授权码或手动配置")


def get_auth_code(username=None):
    """
    获取授权码的入口函数
    优先级：预置文件 > 服务端接口
    """
    # 1. 优先从预置文件读取
    preset_code = get_auth_code_from_preset()
    if preset_code:
        return preset_code

    # 2. 预置文件没有，则尝试从服务端获取
    if username:
        return get_auth_code_from_service(username)

    return None


def get_preset_auth_code():
    """获取预置授权码（仅读取文件）"""
    return get_auth_code_from_preset()


def set_preset_auth_code(code):
    """设置预置授权码"""
    with open(PRESET_FILE, 'w', encoding='utf-8') as f:
        f.write(code)
    return True


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == '--get':
            # 获取授权码
            username = sys.argv[2] if len(sys.argv) > 2 else None
            code = get_auth_code(username)
            if code:
                print(code)
            else:
                print("未找到授权码", file=sys.stderr)
                sys.exit(1)
        elif sys.argv[1] == '--set':
            # 设置预置授权码
            if len(sys.argv) > 2:
                set_preset_auth_code(sys.argv[2])
                print("预置授权码已保存")
            else:
                print("用法: python get_auth_code.py --set <授权码>", file=sys.stderr)
                sys.exit(1)
        elif sys.argv[1] == '--show':
            # 显示当前预置授权码
            code = get_preset_auth_code()
            if code:
                print(f"当前预置授权码: {code}")
            else:
                print("未设置预置授权码")
    else:
        print("用法:")
        print("  python get_auth_code.py --get [username]  获取授权码")
        print("  python get_auth_code.py --set <授权码>    设置预置授权码")
        print("  python get_auth_code.py --show           显示当前预置授权码")
