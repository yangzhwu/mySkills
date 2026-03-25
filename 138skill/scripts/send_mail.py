#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送邮件
"""
import smtplib
import ssl
import mimetypes
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header
from email.utils import formataddr, formatdate
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import configure_console_io
from config_manager import CONFIG_FILE, load_config
from mail_client import connect_smtp

configure_console_io()


def parse_recipients(to_addr):
    """解析收件人字符串，支持逗号或分号分隔多个地址。
    如果收件人是纯手机号（11位数字），自动补全 @139.com 后缀。
    """
    recipients = []
    for item in (to_addr or "").replace(";", ",").split(","):
        address = item.strip()
        if address:
            # 如果是11位纯数字（手机号），自动补全 @139.com
            if address.isdigit() and len(address) == 11:
                address = f"{address}@139.com"
            recipients.append(address)

    if not recipients:
        raise ValueError("至少需要一个有效收件人邮箱")

    return recipients


def attach_files(msg, attachments):
    """将本地文件作为附件加入邮件（模仿邮箱大师格式）。"""
    from email.header import Header

    for attachment in attachments:
        file_path = os.path.abspath(os.path.expanduser(attachment))
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"附件不存在: {attachment}")

        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            maintype, subtype = mime_type.split("/", 1)
        else:
            maintype, subtype = "application", "octet-stream"

        with open(file_path, "rb") as file_obj:
            part = MIMEBase(maintype, subtype)
            part.set_payload(file_obj.read())

        encoders.encode_base64(part)
        filename = os.path.basename(file_path)

        # 使用 RFC 2047 编码文件名（模仿邮箱大师）
        encoded_filename = Header(filename, 'utf-8').encode()

        # 设置 Content-Type 的 name 参数
        part.set_param('name', encoded_filename, header='Content-Type')

        # 设置 Content-Disposition 的 filename 参数
        part.add_header('Content-Disposition', 'attachment', filename=encoded_filename)

        # 移除子 part 的 MIME-Version（只保留最外层的）
        if 'MIME-Version' in part:
            del part['MIME-Version']

        msg.attach(part)


def print_missing_config_help():
    """输出缺少本地配置时的操作指引。"""
    print("错误：未配置139邮箱账号。")
    print(f"请先准备本地配置文件：{CONFIG_FILE}")
    print("")
    print("如果你是 agent，不要再次盲查配置文件，直接引导用户提供以下信息：")
    print("1. 完整139邮箱地址，例如 13800138000@139.com")
    print("2. 如未开启 SMTP 服务，先登录 https://mail.10086.cn/ 开启")
    print("")
    print("保存配置命令：")
    print('python scripts/config_manager.py save --username "你的139邮箱"')
    print("")
    print("保存完成后，重新执行当前 send_mail 命令即可。")


def send_mail(to_addr, subject, body, html=False, attachments=None):
    """发送邮件"""
    config = load_config()
    if not config:
        print_missing_config_help()
        return 1

    attachments = attachments or []

    try:
        recipients = parse_recipients(to_addr)

        # 设置发件人信息
        username = config['username']
        display_name = username.split('@')[0]  # 使用邮箱前缀作为显示名称
        domain = username.split('@')[1] if '@' in username else '139.com'

        # 创建邮件结构（模仿邮箱大师）
        if attachments:
            # 有附件：使用嵌套结构 mixed -> alternative -> [plain, html]
            msg = MIMEMultipart('mixed')
            body_part = MIMEMultipart('alternative')
        else:
            # 无附件：直接使用 alternative
            msg = MIMEMultipart('alternative')
            body_part = msg  # 直接在 msg 上添加正文

        # 设置邮件头
        msg['From'] = formataddr((display_name, username))
        msg['To'] = ", ".join([formataddr(("", addr)) for addr in recipients])
        msg['Subject'] = Header(subject, 'utf-8')
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = f"<{str(uuid.uuid4()).upper()}@{domain}>"
        msg['X-Mailer'] = 'MailMasterPC/5.5.4.1009 (10.0.26200)'
        msg['X-CUSTOM-MAIL-MASTER-SENT-ID'] = str(uuid.uuid4()).upper()

        # 添加正文（同时包含纯文本和HTML版本）
        if html:
            # 用户提供了HTML，同时生成纯文本版本
            plain_part = MIMEText(body, 'plain', 'utf-8')
            html_part = MIMEText(body, 'html', 'utf-8')
        else:
            # 用户提供了纯文本，同时生成HTML版本
            plain_part = MIMEText(body, 'plain', 'utf-8')
            # 生成简单的HTML版本（模仿邮箱大师格式，转义特殊字符）
            import html as html_module
            escaped_body = html_module.escape(body).replace('\n', '<br>\n')
            html_body = f'<html><head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"></head><body style="line-height: 1.5;font-family: \'微软雅黑\'"><div  style="font-family: 微软雅黑; line-height: 1.5;"><div><br></div><div>{escaped_body}</div></div></body></html>'
            html_part = MIMEText(html_body, 'html', 'utf-8')

        # 移除子 part 的 MIME-Version（只保留最外层的）
        if 'MIME-Version' in plain_part:
            del plain_part['MIME-Version']
        if 'MIME-Version' in html_part:
            del html_part['MIME-Version']

        body_part.attach(plain_part)
        body_part.attach(html_part)

        # 如果有附件，将正文容器添加到外层 mixed，然后添加附件
        if attachments:
            msg.attach(body_part)
            attach_files(msg, attachments)
        
        print(f"正在连接 {config['smtp_server']}...")
        
        with connect_smtp(config) as server:
            print(f"登录成功")
            
            # 发送邮件
            server.sendmail(config['username'], recipients, msg.as_string())
            print(f"✓ 邮件发送成功！")
            print(f"  收件人: {msg['To']}")
            print(f"  主题: {subject}")
            if attachments:
                print(f"  附件数: {len(attachments)}")
            return 0
            
    except smtplib.SMTPAuthenticationError:
        print("登录失败：请检查账号和token信息是否有效")
        return 1
    except FileNotFoundError as e:
        print(f"发送失败: {e}")
        return 1
    except ValueError as e:
        print(f"发送失败: {e}")
        return 1
    except ssl.SSLError as e:
        print(f"SSL连接错误: {e}")
        print("当前脚本已默认使用 139 邮箱兼容模式。")
        print("请检查是否已开启 SMTP 服务。")
        return 1
    except Exception as e:
        print(f"发送失败: {e}")
        return 1

def main():
    parser = argparse.ArgumentParser(description='发送邮件')
    parser.add_argument('to', help='收件人邮箱，多个地址可用逗号或分号分隔')
    parser.add_argument('subject', help='邮件主题')
    parser.add_argument('body', help='邮件正文')
    parser.add_argument('--html', action='store_true', help='正文为HTML格式')
    parser.add_argument('--attach', action='append', default=[], help='附件路径，可重复传入多个 --attach')
    
    args = parser.parse_args()
    return send_mail(args.to, args.subject, args.body, args.html, args.attach)

if __name__ == '__main__':
    exit(main())
