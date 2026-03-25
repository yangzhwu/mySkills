#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件管理：标记已读/未读、恢复等
"""
import imapclient
import ssl
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import configure_console_io
from config_manager import load_config
from mail_client import connect_imap

configure_console_io()


TRASH_FOLDER_CANDIDATES = ['已删除', 'Deleted Messages', 'Trash']


def connect_server(config):
    """连接服务器"""
    return connect_imap(config)


def resolve_folder(server, candidates):
    """从候选列表中找到当前邮箱实际存在的文件夹名。"""
    folder_names = {name for _, _, name in server.list_folders()}
    for candidate in candidates:
        if candidate in folder_names:
            return candidate
    return None


def resolve_trash_folder(server):
    """定位已删除/垃圾箱文件夹。"""
    return resolve_folder(server, TRASH_FOLDER_CANDIDATES)


def move_messages(server, msg_ids, target_folder):
    """优先使用 IMAP MOVE，失败时回退到 copy+delete。"""
    try:
        server.move(msg_ids, target_folder)
    except Exception:
        server.copy(msg_ids, target_folder)
        server.delete_messages(msg_ids)
        server.expunge()


def list_messages(server, folder='INBOX', limit=20):
    """列出邮件"""
    server.select_folder(folder)
    messages = server.search(['ALL'])
    
    if not messages:
        print(f"文件夹 '{folder}' 中没有邮件")
        return
    
    messages = messages[-limit:]
    
    from email.header import decode_header
    import email
    
    print(f"\n文件夹: {folder} (显示最新 {len(messages)} 封)")
    print("="*60)
    
    for msg_id in reversed(messages):
        fetch_data = server.fetch([msg_id], ['BODY.PEEK[HEADER]'])
        raw_header = fetch_data[msg_id][b'BODY[HEADER]']
        msg = email.message_from_bytes(raw_header)
        
        # 解码
        def decode_str(s):
            if not s:
                return ""
            decoded_parts = decode_header(s)
            result = ""
            for part, charset in decoded_parts:
                if isinstance(part, bytes):
                    try:
                        result += part.decode(charset or 'utf-8', errors='ignore')
                    except:
                        result += part.decode('utf-8', errors='ignore')
                else:
                    result += part
            return result
        
        subject = decode_str(msg.get('Subject', '无主题'))
        sender = decode_str(msg.get('From', '未知'))
        
        flags = server.fetch([msg_id], ['FLAGS'])
        is_unread = b'\\Seen' not in flags[msg_id][b'FLAGS']
        status = "📧" if is_unread else "✓"
        
        # 截断显示
        subject = (subject[:40] + '...') if len(subject) > 40 else subject
        sender = (sender[:30] + '...') if len(sender) > 30 else sender
        
        print(f"{status} ID:{msg_id:4d} | {sender:33s} | {subject}")

def main():
    parser = argparse.ArgumentParser(description='邮件管理')
    parser.add_argument('--list', action='store_true', help='列出收件箱邮件')
    parser.add_argument('--list-trash', action='store_true', help='列出已删除邮件')
    parser.add_argument('--mark-read', type=int, help='标记指定ID为已读')
    parser.add_argument('--mark-unread', type=int, help='标记指定ID为未读')
    parser.add_argument('--restore', type=int, help='从已删除恢复指定ID邮件')
    parser.add_argument('--permanent-delete', type=int, help='永久删除指定ID邮件')
    parser.add_argument('--limit', type=int, default=20, help='显示数量限制')
    
    args = parser.parse_args()
    
    config = load_config()
    if not config:
        print("错误：未配置139邮箱账号")
        return 1
    
    try:
        with connect_server(config) as server:
            if args.list:
                list_messages(server, 'INBOX', args.limit)
            
            elif args.list_trash:
                trash_folder = resolve_trash_folder(server)
                if not trash_folder:
                    print("无法访问已删除文件夹")
                    return 1
                list_messages(server, trash_folder, args.limit)
            
            elif args.mark_read:
                server.select_folder('INBOX')
                server.add_flags([args.mark_read], ['\\Seen'])
                print(f"✓ 邮件 {args.mark_read} 已标记为已读")
            
            elif args.mark_unread:
                server.select_folder('INBOX')
                server.remove_flags([args.mark_unread], ['\\Seen'])
                print(f"✓ 邮件 {args.mark_unread} 已标记为未读")
            
            elif args.restore:
                trash_folder = resolve_trash_folder(server)
                if not trash_folder:
                    print("错误：未找到已删除文件夹，无法恢复邮件")
                    return 1

                # 从已删除恢复到收件箱
                server.select_folder(trash_folder)
                move_messages(server, [args.restore], 'INBOX')
                print(f"✓ 邮件 {args.restore} 已恢复到收件箱")
            
            elif args.permanent_delete:
                trash_folder = resolve_trash_folder(server)
                if not trash_folder:
                    print("错误：未找到已删除文件夹，无法永久删除邮件")
                    return 1

                server.select_folder(trash_folder)
                server.delete_messages([args.permanent_delete])
                server.expunge()
                print(f"✓ 邮件 {args.permanent_delete} 已永久删除")
            
            else:
                parser.print_help()
        
        return 0
        
    except imapclient.exceptions.LoginError as e:
        print(f"登录失败: {e}")
        print("请检查账号是否正确")
        return 1
    except ssl.SSLError as e:
        print(f"SSL连接错误: {e}")
        print("当前脚本已默认使用 139 邮箱兼容模式。")
        return 1
    except Exception as e:
        print(f"错误: {e}")
        return 1

if __name__ == '__main__':
    exit(main())
