# -*- coding: utf-8 -*-
"""控制层（control）—— 事件响应 + OpenCV 算法实现。

包含三部分：
    1. 图像转换工具 / 结果回写   —— 文件顶部，所有面板共用
    2. cvToolControlMixin        —— 主窗口的菜单/按钮事件（切换面板、打开图片、关于）
    3. XxxPanel                  —— 各算法面板的事件处理与算法实现（继承模板层的 XxxPanelTemplate）

所有算法都从 self.parent_frame 取原图，算完写回 processed_pil_image，
由视图层负责把结果显示到右侧面板。

约定：
    * 取图统一用 frame_bgr() / frame_gray()，自带缓存且返回副本，随便改不会污染原图；
    * 回写统一用 bgr_to_pil()，单通道（灰度/二值）会直接转成 PIL 的 L 模式；
    * 事件入口加 @safe_process，算法出错只弹窗提示，不会让整个程序退出。
"""

import functools
import io
import logging
import os

import wx
import wx.adv

import cv2
import numpy as np

import matplotlib
matplotlib.use('Agg')  # 无 GUI 模式，只画图不弹窗
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from PIL import Image

import gettext
_ = gettext.gettext

# 可选依赖：没装也不影响程序启动，只在真正用到时提示
try:
    import pytesseract
except ImportError:      # pragma: no cover
    pytesseract = None

# tesseract 可执行文件位置：优先读环境变量，方便换机器
TESSERACT_CMD = os.environ.get("TESSERACT_CMD", r"D:\Tesseract-OCR\tesseract.exe")


def ensure_tesseract():
    """配置 tesseract 路径，返回是否可用。"""
    if pytesseract is None:
        logging.error("未安装 pytesseract，无法进行文字识别")
        return False
    if os.path.exists(TESSERACT_CMD):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    return True


from opencvTool_template import (
    ColorExtractionPanelTemplate,
    ImageDifferencePanelTemplate,
    ImageStitchingPanelTemplate,
    HistogramPanelTemplate,
    ColorSpaceAndChannelExtractionPanelTemplate,
    EqualizationPanelTemplate,
    ThresholdProcessingPanelTemplate,
    FilteringPanelTemplate,
    MorphologicalOperationPanelTemplate,
    ROIPanelTemplate,
    CornerDetectionPanelTemplate,
    EdgeDetectionPanelTemplate,
    GeometricShapePanelTemplate,
    MovingObjectDetectionPanelTemplate,
    ObjectDetectionPanelTemplate,
    WatershedPanelTemplate,
    PyramidPanelTemplate,
    AaffineTransformationPanelTemplate,
    PerspectiveTransformationPanelTemplate,
    FourierTransformationPanelTemplate,
    FloodFillPanelTemplate,
    RemappingPanelTemplate,
    BackProjectionPanelTemplate,
    CameraPanelTemplate,
    CoordinateCalibrationPanelTemplate,
    OcrPanelTemplate,
    VehicleLicensePlateRecognitionPanelTemplate,
    QRCodeRecognizationPanelTemplate,
    TriggrRightPanelDisplayEvent,
    myEVT_RIGHT_DISPLAY,
)


###########################################################################
## 图像格式转换工具（PIL <-> OpenCV）：把散落各处的 5 行样板收成 1 行调用
###########################################################################


def pil_to_bgr(pil_img):
    """PIL 图像 -> OpenCV BGR ndarray。

    先统一 convert("RGB")：P / RGBA / L 模式的图片（GIF、带透明通道的 PNG）
    直接丢给 cvtColor(RGB2BGR) 会因为通道数不对而报错。
    """
    if pil_img is None:
        return None
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")
    return cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)


def pil_to_gray(pil_img):
    """PIL 图像 -> 单通道灰度 ndarray（直接取 L 通道，比 BGR->GRAY 少一次转换）。"""
    if pil_img is None:
        return None
    return np.asarray(pil_img.convert("L")).copy()


def bgr_to_pil(img):
    """OpenCV 图像 -> PIL 图像。

    单通道（灰度/二值）直接交给 PIL（自动用 L 模式），不需要再 cvtColor 转三通道；
    3 通道按 BGR->RGB；4 通道按 BGRA->RGBA。
    """
    if img is None:
        return None
    if img.ndim == 2:
        return Image.fromarray(img)
    if img.shape[2] == 4:
        return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA))
    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))


def frame_bgr(frame):
    """取主窗口原图的 BGR 数组（带缓存，返回副本）。

    每点一次按钮都重新 asarray + cvtColor 一遍整图是纯浪费：原图不换就一直复用。
    返回副本是为了让算法可以放心地在图上画框、做分水岭等原地修改。
    """
    pil_img = getattr(frame, "original_pil_image", None)
    if pil_img is None:
        return None
    cache = getattr(frame, "_bgr_cache", None)
    if cache is not None and cache[0] is pil_img:
        return cache[1].copy()
    bgr = pil_to_bgr(pil_img)
    frame._bgr_cache = (pil_img, bgr)
    return bgr.copy()


def frame_gray(frame):
    """取主窗口原图的灰度数组（带缓存，返回副本）。"""
    pil_img = getattr(frame, "original_pil_image", None)
    if pil_img is None:
        return None
    cache = getattr(frame, "_gray_cache", None)
    if cache is not None and cache[0] is pil_img:
        return cache[1].copy()
    gray = pil_to_gray(pil_img)
    frame._gray_cache = (pil_img, gray)
    return gray.copy()


def safe_process(fn):
    """算法入口包装：捕获异常 -> 写日志 + 弹窗，避免一个算法出错整个程序退出。"""

    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except Exception as exc:                      # GUI 里兜住所有异常
            logging.exception("算法 %s 执行失败", fn.__name__)
            wx.MessageBox(f"{fn.__name__} 执行失败：\n{exc}",
                          "算法错误", wx.OK | wx.ICON_ERROR, self)
            return None

    return wrapper


def _get_ximgproc(owner, attr=None):
    """获取 cv2.ximgproc（contrib 扩展模块）。

    两种损坏场景都会被拦下：
    1. 装的是纯净版 opencv-python，根本没有 contrib 模块；
    2. opencv-python 与 opencv-contrib-python 同时安装，cv2.pyd 互相覆盖，
       此时 cv2.ximgproc 只剩空壳命名空间，具体函数不存在。
    检测到问题时不抛 AttributeError，而是给出明确的安装指引。
    """
    ximgproc = getattr(cv2, "ximgproc", None)
    if ximgproc is None or (attr is not None and not hasattr(ximgproc, attr)):
        logging.error("OpenCV contrib 模块不可用（缺少 %s）", attr or "cv2.ximgproc")
        wx.MessageBox(
            "当前环境缺少 OpenCV contrib 扩展模块。\n\n"
            "FastLineDetector / EdgeDrawing 等算法需要扩展版，且"
            "opencv-python 与 opencv-contrib-python 只能装一个：\n"
            "    pip uninstall opencv-python opencv-contrib-python\n"
            "    pip install opencv-contrib-python",
            "缺少依赖模块", wx.OK | wx.ICON_WARNING, owner)
        return None
    return ximgproc


###########################################################################
## 主窗口事件控制
###########################################################################


