#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件分拣 - 移动邮件到不同文件夹
"""
import imapclient
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import configure_console_io
from config_manager import load_config
from mail_client import connect_imap

configure_console_io()

TRASH_FOLDER_CANDIDATES = {'已删除', 'deleted messages', 'trash'}


def connect_server(config):
    """连接服务器"""
    return connect_imap(config)


def move_messages(server, msg_ids, target_folder):
    """优先使用 IMAP MOVE，失败时回退到 copy+delete。"""
    try:
        server.move(msg_ids, target_folder)
    except Exception:
        server.copy(msg_ids, target_folder)
        server.delete_messages(msg_ids)
        server.expunge()


def list_folders(server):
    """列出所有文件夹"""
    folders = server.list_folders()
    print("\n邮箱文件夹列表：")
    print("="*40)
    for flags, delimiter, name in folders:
        print(f"  - {name}")
    print()


def ensure_target_folder(server, target_folder):
    """确保目标文件夹存在，不存在时自动创建。"""
    folder_name = (target_folder or "").strip()
    if not folder_name:
        raise ValueError("目标文件夹不能为空")

    folder_names = {name for _, _, name in server.list_folders()}
    if folder_name in folder_names:
        return folder_name

    server.create_folder(folder_name)
    print(f"已自动创建文件夹: '{folder_name}'")
    return folder_name

def move_mail(msg_id, target_folder):
    """移动邮件"""
    config = load_config()
    if not config:
        print("错误：未配置139邮箱账号")
        return 1

    normalized_target = (target_folder or "").strip()
    if normalized_target.lower() in TRASH_FOLDER_CANDIDATES:
        print("错误：不支持通过 move_mail.py 将邮件移动到已删除文件夹")
        return 1
    
    try:
        with connect_server(config) as server:
            server.select_folder('INBOX')
            
            # 检查邮件是否存在
            messages = server.search(['ALL'])
            if int(msg_id) not in messages:
                print(f"错误：收件箱中没有 ID 为 {msg_id} 的邮件")
                return 1

            target_folder = ensure_target_folder(server, normalized_target)
            move_messages(server, [int(msg_id)], target_folder)

            print(f"✓ 邮件 {msg_id} 已移动到 '{target_folder}'")
            return 0
            
    except imapclient.exceptions.IMAPClientError as e:
        print(f"移动失败: {e}")
        return 1
    except ValueError as e:
        print(f"错误: {e}")
        return 1
    except Exception as e:
        print(f"错误: {e}")
        return 1

def main():
    parser = argparse.ArgumentParser(description='邮件分拣')
    parser.add_argument('--list-folders', action='store_true', help='列出所有文件夹')
    parser.add_argument('--move', type=int, help='要移动的邮件ID')
    parser.add_argument('--to', help='目标文件夹（不存在则自动创建，不能是已删除文件夹）')
    
    args = parser.parse_args()
    
    config = load_config()
    if not config:
        print("错误：未配置139邮箱账号")
        return 1
    
    try:
        with connect_server(config) as server:
            if args.list_folders:
                list_folders(server)
            elif args.move and args.to:
                return move_mail(args.move, args.to)
            else:
                parser.print_help()
        
        return 0
        
    except Exception as e:
        print(f"错误: {e}")
        return 1

if __name__ == '__main__':
    exit(main())
