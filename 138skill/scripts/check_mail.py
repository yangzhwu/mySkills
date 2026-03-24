#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
139邮箱邮件查看器
"""
import imapclient
import ssl
import email
from email.header import decode_header
from datetime import datetime, timedelta
import argparse
import os
import sys

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import configure_console_io
from config_manager import load_config
from mail_client import connect_imap

configure_console_io()


def build_date_search_criteria(date_str):
    """将 YYYY-MM-DD 转为当天的 IMAP 搜索条件。"""
    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    next_date = target_date + timedelta(days=1)
    return [
        'SINCE', target_date.strftime('%d-%b-%Y'),
        'BEFORE', next_date.strftime('%d-%b-%Y'),
    ]

def decode_str(s):
    """解码邮件主题/发件人等字段"""
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

def check_mail(unread_only=False, limit=20, date_str=None):
    """检查邮件"""
    config = load_config()
    if not config:
        print("错误：未配置139邮箱账号")
        print("请先运行: python scripts/config_manager.py save --username <账号> --password-stdin")
        return 1
    
    try:
        print(f"正在连接 {config['imap_server']}...")
        
        # 连接IMAP服务器
        with connect_imap(config) as server:
            print(f"登录成功: {config['username']}")
            
            # 选择收件箱
            server.select_folder('INBOX')
            
            # 搜索邮件
            if date_str:
                criteria = build_date_search_criteria(date_str)
                if unread_only:
                    criteria.append('UNSEEN')
                messages = server.search(criteria)
                title = f"{date_str} 的未读邮件" if unread_only else f"{date_str} 的邮件"
                print(f"\n{title}: {len(messages)} 封")
            elif unread_only:
                messages = server.search(['UNSEEN'])
                print(f"\n未读邮件: {len(messages)} 封")
            else:
                messages = server.search(['ALL'])
                print(f"\n收件箱共 {len(messages)} 封邮件")
            
            if not messages:
                print("没有邮件" if not unread_only else "没有未读邮件")
                return 0
            
            # 获取最新的N封邮件
            messages = messages[-limit:]
            
            print("\n" + "="*60)
            for msg_id in reversed(messages):
                # 获取邮件头部信息
                fetch_data = server.fetch([msg_id], ['BODY.PEEK[HEADER]'])
                raw_header = fetch_data[msg_id][b'BODY[HEADER]']
                msg = email.message_from_bytes(raw_header)
                
                # 解码主题和发件人
                subject = decode_str(msg.get('Subject', '无主题'))
                sender = decode_str(msg.get('From', '未知发件人'))
                date = msg.get('Date', '未知日期')
                
                # 获取已读状态
                flags = server.fetch([msg_id], ['FLAGS'])
                is_unread = b'\\Seen' not in flags[msg_id][b'FLAGS']
                
                status = "[未读]" if is_unread else "[已读]"
                print(f"\n{status} ID: {msg_id}")
                print(f"   发件人: {sender}")
                print(f"   主题: {subject}")
                print(f"   日期: {date}")
                print("-"*60)
            
            return 0
            
    except imapclient.exceptions.LoginError as e:
        print(f"登录失败: {e}")
        print("\n可能原因：")
        print("  1. 账号格式错误，应为: 136xxxxxxxxx@139.com")
        print("  2. 使用了登录密码而非授权码")
        print("  3. 授权码已过期，请重新获取")
        print("  4. 未在网页版开启IMAP服务")
        return 1
    except ValueError:
        print("错误：--date 格式必须为 YYYY-MM-DD，例如 2026-03-12")
        return 1
    except ssl.SSLError as e:
        print(f"SSL连接错误: {e}")
        print("\n当前脚本已默认使用 139 邮箱兼容模式。")
        print("如仍失败，请检查：")
        print("  1. 确保Python >= 3.8")
        print("  2. 确认当前网络没有拦截 IMAP SSL 连接")
        return 1
    except Exception as e:
        print(f"错误: {e}")
        return 1

def main():
    parser = argparse.ArgumentParser(description='查看139邮箱邮件')
    parser.add_argument('--unread', action='store_true', help='只显示未读邮件')
    parser.add_argument('--limit', type=int, default=20, help='显示邮件数量限制')
    parser.add_argument('--date', help='按日期查看邮件，格式 YYYY-MM-DD')
    
    args = parser.parse_args()
    return check_mail(unread_only=args.unread, limit=args.limit, date_str=args.date)

if __name__ == '__main__':
    exit(main())