class cvToolControlMixin:
    """主窗口的事件响应：菜单切换面板、打开图片、关于对话框。

    28 个 *_panel 菜单方法长得一模一样，这里只留一个 _switch_panel，
    其余由下面的 _PANEL_SWITCH_TABLE 表驱动生成（方法名保持不变，
    wxFormBuilder 生成的 self.color_extraction_panel 之类的绑定照旧生效）。
    """

    def _switch_panel(self, panel_name, show_example=False, example_label=None, event=None):
        """切到指定面板，并决定「打开示例图」按钮是否可见。"""
        self.exampleImage.Show(show_example)
        if example_label:
            self.exampleImage.SetLabel(example_label)
        self.switch_panel(getattr(self, panel_name))
        if event is not None:
            event.Skip()

    def _load_image(self, title, display_flag, is_original):
        """打开图片对话框 + 载入 + 显示：原图与对比图共用一套流程，返回是否成功。"""
        wildcard = ("图片文件 (*.jpg;*.jpeg;*.png;*.bmp;*.gif;*.webp;*.tif)"
                    "|*.jpg;*.jpeg;*.png;*.bmp;*.gif;*.webp;*.tif")
        with wx.FileDialog(self, title, wildcard=wildcard,
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return False
            filepath = dlg.GetPath()

        # 用 with 关掉文件句柄，否则 Windows 下图片会被一直占用
        with Image.open(filepath) as im:
            pil_img = im.convert("RGB")

        self.filepath = filepath
        if is_original:
            self.original_pil_image = pil_img
            self._bgr_cache = None      # 换了原图，缓存失效
            self._gray_cache = None
        else:
            self.processed_pil_image = pil_img

        self.display_image(pil_img, display_flag)
        self._refresh_image_info()
        return True

    def _refresh_image_info(self):
        """刷新底部「原图 / 处理后」尺寸提示。"""
        original = self.original_pil_image
        if original is None:
            return
        processed = self.processed_pil_image
        if processed is None:
            self.imageInfoStaticText.SetLabel(f"原图: {original.width}x{original.height}px")
        else:
            self.imageInfoStaticText.SetLabel(
                f"原图: {original.width}x{original.height}px -> "
                f"处理后: {processed.width}x{processed.height}px")
        self.Layout()

    def about_panel(self, event):
        self.exampleImage.Hide()

        info = wx.adv.AboutDialogInfo()
        info.SetName("HQQ's wxPython Program")
        info.SetVersion("1.0")
        info.SetDescription("这是一个opencv计算机视觉常用算法演示程序")
        info.SetCopyright("(C) 2026 Hu QiQiao")
        info.SetWebSite("http://shop71288536.m.taobao.com")
        info.SetLicence("本程序放弃版权，可自由传播")
        info.AddDeveloper("Hu QiQiao")
        info.AddDocWriter("Hu QiQiao")
        info.AddArtist("Hu QiQiao")
        info.AddTranslator("Hu QiQiao")

        wx.adv.AboutBox(info)
        event.Skip()

    def openImageclick(self, event):
        logging.info("打开图片/重新打开图片处理")
        if self._load_image("选择图片", 0, is_original=True):
            self.openImage.SetLabelMarkup(_(u"再次上传图片"))
        event.Skip()

    def exampleImageClick(self, event):
        logging.info("打开示例图片/对比图片处理")
        self._load_image("选择图片", 1, is_original=False)
        event.Skip()


# 菜单方法名 -> (面板属性名, 「打开示例图」按钮是否可见, 按钮文字)
_PANEL_SWITCH_TABLE = {
    "color_extraction_panel":                    ("colorExtractionPanel",                          False, None),
    "image_difference_panel":                    ("imageDifferencePanel",                          True,  "打开对比图"),
    "image_stitching_panel":                     ("imageStitchingPanel",                           True,  "打开拼接图"),
    "histogram_panel":                           ("imageHistogramPanel",                           False, None),
    "color_space_and_channel_extraction_panel":  ("imageColorSpaceAndChannelExtractionPanel",      False, None),
    "equalization_panel":                        ("imageEqualizationPanel",                        False, None),
    "threshold_processing_panel":                ("imageThresholdProcessingPanel",                  False, None),
    "filtering_panel":                           ("imageFilteringPanel",                           False, None),
    "morphological_operation_panel":             ("imageMorphologicalOperationPanel",              False, None),
    "ROI_panel":                                 ("imageROIPanel",                                 False, None),
    "corner_detection_panel":                    ("imageCornerDetectionPanel",                     False, None),
    "edge_detection_panel":                      ("imageEdgeDetectionPanel",                       False, None),
    "geometric_shape_panel":                     ("imageGeometricShapePanel",                      False, None),
    "moving_object_detection_panel":             ("imageMovingObjectDetectionPanel",               False, None),
    "object_detection_panel":                    ("imageObjectDetectionPanel",                     False, None),
    "watershed_panel":                           ("imageWatershedPanel",                           False, None),
    "pyramid_panel":                             ("imagePyramidPanel",                             False, None),
    "affine_transformation_panel":               ("imageAaffineTransformationPanel",               False, None),
    "perspective_transformation_panel":          ("imagePerspectiveTransformationPanel",           False, None),
    "fourier_transformation_panel":              ("imageFourierTransformationPanel",               False, None),
    "flood_fill_panel":                          ("imageFloodFillPanel",                           False, None),
    "remapping_panel":                           ("imageRemappingPanel",                           False, None),
    "back_projection_panel":                     ("imageBackProjectionPanel",                      True,  "打开目标图片"),
    "camera_panel":                              ("imageCameraPanel",                              False, None),
    "coordinate_calibration_panel":              ("imageCoordinateCalibrationPanel",               False, None),
    "ocr_panel":                                 ("imageOcrPanel",                                 False, None),
    "vehicle_license_plate_recognition_panel":   ("imageVehicleLicensePlateRecognitionPanel",      False, None),
    "QR_code_recognization_panel":               ("imageQRCodeRecognizationPanel",                 False, None),
}


def _make_panel_handler(panel_name, show_example, example_label):
    """生成一个菜单回调，行为等价于原来手写的 xxx_panel 方法。"""

    def handler(self, event):
        self._switch_panel(panel_name, show_example, example_label, event)

    handler.__name__ = "panel_handler"
    return handler


for _method_name, (_panel, _show, _label) in _PANEL_SWITCH_TABLE.items():
    setattr(cvToolControlMixin, _method_name, _make_panel_handler(_panel, _show, _label))


###########################################################################
## 各算法面板：事件处理 + 算法实现
###########################################################################


class ColorExtractionPanel(ColorExtractionPanelTemplate):
    """ColorExtractionPanel 的事件处理与算法实现。"""

    # 单选序号 -> 方法名，新增算法只在表里加一项
    _HANDLERS = ("imageProcessBGR2GRAY", "imageProcessBGR2HSV",
                 "imageProcessRGB2BGR", "imageProcessBGR2YCrCb")

    @safe_process
    def imageProcessOnRadioBox(self, event):
        index = self.m_radioBox2.GetSelection()
        if 0 <= index < len(self._HANDLERS):
            getattr(self, self._HANDLERS[index])()
        else:
            logging.warning("未知的色彩空间选项: %s", index)
        self.GetEventHandler().ProcessEvent(self.evt)   # 触发右侧面板刷新
        event.Skip()

    def _set_result(self, img, as_bgr=True):
        """把 OpenCV 结果写回主窗口（as_bgr=False 表示直接把数组交给 PIL）。"""
        self.parent_frame.processed_pil_image = bgr_to_pil(img) if as_bgr else Image.fromarray(img)

    def imageProcessBGR2GRAY(self):
        """BGR -> 灰度（再转回三通道，右侧面板显示灰度效果）"""
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        self._set_result(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR))

    def imageProcessBGR2HSV(self):
        """BGR -> HSV 后按阈值提取黄色区域，其余部分变黑。

        注意：bitwise_and 的输出已经是 BGR 图像，别再拿 HSV2BGR 去转它。
        """
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        # 黄色的 HSV 范围：H 20~40，S/V 下限 50 可以压掉灰色干扰
        lower_yellow = np.array([20, 50, 50])
        upper_yellow = np.array([40, 255, 255])
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        self._set_result(cv2.bitwise_and(img_bgr, img_bgr, mask=mask))

    def imageProcessRGB2BGR(self):
        """通道顺序对调演示：把 BGR 数组直接当成 RGB 显示，红蓝互换"""
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        self._set_result(img_bgr, as_bgr=False)

    def imageProcessBGR2YCrCb(self):
        """BGR -> YCrCb -> 再转回 BGR（两次转换后颜色应与原图基本一致）"""
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
        self._set_result(cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR))


class ImageDifferencePanel(ImageDifferencePanelTemplate):
    """ImageDifferencePanel 的事件处理与算法实现。"""

    SIZE = (800, 600)   # 两张图统一尺寸后才能逐像素相减

    @safe_process
    def imageDiffBtnClick(self, event):
        self.imageProcessDiff()
        self.GetEventHandler().ProcessEvent(self.evt)   # 触发右侧面板刷新
        event.Skip()

    def imageProcessDiff(self):
        frame = self.parent_frame
        if frame.original_pil_image is None or frame.processed_pil_image is None:
            wx.MessageBox("请先在左侧打开原图，再点「打开对比图」选择第二张图片。",
                          "提示", wx.OK | wx.ICON_INFORMATION, self)
            return

        img_1 = pil_to_bgr(frame.original_pil_image.resize(self.SIZE, Image.LANCZOS))
        img_2 = pil_to_bgr(frame.processed_pil_image.resize(self.SIZE, Image.LANCZOS))
        gray_1 = cv2.cvtColor(img_1, cv2.COLOR_BGR2GRAY)
        gray_2 = cv2.cvtColor(img_2, cv2.COLOR_BGR2GRAY)

        diff = cv2.absdiff(gray_1, gray_2)
        self.parent_frame.processed_pil_image = bgr_to_pil(diff)   # 单通道直接交给 PIL


class ImageStitchingPanel(ImageStitchingPanelTemplate):
    """ImageStitchingPanel 的事件处理与算法实现。"""

    SIZE = (800, 600)

    @safe_process
    def imageStitchBtnClick(self, event):
        self.imageProcessStitch()
        self.GetEventHandler().ProcessEvent(self.evt)   # 触发右侧面板刷新
        event.Skip()

    def imageProcessStitch(self):
        frame = self.parent_frame
        if frame.original_pil_image is None or frame.processed_pil_image is None:
            wx.MessageBox("请先在左侧打开原图，再点「打开拼接图」选择第二张图片。",
                          "提示", wx.OK | wx.ICON_INFORMATION, self)
            return

        img_1 = pil_to_bgr(frame.original_pil_image.resize(self.SIZE, Image.LANCZOS))
        img_2 = pil_to_bgr(frame.processed_pil_image.resize(self.SIZE, Image.LANCZOS))

        # PANORAMA 模式：适合手持相机围绕光心旋转拍摄的风景、室内大场景
        # SCANS 模式   ：适合文档扫描、平面物体平行移动拍摄（只做平面仿射拼接）
        stitcher = cv2.Stitcher.create(cv2.Stitcher_PANORAMA)
        status, pano = stitcher.stitch([img_1, img_2])

        if status == cv2.Stitcher_OK:
            logging.info("拼接成功!")
            frame.processed_pil_image = bgr_to_pil(pano)
        else:
            logging.error("拼接失败，错误码：%s", status)
            wx.MessageBox(f"拼接失败，错误码：{status}\n（两张图重叠区域不足时容易失败）",
                          "拼接失败", wx.OK | wx.ICON_WARNING, self)


class HistogramPanel(HistogramPanelTemplate):
    """HistogramPanel 的事件处理与算法实现。"""

    @safe_process
    def imageHistBtnClick(self, event):
        self.imageProcessHist()
        self.GetEventHandler().ProcessEvent(self.evt)   # 触发右侧面板刷新
        event.Skip()

    def imageProcessHist(self):
        """用 Matplotlib 画三通道直方图。

        用 Figure + FigureCanvasAgg 而不是 pyplot：pyplot 会维护全局画布，
        多次调用容易泄漏 figure，也不用再手动 plt.close()。
        """
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return

        fig = Figure(figsize=(8, 5), dpi=100)
        FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)
        for i, (color, name) in enumerate((("r", "R"), ("g", "G"), ("b", "B"))):
            ax.hist(img_bgr[:, :, i].ravel(), bins=256, range=(0, 256),
                    color=color, alpha=0.5, label=f"{name} channel")
        ax.set_xlim(0, 255)
        ax.set_xlabel("Pixel Value")
        ax.set_ylabel("Frequency")
        ax.set_title("RGB Histogram")
        ax.legend()

        # 画到内存缓冲区，不落盘
        with io.BytesIO() as buf:
            fig.savefig(buf, format="PNG", bbox_inches="tight")
            buf.seek(0)
            with Image.open(buf) as im:
                self.parent_frame.processed_pil_image = im.convert("RGB")


class ColorSpaceAndChannelExtractionPanel(ColorSpaceAndChannelExtractionPanelTemplate):
    """ColorSpaceAndChannelExtractionPanel 的事件处理与算法实现。"""

    _HANDLERS = ("imageProcessBGR2B", "imageProcessBGR2G", "imageProcessBGR2R",
                 "imageProcessHSV2H", "imageProcessHSV2S", "imageProcessHSV2V")

    @safe_process
    def imageProcessChannelExtraction(self, event):
        index = self.m_radioBox2.GetSelection()
        if 0 <= index < len(self._HANDLERS):
            getattr(self, self._HANDLERS[index])()
        else:
            logging.warning("未知的通道选项: %s", index)
        self.GetEventHandler().ProcessEvent(self.evt)   # 触发右侧面板刷新
        event.Skip()

    def _show_channel(self, space, index):
        """取 BGR 或 HSV 空间的第 index 个通道显示（单通道直接交给 PIL）。"""
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        source = img_bgr if space == "BGR" else cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        self.parent_frame.processed_pil_image = bgr_to_pil(cv2.split(source)[index])

    def imageProcessBGR2B(self):
        self._show_channel("BGR", 0)

    def imageProcessBGR2G(self):
        self._show_channel("BGR", 1)

    def imageProcessBGR2R(self):
        self._show_channel("BGR", 2)

    def imageProcessHSV2H(self):
        self._show_channel("HSV", 0)

    def imageProcessHSV2S(self):
        self._show_channel("HSV", 1)

    def imageProcessHSV2V(self):
        self._show_channel("HSV", 2)


class EqualizationPanel(EqualizationPanelTemplate):
    """EqualizationPanel 的事件处理与算法实现。"""

    @safe_process
    def imageEqualizationBtnClick(self, event):
        self.imageProcessEqualization()
        self.GetEventHandler().ProcessEvent(self.evt)   # 触发右侧面板刷新
        event.Skip()

    def imageProcessEqualization(self):
        """全局直方图均衡化：只在 YCrCb 的 Y（亮度）通道上做，避免偏色。"""
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        img_ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
        img_ycrcb[:, :, 0] = cv2.equalizeHist(img_ycrcb[:, :, 0])
        self.parent_frame.processed_pil_image = bgr_to_pil(
            cv2.cvtColor(img_ycrcb, cv2.COLOR_YCrCb2BGR))


###########################################################################
## 阈值分割的自定义算法
## （原来写在各方法的嵌套函数里，每次点击都会重新定义一遍，挪到模块级）
###########################################################################


