# -*- coding: utf-8 -*-
"""程序入口 / 组装层。

原来 3400 行的 opencvTool.py 已按三层拆分：

    opencvTool_template.py  界面模板层 —— 控件布局，不含逻辑（对应 opencvTool.fbp）
    opencvTool_view.py      视图层     —— 图片显示、面板切换、重绘
    opencvTool_control.py   控制层     —— 事件响应 + OpenCV 算法

本文件只做三件事：配置日志、把三层组装成 cvTool、提供独立运行入口。
"""

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s',
    filename='app.log',  # 日志文件，不存在则自动创建
    filemode='a'         # 'a' 追加模式，'w' 覆盖模式
)

import wx

from opencvTool_view import cvToolView


class cvTool(cvToolView):
    """OpenCV 算法演示工具主窗口（视图 + 控制 + 模板 三者合一）。"""

    pass


if __name__ == '__main__':
    app = wx.App(False)
    frame = cvTool(None)
    frame.Show()
    app.MainLoop()
