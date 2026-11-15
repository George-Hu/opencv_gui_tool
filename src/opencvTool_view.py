# -*- coding: utf-8 -*-
"""视图层（view）—— 界面显示：面板切换、图片缩放显示、面板重绘。

主窗口 cvToolView 继承「模板层布局 + 控制层事件」，
自身只关心怎么把图片显示出来：
    * display_image()      图片按面板尺寸等比缩放显示
    * PanelOnPaint()       绘制图片与截图框
    * switch_panel()       切换底部算法参数面板
"""

import logging

import wx

from opencvTool_template import cvToolTemplate, EVT_RIGHT_DISPLAY
from opencvTool_control import (
    cvToolControlMixin,
    ColorExtractionPanel,
    ImageDifferencePanel,
    ImageStitchingPanel,
    HistogramPanel,
    ColorSpaceAndChannelExtractionPanel,
    EqualizationPanel,
    ThresholdProcessingPanel,
    FilteringPanel,
    MorphologicalOperationPanel,
    ROIPanel,
    CornerDetectionPanel,
    EdgeDetectionPanel,
    GeometricShapePanel,
    MovingObjectDetectionPanel,
    ObjectDetectionPanel,
    WatershedPanel,
    PyramidPanel,
    AaffineTransformationPanel,
    PerspectiveTransformationPanel,
    FourierTransformationPanel,
    FloodFillPanel,
    RemappingPanel,
    BackProjectionPanel,
    CameraPanel,
    CoordinateCalibrationPanel,
    OcrPanel,
    VehicleLicensePlateRecognitionPanel,
    QRCodeRecognizationPanel,
)