def iterative_threshold(gray, tolerance=1, max_iter=100):
    """迭代阈值法：用「前景均值 + 背景均值」的一半不断逼近，直到变化小于容差。"""
    T = float(np.mean(gray))
    for _ in range(max_iter):
        foreground = gray[gray >= T]
        background = gray[gray < T]
        if foreground.size == 0 or background.size == 0:   # 某一类为空，提前结束
            break
        new_T = (float(np.mean(foreground)) + float(np.mean(background))) / 2.0
        converged = abs(new_T - T) < tolerance
        T = new_T
        if converged:
            break
    return int(T)


def niblack_threshold(gray, window_size=25, k=-0.2):
    """Niblack：阈值曲面 = 局部均值 + k * 局部标准差。"""
    f = gray.astype(np.float32)
    mean = cv2.blur(f, (window_size, window_size))
    mean_sq = cv2.blur(f ** 2, (window_size, window_size))
    std = np.sqrt(np.maximum(mean_sq - mean ** 2, 0))
    # cv2.blur 默认 BORDER_REFLECT，边界不会越界，不必手动补边
    return ((f > mean + k * std).astype(np.uint8)) * 255


def sauvola_threshold(gray, window_size=25, k=0.2, r=128):
    """Sauvola：在 Niblack 基础上引入动态范围 R，对光照不均更鲁棒。"""
    f = gray.astype(np.float32)
    mean = cv2.blur(f, (window_size, window_size))
    mean_sq = cv2.blur(f ** 2, (window_size, window_size))
    std = np.sqrt(np.maximum(mean_sq - mean ** 2, 0))
    threshold = mean * (1 + k * (std / r - 1))
    return ((f > threshold).astype(np.uint8)) * 255


def max_entropy_threshold(gray):
    """最大熵法（MEM）：取「背景熵 + 前景熵」最大的那个灰度作为阈值。"""
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).ravel()
    total = hist.sum()
    if total <= 0:
        return 127
    prob = hist / total
    cum = np.cumsum(prob)
    best_threshold, best_entropy = 0, -1.0
    for t in range(1, 256):
        sum_b, sum_f = cum[t - 1], 1.0 - cum[t - 1]
        if sum_b <= 0 or sum_f <= 0:
            continue
        p_b = prob[:t]
        p_f = prob[t:]
        p_b = p_b[p_b > 0] / sum_b
        p_f = p_f[p_f > 0] / sum_f
        entropy = -(p_b * np.log2(p_b)).sum() - (p_f * np.log2(p_f)).sum()
        if entropy > best_entropy:
            best_entropy, best_threshold = entropy, t
    return best_threshold


def multi_threshold(gray, thresholds=(60, 120, 180), values=(0, 85, 170, 255)):
    """多阈值分层：按阈值把灰度切成若干段，每段映射成一个固定灰度值。"""
    if len(values) != len(thresholds) + 1:
        raise ValueError("values 的个数必须比 thresholds 多 1")
    result = np.zeros_like(gray)
    bounds = (0,) + tuple(thresholds) + (256,)
    for i, value in enumerate(values):
        lo, hi = bounds[i], bounds[i + 1]
        result[(gray >= lo) & (gray < hi)] = value
    return result


class ThresholdProcessingPanel(ThresholdProcessingPanelTemplate):
    """ThresholdProcessingPanel 的事件处理与算法实现。

    13 种阈值方法共用同一套骨架（取灰度 -> 求阈值 -> 二值化 -> 回写），
    差别只在 OpenCV 的 flag 或自定义算法的几行，所以抽出 _global_threshold /
    _adaptive_threshold 两个工具，每种算法压缩成一行声明。
    """

    # 单选序号 -> 方法名，新增算法只需在末尾追加
    _HANDLERS = (
        "imageThresBINARY", "imageThresBINARYINV", "imageThresTRUNC",
        "imageThresTOZERO", "imageThresTOZEROINV", "imageThresMEANC",
        "imageThresGAUSSIANC", "imageThresOtsu", "imageThresTriangle",
        "imageThresIterative", "imageThresNiblack", "imageThresSauvola",
        "imageThresMEM", "imageThresMultiDomainSegmentation",
    )

    @safe_process
    def imageThresholdOnRadioBox(self, event):
        index = self.m_radioBox2.GetSelection()
        if 0 <= index < len(self._HANDLERS):
            getattr(self, self._HANDLERS[index])()
        else:
            logging.warning("未知的阈值选项: %s", index)
        self.GetEventHandler().ProcessEvent(self.evt)   # 触发右侧面板刷新
        event.Skip()

    # ---------------- 公共骨架 ----------------
    def _set_binary(self, binary):
        """二值图/灰度图直接交给 PIL（L 模式），不需要再 cvtColor 转三通道。"""
        self.parent_frame.processed_pil_image = bgr_to_pil(binary)

    def _global_threshold(self, thresh_type, thresh=127, maxval=255):
        gray = frame_gray(self.parent_frame)
        if gray is None:
            return
        _, binary = cv2.threshold(gray, thresh, maxval, thresh_type)
        self._set_binary(binary)

    def _adaptive_threshold(self, method, block_size=5, c=0):
        gray = frame_gray(self.parent_frame)
        if gray is None:
            return
        binary = cv2.adaptiveThreshold(gray, 255, method, cv2.THRESH_BINARY, block_size, c)
        self._set_binary(binary)

    # ---------------- 7 种全局阈值：一行一个 ----------------
    def imageThresBINARY(self):
        """黑字白底"""
        self._global_threshold(cv2.THRESH_BINARY)

    def imageThresBINARYINV(self):
        """白字黑底"""
        self._global_threshold(cv2.THRESH_BINARY_INV)

    def imageThresTRUNC(self):
        """超过阈值的像素被截断为阈值"""
        self._global_threshold(cv2.THRESH_TRUNC)

    def imageThresTOZERO(self):
        """小于阈值的像素置 0，其余不变"""
        self._global_threshold(cv2.THRESH_TOZERO)

    def imageThresTOZEROINV(self):
        """大于阈值的像素置 0，其余不变"""
        self._global_threshold(cv2.THRESH_TOZERO_INV)

    def imageThresOtsu(self):
        """Otsu：自动取类间方差最大的阈值（thresh 参数会被忽略，填 0）"""
        self._global_threshold(cv2.THRESH_BINARY + cv2.THRESH_OTSU, 0)

    def imageThresTriangle(self):
        """Triangle：适合直方图呈单峰的图像"""
        self._global_threshold(cv2.THRESH_BINARY + cv2.THRESH_TRIANGLE, 0)

    # ---------------- 2 种自适应阈值 ----------------
    def imageThresMEANC(self):
        self._adaptive_threshold(cv2.ADAPTIVE_THRESH_MEAN_C, block_size=3)

    def imageThresGAUSSIANC(self):
        self._adaptive_threshold(cv2.ADAPTIVE_THRESH_GAUSSIAN_C, block_size=5)

    # ---------------- 5 种自定义阈值 ----------------
    def imageThresIterative(self):
        """迭代阈值法"""
        gray = frame_gray(self.parent_frame)
        if gray is None:
            return
        threshold = iterative_threshold(gray, tolerance=1)
        logging.info("迭代法求得阈值: %s", threshold)
        self._set_binary(cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)[1])

    def imageThresNiblack(self):
        """Niblack 局部阈值"""
        gray = frame_gray(self.parent_frame)
        if gray is None:
            return
        self._set_binary(niblack_threshold(gray, window_size=25, k=-0.2))

    def imageThresSauvola(self):
        """Sauvola 局部阈值"""
        gray = frame_gray(self.parent_frame)
        if gray is None:
            return
        self._set_binary(sauvola_threshold(gray, window_size=25, k=0.2))

    def imageThresMEM(self):
        """最大熵法"""
        gray = frame_gray(self.parent_frame)
        if gray is None:
            return
        threshold = max_entropy_threshold(gray)
        logging.info("最大熵法求得阈值: %s", threshold)
        self._set_binary(cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)[1])

    def imageThresMultiDomainSegmentation(self):
        """多阈值分层：0/85/170/255 四档灰度，能直观看出灰度区间分布"""
        gray = frame_gray(self.parent_frame)
        if gray is None:
            return
        self._set_binary(multi_threshold(gray, thresholds=(60, 120, 180),
                                        values=(0, 85, 170, 255)))


class FilteringPanel(FilteringPanelTemplate):
    """FilteringPanel 的事件处理与算法实现。"""

    _HANDLERS = ("imageProcessBlur", "imageProcessBoxBlur", "imageProcessGaussianBlur",
                 "imageProcessMedianBlur", "imageProcessBilateral")

    @safe_process
    def imageFilteringOnRadioBox(self, event):
        index = self.m_radioBox2.GetSelection()
        if 0 <= index < len(self._HANDLERS):
            getattr(self, self._HANDLERS[index])()
        else:
            logging.warning("未知的滤波选项: %s", index)
        self.GetEventHandler().ProcessEvent(self.evt)   # 触发右侧面板刷新
        event.Skip()

    def _apply(self, fn):
        """取原图 BGR -> 套用滤波函数 -> 回写，五种滤波只差一个 fn。"""
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        self.parent_frame.processed_pil_image = bgr_to_pil(fn(img_bgr))

    def imageProcessBlur(self):
        """均值滤波：核大小 (宽, 高)，必须是奇数"""
        self._apply(lambda im: cv2.blur(im, (5, 5)))

    def imageProcessBoxBlur(self):
        """方框滤波：normalize=True 时等价于均值滤波；
        normalize=False 是求像素和，5x5 时很容易溢出成纯白，这里用 True 演示。"""
        self._apply(lambda im: cv2.boxFilter(im, -1, (5, 5), normalize=True))

    def imageProcessGaussianBlur(self):
        """高斯滤波：sigmaX=0 时按核尺寸自动推算"""
        self._apply(lambda im: cv2.GaussianBlur(im, (5, 5), 0))

    def imageProcessMedianBlur(self):
        """中值滤波：对椒盐噪声效果最好"""
        self._apply(lambda im: cv2.medianBlur(im, 5))

    def imageProcessBilateral(self):
        """双边滤波：d=9, sigmaColor=75, sigmaSpace=75 是常用经验值，保边去噪"""
        self._apply(lambda im: cv2.bilateralFilter(im, 9, 75, 75))


