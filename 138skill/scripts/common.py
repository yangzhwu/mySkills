#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轻量公共工具。
仅放不依赖第三方库的函数，避免配置脚本被不必要依赖阻塞。
"""
import sys


def configure_console_io():
    """统一控制台输出编码，避免 Windows 非 UTF-8 终端直接崩溃。"""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None or not hasattr(stream, "reconfigure"):
            continue

        try:
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
        except Exception:
            try:
                stream.reconfigure(errors="backslashreplace")
            except Exception:
                pass


def normalize_username(username):
    """清理配置里的邮箱账号，避免前后空格导致认证失败。"""
    return (username or "").strip()