class cvToolView(cvToolControlMixin, cvToolTemplate):
    """主窗口视图：模板布局 + 控制事件 + 显示逻辑。"""

    # ------------------------------------------------------------ 初始化
    def __init__(self, parent):
        # 模板层负责搭界面（内部会回调 _build_panels 挂载算法面板）
        super().__init__(parent)

        # 当前显示面板
        self.current_panel = None
        # 原图 和 处理后图片数据保存变量
        self.original_pil_image  = None
        self.processed_pil_image = None

        self.bitmap              = None  # 当前左panel显示的wx.Bitmap
        self.processed_bitmap    = None  # 当前右panel显示的wx.Bitmap

        self.scale               = 1.0   # 显示缩放比例
        self.start_pos           = None  # 鼠标按下时的坐标
        self.current_pos         = None  # 鼠标当前坐标

        self.original_pil_image_width   = 0
        self.original_pil_image_height  = 0
        self.used_function = f"Test  测试函数"
        self.processed_pil_image_width  = 0
        self.processed_pil_image_height = 0

        self.exampleImage.Hide()

        # 面板算法算完后发来的「刷新右侧面板」事件
        self.Bind(EVT_RIGHT_DISPLAY, self.OnDoRightPanelImageDisplayEvent)

    def __del__(self):
        logging.info("run __del__ ")
        pass

    # ------------------------------------------------------------ 面板挂载
    def _build_panels(self, frameSizer):
        # 可切换面板定义
        self.colorExtractionPanel = ColorExtractionPanel(self);frameSizer.Add( self.colorExtractionPanel, 0, wx.ALL, 30 );
        self.colorExtractionPanel.Hide()
        self.imageDifferencePanel = ImageDifferencePanel(self);frameSizer.Add( self.imageDifferencePanel, 0, wx.ALL, 30 );
        self.imageDifferencePanel.Hide()
        self.imageStitchingPanel  = ImageStitchingPanel(self);frameSizer.Add( self.imageStitchingPanel, 0, wx.ALL, 30 );
        self.imageStitchingPanel.Hide()        
        self.imageHistogramPanel  = HistogramPanel(self);frameSizer.Add( self.imageHistogramPanel, 0, wx.ALL, 30 );
        self.imageHistogramPanel.Hide()
        self.imageColorSpaceAndChannelExtractionPanel = ColorSpaceAndChannelExtractionPanel(self);frameSizer.Add( self.imageColorSpaceAndChannelExtractionPanel, 0, wx.ALL, 30 )
        self.imageColorSpaceAndChannelExtractionPanel.Hide()
        self.imageEqualizationPanel = EqualizationPanel(self);frameSizer.Add( self.imageEqualizationPanel, 0, wx.ALL, 30 );
        self.imageEqualizationPanel.Hide()        
        self.imageThresholdProcessingPanel = ThresholdProcessingPanel(self);frameSizer.Add( self.imageThresholdProcessingPanel, 0, wx.ALL, 30 )
        self.imageThresholdProcessingPanel.Hide()
        self.imageFilteringPanel = FilteringPanel(self); frameSizer.Add( self.imageFilteringPanel, 0, wx.ALL, 30 )
        self.imageFilteringPanel.Hide()
        self.imageMorphologicalOperationPanel = MorphologicalOperationPanel(self);frameSizer.Add( self.imageMorphologicalOperationPanel, 0, wx.ALL, 30 )
        self.imageMorphologicalOperationPanel.Hide()
        self.imageROIPanel = ROIPanel(self);frameSizer.Add( self.imageROIPanel, 0, wx.ALL, 30 )
        self.imageROIPanel.Hide()        
        self.imageCornerDetectionPanel = CornerDetectionPanel(self);frameSizer.Add( self.imageCornerDetectionPanel, 0, wx.ALL, 30 )
        self.imageCornerDetectionPanel.Hide()
        self.imageEdgeDetectionPanel = EdgeDetectionPanel(self);frameSizer.Add( self.imageEdgeDetectionPanel, 0, wx.ALL, 30 )
        self.imageEdgeDetectionPanel.Hide()
        self.imageGeometricShapePanel = GeometricShapePanel(self);frameSizer.Add( self.imageGeometricShapePanel, 0, wx.ALL, 30 )
        self.imageGeometricShapePanel.Hide()        
        self.imageMovingObjectDetectionPanel = MovingObjectDetectionPanel(self);frameSizer.Add( self.imageMovingObjectDetectionPanel, 0, wx.ALL, 30 )
        self.imageMovingObjectDetectionPanel.Hide()
        self.imageObjectDetectionPanel = ObjectDetectionPanel(self);frameSizer.Add( self.imageObjectDetectionPanel, 0, wx.ALL, 30 )
        self.imageObjectDetectionPanel.Hide()
        self.imageWatershedPanel = WatershedPanel(self);frameSizer.Add( self.imageWatershedPanel, 0, wx.ALL, 30 )
        self.imageWatershedPanel.Hide()        
        self.imagePyramidPanel = PyramidPanel(self);frameSizer.Add( self.imagePyramidPanel, 0, wx.ALL, 30 )
        self.imagePyramidPanel.Hide()
        self.imageAaffineTransformationPanel = AaffineTransformationPanel(self);frameSizer.Add( self.imageAaffineTransformationPanel, 0, wx.ALL, 30 )
        self.imageAaffineTransformationPanel.Hide()
        self.imagePerspectiveTransformationPanel = PerspectiveTransformationPanel(self);frameSizer.Add( self.imagePerspectiveTransformationPanel, 0, wx.ALL, 30 )
        self.imagePerspectiveTransformationPanel.Hide()
        self.imageFourierTransformationPanel = FourierTransformationPanel(self);frameSizer.Add( self.imageFourierTransformationPanel, 0, wx.ALL, 30 )
        self.imageFourierTransformationPanel.Hide()
        self.imageFloodFillPanel = FloodFillPanel(self);frameSizer.Add( self.imageFloodFillPanel, 0, wx.ALL, 30 )
        self.imageFloodFillPanel.Hide()
        self.imageRemappingPanel = RemappingPanel(self);frameSizer.Add( self.imageRemappingPanel, 0, wx.ALL, 30 )
        self.imageRemappingPanel.Hide()
        self.imageBackProjectionPanel = BackProjectionPanel(self);frameSizer.Add( self.imageBackProjectionPanel, 0, wx.ALL, 30 )
        self.imageBackProjectionPanel.Hide()
        self.imageCameraPanel = CameraPanel(self);frameSizer.Add( self.imageCameraPanel, 0, wx.ALL, 30 )
        self.imageCameraPanel.Hide()
        self.imageCoordinateCalibrationPanel = CoordinateCalibrationPanel(self);frameSizer.Add( self.imageCoordinateCalibrationPanel, 0, wx.ALL, 30 )
        self.imageCoordinateCalibrationPanel.Hide()
        self.imageOcrPanel = OcrPanel(self);frameSizer.Add( self.imageOcrPanel, 0, wx.ALL, 30 )
        self.imageOcrPanel.Hide()
        self.imageVehicleLicensePlateRecognitionPanel = VehicleLicensePlateRecognitionPanel(self);frameSizer.Add( self.imageVehicleLicensePlateRecognitionPanel, 0, wx.ALL, 30 )
        self.imageVehicleLicensePlateRecognitionPanel.Hide()
        self.imageQRCodeRecognizationPanel = QRCodeRecognizationPanel(self);frameSizer.Add( self.imageQRCodeRecognizationPanel, 0, wx.ALL, 30 )
        self.imageQRCodeRecognizationPanel.Hide()

    def PanelOnPaint( self, bitmap, image_panel ):        
        """绘制图片和截图框"""
        dc = wx.PaintDC(image_panel)
        if bitmap:
            dc.DrawBitmap(bitmap, 0, 0)
        # 绘制拖拽中的矩形框
        if self.start_pos and self.current_pos:
            x1, y1 = self.start_pos
            x2, y2 = self.current_pos
            left, top = min(x1, x2), min(y1, y2)
            width, height = abs(x2 - x1), abs(y2 - y1)
            if 0:
                dc.SetPen(wx.Pen(wx.Colour(255, 0, 0), 2))
                dc.SetBrush(wx.Brush(wx.Colour(255, 0, 0, 50)))
            else:
                dc.SetPen(wx.Pen(wx.Colour(100, 150, 200), 2))
                # 外框天蓝色，框内透明
                dc.SetBrush(wx.Brush("sky blue", wx.TRANSPARENT))
            dc.DrawRectangle(left, top, width, height)

    def leftPanelOnPaint( self, event ): 
        self.PanelOnPaint(self.bitmap,self.leftImagePanel)
        event.Skip()

    def rightPanelOnPaint( self, event ): 
        self.PanelOnPaint(self.processed_bitmap,self.rightImagePanel)        
        event.Skip()

    def OnDoRightPanelImageDisplayEvent(self, event):
        """Frame中处理图片变换"""
        # 这里做图片变换逻辑（比如翻转、缩放、换图）   
        self.display_image(self.processed_pil_image, 1) 
        
        self.statusBar.SetStatusText(f"原始图片大小: {self.original_pil_image.width}x{self.original_pil_image.height} -> \
            转换后图片大小: {self.processed_pil_image.width}x{self.processed_pil_image.height}")

        self.imageInfoStaticText.SetLabel((f"原图: {self.original_pil_image.width}x{self.original_pil_image.height}px -> \
            处理后图片: {self.processed_pil_image.width}x{self.processed_pil_image.height}px"))
        event.Skip()

    def display_image(self, pil_image, display_flag):
        """按Panel大小缩放显示图片"""
        if not pil_image:
            return
        
        if display_flag == 0:
            panel_w, panel_h = self.leftImagePanel.GetClientSize()
        else:
            panel_w, panel_h = self.rightImagePanel.GetClientSize()

        img_w, img_h     = pil_image.size

        # 计算缩放比例，保持宽高比
        self.scale      = min(panel_w / img_w, panel_h / img_h)
        new_w, new_h    = int(img_w * self.scale), int(img_h * self.scale)
        
        # 转换为wx.Image并缩放
        wx_img = wx.Image(pil_image.size, pil_image.convert("RGB").tobytes())
        wx_img = wx_img.Scale(new_w, new_h)

        if display_flag == 0:            
            self.bitmap = wx_img.ConvertToBitmap()  # <class 'wx._core.Bitmap'>
            self.leftImagePanel.Refresh()
        else:
            self.processed_bitmap = wx_img.ConvertToBitmap() # <class 'wx._core.Bitmap'>
            self.rightImagePanel.Refresh()

    def switch_panel(self, new_panel):
        """切换内容面板的通用方法"""
        if self.current_panel:
            self.current_panel.Hide()        
        self.current_panel = new_panel
        self.current_panel.Show()
        self.current_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOW ) )
        self.Layout()