class MorphologicalOperationPanel(MorphologicalOperationPanelTemplate):
    """MorphologicalOperationPanel 的事件处理与算法实现。"""

    _HANDLERS = ("imageErosion", "imageDilation", "imageOpening", "imageClosing",
                 "imageGradient", "imageTophat", "imageBlackhat")

    # 结构元素只建一次：矩形核 5x5（原来每个方法都建三个核，其中两个从没用过）
    _KERNEL = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

    @safe_process
    def imageMorphologicalOnRadioBox(self, event):
        index = self.m_radioBox2.GetSelection()
        if 0 <= index < len(self._HANDLERS):
            getattr(self, self._HANDLERS[index])()
        else:
            logging.warning("未知的形态学选项: %s", index)
        self.GetEventHandler().ProcessEvent(self.evt)   # 触发右侧面板刷新
        event.Skip()

    def _binary(self):
        """形态学通常处理二值图：灰度化 + 固定阈值 127 二值化。"""
        gray = frame_gray(self.parent_frame)
        if gray is None:
            return None
        return cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)[1]

    def _simple(self, fn):
        binary = self._binary()
        if binary is None:
            return
        self.parent_frame.processed_pil_image = bgr_to_pil(fn(binary, self._KERNEL, iterations=1))

    def _morph_ex(self, op):
        binary = self._binary()
        if binary is None:
            return
        result = cv2.morphologyEx(binary, op, self._KERNEL)
        self.parent_frame.processed_pil_image = bgr_to_pil(result)

    def imageErosion(self):
        """腐蚀：让白色前景变小，去掉细小噪点"""
        self._simple(cv2.erode)

    def imageDilation(self):
        """膨胀：让白色前景变大，填补小孔"""
        self._simple(cv2.dilate)

    def imageOpening(self):
        """开运算 = 先腐蚀后膨胀：去掉外部噪点，位置和大小基本不变"""
        self._morph_ex(cv2.MORPH_OPEN)

    def imageClosing(self):
        """闭运算 = 先膨胀后腐蚀：填补前景内部的小洞"""
        self._morph_ex(cv2.MORPH_CLOSE)

    def imageGradient(self):
        """形态学梯度 = 膨胀 - 腐蚀：得到边缘"""
        self._morph_ex(cv2.MORPH_GRADIENT)

    def imageTophat(self):
        """顶帽 = 原图 - 开运算：提取亮的小细节"""
        self._morph_ex(cv2.MORPH_TOPHAT)

    def imageBlackhat(self):
        """黑帽 = 闭运算 - 原图：提取暗的小细节"""
        self._morph_ex(cv2.MORPH_BLACKHAT)


class ROIPanel(ROIPanelTemplate):
    """ROIPanel 的事件处理与算法实现。"""

    @safe_process
    def imageAutoROIBtnClick(self, event):
        self.imageAutoROI()
        self.GetEventHandler().ProcessEvent(self.evt)   # 触发右侧面板刷新
        event.Skip()

    def imageAutoROI(self):
        """用 Haar 级联检测人脸，把最大的一张脸裁出来当作 ROI。"""
        gray = frame_gray(self.parent_frame)
        if gray is None:
            return
        height, width = gray.shape[:2]

        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

        if len(faces) == 0:
            logging.info("未检测到人脸，右侧显示原图")
            wx.MessageBox("没有检测到人脸，可能这张图里没有人或者角度太偏。",
                          "提示", wx.OK | wx.ICON_INFORMATION, self)
            return

        # 多张脸时取面积最大的那张，避免只留下循环里最后一张
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        pad = 20                                      # 往外扩一点，别裁太贴
        x1, y1 = max(x - pad, 0), max(y - pad, 0)
        x2, y2 = min(x + w + pad, width), min(y + h + pad, height)   # 宽用 width、高用 height
        self.parent_frame.processed_pil_image = bgr_to_pil(gray[y1:y2, x1:x2])


