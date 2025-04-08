#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
为应用程序提供基本的 Material Design 图标资源
"""

from PyQt5.QtGui import QIcon

def get_icon(name):
    """返回空图标，避免libpng错误"""
    return QIcon()  # 返回空图标 