class CornerDetectionPanel(CornerDetectionPanelTemplate):
    """CornerDetectionPanel 的事件处理与算法实现。"""

    _HANDLERS = ("imageHarris", "imageShiTomasi", "imageOrb", "imageFast", "imageSift")

    @safe_process
    def imageCornerDetectionOnRadioBox(self, event):
        index = self.m_radioBox2.GetSelection()
        if 0 <= index < len(self._HANDLERS):
            getattr(self, self._HANDLERS[index])()
        else:
            logging.warning("未知的角点检测选项: %s", index)
        self.GetEventHandler().ProcessEvent(self.evt)   # 触发右侧面板刷新
        event.Skip()

    def imageHarris(self):
        """Harris 角点：响应值超过最大值 1% 的像素标红"""
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        # blockSize 邻域大小，ksize Sobel 孔径，k 经验值 0.04~0.06
        response = cv2.cornerHarris(np.float32(gray), blockSize=2, ksize=3, k=0.04)
        response = cv2.dilate(response, None)            # 膨胀让角点更显眼
        img_bgr[response > 0.01 * response.max()] = [0, 0, 255]
        self.parent_frame.processed_pil_image = bgr_to_pil(img_bgr)

    def imageShiTomasi(self):
        """Shi-Tomasi（goodFeaturesToTrack）角点：绿色圆点标记"""
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        # qualityLevel 越小检出越多，minDistance 避免角点扎堆
        corners = cv2.goodFeaturesToTrack(gray, maxCorners=50,
                                          qualityLevel=0.01, minDistance=10)
        if corners is not None:
            for x, y in np.int32(corners).reshape(-1, 2):
                cv2.circle(img_bgr, (x, y), 3, (0, 255, 0), -1)
        self.parent_frame.processed_pil_image = bgr_to_pil(img_bgr)

    def imageOrb(self):
        """ORB：在彩色原图上画关键点，圆的大小代表特征尺度"""
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        keypoints = cv2.ORB_create(nfeatures=500).detect(gray, None)
        result = cv2.drawKeypoints(img_bgr, keypoints, None,
                                   color=(0, 255, 0),
                                   flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
        self.parent_frame.processed_pil_image = bgr_to_pil(result)

    def imageFast(self):
        """FAST：threshold 越大角点越少但越稳定"""
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        detector = cv2.FastFeatureDetector_create(threshold=30, nonmaxSuppression=True)
        keypoints = detector.detect(gray, None)
        result = cv2.drawKeypoints(img_bgr, keypoints, None, color=(0, 255, 0))
        self.parent_frame.processed_pil_image = bgr_to_pil(result)

    def imageSift(self):
        """SIFT：OpenCV 4.4+ 可直接 cv2.SIFT_create"""
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        sift = cv2.SIFT_create(nfeatures=5000, contrastThreshold=0.04, edgeThreshold=10)
        keypoints = sift.detect(gray, None)
        result = cv2.drawKeypoints(img_bgr, keypoints, None,
                                   color=(0, 255, 0),
                                   flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
        self.parent_frame.processed_pil_image = bgr_to_pil(result)


class EdgeDetectionPanel(EdgeDetectionPanelTemplate):
    """EdgeDetectionPanel 的事件处理与算法实现。"""

    def imageEdgeDetectionOnRadioBox( self, event ): 
        match self.m_radioBox2.GetSelection():
            case 0:
                self.imageCanny()
            case 1:
                self.imageSobel()
            case 2:
                self.imageLaplacian()
            case 3:
                self.imageScharr()
            case _:
                logging.warning("未知的选项: %s", self.m_radioBox2.GetSelection())
        self.GetEventHandler().ProcessEvent(self.evt)  # 触发事件  
        event.Skip()

    def imageCanny(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr     = frame_bgr(self.parent_frame)
            img_gray    = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            # 2. 高斯模糊降噪（核大小5x5）
            blurred     = cv2.GaussianBlur(img_gray, (5, 5), 1.4)

            # 3. Canny边缘检测（低阈值50，高阈值150）
            edges       = cv2.Canny(blurred, 50, 150)
            self.parent_frame.processed_pil_image = bgr_to_pil(edges)

    def imageSobel(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr     = frame_bgr(self.parent_frame)
            img_gray    = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)        

            sobel_x     = cv2.Sobel(img_gray, cv2.CV_64F, 1, 0, ksize=3)  # x方向
            sobel_y     = cv2.Sobel(img_gray, cv2.CV_64F, 0, 1, ksize=3)  # y方向
            sobel       = np.sqrt(sobel_x**2 + sobel_y**2)
            sobel_abs   = cv2.convertScaleAbs(sobel)
            self.parent_frame.processed_pil_image = bgr_to_pil(sobel_abs)

    def imageLaplacian(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr         = frame_bgr(self.parent_frame)
            img_gray        = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

            # 2. 应用 Laplacian 算子
            # ddepth=cv2.CV_64F 保留负值，避免截断；ksize=3 是核大小，必须为正奇数
            laplacian       = cv2.Laplacian(img_gray, cv2.CV_64F, ksize=3)
            # 3. 取绝对值并转回 8 位图以便显示
            laplacian_abs   = cv2.convertScaleAbs(laplacian)
            self.parent_frame.processed_pil_image = bgr_to_pil(laplacian_abs)

    def imageScharr(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr         = frame_bgr(self.parent_frame)
            img_gray        = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

            # 2. 计算X和Y方向的Scharr梯度
            # 注意：ddepth建议用CV_32F或CV_64F，避免负值被截断
            grad_x          = cv2.Scharr(img_gray, cv2.CV_32F, 1, 0)  # X方向
            grad_y          = cv2.Scharr(img_gray, cv2.CV_32F, 0, 1)  # Y方向
            # 3. 取绝对值并转回uint8格式
            abs_x           = cv2.convertScaleAbs(grad_x)
            abs_y           = cv2.convertScaleAbs(grad_y)
            # 4. 将两个方向加权合并（各占50%）
            scharr_xy       = cv2.addWeighted(abs_x, 0.5, abs_y, 0.5, 0)
            self.parent_frame.processed_pil_image = bgr_to_pil(scharr_xy)


class GeometricShapePanel(GeometricShapePanelTemplate):
    """GeometricShapePanel 的事件处理与算法实现。"""

    def imageGeometricShapeOnRadioBox( self, event ): 
        match self.m_radioBox2.GetSelection():
            case 0:
                self.imageHoughLinesP()
            case 1:
                self.imageHoughCircles()
            case 2:
                self.imageContour()
            case 3:
                self.imageLineSegmentDetector()
            case 4:
                self.imageFastLineDetector()
            case 5:
                self.imageBlob()
            case 6:
                self.imageEdgeDrawing()
            case 7:
                self.imageHull()
            case 8:
                self.imageLeastSquaresCircleFitting()
            case _:
                logging.warning("未知的选项: %s", self.m_radioBox2.GetSelection())
        self.GetEventHandler().ProcessEvent(self.evt)  # 触发事件  
        event.Skip()

    def imageHoughLinesP(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr         = frame_bgr(self.parent_frame)
            img_gray        = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)        
            # 2. Canny 边缘检测（HoughLinesP 输入必须是二值图）
            edges           = cv2.Canny(img_gray, 50, 150, apertureSize=3)

            # 3. 概率霍夫变换
            lines           = cv2.HoughLinesP(
                edges,
                rho=1,              # 距离分辨率，1 像素
                theta=np.pi/180,    # 角度分辨率，1 度
                threshold=80,       # 投票阈值，越小直线越多
                minLineLength=50,   # 最小线段长度，过滤短线段
                maxLineGap=10       # 最大断缝间隔，允许连接断开的线段
            )

            # 4. 在彩色原图上绘制线段（画在灰度图上会丢掉颜色）
            if lines is not None:
                for x1, y1, x2, y2 in lines.reshape(-1, 4):
                    cv2.line(img_bgr, (x1, y1), (x2, y2), (0, 255, 0), 2)
            self.parent_frame.processed_pil_image = bgr_to_pil(img_bgr)

    def imageHoughCircles(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr         = frame_bgr(self.parent_frame)
            img_gray        = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)         
            # 2. 平滑去噪（中值滤波对椒盐噪声效果好）
            img_gray        = cv2.medianBlur(img_gray, 5)

            circles = cv2.HoughCircles(img_gray, cv2.HOUGH_GRADIENT, 
                           dp=1, minDist=30,
                           param1=100, param2=30,
                           minRadius=10, maxRadius=100)

            # 3. 霍夫圆检测 
            if circles is not None:
                circles = np.uint16(np.around(circles))  # 先四舍五入再转整型
                for (x, y, r) in circles[0, :]:
                    cv2.circle(img_bgr, (x, y), r, (0, 255, 0), 2)   # 画圆
                    cv2.circle(img_bgr, (x, y), 2, (0, 0, 255), 3)   # 画圆心
            self.parent_frame.processed_pil_image = bgr_to_pil(img_bgr)

    def imageContour(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr             = frame_bgr(self.parent_frame)
            img_gray            = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)         
            # 2. 二值化（黑底白物）
            ret, binary         = cv2.threshold(img_gray, 127, 255, cv2.THRESH_BINARY)

            # 3. 查找轮廓
            contours, hierarchy = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # 4. 在原图上画出所有轮廓
            cv2.drawContours(img_bgr, contours, -1, (0, 255, 0), 2)

            self.parent_frame.processed_pil_image = bgr_to_pil(img_bgr)

    def imageLineSegmentDetector(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr             = frame_bgr(self.parent_frame)
            img_gray            = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

            # 3. 创建 LSD 检测器
            # 参数说明：refine 细化模式，scale 缩放因子，sigma_scale 高斯滤波系数
            lsd = cv2.createLineSegmentDetector(
                refine=cv2.LSD_REFINE_STD,  # 标准细化，也可用 LSD_REFINE_ADV 或 LSD_REFINE_NONE
                scale=0.8,                  # 图像缩放因子，越小检测越密集
                sigma_scale=0.6,            # 高斯滤波标准差
                ang_th=22.5                 # 角度容差阈值（度）
            )
            lines, _, _, _ = lsd.detect(img_gray)

            # 3. 在原图上绘制检测到的线段
            result = img_bgr.copy()
            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = map(int, line)
                    cv2.line(result, (x1, y1), (x2, y2), (0, 0, 255), 2)

            self.parent_frame.processed_pil_image = bgr_to_pil(result)

    def imageFastLineDetector(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr             = frame_bgr(self.parent_frame)
            img_gray            = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)        
            # 3. 创建FLD检测器（参数可调）
            # length_threshold: 线段最小长度，小于该值被丢弃
            # distance_threshold: 点到假设线段的距离超过该值视为异常点
            # canny_th1/canny_th2: Canny边缘检测的双阈值
            # do_merge: 是否合并短线段
            fld = _get_ximgproc(self, "createFastLineDetector")
            if fld is None:
                return
            fld = fld.createFastLineDetector(
                length_threshold=10,
                distance_threshold=1.41421356,
                canny_th1=50,
                canny_th2=50,
                canny_aperture_size=3,
                do_merge=False
            )

            # 4. 检测直线
            lines = fld.detect(img_gray)
            if lines is None:                      # 没检测到时直接返回，避免 len(None) 报错
                logging.info("未检测到直线")
                self.parent_frame.processed_pil_image = bgr_to_pil(img_bgr)
                return
            logging.info("检测到 %s 条直线", len(lines))

            # 5. 在原图上绘制检测结果
            drawn_img = fld.drawSegments(img_bgr, lines)
            # 或者手动绘制（可以自定义颜色和粗细）
            # for line in lines:
            #     x0, y0, x1, y1 = line
            #     cv2.line(drawn_img, (int(x0), int(y0)), (int(x1), int(y1)), (0, 255, 0), 1)
            # 6. 转换为PIL Image格式（关键步骤：BGR → RGB）
            self.parent_frame.processed_pil_image = bgr_to_pil(drawn_img)

    def imageBlob(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr             = frame_bgr(self.parent_frame)
            img_gray            = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY) 

            # 3. 设置 SimpleBlobDetector 参数
            params = cv2.SimpleBlobDetector_Params()

            # 阈值范围
            params.minThreshold = 10
            params.maxThreshold = 200
            params.thresholdStep = 10

            # 按面积过滤
            params.filterByArea = True
            params.minArea = 100
            params.maxArea = 10000

            # 按圆度过滤（圆为1，正方形约0.785）
            params.filterByCircularity = True
            params.minCircularity = 0.5

            # 按凸度过滤
            params.filterByConvexity = True
            params.minConvexity = 0.8

            # 按惯性比过滤（拉长程度）
            params.filterByInertia = True
            params.minInertiaRatio = 0.3

            # 4. 创建检测器并运行
            detector  = cv2.SimpleBlobDetector_create(params)
            keypoints = detector.detect(img_gray)

            # 5. 把 Blob 画在彩色原图上（红色圆圈，大小对应 Blob 半径）
            result = cv2.drawKeypoints(
                img_bgr, keypoints, None, (0, 0, 255),
                cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS
            )
            self.parent_frame.processed_pil_image = bgr_to_pil(result)

    def imageEdgeDrawing(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr             = frame_bgr(self.parent_frame)
            img_gray            = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

            ximgproc = _get_ximgproc(self, "createEdgeDrawing")
            if ximgproc is None:
                return
            # 3. 创建 EdgeDrawing 对象并设置参数
            ed                              = ximgproc.createEdgeDrawing()
            #params                          = ximgproc.EdgeDrawing_Params()
            ed.Params.MinPathLength            = 50      # 最小边缘路径长度，值越大越过滤短边
            ed.Params.PFmode                   = False   # 是否使用概率森林模式
            ed.Params.MinLineLength            = 20      # 最小直线长度
            ed.Params.NFAValidation            = True    # 是否开启 NFA 误检验证
            ed.Params.GradientThresholdValue   = 20      # 梯度阈值，越小越敏感
            #ed.setParams(params)

            # 4. 执行边缘检测（必须先调用 detectEdges）
            ed.detectEdges(img_gray)
            segments = ed.getSegments()    # 获取边缘线段

            # 5. 检测直线和椭圆/圆
            lines    = ed.detectLines()
            ellipses = ed.detectEllipses() #包含椭圆中心x坐标、中心y坐标、长半轴长度、短半轴长度、椭圆长轴与水平轴的旋转角度、椭圆的置信度
            logging.info("边缘线段 %s 条, 直线 %s 条, 椭圆 %s 个",
                         len(segments) if segments is not None else 0,
                         len(lines) if lines is not None else 0,
                         len(ellipses) if ellipses is not None else 0)

            # 6. 把结果画到原图上
            result = img_bgr.copy()

            # 画边缘线段（随机颜色）
            if segments is not None:
                for seg in segments:
                    color = tuple(int(c) for c in np.random.randint(0, 256, 3))
                    cv2.polylines(result, [seg], False, color, 1, cv2.LINE_8)

            # 画直线（红色）
            if lines is not None:
                for line in np.uint16(np.around(lines)).reshape(-1, 4):
                    x1, y1, x2, y2 = map(int, line)
                    cv2.line(result, (x1, y1), (x2, y2), (0, 0, 255), 1, cv2.LINE_AA)

            # 画椭圆/圆（圆=红色，椭圆=绿色）
            if ellipses is not None:
                for ellipse in np.uint16(np.around(ellipses)).reshape(-1, 6):
                    x_center, y_center, long_length, short_length, angle, _ = map(int, ellipse)
                    center = (x_center, y_center)
                    axes = (long_length, short_length)      # 长短半轴，不是中心坐标+半轴
                    color = (0, 0, 255) if abs(long_length - short_length) < 5 else (0, 255, 0)
                    cv2.ellipse(result, center, axes, angle, 0, 360, color, 2, cv2.LINE_AA)

            self.parent_frame.processed_pil_image = bgr_to_pil(result)

    def imageHull(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr             = frame_bgr(self.parent_frame)
            img_gray            = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

            # 2. 二值化（前景为白色）
            _, binary = cv2.threshold(img_gray, 127, 255, cv2.THRESH_BINARY)

            # 3. 找轮廓（OpenCV 4.x 返回两个值）
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # 4. 对每个轮廓求凸包并绘制
            result = img_bgr.copy()
            for cnt in contours:
                if cv2.contourArea(cnt) < 100:  # 过滤小噪点
                    continue
                hull = cv2.convexHull(cnt)      # 默认 returnPoints=True，返回顶点坐标
                cv2.polylines(result, [hull], True, (0, 0, 255), 2)

            self.parent_frame.processed_pil_image = bgr_to_pil(result)

    def imageLeastSquaresCircleFitting(self):
        """TODO: 最小二乘圆拟合（可用 cv2.fitEllipse 或 Kasa 算法求圆心半径）"""
        logging.warning("最小二乘圆拟合尚未实现")


class MovingObjectDetectionPanel(MovingObjectDetectionPanelTemplate):
    """MovingObjectDetectionPanel 的事件处理与算法实现。"""

    def imageMODOnRadioBox( self, event ): 
        match self.m_radioBox2.GetSelection():
            case 0:
                self.imageHaar()
            case 1:
                self.imageMatchTemplate()
            case 2:
                self.imageHOG()
            case _:
                logging.warning("未知的选项: %s", self.m_radioBox2.GetSelection())
        self.GetEventHandler().ProcessEvent(self.evt)  # 触发事件  
        event.Skip()

    def imageHaar(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr             = frame_bgr(self.parent_frame)
            img_gray            = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

            # 1. 加载 Haar 级联分类器（使用 OpenCV 自带的人脸检测模型）
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )

            # 3. 检测人脸，返回人脸区域的坐标列表
            faces = face_cascade.detectMultiScale(
                img_gray,
                scaleFactor=1.1,   # 图像缩放比例，越小越精确但越慢
                minNeighbors=5,    # 候选矩形保留的邻域个数，越大越严格
                minSize=(30, 30)   # 最小人脸尺寸，避免检测到过小的噪点
            )

            # 4. 在原始图像上绘制矩形框标记人脸
            for (x, y, w, h) in faces:
                cv2.rectangle(img_bgr, (x, y), (x + w, y + h), (0, 0, 255), 2)

            # 5. 关键步骤：OpenCV 默认是 BGR，PIL 需要 RGB，必须转换
            self.parent_frame.processed_pil_image = bgr_to_pil(img_bgr)

    def imageMatchTemplate(self):
        """模板匹配：用右侧的对比图当模板，在左侧主图里找最相似的位置。"""
        pil_img = self.parent_frame.original_pil_image
        pil_img_template = self.parent_frame.processed_pil_image
        if pil_img is None:
            return
        if pil_img_template is None:
            wx.MessageBox("请先点「打开对比图」选一张模板图片，再执行模板匹配。",
                          "提示", wx.OK | wx.ICON_INFORMATION, self)
            return

        img_bgr = frame_bgr(self.parent_frame)
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        template_gray = pil_to_gray(pil_img_template)

        # 模板比原图还大时 matchTemplate 会直接抛错，先挡掉
        if (template_gray.shape[0] > img_gray.shape[0]
                or template_gray.shape[1] > img_gray.shape[1]):
            wx.MessageBox("模板图片比原图还大，无法匹配，请换一张更小的模板。",
                          "提示", wx.OK | wx.ICON_INFORMATION, self)
            return

        method = cv2.TM_CCOEFF_NORMED
        result = cv2.matchTemplate(img_gray, template_gray, method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # TM_CCOEFF_NORMED 是「越大越匹配」，所以取 max_loc；
        # 如果换成 TM_SQDIFF / TM_SQDIFF_NORMED，就要改成 min_loc（值越小越匹配）
        if method in (cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED):
            top_left, score = min_loc, min_val
        else:
            top_left, score = max_loc, max_val
        logging.info("模板匹配相似度: %.4f", score)

        h, w = template_gray.shape[:2]
        bottom_right = (top_left[0] + w, top_left[1] + h)
        cv2.rectangle(img_bgr, top_left, bottom_right, (0, 0, 255), 2)
        self.parent_frame.processed_pil_image = bgr_to_pil(img_bgr)

    def imageHOG(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr             = frame_bgr(self.parent_frame)
            img_gray            = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)# 1. 读取图像并转灰度

            # 2. 初始化 HOG 描述符
            hog = cv2.HOGDescriptor()
            
            # 3. 设置 SVM 检测器
            # 使用 OpenCV 内置的默认行人检测模型
            hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            
            # 4. 执行多尺度检测
            # detectMultiScale 会在不同尺度下滑动窗口进行检测
            # winStride: 窗口步长，越小检测越精细但速度越慢
            # padding: 填充大小，有助于检测边缘对象
            # scale: 尺度缩放因子，通常设为 1.05 - 1.25
            found_locations, weights = hog.detectMultiScale(
                img_gray, 
                winStride=(8, 8), 
                padding=(16, 16), 
                scale=1.05
            )
            
            # 5. 绘制检测结果
            for (x, y, w, h) in found_locations:
                # 绘制绿色矩形框
                cv2.rectangle(img_bgr, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
            # 6. 将 OpenCV 的 BGR 图转为 PIL Image
            # 关键：必须先把 BGR 转成 RGB，否则颜色会失真
            self.parent_frame.processed_pil_image = bgr_to_pil(img_bgr)


class ObjectDetectionPanel(ObjectDetectionPanelTemplate):
    """ObjectDetectionPanel 的事件处理与算法实现。"""

    def imageMODOnRadioBox( self, event ): 
        match self.m_radioBox2.GetSelection():
            case 0:
                self.imageBackgroundSubstraction()
            case 1:
                self.imageFrameDifferencing()
            case 2:
                self.imageOpticalFlow()
            case _:
                logging.warning("未知的选项: %s", self.m_radioBox2.GetSelection())
        self.GetEventHandler().ProcessEvent(self.evt)  # 触发事件  
        event.Skip()

    def _todo(self, name):
        logging.warning("%s 尚未实现", name)

    def imageBackgroundSubstraction(self):
        """TODO: 背景减除，可用 cv2.createBackgroundSubtractorMOG2() 处理视频帧"""
        self._todo("背景减除")

    def imageFrameDifferencing(self):
        """TODO: 帧差法，处理视频帧序列时用 absdiff(前一帧, 当前帧)"""
        self._todo("帧差法")

    def imageOpticalFlow(self):
        """TODO: 光流法，可用 cv2.calcOpticalFlowFarneback()"""
        self._todo("光流法")


class WatershedPanel(WatershedPanelTemplate):
    """WatershedPanel 的事件处理与算法实现。"""

    def imageWatershedBtnClick( self, event ):
        self.imageWatershedGetWhiteBackground()
        self.GetEventHandler().ProcessEvent(self.evt)  # 触发事件  
        event.Skip()

    def imageWatershedCoinsBtnClick( self, event ):
        self.imageWatershedCoinsPro()
        self.GetEventHandler().ProcessEvent(self.evt)  # 触发事件  
        event.Skip()

    def imageWatershedGetWhiteBackground(self):
        pil_img             = self.parent_frame.original_pil_image
        pil_img_template    = self.parent_frame.processed_pil_image
        if pil_img: 
            # 1. 读取原图和模板
            # 待匹配的大图          
            img_bgr                 = frame_bgr(self.parent_frame)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度）

            ret, thresh = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # 3. 形态学开运算去噪
            kernel  = np.ones((3, 3), np.uint8)
            opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)
            
            # 4. 确定背景区域（膨胀）
            sure_bg = cv2.dilate(opening, kernel, iterations=3)
            
            # 5. 距离变换确定前景
            dist_thresh    = 0.7
            dist_transform = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
            ret, sure_fg   = cv2.threshold(dist_transform, dist_thresh * dist_transform.max(), 255, 0)
            sure_fg        = np.uint8(sure_fg)
            
            # 6. 未知区域 = 背景 - 前景
            unknown = cv2.subtract(sure_bg, sure_fg)
            
            # 7. 创建标记图
            ret, markers = cv2.connectedComponents(sure_fg)
            markers      = markers + 1  # 背景从1开始，避免0被当作未知区域
            markers[unknown == 255] = 0  # 未知区域标记为0
            
            # 8. 运行分水岭算法
            markers = cv2.watershed(img_bgr, markers)
            
            # 9. 生成白底图：背景（markers==1）设为白色，前景保留原色
            result = img_bgr.copy()
            # 分水岭线（-1）也当作背景处理，设为白色
            bg_mask = (markers == 1) | (markers == -1)
            result[bg_mask] = [255, 255, 255]  # BGR白色

            self.parent_frame.processed_pil_image = bgr_to_pil(result)

    def imageWatershedCoinsPro(self):
        pil_img             = self.parent_frame.original_pil_image
        pil_img_template    = self.parent_frame.processed_pil_image
        if pil_img: 
            # 1. 读取原图和模板
            # 待匹配的大图          
            img_bgr                 = frame_bgr(self.parent_frame)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度）

            # 3. Otsu 二值化（反转，前景为白）
            _, thresh = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            # 4. 形态学开运算去除小噪点
            kernel = np.ones((3, 3), np.uint8)
            opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)

            # 5. 膨胀确定背景区域
            sure_bg = cv2.dilate(opening, kernel, iterations=3)

            # 6. 距离变换确定前景区域
            dist_transform = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
            _, sure_fg     = cv2.threshold(dist_transform, 0.7 * dist_transform.max(), 255, 0)
            sure_fg = np.uint8(sure_fg)

            # 7. 确定未知区域
            unknown = cv2.subtract(sure_bg, sure_fg)

            # 8. 连通域标记并生成 marker
            _, markers = cv2.connectedComponents(sure_fg)
            markers    = markers + 1          # 背景标记为 1，而非 0
            markers[unknown == 255] = 0       # 未知区域标记为 0

            # 9. 应用分水岭算法
            markers = cv2.watershed(img_bgr, markers)

            # 10. 将边界标为红色
            img_bgr[markers == -1] = [0, 0, 255]

            # 11. 将 BGR 转为 RGB，再用 PIL Image 显示
            self.parent_frame.processed_pil_image = bgr_to_pil(img_bgr)


class PyramidPanel(PyramidPanelTemplate):
    """PyramidPanel 的事件处理与算法实现。"""

    _HANDLERS = ("imageGaussianPyramid", "imageLaplusPyramid",
                 "imageLaplacianPyramidReconstruction")

    @safe_process
    def imagePyramidOnRadioBox(self, event):
        index = self.m_radioBox2.GetSelection()
        if 0 <= index < len(self._HANDLERS):
            getattr(self, self._HANDLERS[index])()
        else:
            logging.warning("未知的金字塔选项: %s", index)
        self.GetEventHandler().ProcessEvent(self.evt)   # 触发右侧面板刷新
        event.Skip()

    def build_gaussian_pyramid(self, img, levels=3):
        """构建高斯金字塔（逐级 pyrDown 下采样）"""
        pyramid = [img.copy()]
        for _ in range(levels):
            pyramid.append(cv2.pyrDown(pyramid[-1]))
        return pyramid

    def build_laplacian_pyramid(self, img, levels=4):
        """
        构建拉普拉斯金字塔
        :param img: 输入图像 (BGR, uint8)
        :param levels: 金字塔层数
        :return: 拉普拉斯金字塔列表，最后一项是最小的高斯残差图
        """
        # 1. 构建高斯金字塔
        gaussian_pyramid = [img]
        for _ in range(levels - 1):
            gaussian_pyramid.append(cv2.pyrDown(gaussian_pyramid[-1]))

        # 2. 构建拉普拉斯金字塔：每层 = 该层高斯 - 下一层上采样
        laplacian_pyramid = []
        for i in range(levels - 1):
            # pyrUp 的 dstsize 是 (宽, 高)，写成 (高, 高) 会让非正方形图直接报错
            size = (gaussian_pyramid[i].shape[1], gaussian_pyramid[i].shape[0])
            expanded = cv2.pyrUp(gaussian_pyramid[i + 1], dstsize=size)
            laplacian_pyramid.append(cv2.subtract(gaussian_pyramid[i], expanded))

        # 最后一级直接保留高斯金字塔顶层
        laplacian_pyramid.append(gaussian_pyramid[-1])
        return laplacian_pyramid

    def reconstruct_from_laplacian(self, laplacian_pyramid):
        """从拉普拉斯金字塔逐级上采样重建原始图像"""
        current = laplacian_pyramid[-1]
        for i in range(len(laplacian_pyramid) - 2, -1, -1):
            size = (laplacian_pyramid[i].shape[1], laplacian_pyramid[i].shape[0])
            current = cv2.add(cv2.pyrUp(current, dstsize=size), laplacian_pyramid[i])
        return current

    def cv2_to_pil(self, img):
        """OpenCV BGR 转 PIL RGB（单通道直接交给 PIL）"""
        return bgr_to_pil(img)

    @staticmethod
    def _stack_layers(layers):
        """把金字塔各层横排拼成一张图，高度对齐到第一层，宽度等比缩放。

        原来每个方法都在循环里反复覆盖 processed_pil_image，
        最后屏幕上只剩最小的一层，看不出金字塔是怎么变的。
        """
        target_h = layers[0].shape[0]
        panels = []
        for layer in layers:
            if layer.ndim == 2:
                layer = cv2.cvtColor(layer, cv2.COLOR_GRAY2BGR)
            width = max(int(layer.shape[1] * target_h / layer.shape[0]), 1)
            panels.append(cv2.resize(layer, (width, target_h)))
        return np.hstack(panels)

    @safe_process
    def imageGaussianPyramid(self):
        """高斯金字塔：原图 + 4 层下采样，横排显示"""
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        pyramid = self.build_gaussian_pyramid(img_bgr, levels=4)
        logging.info("高斯金字塔各层尺寸: %s", [p.shape[:2] for p in pyramid])
        self.parent_frame.processed_pil_image = bgr_to_pil(self._stack_layers(pyramid))

    @safe_process
    def imageLaplusPyramid(self):
        """拉普拉斯金字塔：各层是高频细节，横排显示"""
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        pyramid = self.build_laplacian_pyramid(img_bgr)
        logging.info("拉普拉斯金字塔各层尺寸: %s", [p.shape[:2] for p in pyramid])
        self.parent_frame.processed_pil_image = bgr_to_pil(self._stack_layers(pyramid))

    @safe_process
    def imageLaplacianPyramidReconstruction(self):
        """拉普拉斯金字塔重建：应与原图基本一致"""
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        pyramid = self.build_laplacian_pyramid(img_bgr, levels=4)
        self.parent_frame.processed_pil_image = self.cv2_to_pil(
            self.reconstruct_from_laplacian(pyramid))


class AaffineTransformationPanel(AaffineTransformationPanelTemplate):
    """AaffineTransformationPanel 的事件处理与算法实现。

    仿射变换的统一套路：构造 2x3 矩阵 -> cv2.warpAffine。
    五种变换的差别只在于矩阵怎么算。
    """

    _HANDLERS = ("imageTranslation", "imageRotate", "imageScaling", "imageShear",
                 "imageCombinationTransformation")

    @safe_process
    def imageAaffineTransformationOnRadioBox(self, event):
        index = self.m_radioBox2.GetSelection()
        if 0 <= index < len(self._HANDLERS):
            getattr(self, self._HANDLERS[index])()
        else:
            logging.warning("未知的仿射变换选项: %s", index)
        self.GetEventHandler().ProcessEvent(self.evt)   # 触发右侧面板刷新
        event.Skip()

    @safe_process
    def imageTranslation(self):
        """平移：向右 100 像素、向下 50 像素"""
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        h, w = img_bgr.shape[:2]
        matrix = np.float32([[1, 0, 100], [0, 1, 50]])
        self.parent_frame.processed_pil_image = bgr_to_pil(
            cv2.warpAffine(img_bgr, matrix, (w, h)))

    def rotate_arbitrary(self, img, angle, fill_color=(255, 255, 255)):
        """绕中心旋转任意角度，并自动扩大画布避免四角被裁掉。"""
        h, w = img.shape[:2]
        matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)

        cos, sin = abs(matrix[0, 0]), abs(matrix[0, 1])
        new_w, new_h = int(h * sin + w * cos), int(h * cos + w * sin)

        # 补偿平移，让图像居中
        matrix[0, 2] += (new_w - w) / 2
        matrix[1, 2] += (new_h - h) / 2
        return cv2.warpAffine(img, matrix, (new_w, new_h),
                              borderMode=cv2.BORDER_CONSTANT,
                              borderValue=fill_color)

    @safe_process
    def imageRotate(self):
        """以图像中心为旋转中心，逆时针旋转 45 度，不缩放"""
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        self.parent_frame.processed_pil_image = bgr_to_pil(
            self.rotate_arbitrary(img_bgr, 45))

    def affine_scale(self, img, sx, sy):
        """仿射变换缩放：只改矩阵对角线元素"""
        h, w = img.shape[:2]
        matrix = np.float32([[sx, 0, 0], [0, sy, 0]])
        return cv2.warpAffine(img, matrix, (int(w * sx), int(h * sy)),
                              flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT,
                              borderValue=(255, 255, 255))

    @safe_process
    def imageScaling(self):
        """放大 2 倍"""
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        self.parent_frame.processed_pil_image = bgr_to_pil(
            self.affine_scale(img_bgr, 2, 2))

    @safe_process
    def imageShear(self):
        """水平错切 30 度：画布同步加宽，右边不会被裁掉"""
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        h, w = img_bgr.shape[:2]
        theta = np.radians(30)
        matrix = np.float32([[1, np.tan(theta), 0], [0, 1, 0]])

        new_w = int(w + abs(np.tan(theta)) * h)
        matrix[0, 2] += (new_w - w) / 2       # 平移修正，让图像居中

        sheared = cv2.warpAffine(img_bgr, matrix, (new_w, h),
                                 flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_CONSTANT,
                                 borderValue=(255, 255, 255))
        self.parent_frame.processed_pil_image = bgr_to_pil(sheared)

    def combined_affine(self, image, rotate_angle=0, scale=1.0, translate=(0, 0), center=None):
        """旋转 + 缩放 + 平移：三个矩阵乘成一个，只需一次插值"""
        h, w = image.shape[:2]
        if center is None:
            center = (w // 2, h // 2)

        rot_scale = cv2.getRotationMatrix2D(center, rotate_angle, scale)
        translate_matrix = np.float32([[1, 0, translate[0]], [0, 1, translate[1]]])

        # 补成 3x3 齐次矩阵才能相乘
        rot_scale_h = np.vstack([rot_scale, [0, 0, 1]])
        translate_h = np.vstack([translate_matrix, [0, 0, 1]])
        combined = (translate_h @ rot_scale_h)[:2]     # 先旋转缩放，再平移

        result = cv2.warpAffine(image, combined, (w, h),
                                borderMode=cv2.BORDER_CONSTANT,
                                borderValue=(255, 255, 255))
        return result, combined

    @safe_process
    def imageCombinationTransformation(self):
        """组合变换：旋转 30 度 + 放大 2 倍 + 平移 (100, 100)"""
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        result, _ = self.combined_affine(img_bgr, 30, 2, (100, 100))
        self.parent_frame.processed_pil_image = bgr_to_pil(result)


class PerspectiveTransformationPanel(PerspectiveTransformationPanelTemplate):
    """PerspectiveTransformationPanel 的事件处理与算法实现。"""

    def imagePerspectiveTransformationBtnClick( self, event ):
        self.imagePerspectiveTransformationPro()
        self.GetEventHandler().ProcessEvent(self.evt)  # 触发事件  
        event.Skip()

    def imagePerspectiveTransformationPro(self):
        pil_img             = self.parent_frame.original_pil_image  
        if pil_img: 
            # 1. 读取原图并转灰度图     
            img_bgr                 = frame_bgr(self.parent_frame)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度)

            h, w = img_bgr.shape[:2]

            # 2. 定义原图上四个点（左上、右上、右下、左下），顺序要对应
            pts1 = np.float32([[114, 82], [287, 156], [216, 333], [8, 322]])
            # 3. 定义目标矩形四个点
            pts2 = np.float32([[0, 0], [188, 0], [188, 262], [0, 262]])

            # 4. 计算透视变换矩阵（3×3）
            M = cv2.getPerspectiveTransform(pts1, pts2)

            # 5. 执行透视变换，输出尺寸 (width, height)
            warped = cv2.warpPerspective(img_bgr, M, (188, 262))
            self.parent_frame.processed_pil_image = bgr_to_pil(warped)


class FourierTransformationPanel(FourierTransformationPanelTemplate):
    """FourierTransformationPanel 的事件处理与算法实现。"""

    def imageFourierTransformationOnRadioBox( self, event ): 
        match self.m_radioBox2.GetSelection():
            case 0:
                self.imageFourierSpectrum()
            case 1:
                self.imageFourierRestored()
            case _:
                logging.warning("未知的选项: %s", self.m_radioBox2.GetSelection())
        self.GetEventHandler().ProcessEvent(self.evt)  # 触发事件  
        event.Skip()

    def imageFourierSpectrum(self):
        'OpenCV 实现傅里叶变换的核心流程是：读图转灰度 → 转 float32 → cv2.dft() → fftshift 中心化 → 计算幅度谱 → 转 PIL Image'
        """
        关键点说明:
        1、数据类型  ：cv2.dft() 要求输入为 np.float32，直接传 uint8 会报错。
        2、频谱中心化：np.fft.fftshift() 把低频分量从四角移到中心，便于观察和滤波操作。
        3、对数变换  ：幅度谱动态范围极大，不取对数的话高频细节几乎全黑，20 * np.log(magnitude + 1) 是标配做法。
        4、逆变换取模：cv2.idft() 返回复数，用 cv2.magnitude() 取幅值才能得到真实图像。
        """
        pil_img             = self.parent_frame.original_pil_image  
        if pil_img: 
            # 1. 读取原图并转灰度图     
            img_bgr                 = frame_bgr(self.parent_frame)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度)
            
            # 2. 转 float32（cv2.dft 不接受 uint8）
            img_float = np.float32(img_gray)

            # 3. 傅里叶变换，输出双通道（实部、虚部）
            dft = cv2.dft(img_float, flags=cv2.DFT_COMPLEX_OUTPUT)

            # 4. 低频移到中心
            dft_shift = np.fft.fftshift(dft)

            # 5. 计算幅度谱并做对数变换（否则动态范围太大看不清）
            magnitude = cv2.magnitude(dft_shift[:, :, 0], dft_shift[:, :, 1])
            magnitude_log = 20 * np.log(magnitude + 1)

            # 6. 归一化到 0-255 并转 uint8
            magnitude_norm = cv2.normalize(magnitude_log, None, 0, 255, cv2.NORM_MINMAX)
            magnitude_uint8 = np.uint8(magnitude_norm)

            # 7. 逆变换还原图像
            f_ishift = np.fft.ifftshift(dft_shift)
            img_back = cv2.idft(f_ishift)
            img_back = cv2.magnitude(img_back[:, :, 0], img_back[:, :, 1])
            img_back = cv2.normalize(img_back, None, 0, 255, cv2.NORM_MINMAX)
            img_back = np.uint8(img_back)

            # 8. 转 PIL Image（OpenCV 是 BGR，单通道灰度图不需要通道转换            
            self.parent_frame.processed_pil_image = Image.fromarray(magnitude_uint8)

    def imageFourierRestored(self):
        
        pil_img             = self.parent_frame.original_pil_image  
        if pil_img: 
            # 1. 读取原图并转灰度图     
            img_bgr                 = frame_bgr(self.parent_frame)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度)

            # 2. 转 float32（cv2.dft 不接受 uint8）
            img_float = np.float32(img_gray)

            # 3. 傅里叶变换，输出双通道（实部、虚部）
            dft = cv2.dft(img_float, flags=cv2.DFT_COMPLEX_OUTPUT)

            # 4. 低频移到中心
            dft_shift = np.fft.fftshift(dft)

            # 5. 计算幅度谱并做对数变换（否则动态范围太大看不清）
            magnitude = cv2.magnitude(dft_shift[:, :, 0], dft_shift[:, :, 1])
            magnitude_log = 20 * np.log(magnitude + 1)

            # 6. 归一化到 0-255 并转 uint8
            magnitude_norm  = cv2.normalize(magnitude_log, None, 0, 255, cv2.NORM_MINMAX)
            magnitude_uint8 = np.uint8(magnitude_norm)

            # 7. 逆变换还原图像
            f_ishift = np.fft.ifftshift(dft_shift)
            img_back = cv2.idft(f_ishift)
            img_back = cv2.magnitude(img_back[:, :, 0], img_back[:, :, 1])
            img_back = cv2.normalize(img_back, None, 0, 255, cv2.NORM_MINMAX)
            img_back = np.uint8(img_back)

            # 8. 转 PIL Image（OpenCV 是 BGR，单通道灰度图不需要通道转换）
            
            self.parent_frame.processed_pil_image = Image.fromarray(img_back)


class FloodFillPanel(FloodFillPanelTemplate):
    """FloodFillPanel 的事件处理与算法实现。"""

    def imageFloodFillOnBtnClick( self, event ):
        self.imageFloodFillOnBtnClickPro()
        self.GetEventHandler().ProcessEvent(self.evt)  # 触发事件  
        event.Skip()

    def imageFloodFillOnBtnClickPro(self):
        """
        关键说明:
        1、mask 尺寸必须是 (h+2, w+2)，否则会报错，这是 OpenCV 的硬性要求。
        2、flags 低 8 位控制连通性（4 或 8），FLOODFILL_FIXED_RANGE 表示与种子点像素值比较，否则与相邻像素比较。
        """
        pil_img             = self.parent_frame.original_pil_image
        if pil_img: 
            # 1. 读取原图并转灰度图     
            img_bgr                 = frame_bgr(self.parent_frame)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度)

            h, w = img_bgr.shape[:2]

            # 3. 创建 mask，尺寸必须比原图大 2（高+2，宽+2），单通道 uint8
            mask = np.zeros((h + 2, w + 2), np.uint8)

            # 4. 设置种子点、填充颜色和像素差值范围
            seed_point  = (50, 50)        # (x, y) 坐标
            new_val     = (0, 255, 255)      # 填充为黄色（BGR）
            lo_diff     = (30, 30, 30)       # 下界差值
            up_diff     = (30, 30, 30)       # 上界差值

            # 5. 执行漫水填充：4连通 + FLOODFILL_FIXED_RANGE（与种子点比较）
            flags = 4 | cv2.FLOODFILL_FIXED_RANGE
            cv2.floodFill(img_bgr, mask, seed_point, new_val, lo_diff, up_diff, flags)

            # 6. OpenCV BGR -> RGB，再转 PIL Image
            self.parent_frame.processed_pil_image = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))


class RemappingPanel(RemappingPanelTemplate):
    """RemappingPanel 的事件处理与算法实现。

    map_x / map_y 的含义：目标图 (x, y) 处的像素取自原图的 (map_x[y,x], map_y[y,x])。
    dtype 必须是 np.float32，否则 cv2.remap 直接报错。

    原理演示用的是坐标映射，所以复用同一套骨架；原来每个方法都写了一遍
    h*w 的双重 for 循环（750x437 就是 33 万次 Python 迭代），
    这里换成 np.indices 向量化，快两个数量级。
    """

    _HANDLERS = ("imageHorizontalMirror", "imageVerticalMirror", "imageFlipAroundXYAxis",
                 "imageCompressXAxisByHalf", "imageCompressYAxisByHalf",
                 "imageCompressEachXAndYAxesByHalf")

    @safe_process
    def imageRemappingOnRadioBox(self, event):
        index = self.m_radioBox2.GetSelection()
        if 0 <= index < len(self._HANDLERS):
            getattr(self, self._HANDLERS[index])()
        else:
            logging.warning("未知的重映射选项: %s", index)
        self.GetEventHandler().ProcessEvent(self.evt)   # 触发右侧面板刷新
        event.Skip()

    def _apply(self, build_maps):
        """build_maps(xs, ys, h, w) -> (map_x, map_y)，各算法只描述映射规则。"""
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        h, w = img_bgr.shape[:2]
        ys, xs = np.indices((h, w), dtype=np.float32)   # xs 是列号，ys 是行号
        map_x, map_y = build_maps(xs, ys, h, w)
        remapped = cv2.remap(img_bgr, map_x, map_y, interpolation=cv2.INTER_LINEAR)
        self.parent_frame.processed_pil_image = bgr_to_pil(remapped)

    def imageHorizontalMirror(self):
        """水平镜像：x 翻转，y 不变"""
        self._apply(lambda xs, ys, h, w: (w - 1 - xs, ys))

    def imageVerticalMirror(self):
        """垂直镜像：y 翻转，x 不变"""
        self._apply(lambda xs, ys, h, w: (xs, h - 1 - ys))

    def imageFlipAroundXYAxis(self):
        """绕 XY 轴翻转：x、y 都翻转，等价于旋转 180 度"""
        self._apply(lambda xs, ys, h, w: (w - 1 - xs, h - 1 - ys))

    def imageCompressXAxisByHalf(self):
        """x 方向压缩一半：map_x = 2*x（右半边会被裁掉）"""
        self._apply(lambda xs, ys, h, w: (2 * xs, ys))

    def imageCompressYAxisByHalf(self):
        """y 方向压缩一半：map_y = 2*y（下半部分会被裁掉）"""
        self._apply(lambda xs, ys, h, w: (xs, 2 * ys))

    def imageCompressEachXAndYAxesByHalf(self):
        """x、y 同时压缩一半：整幅图缩到左上角 1/4"""
        self._apply(lambda xs, ys, h, w: (2 * xs, 2 * ys))


class BackProjectionPanel(BackProjectionPanelTemplate):
    """BackProjectionPanel 的事件处理与算法实现。"""

    @safe_process
    def imageBackProjectionOnBtnClick(self, event):
        self.imageBackProjectionOnBtnClickPro()
        self.GetEventHandler().ProcessEvent(self.evt)   # 触发右侧面板刷新
        event.Skip()

    def imageBackProjectionOnBtnClickPro(self):
        """反向投影：用左侧图当样本、右侧图当目标，找出目标里与样本相似的颜色区域。"""
        roi_img = self.parent_frame.original_pil_image
        target_img = self.parent_frame.processed_pil_image
        if roi_img is None:
            return
        if target_img is None:
            wx.MessageBox("请先点「打开目标图片」选一张要在其中搜索的图片。",
                          "提示", wx.OK | wx.ICON_INFORMATION, self)
            return

        # 1. 统一转成 BGR（PIL 是 RGB，直接 cvtColor(BGR2HSV) 会算错通道）
        roi_bgr = pil_to_bgr(roi_img)
        target_bgr = pil_to_bgr(target_img)

        # 2. 转 HSV 色彩空间（只用 H 和 S 通道，减弱光照影响）
        roi_hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
        target_hsv = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2HSV)

        # 3. 计算样本的 2D 直方图（H: 0-180, S: 0-256）
        roi_hist = cv2.calcHist([roi_hsv], [0, 1], None, [180, 256], [0, 180, 0, 256])
        # 4. 归一化到 0~255，这一步很关键
        cv2.normalize(roi_hist, roi_hist, 0, 255, cv2.NORM_MINMAX)

        # 5. 反向投影：把样本直方图"投影"到目标图上
        back_proj = cv2.calcBackProject([target_hsv], [0, 1], roi_hist, [0, 180, 0, 256], 1)

        # 6. 用椭圆核做卷积，把离散的点连成片
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        back_proj = cv2.filter2D(back_proj, -1, kernel)

        # 7. 阈值二值化，只保留匹配度高的区域
        _, thresh = cv2.threshold(back_proj, 50, 255, cv2.THRESH_BINARY)

        # 8. 二值图与原图按位与，得到彩色的匹配结果
        thresh_3ch = cv2.merge([thresh, thresh, thresh])
        result = cv2.bitwise_and(target_bgr, thresh_3ch)
        self.parent_frame.processed_pil_image = bgr_to_pil(result)


class CameraPanel(CameraPanelTemplate):
    """CameraPanel 暂无算法实现。"""
    pass


class CoordinateCalibrationPanel(CoordinateCalibrationPanelTemplate):
    """CoordinateCalibrationPanel 暂无算法实现。"""
    pass


class OcrPanel(OcrPanelTemplate):
    """OcrPanel 的事件处理与算法实现。"""

    @safe_process
    def imageOcrOnBtnClick(self, event):
        self.imageOcrOnBtnClickPro()
        self.GetEventHandler().ProcessEvent(self.evt)   # 触发右侧面板刷新
        event.Skip()

    def imageOcrOnBtnClickPro(self):
        gray = frame_gray(self.parent_frame)
        if gray is None:
            return
        if not ensure_tesseract():
            wx.MessageBox("未安装 pytesseract，无法进行文字识别。",
                          "缺少依赖", wx.OK | wx.ICON_WARNING, self)
            return

        # 自适应阈值：对光照不均的文档比全局阈值更稳
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 31, 10)
        try:
            text = pytesseract.image_to_string(binary, config=r'--oem 3 --psm 6 -l chi_sim+eng')
        except Exception as exc:
            logging.exception("OCR 识别失败")
            wx.MessageBox(f"OCR 识别失败，请检查 tesseract 与中文语言包：\n{exc}",
                          "识别失败", wx.OK | wx.ICON_ERROR, self)
            text = ""
        logging.info("识别结果: %s", text)
        self.parent_frame.imageInfoStaticText.SetLabel(f"识别结果: {text.strip()}")
        self.parent_frame.processed_pil_image = bgr_to_pil(binary)


class VehicleLicensePlateRecognitionPanel(VehicleLicensePlateRecognitionPanelTemplate):
    """VehicleLicensePlateRecognitionPanel 的事件处理与算法实现。"""

    @safe_process
    def imageVLPROnBtnClick(self, event):
        self.imageVLPROnBtnClickPro()
        self.GetEventHandler().ProcessEvent(self.evt)   # 触发右侧面板刷新
        event.Skip()

    def locate_license_plate(self, edged, img):
        """定位车牌区域：形态学闭运算 + 轮廓筛选（矩形 + 宽高比 2~5）"""
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 5))
        closed = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

        for contour in contours:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            if len(approx) != 4:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            if h > 0 and 2 < w / float(h) < 5:      # 车牌宽高比一般 2~5
                return (x, y, w, h), approx
        return None, None

    def segment_characters(self, plate_img):
        """字符分割的第一步：灰度 + Otsu 反色二值化（字符为白）"""
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        return cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    def recognize_with_tesseract(self, char_img):
        """用 Tesseract 识别字符（白名单限定为数字 + 大写字母）"""
        if not ensure_tesseract():          # 和 OCR 面板共用同一个 tesseract 路径配置
            return ""
        config = '--psm 8 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        return pytesseract.image_to_string(Image.fromarray(char_img), config=config).strip()

    def imageVLPROnBtnClickPro(self):
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return

        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)

        plate_rect, _ = self.locate_license_plate(edged, img_bgr)
        if plate_rect is None:
            logging.info("未检测到车牌区域")
            wx.MessageBox("没有定位到车牌，可以换一张角度更正的照片试试。",
                          "提示", wx.OK | wx.ICON_INFORMATION, self)
            return

        x, y, w, h = plate_rect
        plate_img = img_bgr[y:y + h, x:x + w]
        if plate_img.size == 0:
            return

        char_binary = self.segment_characters(plate_img)
        try:
            plate_text = self.recognize_with_tesseract(char_binary)
        except Exception:
            logging.exception("车牌字符识别失败")
            plate_text = ""
        logging.info("车牌识别结果: %s", plate_text)
        if plate_text:
            self.parent_frame.imageInfoStaticText.SetLabel(f"车牌识别结果: {plate_text}")

        result_img = img_bgr.copy()
        cv2.rectangle(result_img, (x, y), (x + w, y + h), (0, 255, 0), 3)
        if plate_text:
            cv2.putText(result_img, plate_text, (x, max(y - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
        self.parent_frame.processed_pil_image = bgr_to_pil(result_img)


class QRCodeRecognizationPanel(QRCodeRecognizationPanelTemplate):
    """QRCodeRecognizationPanel 的事件处理与算法实现。"""

    @safe_process
    def imageQRCodeRecognizationOnBtnClick(self, event):
        self.imageQRCodeRecognizationOnPro()
        self.GetEventHandler().ProcessEvent(self.evt)   # 触发右侧面板刷新
        event.Skip()

    def imageQRCodeRecognizationOnPro(self):
        img_bgr = frame_bgr(self.parent_frame)
        if img_bgr is None:
            return
        try:
            from pyzbar.pyzbar import decode         # 可选依赖，延迟导入
        except ImportError:
            wx.MessageBox("未安装 pyzbar，无法识别二维码。\n可执行：pip install pyzbar",
                          "缺少依赖", wx.OK | wx.ICON_WARNING, self)
            return

        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        # 直接对灰度图解码比先二值化更稳（pyzbar 内部会自己做二值化）
        decoded_objects = decode(gray)

        if not decoded_objects:
            logging.info("未识别到二维码")
            wx.MessageBox("没有识别到二维码，试试裁剪到二维码区域再点一次。",
                          "提示", wx.OK | wx.ICON_INFORMATION, self)
            return

        for obj in decoded_objects:
            data = obj.data.decode('utf-8', errors='replace')   # 容错，避免解码异常
            logging.info("识别内容: %s (%s)", data, obj.type)
            if obj.polygon:
                points = np.array(obj.polygon, dtype=np.int32)
                cv2.polylines(img_bgr, [points], True, (0, 255, 0), 3)
            x, y, _, _ = obj.rect
            cv2.putText(img_bgr, data, (x, max(y - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 255, 0), 2, cv2.LINE_AA)
            self.parent_frame.imageInfoStaticText.SetLabel(f"二维码内容: {data}")

        self.parent_frame.processed_pil_image = bgr_to_pil(img_bgr)
