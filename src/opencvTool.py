
# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version 4.2.1-0-g80c4cb6)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc
import wx.adv

import cv2
import numpy as np
import os
import time
import onnxruntime as ort
import sys

from PIL import Image
from wx.lib.newevent import NewEvent

import matplotlib
import matplotlib.pyplot as plt
matplotlib.use("WXAgg")
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.figure import Figure

import io
import pytesseract

import gettext
_ = gettext.gettext

# 日志记录到文件功能
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s',
    filename='app.log',  # 日志文件，不存在则自动创建
    filemode='a'         # 'a' 追加模式，'w' 覆盖模式
)

# 1、定义事件类
class TriggrRightPanelDisplayEvent(wx.PyCommandEvent):
    def __init__(self, evtType, id):
        wx.PyCommandEvent.__init__(self, evtType, id)
# 2、 创建一个事件类型
myEVT_RIGHT_DISPLAY = wx.NewEventType() 
# 3、 创建一个绑定器对象
EVT_RIGHT_DISPLAY = wx.PyEventBinder(myEVT_RIGHT_DISPLAY, 1)  


###########################################################################
## Class AlgorithmPanelBase - 所有算法面板的公共基类
###########################################################################

class AlgorithmPanelBase( wx.Panel ):
    """算法面板公共基类，统一：
       1. 构造流程（wx.Panel 初始化 + parent_frame 引用）
       2. 结果输出（finish：ndarray -> PIL -> 主框架 processed_pil_image）
       3. 显示事件通知（fire_display_event）
       4. RadioBox 分发（run_algorithm + ALGORITHM_METHODS 表驱动）
    """
    ALGORITHM_METHODS = []  # 子类按 RadioBox 顺序覆写

    def __init__( self, parent ):
        wx.Panel.__init__( self, parent )
        self.parent_frame = parent

    # ---------- 结果输出 ----------
    def finish( self, img ):
        """将算法结果写入主框架并触发右侧刷新。
           img: BGR(3通道) ndarray 自动转 RGB；灰度/单通道(2维) ndarray 直接输出。"""
        if isinstance( img, np.ndarray ) and img.ndim == 2:
            pil_img = Image.fromarray( img )
        else:
            pil_img = Image.fromarray( cv2.cvtColor( img, cv2.COLOR_BGR2RGB ) )
        self.parent_frame.processed_pil_image = pil_img
        self.fire_display_event()

    def fire_display_event( self ):
        """通知主框架刷新右侧显示面板。"""
        evt = TriggrRightPanelDisplayEvent( myEVT_RIGHT_DISPLAY, self.GetId() )
        self.GetEventHandler().ProcessEvent( evt )

    # ---------- RadioBox 表驱动分发 ----------
    def run_algorithm( self, index ):
        """按 ALGORITHM_METHODS 表调用对应算法方法。"""
        if 0 <= index < len( self.ALGORITHM_METHODS ):
            getattr( self, self.ALGORITHM_METHODS[index] )()


###########################################################################
## Class cvToolDemo
###########################################################################

class cvTool ( wx.Frame ):

    def __init__( self, parent ):
        wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = _(u"OpenCV算法演示工具"), pos = wx.DefaultPosition, size = wx.Size( 1200,1600 ), style = wx.DEFAULT_FRAME_STYLE|wx.BORDER_THEME|wx.TAB_TRAVERSAL )

        self.SetSizeHints( wx.Size( 1600,-1 ), wx.DefaultSize )
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_INACTIVECAPTION ) )

        self.menuBar = wx.MenuBar( 0 )
        self.image_processing = wx.Menu()
        self.color_extraction = wx.MenuItem( self.image_processing, wx.ID_ANY, _(u"颜色提取"), wx.EmptyString, wx.ITEM_NORMAL )
        self.image_processing.Append( self.color_extraction )
        self.image_difference = wx.MenuItem( self.image_processing, wx.ID_ANY, _(u"图像差"), wx.EmptyString, wx.ITEM_NORMAL )
        self.image_processing.Append( self.image_difference )
        self.image_stitching = wx.MenuItem( self.image_processing, wx.ID_ANY, _(u"图像拼接"), wx.EmptyString, wx.ITEM_NORMAL )
        self.image_processing.Append( self.image_stitching )
        self.histogram = wx.MenuItem( self.image_processing, wx.ID_ANY, _(u"直方图"), wx.EmptyString, wx.ITEM_NORMAL )
        self.image_processing.Append( self.histogram )
        self.color_space_and_channel_extraction = wx.MenuItem( self.image_processing, wx.ID_ANY, _(u"颜色空间与通道提取"), wx.EmptyString, wx.ITEM_NORMAL )
        self.image_processing.Append( self.color_space_and_channel_extraction )
        self.menuBar.Append( self.image_processing, _(u"图像处理") )

        self.preprocessing = wx.Menu()
        self.equalization = wx.MenuItem( self.preprocessing, wx.ID_ANY, _(u"均衡化"), wx.EmptyString, wx.ITEM_NORMAL )
        self.preprocessing.Append( self.equalization )
        self.threshold_processing = wx.MenuItem( self.preprocessing, wx.ID_ANY, _(u"阈值处理"), wx.EmptyString, wx.ITEM_NORMAL )
        self.preprocessing.Append( self.threshold_processing )
        self.filtering = wx.MenuItem( self.preprocessing, wx.ID_ANY, _(u"滤波"), wx.EmptyString, wx.ITEM_NORMAL )
        self.preprocessing.Append( self.filtering )
        self.morphological_operation = wx.MenuItem( self.preprocessing, wx.ID_ANY, _(u"形态学运算"), wx.EmptyString, wx.ITEM_NORMAL )
        self.preprocessing.Append( self.morphological_operation )
        self.ROI = wx.MenuItem( self.preprocessing, wx.ID_ANY, _(u"感兴趣区域"), wx.EmptyString, wx.ITEM_NORMAL )
        self.preprocessing.Append( self.ROI )
        self.menuBar.Append( self.preprocessing, _(u"预处理") )

        self.detection = wx.Menu()
        self.corner_detection = wx.MenuItem( self.detection, wx.ID_ANY, _(u"角点检测"), wx.EmptyString, wx.ITEM_NORMAL )
        self.detection.Append( self.corner_detection )
        self.edge_detection = wx.MenuItem( self.detection, wx.ID_ANY, _(u"边缘检测"), wx.EmptyString, wx.ITEM_NORMAL )
        self.detection.Append( self.edge_detection )
        self.geometric_shape = wx.MenuItem( self.detection, wx.ID_ANY, _(u"几何形状检测"), wx.EmptyString, wx.ITEM_NORMAL )
        self.detection.Append( self.geometric_shape )
        self.moving_object_detection = wx.MenuItem( self.detection, wx.ID_ANY, _(u"运动目标检测"), wx.EmptyString, wx.ITEM_NORMAL )
        self.detection.Append( self.moving_object_detection )
        self.object_detection = wx.MenuItem( self.detection, wx.ID_ANY, _(u"目标检测"), wx.EmptyString, wx.ITEM_NORMAL )
        self.detection.Append( self.object_detection )
        self.menuBar.Append( self.detection, _(u"检测") )

        self.positioning = wx.Menu()        
        self.watershed = wx.MenuItem( self.positioning, wx.ID_ANY, _(u"分水岭"), wx.EmptyString, wx.ITEM_NORMAL )
        self.positioning.Append( self.watershed )
        self.menuBar.Append( self.positioning, _(u"定位") )

        self.image_transformation = wx.Menu()
        self.pyramid = wx.MenuItem( self.image_transformation, wx.ID_ANY, _(u"金字塔"), wx.EmptyString, wx.ITEM_NORMAL )
        self.image_transformation.Append( self.pyramid )
        self.affine_transformation = wx.MenuItem( self.image_transformation, wx.ID_ANY, _(u"仿射变换"), wx.EmptyString, wx.ITEM_NORMAL )
        self.image_transformation.Append( self.affine_transformation )
        self.perspective_transformation = wx.MenuItem( self.image_transformation, wx.ID_ANY, _(u"透视变换"), wx.EmptyString, wx.ITEM_NORMAL )
        self.image_transformation.Append( self.perspective_transformation )
        self.fourier_transformation = wx.MenuItem( self.image_transformation, wx.ID_ANY, _(u"傅里叶变换"), wx.EmptyString, wx.ITEM_NORMAL )
        self.image_transformation.Append( self.fourier_transformation )
        self.flood_fill = wx.MenuItem( self.image_transformation, wx.ID_ANY, _(u"漫水填充"), wx.EmptyString, wx.ITEM_NORMAL )
        self.image_transformation.Append( self.flood_fill )
        self.remapping = wx.MenuItem( self.image_transformation, wx.ID_ANY, _(u"重映射"), wx.EmptyString, wx.ITEM_NORMAL )
        self.image_transformation.Append( self.remapping )
        self.back_projection = wx.MenuItem( self.image_transformation, wx.ID_ANY, _(u"反向投影"), wx.EmptyString, wx.ITEM_NORMAL )
        self.image_transformation.Append( self.back_projection )
        self.menuBar.Append( self.image_transformation, _(u"图像变换") )

        self.calibration = wx.Menu()
        self.camera = wx.MenuItem( self.calibration, wx.ID_ANY, _(u"摄像头与相机标定"), wx.EmptyString, wx.ITEM_NORMAL )
        self.calibration.Append( self.camera )
        self.coordinate_calibration = wx.MenuItem( self.calibration, wx.ID_ANY, _(u"坐标标定"), wx.EmptyString, wx.ITEM_NORMAL )
        self.calibration.Append( self.coordinate_calibration )
        self.menuBar.Append( self.calibration, _(u"标定") )

        self.recognize = wx.Menu()
        self.ocr = wx.MenuItem( self.recognize, wx.ID_ANY, _(u"光学字符识别"), wx.EmptyString, wx.ITEM_NORMAL )
        self.recognize.Append( self.ocr )
        self.vehicle_license_plate_recognition = wx.MenuItem( self.recognize, wx.ID_ANY, _(u"车牌识别"), wx.EmptyString, wx.ITEM_NORMAL )
        self.recognize.Append( self.vehicle_license_plate_recognition )
        self.menuBar.Append( self.recognize, _(u"识别") )

        self.measurement = wx.Menu()
        self.QR_code_recognization = wx.MenuItem( self.measurement, wx.ID_ANY, _(u"二维码识别"), wx.EmptyString, wx.ITEM_NORMAL )
        self.measurement.Append( self.QR_code_recognization )
        self.menuBar.Append( self.measurement, _(u"测量") )

        self.about_menu = wx.Menu()
        self.about = wx.MenuItem( self.about_menu, wx.ID_ANY, _(u"关于"), wx.EmptyString, wx.ITEM_NORMAL )
        self.about_menu.Append( self.about )

        self.menuBar.Append( self.about_menu, _(u"关于") )

        self.SetMenuBar( self.menuBar )

        frameSizer = wx.BoxSizer( wx.VERTICAL )
        ButtonSizer = wx.BoxSizer( wx.HORIZONTAL )
        self.openImage = wx.Button( self, wx.ID_ANY, _(u"打开图片"), wx.DefaultPosition, wx.DefaultSize, wx.BU_TOP )
        self.openImage.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOWTEXT ) )
        self.openImage.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOW ) )
        ButtonSizer.Add( self.openImage, 0, wx.ALL, 5 )
        self.exampleImage = wx.Button( self, wx.ID_ANY, _(u"示例图"), wx.DefaultPosition, wx.DefaultSize, wx.BU_TOP )
        ButtonSizer.Add( self.exampleImage, 0, wx.ALL, 5 )
        self.imageInfoStaticText = wx.StaticText( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( -1,25 ), wx.ST_NO_AUTORESIZE )
        self.imageInfoStaticText.Wrap( -1 )
        self.imageInfoStaticText.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_ACTIVEBORDER ) )
        ButtonSizer.Add( self.imageInfoStaticText, 1, wx.ALL, 5 )
        frameSizer.Add( ButtonSizer, 0, wx.EXPAND|wx.LEFT|wx.TOP, 5 )

        imageSizer = wx.FlexGridSizer( 0, 2, 0, 0 )
        imageSizer.SetFlexibleDirection( wx.BOTH )
        imageSizer.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_ALL )

        self.imageStaticText = wx.StaticText( self, wx.ID_ANY, _(u"原图"), wx.DefaultPosition, wx.Size( -1,30 ), wx.ALIGN_CENTER_HORIZONTAL )
        self.imageStaticText.Wrap( -1 )
        self.imageStaticText.SetFont( wx.Font( 20, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, wx.EmptyString ) )
        self.imageStaticText.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BACKGROUND ) )
        self.imageStaticText.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_ACTIVECAPTION ) )
        self.imageStaticText.SetMinSize( wx.Size( 800,30 ) )
        imageSizer.Add( self.imageStaticText, 0, wx.ALIGN_CENTER_HORIZONTAL, 10 )
        
        self.imageProcessedStaticText = wx.StaticText( self, wx.ID_ANY, _(u"处理后图片"), wx.DefaultPosition, wx.Size( -1,30 ), wx.ALIGN_CENTER_HORIZONTAL )
        self.imageProcessedStaticText.Wrap( -1 )
        self.imageProcessedStaticText.SetFont( wx.Font( 20, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, wx.EmptyString ) )
        self.imageProcessedStaticText.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BACKGROUND ) )
        self.imageProcessedStaticText.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_ACTIVECAPTION ) )
        self.imageProcessedStaticText.SetMinSize( wx.Size( 800,30 ) )
        imageSizer.Add( self.imageProcessedStaticText, 1, wx.ALIGN_CENTER_HORIZONTAL, 5 )

        self.leftImagePanel = ImagePanel(self)
        # self.leftImagePanel = wx.Panel( self, wx.ID_ANY, wx.DefaultPosition, wx.Size( -1,-1 ), wx.BORDER_SIMPLE )
        # self.leftImagePanel.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOW ) )
        # self.leftImagePanel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOW ) )
        # self.leftImagePanel.SetMinSize( wx.Size( 800,600 ) )        
        imageSizer.Add( self.leftImagePanel, 1, wx.ALIGN_BOTTOM|wx.ALIGN_CENTER_HORIZONTAL, 5 )

        self.rightImagePanel = ImagePanel(self)
        # self.rightImagePanel = wx.Panel( self, wx.ID_ANY, wx.DefaultPosition, wx.Size( -1,-1 ), wx.BORDER_SIMPLE )        
        # self.rightImagePanel.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOW ) )
        # self.rightImagePanel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOW ) )
        # self.rightImagePanel.SetMinSize( wx.Size( 800,600 ) )
        imageSizer.Add( self.rightImagePanel, 1, wx.ALIGN_BOTTOM|wx.ALIGN_LEFT, 5 )

        frameSizer.Add( imageSizer, 0, 0, 5 )
        self.parameterStaticText = wx.StaticText( self, wx.ID_ANY, _(u"算法选择与参数调整"), wx.DefaultPosition, wx.Size( -1,30 ), 0  )
        self.parameterStaticText.Wrap( -1 )
        self.parameterStaticText.SetFont( wx.Font( 20, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, wx.EmptyString ) )
        self.parameterStaticText.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BACKGROUND ) )
        self.parameterStaticText.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_ACTIVECAPTION ) )
        self.parameterStaticText.SetMaxSize( wx.Size( 1600,30 ) )
        frameSizer.Add( self.parameterStaticText, 0, wx.ALL|wx.EXPAND, 5 )

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

        self.SetSizer( frameSizer )
        self.Layout()
        frameSizer.Fit( self )
        self.statusBar = self.CreateStatusBar( 1, wx.STB_SIZEGRIP, wx.ID_ANY )
        self.Centre( wx.BOTH )


        # 当前显示面板
        self.current_panel = None
        # 原图 和 处理后图片数据保存变量
        self.original_pil_image  = None 
        self.processed_pil_image = None 

        # image_show
        self.bitmap              = None  # 当前左panel显示的wx.Bitmap
        self.processed_bitmap    = None  # 当前右panel显示的wx.Bitmap

        self.scale              = 1.0   # 显示缩放比例
        self.start_pos          = None  # 鼠标按下时的坐标
        self.current_pos        = None  # 鼠标当前坐标

        self.original_pil_image_width   = 0
        self.original_pil_image_height  = 0
        self.used_function = f"Test  测试函数"
        self.processed_pil_image_width  = 0
        self.processed_pil_image_height = 0

        self.exampleImage.Hide()

        # Connect Events
        self.Bind( wx.EVT_MENU, self.color_extraction_panel, id = self.color_extraction.GetId() )
        self.Bind( wx.EVT_MENU, self.image_difference_panel, id = self.image_difference.GetId() )
        self.Bind( wx.EVT_MENU, self.image_stitching_panel, id = self.image_stitching.GetId() )
        self.Bind( wx.EVT_MENU, self.histogram_panel, id = self.histogram.GetId() )
        self.Bind( wx.EVT_MENU, self.color_space_and_channel_extraction_panel, id = self.color_space_and_channel_extraction.GetId() )
        self.Bind( wx.EVT_MENU, self.equalization_panel, id = self.equalization.GetId() )
        self.Bind( wx.EVT_MENU, self.threshold_processing_panel, id = self.threshold_processing.GetId() )
        self.Bind( wx.EVT_MENU, self.filtering_panel, id = self.filtering.GetId() )
        self.Bind( wx.EVT_MENU, self.morphological_operation_panel, id = self.morphological_operation.GetId() )
        self.Bind( wx.EVT_MENU, self.ROI_panel, id = self.ROI.GetId() )
        self.Bind( wx.EVT_MENU, self.corner_detection_panel, id = self.corner_detection.GetId() )
        self.Bind( wx.EVT_MENU, self.edge_detection_panel, id = self.edge_detection.GetId() )
        self.Bind( wx.EVT_MENU, self.geometric_shape_panel, id = self.geometric_shape.GetId() )
        self.Bind( wx.EVT_MENU, self.moving_object_detection_panel, id = self.moving_object_detection.GetId() )
        self.Bind( wx.EVT_MENU, self.object_detection_panel, id = self.object_detection.GetId() )        
        self.Bind( wx.EVT_MENU, self.watershed_panel, id = self.watershed.GetId() )
        self.Bind( wx.EVT_MENU, self.pyramid_panel, id = self.pyramid.GetId() )
        self.Bind( wx.EVT_MENU, self.affine_transformation_panel, id = self.affine_transformation.GetId() )
        self.Bind( wx.EVT_MENU, self.perspective_transformation_panel, id = self.perspective_transformation.GetId() )
        self.Bind( wx.EVT_MENU, self.fourier_transformation_panel, id = self.fourier_transformation.GetId() )
        self.Bind( wx.EVT_MENU, self.flood_fill_panel, id = self.flood_fill.GetId() )
        self.Bind( wx.EVT_MENU, self.remapping_panel, id = self.remapping.GetId() )
        self.Bind( wx.EVT_MENU, self.back_projection_panel, id = self.back_projection.GetId() )
        self.Bind( wx.EVT_MENU, self.camera_panel, id = self.camera.GetId() )
        self.Bind( wx.EVT_MENU, self.coordinate_calibration_panel, id = self.coordinate_calibration.GetId() )        
        self.Bind( wx.EVT_MENU, self.ocr_panel, id = self.ocr.GetId() )
        self.Bind( wx.EVT_MENU, self.vehicle_license_plate_recognition_panel, id = self.vehicle_license_plate_recognition.GetId() )
        self.Bind( wx.EVT_MENU, self.QR_code_recognization_panel, id = self.QR_code_recognization.GetId() )
        self.Bind( wx.EVT_MENU, self.about_panel, id = self.about.GetId() )
        self.openImage.Bind( wx.EVT_BUTTON, self.openImageclick )
        self.exampleImage.Bind( wx.EVT_BUTTON, self.exampleImageClick )
        self.leftImagePanel.Bind( wx.EVT_PAINT, self.leftPanelOnPaint )
        self.rightImagePanel.Bind( wx.EVT_PAINT, self.rightPanelOnPaint )
        
        # 4、绑定事件处理函数
        self.Bind( EVT_RIGHT_DISPLAY, self.OnDoRightPanelImageDisplayEvent)
        
    def __del__( self ):
        logging.info("run __del__ ")
        pass

    def PanelOnPaint( self, bitmap, image_panel ,display_mode): 
        if display_mode == 1:
            pass
        else:
            return

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
        self.PanelOnPaint(self.bitmap,self.leftImagePanel,1)
        event.Skip()

    def rightPanelOnPaint( self, event ): 
        self.PanelOnPaint(self.processed_bitmap,self.rightImagePanel,1)        
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
        """显示方式二：pil_image在画板上直接画图"""
        if display_flag == 0:
            self.leftImagePanel.show_image(self.original_pil_image)
        else:
            self.rightImagePanel.show_image(self.processed_pil_image)
        return

        """显示方式一：按Panel大小缩放显示图片，输入的图片为PIL Image格式,再转换为bitmap格式"""
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

    def openImageclick ( self, event ):
        logging.info("""打开图片和重新打开图片处理""")
        # 弹出文件选择对话框
        with wx.FileDialog(self, "选择图片", wildcard="图片文件 (*.jpg;*.png;*.bmp;*.gif)|*.jpg;*.png;*.bmp;*.gif",
                          style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.filepath = dlg.GetPath() 
                self.original_pil_image = Image.open(self.filepath)  # PIL image          
                self.display_image(self.original_pil_image, 0)
                self.imageInfoStaticText.SetLabel(f"原图: {self.original_pil_image.width}x{self.original_pil_image.height}")
                self.openImage.SetLabelMarkup( _(u"再次上传图片") )
        event.Skip()

    def exampleImageClick ( self, event ):
        logging.info("""打开示例图片和重新打开图片处理""")
        # 弹出文件选择对话框
        with wx.FileDialog(self, "选择图片", wildcard="图片文件 (*.jpg;*.png;*.bmp;*.gif)|*.jpg;*.png;*.bmp;*.gif",
                          style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.filepath = dlg.GetPath() 
                self.processed_pil_image = Image.open(self.filepath)   # PIL image
                self.display_image(self.processed_pil_image, 1)
                self.imageInfoStaticText.SetLabel(f"原图: {self.original_pil_image.width}x{self.original_pil_image.height} \
                   使用函数: {self.used_function}   处理后: {self.processed_pil_image.width}x{self.processed_pil_image.height}")           
        event.Skip()

    def switch_panel(self, new_panel):
        """切换内容面板的通用方法"""
        if self.current_panel:
            self.current_panel.Hide()        
        self.current_panel = new_panel
        self.current_panel.Show()
        self.current_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOW ) )
        self.Layout()

    # Virtual event handlers, override them in your derived class
    def color_extraction_panel( self, event ): 
        self.exampleImage.Hide()

        self.switch_panel(self.colorExtractionPanel)
        event.Skip()

    def image_difference_panel( self, event ):
        self.exampleImage.Show()
        self.exampleImage.SetLabel("打开对比图")

        self.switch_panel(self.imageDifferencePanel)
        event.Skip()

    def image_stitching_panel( self, event ):
        self.exampleImage.Show()
        self.exampleImage.SetLabel("打开拼接图")        

        self.switch_panel(self.imageStitchingPanel)
        event.Skip()

    def histogram_panel( self, event ):
        self.exampleImage.Hide()
        self.switch_panel(self.imageHistogramPanel)
        event.Skip()

    def color_space_and_channel_extraction_panel( self, event ):
        self.exampleImage.Hide()
        self.switch_panel(self.imageColorSpaceAndChannelExtractionPanel)
        event.Skip()

    def equalization_panel( self, event ):
        self.exampleImage.Hide()
        self.switch_panel(self.imageEqualizationPanel)
        event.Skip()

    def threshold_processing_panel( self, event ):
        self.exampleImage.Hide()        
        self.switch_panel(self.imageThresholdProcessingPanel)
        event.Skip()

    def filtering_panel( self, event ):
        self.exampleImage.Hide()        
        self.switch_panel(self.imageFilteringPanel)
        event.Skip()

    def morphological_operation_panel( self, event ):
        self.exampleImage.Hide()        
        self.switch_panel(self.imageMorphologicalOperationPanel)
        event.Skip()

    def ROI_panel( self, event ):
        self.exampleImage.Hide()        
        self.switch_panel(self.imageROIPanel)
        event.Skip()

    def corner_detection_panel( self, event ):
        self.exampleImage.Hide()        
        self.switch_panel(self.imageCornerDetectionPanel)
        event.Skip()

    def edge_detection_panel( self, event ):
        self.exampleImage.Hide()        
        self.switch_panel(self.imageEdgeDetectionPanel)
        event.Skip()

    def geometric_shape_panel( self, event ):
        self.exampleImage.Hide()        
        self.switch_panel(self.imageGeometricShapePanel)
        event.Skip()

    def moving_object_detection_panel( self, event ):
        self.exampleImage.Hide()        
        self.switch_panel(self.imageMovingObjectDetectionPanel)
        event.Skip()

    def object_detection_panel( self, event ):
        self.exampleImage.Hide()        
        self.switch_panel(self.imageObjectDetectionPanel)
        event.Skip()

    def watershed_panel( self, event ):
        self.exampleImage.Hide()        
        self.switch_panel(self.imageWatershedPanel)
        event.Skip()

    def pyramid_panel( self, event ):
        self.exampleImage.Hide()        
        self.switch_panel(self.imagePyramidPanel)
        event.Skip()

    def affine_transformation_panel( self, event ): 
        self.exampleImage.Hide()
        self.switch_panel(self.imageAaffineTransformationPanel)
        event.Skip()

    def perspective_transformation_panel( self, event ):
        self.exampleImage.Hide()        
        self.switch_panel(self.imagePerspectiveTransformationPanel)
        event.Skip()

    def fourier_transformation_panel( self, event ):
        self.exampleImage.Hide()        
        self.switch_panel(self.imageFourierTransformationPanel)
        event.Skip()

    def flood_fill_panel( self, event ):
        self.exampleImage.Hide()        
        self.switch_panel(self.imageFloodFillPanel)
        event.Skip()

    def remapping_panel( self, event ):
        self.exampleImage.Hide()        
        self.switch_panel(self.imageRemappingPanel)
        event.Skip()

    def back_projection_panel( self, event ):
        self.exampleImage.Show()
        self.exampleImage.SetLabel("打开目标图片")        
        
        self.switch_panel(self.imageBackProjectionPanel)
        event.Skip()

    def camera_panel( self, event ):
        self.exampleImage.Hide()
        self.switch_panel(self.imageCameraPanel)
        event.Skip()

    def coordinate_calibration_panel( self, event ):
        self.exampleImage.Hide()
        self.switch_panel(self.imageCoordinateCalibrationPanel)
        event.Skip()

    def ocr_panel( self, event ):
        self.exampleImage.Hide()
        self.switch_panel(self.imageOcrPanel)
        event.Skip()

    def vehicle_license_plate_recognition_panel( self, event ):
        self.exampleImage.Hide()
        self.switch_panel(self.imageVehicleLicensePlateRecognitionPanel)
        event.Skip()

    def QR_code_recognization_panel( self, event ):
        self.exampleImage.Hide()
        self.switch_panel(self.imageQRCodeRecognizationPanel)
        event.Skip()

    def about_panel( self, event ):
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

class ImagePanel(AlgorithmPanelBase):
    def __init__(self, parent):
        super().__init__(parent)

        # 每个 panel 独立创建自己的 Figure 和 Canvas
        self.figure = Figure()
        self.axes   = self.figure.add_subplot(111)
        self.axes.axis('off')  # 不显示坐标轴
        self.canvas = FigureCanvas(self, -1, self.figure)
        
        # 用 sizer 让 canvas 填满 panel
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)
        self.Layout()
    
    def show_image(self, img_array):
        """传入 numpy 数组显示图片"""
        self.axes.clear()
        self.axes.axis('off')
        self.axes.imshow(img_array)
        self.canvas.draw()

class ColorExtractionPanel(AlgorithmPanelBase):
    ALGORITHM_METHODS = ["imageProcessBGR2GRAY", "imageProcessBGR2HSV", "imageProcessRGB2BGR", "imageProcessBGR2YCrCb"]
    def __init__(self, parent):
        super().__init__(parent)  # 只调用了父类 wx.Panel 的构造函数
        
        m_radioBox2Choices  = [ _(u"BGR2GRAY"), _(u"BGR2HSV"), _(u"RGB2BGR"), _(u"BGR2YCrCb") ]
        self.m_radioBox2    = wx.RadioBox( self, wx.ID_ANY, _(u"选择转换色彩空间"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 4, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer   = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        controlPanelSizer.SetMinSize(wx.Size(-1,30))
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageProcessOnRadioBox )

    def imageProcessOnRadioBox( self, event ):
        self.run_algorithm(self.m_radioBox2.GetSelection())
        event.Skip()
    def imageProcessBGR2GRAY( self ):  
        pil_img =self.parent_frame.original_pil_image       
        if pil_img:
            # 1、PIL 转 OpenCV：先转numpy数组，再 BGR 转 RGB
            img_bgr             = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)

            # 2、 Convert BGR to GRAY
            gray_img            = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)            

            # 3. Convert GRAY to BGR（转回才能正常显示或保存）
            img_bgr_new         = cv2.cvtColor(gray_img, cv2.COLOR_GRAY2BGR)

            # 4. Conert BGR to RGB（PIL 需要 RGB 顺序）
            self.finish(img_bgr_new)

    def imageProcessBGR2HSV( self ):
        """OpenCV 的 cv2.imread() 读取结果是 numpy.ndarray 数组，
           PIL 的 Image.open() 返回的是 PIL.Image.Image 对象，
           两者互转的关键是颜色通道顺序不同：OpenCV 默认是 BGR，
           PIL 是 RGB。转换时需用 cv2.cvtColor() 调整通道顺序，
           再用 np.asarray() 或 Image.fromarray() 做格式切换"""
        pil_img = self.parent_frame.original_pil_image     # <PIL.PngImagePlugin.PngImageFile image mode=RGB size=750x437 at 0x2CCC8D71C70>
        # type(pil_img) # <class 'PIL.PngImagePlugin.PngImageFile'>

        if pil_img:
            # 1、PIL 转 OpenCV：先转numpy数组，再 BGR 转 RGB
            img_bgr = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)

            # 2、 Convert BGR to HSV
            hsv_img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

            # 3、 做HSV通道调整
            # define range of yellow color in HSV
            # 定义黄色的HSV阈值范围
            # 
            # 参数         初始范围    优化建议
            # H（色调）    [20, 40]    根据环境光线动态调整
            # S（饱和度）  [50, 255]   提高下限以减少干扰
            # V（亮度）    [50, 255]   结合实际场景调整上限和下限
            lower_yellow = np.array([20, 50, 50])
            upper_yellow = np.array([40, 255, 255])

            # 4、 Threshold the HSV image to get only blue colors
            mask                = cv2.inRange(hsv_img, lower_yellow, upper_yellow)

            # 5、 Bitwise-AND mask and original image
            processed_hsv_img   = cv2.bitwise_and(img_bgr, img_bgr, mask=mask)

            # 6. Convert HSV to BGR（转回才能正常显示或保存）
            img_bgr_new         = cv2.cvtColor(processed_hsv_img, cv2.COLOR_HSV2BGR)

            # 7. Conert BGR to RGB（PIL 需要 RGB 顺序）
            self.finish(img_bgr_new)

    def imageProcessRGB2BGR( self ):
        pil_img = self.parent_frame.original_pil_image        
        if pil_img:
            # 1、PIL 转 OpenCV：先转numpy数组，再 BGR 转 RGB
            img_bgr = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)

            # 2. BGR 转为 PIL Image 格式，右侧面板显示算法转换后的结果，这里准备显示数据
            #    （故意不做 BGR->RGB 还原，以展示 RGB2BGR 后红蓝通道互换的视觉效果）
            self.parent_frame.processed_pil_image = Image.fromarray(img_bgr)
            self.fire_display_event()

    def imageProcessBGR2YCrCb( self ):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            # 1、PIL 转 OpenCV：先转numpy数组，再 BGR 转 RGB
            img_bgr     = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)

            # 2、 Convert BGR to YCrCb
            ycrcb_img   = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)

            # 3. Convert YCrCb back to BGR（转回才能正常显示或保存）
            img_bgr_new = cv2.cvtColor(ycrcb_img, cv2.COLOR_YCrCb2BGR)

            # 4. Conert BGR to RGB（PIL 需要 RGB 顺序）
            self.finish(img_bgr_new)

class ImageDifferencePanel(AlgorithmPanelBase):
    def __init__(self, parent,):
        super().__init__(parent)

        self.imageDiff = wx.Button( self, wx.ID_ANY, _(u"计算图像差"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )        
        controlPanelSizer.Add( self.imageDiff, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageDiff.Bind( wx.EVT_BUTTON, self.imageDiffBtnClick )

    def imageDiffBtnClick( self, event ):
        self.imageProcessDiff()
        self.fire_display_event()  # 触发事件  
        event.Skip()

    def imageProcessDiff( self ):
        # 对比图片尺寸统一转为 800 x 600大小
        pil_img_1 = self.parent_frame.original_pil_image.resize((800, 600), Image.LANCZOS)
        pil_img_2 = self.parent_frame.processed_pil_image.resize((800, 600), Image.LANCZOS)

        # 1、PIL 转 OpenCV：先转numpy数组，再 BGR 转 RGB
        pil_img_1_bgr = cv2.cvtColor(np.asarray(pil_img_1), cv2.COLOR_RGB2BGR)
        pil_img_2_bgr = cv2.cvtColor(np.asarray(pil_img_2), cv2.COLOR_RGB2BGR)

        # 2、 Convert BGR to GRAY
        gray_img_1   = cv2.cvtColor(pil_img_1_bgr, cv2.COLOR_BGR2GRAY) 
        gray_img_2   = cv2.cvtColor(pil_img_2_bgr, cv2.COLOR_BGR2GRAY) 

        diff = cv2.absdiff(gray_img_1, gray_img_2)
        # 3. Convert GRAY to BGR（转回才能正常显示或保存）
        diff_new    = cv2.cvtColor(diff, cv2.COLOR_GRAY2BGR) 
        self.finish(diff_new)

class ImageStitchingPanel(AlgorithmPanelBase):
    def __init__(self, parent):
        super().__init__(parent)

        self.imageStitch  = wx.Button( self, wx.ID_ANY, _(u"开始图像拼接"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )        
        controlPanelSizer.Add( self.imageStitch, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageStitch.Bind( wx.EVT_BUTTON, self.imageStitchBtnClick )

    def imageStitchBtnClick( self, event ):
        self.imageProcessStitch()
        self.fire_display_event()  # 触发事件  
        event.Skip()

    def imageProcessStitch( self ):
        pil_img_1 = self.parent_frame.original_pil_image.resize((800, 600), Image.LANCZOS)
        pil_img_2 = self.parent_frame.processed_pil_image.resize((800, 600), Image.LANCZOS)

        # PANORAMA模式:适合手持相机围绕光心旋转拍摄的风景、室内大场景，内部会按全景模型校正畸变并做球面或柱面投影。
        # SCANS模式:   适合文档扫描、平面物体平行移动拍摄，内部主要做平面仿射拼接，不会强行做球面投影。
        stitcher = cv2.Stitcher.create(cv2.Stitcher_PANORAMA)

         # 1、PIL 转 OpenCV：先转numpy数组，再 BGR 转 RGB
        pil_img_1_bgr = cv2.cvtColor(np.asarray(pil_img_1), cv2.COLOR_RGB2BGR)
        pil_img_2_bgr = cv2.cvtColor(np.asarray(pil_img_2), cv2.COLOR_RGB2BGR)

        # 执行拼接，返回状态码和结果 
        # nano 返回的是 numpy.ndarray格式图片数据
        status, pano = stitcher.stitch([pil_img_1_bgr, pil_img_2_bgr])

        if status == cv2.Stitcher_OK:
            logging.info("拼接成功!")
            # 先转numpy数组，再BGR -> RGB
            pano_rgb = cv2.cvtColor(np.asarray(pano), cv2.COLOR_BGR2RGB)
            # RGB -> PIL Image
            self.parent_frame.processed_pil_image = Image.fromarray(pano_rgb)
        else:
            logging.error(f"拼接失败，错误码：{status}")

class HistogramPanel(AlgorithmPanelBase):
    def __init__(self, parent):  # 定义构造方法，parent 是外部传入的父对象
        super().__init__(parent) # 调用父类的构造方法，并把 parent 传进去。这样父类能完成自身初始化，比如设置 Qt/C++ 层面的父子关系

        self.imageHist = wx.Button( self, wx.ID_ANY, _(u"生成直方图"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )        
        controlPanelSizer.Add( self.imageHist, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageHist.Bind( wx.EVT_BUTTON, self.imageHistBtnClick )

    def imageHistBtnClick( self, event):
        self.imageProcessHist()        
        self.fire_display_event()  # 触发事件  
        event.Skip()

    def imageProcessHist( self ):
        pil_img = self.parent_frame.original_pil_image        
        if pil_img:
            # 1、PIL 转 OpenCV：先转numpy数组，再 BGR 转 RGB
            img_bgr = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)

            # 2. 用 Matplotlib 画三通道直方图
            fig, ax = plt.subplots(figsize=(8, 5))
            colors = ('r', 'g', 'b')
            for i, color in enumerate(colors):
                ax.hist(img_bgr[:, :, i].flatten(), bins=256, 
                        range=(0, 256), color=color, alpha=0.5, label=f'{color.upper()} channel')
            ax.set_xlim(0, 255)
            ax.set_xlabel('Pixel Value')
            ax.set_ylabel('Frequency')
            ax.set_title('RGB Histogram')
            ax.legend()
            
            # 3. 把直方图保存到内存缓冲区，不落盘
            buf = io.BytesIO()
            fig.savefig(buf, format='PNG', dpi=100, bbox_inches='tight')
            plt.close(fig)
            buf.seek(0)
            
            # 4. 用 PIL 打开缓冲区里的直方图图片
            self.parent_frame.processed_pil_image = Image.open(buf).copy()


class ColorSpaceAndChannelExtractionPanel(AlgorithmPanelBase):
    ALGORITHM_METHODS = ["imageProcessBGR2B", "imageProcessBGR2G", "imageProcessBGR2R",
                         "imageProcessHSV2H", "imageProcessHSV2S", "imageProcessHSV2V"]
    def __init__(self, parent):
        super().__init__(parent)

        m_radioBox2Choices = [ _(u"BGR图片提取B通道"), _(u"BGR图片提取G通道"), _(u"BGR图片提取R通道"), _(u"HSV图片提取H通道"), _(u"HSV图片提取S通道"), _(u"HSV图片提取V通道") ]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"算法选择"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 6, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageProcessChannelExtraction )

    def imageProcessChannelExtraction( self, event ):              
        self.run_algorithm(self.m_radioBox2.GetSelection())
        event.Skip()

    def imageProcessBGR2B(self):
        pil_img = self.parent_frame.original_pil_image    # <PIL.PngImagePlugin.PngImageFile image mode=RGB size=750x437 at 0x2CCC8D71C70>
        # type(pil_img) # <class 'PIL.PngImagePlugin.PngImageFile'>

        if pil_img:
            # 1、PIL 转 OpenCV：先转numpy数组，再 BGR 转 RGB
            img_bgr = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            
            b,g,r = cv2.split(img_bgr)            

            # 8. 转为 PIL Image 格式，右侧面板显示算法转换后的结果，这里准备显示数据
            self.finish(b)

    def imageProcessBGR2G(self):       
        pil_img = self.parent_frame.original_pil_image    # <PIL.PngImagePlugin.PngImageFile image mode=RGB size=750x437 at 0x2CCC8D71C70>
        # type(pil_img) # <class 'PIL.PngImagePlugin.PngImageFile'>

        if pil_img:
            # 1、PIL 转 OpenCV：先转numpy数组，再 BGR 转 RGB
            img_bgr = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            
            b,g,r = cv2.split(img_bgr)            

            # 8. 转为 PIL Image 格式，右侧面板显示算法转换后的结果，这里准备显示数据
            self.finish(g)

    def imageProcessBGR2R(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            # 1、PIL 转 OpenCV：先转numpy数组，再 BGR 转 RGB
            img_bgr = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            
            b,g,r   = cv2.split(img_bgr)

            # 8. 转为 PIL Image 格式，右侧面板显示算法转换后的结果，这里准备显示数据
            self.finish(r)

    def imageProcessHSV2H(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:        
            img_bgr         = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            hsv_img         = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
            h,s,v           = cv2.split(hsv_img)
            self.finish(h)

    def imageProcessHSV2S(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:        
            img_bgr         = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            hsv_img         = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
            h,s,v           = cv2.split(hsv_img)
            self.finish(s)

    def imageProcessHSV2V(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:        
            img_bgr             = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            hsv_img             = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
            h,s,v               = cv2.split(hsv_img)
            self.finish(v)     


class EqualizationPanel(AlgorithmPanelBase):
    def __init__(self, parent):
        super().__init__(parent)

        self.imageProcess = wx.Button( self, wx.ID_ANY, _(u"图像均衡化处理"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )        
        controlPanelSizer.Add( self.imageProcess, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageProcess.Bind( wx.EVT_BUTTON, self.imageEqualizationBtnClick )

    def imageEqualizationBtnClick( self, event ):
        self.imageProcessEqualization()
        self.fire_display_event()  # 触发事件  
        event.Skip()

    # 预处理算法
    def imageProcessEqualization(self):
        '''全局均衡化算法'''        
        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            # 全局均衡化算法
            img_bgr             = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_yuv             = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
            img_yuv[:,:,0]      = cv2.equalizeHist(img_yuv[:,:,0]) # 只处理Y亮度通道
            img_yuv_bgr         = cv2.cvtColor(img_yuv, cv2.COLOR_YCrCb2BGR)
            self.finish(img_yuv_bgr)
            # 全局均衡化易放大噪声、在光照不均时效果差

            # CLAHE算法
            # clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            # result = clahe.apply()

class ThresholdProcessingPanel(AlgorithmPanelBase):
    ALGORITHM_METHODS = ["imageThresBINARY", "imageThresBINARYINV", "imageThresTRUNC", "imageThresTOZERO", "imageThresTOZEROINV", "imageThresMEANC", "imageThresGAUSSIANC", "imageThresOtsu", "imageThresTriangle", "imageThresIterative", "imageThresNiblack", "imageThresSauvola", "imageThresMEM", "imageThresMultiDomainSegmentation"]
    def __init__(self, parent):
        super().__init__(parent)

        m_radioBox2Choices = [ _(u"BINARY(白底黑字)"), _(u"BINARY_INV(反色二值化)"), _(u"TRUNC(压暗高光区)"), _(u"TOZERO(除暗留亮)"),\
        _(u"TOZERO_INV(除亮留暗)"),  _(u"MEAN_C(局部均值法)"), _(u"GAUSSIAN_C(局部高斯加权法)"), _(u"Otsu(大津法)"),\
        _(u"Triangle(三角法)"), _(u"Iterative(迭代阈值法)"), _(u"Niblack算法"), _(u"Sauvola算法"), _(u"MEM最大熵法"), _(u"多阈值分割算法")]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"阈值处理"), wx.DefaultPosition, wx.Size( 1600,200 ), m_radioBox2Choices, 5, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageThresholdOnRadioBox )

    def imageThresholdOnRadioBox( self, event ):
        self.run_algorithm(self.m_radioBox2.GetSelection())
        event.Skip()
    def imageThresBINARY(self):
        '''黑字白底阈值算法'''        
        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            # 全局均衡化算法
            img_bgr             = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray            = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            ret,img_binary      = cv2.threshold(img_gray, 127,255,cv2.THRESH_BINARY)
            self.finish(img_binary)

    def imageThresBINARYINV(self):        
        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            # 全局均衡化算法
            img_bgr             = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray            = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            ret,img_binary      = cv2.threshold(img_gray, 127,255,cv2.THRESH_BINARY_INV)
            self.finish(img_binary)

    def imageThresTRUNC(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            # 全局均衡化算法
            img_bgr             = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray            = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            ret,img_binary      = cv2.threshold(img_gray, 127,255,cv2.THRESH_TRUNC)
            self.finish(img_binary)

    def imageThresTOZERO(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            # 全局均衡化算法
            img_bgr             = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray            = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            ret,img_binary      = cv2.threshold(img_gray, 127,255,cv2.THRESH_TOZERO)
            self.finish(img_binary)

    def imageThresTOZEROINV(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            # 全局均衡化算法
            img_bgr             = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray            = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            ret,img_binary      = cv2.threshold(img_gray, 127,255,cv2.THRESH_TOZERO_INV)
            self.finish(img_binary)

    def imageThresMEANC(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            # 全局均衡化算法
            img_bgr    = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray   = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            img_binary = cv2.adaptiveThreshold(img_gray, 255,cv2.ADAPTIVE_THRESH_MEAN_C,cv2.THRESH_BINARY, 3, 0) 
            self.finish(img_binary)

    def imageThresGAUSSIANC(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            # 全局均衡化算法
            img_bgr    = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray   = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            img_binary = cv2.adaptiveThreshold(img_gray, 255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,5, 0)
            self.finish(img_binary)

    def imageThresOtsu(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            # 全局均衡化算法
            img_bgr             = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray            = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            ret,img_binary      = cv2.threshold(img_gray, 0,255,cv2.THRESH_BINARY + cv2.THRESH_OTSU )
            self.finish(img_binary)

    def imageThresTriangle(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            # 全局均衡化算法
            img_bgr             = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray            = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            ret,img_binary      = cv2.threshold(img_gray, 0,255,cv2.THRESH_BINARY + cv2.THRESH_TRIANGLE )
            self.finish(img_binary)

    def imageThresIterative(self):
        '''迭代阈值法'''
        def iterative_threshold(img, tolerance=1):
            """
            迭代阈值法自动求阈值并二值化
            :param img: 灰度图像
            :param tolerance: 收敛容差，默认1
            :return: (最终阈值, 二值图像)
            """
            # 步骤1：初始阈值取图像灰度均值
            T = np.mean(img)
            
            while True:
                # 步骤2：按当前阈值分割前景和背景
                foreground = img[img >= T]
                background = img[img < T]
                
                # 防止某一类为空导致均值计算报错
                if len(foreground) == 0 or len(background) == 0:
                    break
                
                # 步骤3：计算新阈值
                new_T = (np.mean(foreground) + np.mean(background)) / 2
                
                # 步骤4：收敛判断
                if abs(new_T - T) < tolerance:
                    T = new_T
                    break
                
                T = new_T

            T = int(T)
            return T

        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            # 全局均衡化算法
            img_bgr    = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray   = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            T = iterative_threshold(img_gray,1)
             # 用最终阈值做二值化
            _,img_binary = cv2.threshold(img_gray, T,255,cv2.THRESH_BINARY)
            self.finish(img_binary)

    def imageThresNiblack(self):
        def niblack_threshold(img, window_size=25, k=-0.2):
            # 窗口半径
            h, w = img.shape
            pad = window_size // 2
            
            # 边界填充，避免边缘越界
            padded = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
            
            # 转 float 避免溢出
            padded = padded.astype(np.float32)
            
            # 用均值滤波算局部均值
            mean = cv2.blur(padded, (window_size, window_size))
            
            # 算局部标准差：sqrt(E(x^2) - (E(x))^2)
            sq_mean = cv2.blur(padded ** 2, (window_size, window_size))
            std = np.sqrt(sq_mean - mean ** 2)
            
            # 阈值曲面
            thresh = mean + k * std
            
            # 去掉填充，恢复原尺寸
            thresh = thresh[pad:pad+h, pad:pad+w]
            
            # 二值化
            binary = (img > thresh).astype(np.uint8) * 255
            return binary

        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            # 全局均衡化算法
            img_bgr    = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray   = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            img_binary = niblack_threshold(img_gray, window_size=25, k=-0.2)
            self.finish(img_binary)

    def imageThresSauvola(self):
        def sauvola_threshold(image, window_size=25, k=0.2, r=128):
            # 转灰度
            if len(image.shape) > 2:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            # 局部均值 m
            mean = cv2.blur(gray, (window_size, window_size))

            # 局部标准差 s = sqrt(E(x^2) - (E(x))^2)
            mean_square = cv2.blur(gray.astype(np.float32)**2, (window_size, window_size))
            std = np.sqrt(np.maximum(mean_square - mean.astype(np.float32)**2, 0))

            # 计算阈值矩阵
            threshold = mean.astype(np.float32) * (1 + k * (std / r - 1))

            # 二值化
            binary = np.zeros_like(gray)
            binary[gray > threshold] = 255
            return binary

        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            # 全局均衡化算法
            img_bgr    = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray   = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            img_binary = sauvola_threshold(img_gray, window_size=25, k=-0.2)
            self.finish(img_binary)

    def imageThresMEM(self):
        def mem_threshold(img):
            # 计算灰度直方图
            hist = cv2.calcHist([img], [0], None, [256], [0, 256]).ravel()
            total_pixels = img.shape[0] * img.shape[1]
            prob = hist / total_pixels  # 归一化概率分布
            
            best_thresh = 0
            max_entropy = -1.0
            
            # 遍历所有可能的阈值
            for t in range(1, 256):
                # 背景概率分布
                p_b = prob[:t]
                sum_b = np.sum(p_b)
                if sum_b == 0:
                    continue
                
                # 前景概率分布
                p_f = prob[t:]
                sum_f = np.sum(p_f)
                if sum_f == 0:
                    continue
                
                # 归一化并计算背景熵
                p_b_norm = p_b / sum_b
                # 避免log(0)
                p_b_norm = p_b_norm[p_b_norm > 0]
                entropy_b = -np.sum(p_b_norm * np.log2(p_b_norm))
                
                # 归一化并计算前景熵
                p_f_norm = p_f / sum_f
                p_f_norm = p_f_norm[p_f_norm > 0]
                entropy_f = -np.sum(p_f_norm * np.log2(p_f_norm))
                
                # 总熵
                total_entropy = entropy_b + entropy_f
                
                if total_entropy > max_entropy:
                    max_entropy = total_entropy
                    best_thresh = t
            
            # 用最佳阈值做二值化
            _, binary = cv2.threshold(img, best_thresh, 255, cv2.THRESH_BINARY)
            return best_thresh, binary

        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            # 全局均衡化算法
            img_bgr    = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray   = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            best_thresh, binary = mem_threshold(img_gray)
            _,img_binary = cv2.threshold(binary, best_thresh, 255, cv2.THRESH_BINARY)
            self.finish(img_binary)

    def imageThresMultiDomainSegmentation(self):
        # ---------- 方法一：NumPy 分段映射 ----------
        def multi_threshold_numpy(image, thresholds, values):
            """
            thresholds: 阈值列表，如 [80, 160]
            values: 各区间对应的输出灰度值，长度 = len(thresholds) + 1
            """
            result = np.zeros_like(image)
            # 第一段：小于 thresholds
            result[image < thresholds] = values
            # 中间段
            for i in range(len(thresholds) - 1):
                mask = (image >= thresholds[i]) & (image < thresholds[i+1])
                result[mask] = values[i+1]
            # 最后一段：大于等于最后一个阈值
            result[image >= thresholds[-1]] = values[-1]
            return result
            # 示例：分成4个灰度区间
            # thresh_list = [60, 120, 180]
            # out_values = [0, 85, 170, 255]  # 对应4个区间
            # result_np = multi_threshold_numpy(img, thresh_list, out_values)

        # ---------- 方法二：多次 threshold + 掩码组合 ----------
        def multi_threshold_opencv(image, thresholds):
            """返回多个二值掩码，每个掩码对应一个区间"""
            thresholds = sorted(thresholds)  # 确保阈值有序
            masks = []
            
            # 小于第一个阈值
            _, mask_lt = cv2.threshold(image, thresholds[0], 255, cv2.THRESH_BINARY_INV)
            masks.append(mask_lt)
            
            # 中间区间 [t[i], t[i+1])
            for i in range(len(thresholds) - 1):
                _, low = cv2.threshold(image, thresholds[i], 255, cv2.THRESH_BINARY)
                _, high = cv2.threshold(image, thresholds[i+1], 255, cv2.THRESH_BINARY_INV)
                masks.append(cv2.bitwise_and(low, high))
            
            # 大于等于最后一个阈值
            _, mask_ge = cv2.threshold(image, thresholds[-1], 255, cv2.THRESH_BINARY)
            masks.append(mask_ge)
            return masks
        
        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            # 全局均衡化算法
            thresh_list = [60, 120, 180, 240]  # 阈值参数可以调整
            img_bgr    = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray   = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            masks      = multi_threshold_opencv(img_gray, thresh_list)
            img_rgb    = cv2.cvtColor(masks[0], cv2.COLOR_GRAY2RGB)
            self.parent_frame.processed_pil_image = Image.fromarray(img_rgb)         

class FilteringPanel(AlgorithmPanelBase):
    ALGORITHM_METHODS = ["imageProcessBlur", "imageProcessBoxBlur", "imageProcessGaussianBlur", "imageProcessMedianBlur", "imageProcessBilateral"]
    def __init__(self, parent):
        super().__init__(parent)  # 只调用了父类 wx.Panel 的构造函数
        
        m_radioBox2Choices = [ _(u"均值Blur"), _(u"方框BoxBlur"), _(u"高斯GaussianBlur"), _(u"中值MedianBlur") , _(u"双边Bilateral")]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"选择滤波算法"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 5, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageFilteringOnRadioBox )

    def imageFilteringOnRadioBox( self, event ):
        self.run_algorithm(self.m_radioBox2.GetSelection())
        event.Skip()
    def imageProcessBlur(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            img_bgr    = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            # 1. 均值滤波：核大小用元组(宽,高)，必须是奇数
            mean_blur  = cv2.blur(img_bgr, (5, 5))
            self.finish(mean_blur)

    def imageProcessBoxBlur(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            img_bgr    = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            # 2. 方框滤波：normalize=True时与均值滤波相同；False时求像素和，易溢出变白
            box_normal = cv2.boxFilter(img_bgr, -1, (5, 5), normalize=True)
            box_raw    = cv2.boxFilter(img_bgr, -1, (5, 5), normalize=False)
            self.finish(box_raw)

    def imageProcessGaussianBlur(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            img_bgr        = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            # 3. 高斯滤波：核大小必须奇数，sigmaX=0时自动根据核尺寸计算
            gaussian_blur  = cv2.GaussianBlur(img_bgr, (5, 5), 0)
            # 也可手动指定sigma，sigma越大越模糊
            gaussian_blur2 = cv2.GaussianBlur(img_bgr, (5, 5), 1.5)
            self.finish(gaussian_blur)

    def imageProcessMedianBlur(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            img_bgr     = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            median_blur = cv2.medianBlur(img_bgr, 5)
            self.finish(median_blur)

    def imageProcessBilateral(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:
            img_bgr       = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            # 5. 双边滤波：能在去噪的同时保留边缘（d 直径、sigmaColor 颜色空间方差、sigmaSpace 坐标空间方差）
            bilateral     = cv2.bilateralFilter(img_bgr, 9, 75, 75)
            self.finish(bilateral)

class MorphologicalOperationPanel(AlgorithmPanelBase):
    ALGORITHM_METHODS = ["imageErosion", "imageDilation", "imageOpening", "imageClosing", "imageGradient", "imageTophat", "imageBlackhat"]
    def __init__(self, parent):
        super().__init__(parent)

        m_radioBox2Choices = [ _(u"Erosion(腐蚀)"), _(u"Dilation(膨胀)"), _(u"Opening(开运算)"), _(u"Closing(闭运算)"),\
        _(u"Gradient(形态学梯度)"),  _(u"Top-hat(顶帽)"), _(u"Black-hat(黑帽)")]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"阈值处理"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 7, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageMorphologicalOnRadioBox )

    def imageMorphologicalOnRadioBox( self, event ):
        self.run_algorithm(self.m_radioBox2.GetSelection())
        event.Skip()
    def imageErosion(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:            
            img_bgr         = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray        = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            # 二值化（形态学通常处理二值图）
            _, binary       = cv2.threshold(img_gray, 127, 255, cv2.THRESH_BINARY)
            # 创建结构元素（核）
            kernel_rect     = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))      # 矩形核
            kernel_ellipse  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)) # 椭圆核
            kernel_cross    = cv2.getStructuringElement(cv2.MORPH_CROSS, (5, 5))     # 十字核

            # 腐蚀
            eroded          = cv2.erode(binary, kernel_rect, iterations=1)
            self.finish(eroded)

    def imageDilation(self) :
        pil_img = self.parent_frame.original_pil_image
        if pil_img:            
            img_bgr         = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray        = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            # 二值化（形态学通常处理二值图）
            _, binary       = cv2.threshold(img_gray, 127, 255, cv2.THRESH_BINARY)
            # 创建结构元素（核）
            kernel_rect     = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))      # 矩形核
            kernel_ellipse  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)) # 椭圆核
            kernel_cross    = cv2.getStructuringElement(cv2.MORPH_CROSS, (5, 5))     # 十字核

            # 膨胀
            dilated         = cv2.dilate(binary, kernel_rect, iterations=1)
            self.finish(dilated)

    def imageOpening(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:            
            img_bgr         = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray        = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            # 二值化（形态学通常处理二值图）
            _, binary       = cv2.threshold(img_gray, 127, 255, cv2.THRESH_BINARY)
            # 创建结构元素（核）
            kernel_rect     = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))      # 矩形核
            kernel_ellipse  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)) # 椭圆核
            kernel_cross    = cv2.getStructuringElement(cv2.MORPH_CROSS, (5, 5))     # 十字核

            # 开运算（去噪）
            opened          = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_rect)
            self.finish(opened)

    def imageClosing(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:            
            img_bgr         = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray        = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            # 二值化（形态学通常处理二值图）
            _, binary       = cv2.threshold(img_gray, 127, 255, cv2.THRESH_BINARY)
            # 创建结构元素（核）
            kernel_rect     = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))      # 矩形核
            kernel_ellipse  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)) # 椭圆核
            kernel_cross    = cv2.getStructuringElement(cv2.MORPH_CROSS, (5, 5))     # 十字核

            # 闭运算（补洞）
            closed          = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_rect)
            self.finish(closed)

    def imageGradient(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:            
            img_bgr         = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray        = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            # 二值化（形态学通常处理二值图）
            _, binary       = cv2.threshold(img_gray, 127, 255, cv2.THRESH_BINARY)
            # 创建结构元素（核）
            kernel_rect     = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))      # 矩形核
            kernel_ellipse  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)) # 椭圆核
            kernel_cross    = cv2.getStructuringElement(cv2.MORPH_CROSS, (5, 5))     # 十字核

            # 形态学梯度（边缘）
            gradient        = cv2.morphologyEx(binary, cv2.MORPH_GRADIENT, kernel_rect)
            self.finish(gradient)

    def imageTophat(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:            
            img_bgr         = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray        = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            # 二值化（形态学通常处理二值图）
            _, binary       = cv2.threshold(img_gray, 127, 255, cv2.THRESH_BINARY)
            # 创建结构元素（核）
            kernel_rect     = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))      # 矩形核
            kernel_ellipse  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))   # 椭圆核
            kernel_cross    = cv2.getStructuringElement(cv2.MORPH_CROSS, (5, 5))     # 十字核

            # 顶帽（提取亮细节）
            tophat          = cv2.morphologyEx(binary, cv2.MORPH_TOPHAT, kernel_rect)
            self.finish(tophat)

    def imageBlackhat(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:            
            img_bgr         = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray        = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            # 二值化（形态学通常处理二值图）
            _, binary       = cv2.threshold(img_gray, 127, 255, cv2.THRESH_BINARY)
            # 创建结构元素（核）
            kernel_rect     = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))      # 矩形核
            kernel_ellipse  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)) # 椭圆核
            kernel_cross    = cv2.getStructuringElement(cv2.MORPH_CROSS, (5, 5))     # 十字核

            # 黑帽（提取暗细节）
            blackhat        = cv2.morphologyEx(binary, cv2.MORPH_BLACKHAT, kernel_rect)
            self.finish(blackhat)

class ROIPanel(AlgorithmPanelBase):
    def __init__(self, parent):
        super().__init__(parent)

        self.imageDiff = wx.Button( self, wx.ID_ANY, _(u"自动感兴趣区域ROI人脸检测算法"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )        
        controlPanelSizer.Add( self.imageDiff, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageDiff.Bind( wx.EVT_BUTTON, self.imageAutoROIBtnClick )

    def imageAutoROIBtnClick( self, event ):
        self.imageAutoROI()
        self.fire_display_event()  # 触发事件  
        event.Skip()

    def imageAutoROI(self):        
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr         = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray        = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            # 用Haar级联检测人脸，自动得到ROI
            face_cascade    = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces           = face_cascade.detectMultiScale(img_gray, scaleFactor=1.1, minNeighbors=5)            

            if len(faces) == 0:
                print("未检测到人脸")
                return

            for (x, y, w, h) in faces:
                pad = 20  # 往外扩一点，别裁太贴
                # 注意：shape[1] 是宽度(x 方向上限)，shape[0] 是高度(y 方向上限)
                x1, y1      = max(x-pad, 0), max(y-pad, 0)
                x2, y2      = min(x+w+pad, img_gray.shape[1]), min(y+h+pad, img_gray.shape[0])
                face_roi    = img_gray[y1:y2, x1:x2].copy()
            self.finish(face_roi)
  

class CornerDetectionPanel(AlgorithmPanelBase):
    ALGORITHM_METHODS = ["imageHarris", "imageShiTomasi", "imageOrb", "imageFast", "imageSift"]
    def __init__(self, parent):
        super().__init__(parent)

        m_radioBox2Choices = [ _(u"Harris"), _(u"Shi-Tomasi"), _(u"ORB"), _(u"FAST"), _(u"SIFT")]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"阈值处理"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 5, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageCornerDetectionOnRadioBox )

    def imageCornerDetectionOnRadioBox( self, event ):
        self.run_algorithm(self.m_radioBox2.GetSelection())
        event.Skip()
    def imageHarris(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr    = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray   = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            img_gray   = np.float32(img_gray)

            # 核心一行：blockSize 邻域大小，ksize Sobel 孔径，k 经验值 0.04~0.06
            dst         = cv2.cornerHarris(img_gray, blockSize=2, ksize=3, k=0.04)

            # 膨胀让角点更显眼，阈值取响应最大值的 1%~5%
            dst         = cv2.dilate(dst, None)
            img_bgr[dst > 0.01 * dst.max()] = [0, 0, 255]  # 红色标记
            self.finish(img_bgr)

    def imageShiTomasi(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr    = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray   = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

            # maxCorners 最多返回多少个角点
            # qualityLevel 质量阈值，越小检测越严格（0.01~0.1）
            # minDistance 两个角点之间的最小距离，避免密集扎堆
            corners = cv2.goodFeaturesToTrack(img_gray, maxCorners=50, qualityLevel=0.01, minDistance=10)

            if corners is not None:
                corners = np.int32(corners)
                for i in corners:
                    x, y = i.ravel()
                    cv2.circle(img_bgr, (x, y), 3, (0, 255, 0), -1)
            self.finish(img_bgr)

    def imageOrb(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr    = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray   = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

            orb = cv2.ORB_create(nfeatures=500)

            # 检测关键点和描述子
            kp, des = orb.detectAndCompute(img_gray, None)
            # 3. 把关键点绘制在原图上
            img_with_kp = cv2.drawKeypoints(img_gray, kp, None, color=(0, 255, 0), flags=0)
            self.finish(img_with_kp)

    def imageFast(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr     = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray    = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)        
            # threshold 越大角点越少但更稳定
            # nonmaxSuppression 开启非极大值抑制，避免重复检测
            fast        = cv2.FastFeatureDetector_create(threshold=30, nonmaxSuppression=True)

            keypoints   = fast.detect(img_gray, None)
            img_kp      = cv2.drawKeypoints(img_bgr, keypoints, None, color=(0, 255, 0))

            self.finish(img_kp)

    def imageSift(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr     = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray    = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            # 2. 创建SIFT对象（OpenCV 4.4+直接用cv2.SIFT_create）
            sift        = cv2.SIFT_create(nfeatures=5000, contrastThreshold=0.04, edgeThreshold=10)

            # 3. 检测关键点并计算128维描述子
            kp, des     = sift.detectAndCompute(img_gray, None)

            # 4. 把关键点绘制在原图上
            img_with_kp = cv2.drawKeypoints(img_gray, kp, None, color=(0, 255, 0), flags=0)
            self.finish(img_with_kp)

class EdgeDetectionPanel(AlgorithmPanelBase):
    ALGORITHM_METHODS = ["imageCanny", "imageSobel", "imageLaplacian", "imageScharr"]
    def __init__(self, parent):
        super().__init__(parent)

        m_radioBox2Choices = [ _(u"Canny"), _(u"Sobel"), _(u"Laplacian"), _(u"Scharr")]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"边缘检测算法"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 4, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageEdgeDetectionOnRadioBox )

    def imageEdgeDetectionOnRadioBox( self, event ):
        self.run_algorithm(self.m_radioBox2.GetSelection())
        event.Skip()
    def imageCanny(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr     = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray    = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            # 2. 高斯模糊降噪（核大小5x5）
            blurred     = cv2.GaussianBlur(img_gray, (5, 5), 1.4)

            # 3. Canny边缘检测（低阈值50，高阈值150）
            edges       = cv2.Canny(blurred, 50, 150)
            self.finish(edges)

    def imageSobel(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr     = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray    = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)        

            sobel_x     = cv2.Sobel(img_gray, cv2.CV_64F, 1, 0, ksize=3)  # x方向
            sobel_y     = cv2.Sobel(img_gray, cv2.CV_64F, 0, 1, ksize=3)  # y方向
            sobel       = np.sqrt(sobel_x**2 + sobel_y**2)
            sobel_abs   = cv2.convertScaleAbs(sobel)
            self.finish(sobel_abs)

    def imageLaplacian(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr         = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray        = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

            # 2. 应用 Laplacian 算子
            # ddepth=cv2.CV_64F 保留负值，避免截断；ksize=3 是核大小，必须为正奇数
            laplacian       = cv2.Laplacian(img_gray, cv2.CV_64F, ksize=3)
            # 3. 取绝对值并转回 8 位图以便显示
            laplacian_abs   = cv2.convertScaleAbs(laplacian)
            self.finish(laplacian_abs)

    def imageScharr(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr         = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
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
            self.finish(scharr_xy)


class GeometricShapePanel(AlgorithmPanelBase):
    ALGORITHM_METHODS = ["imageHoughLinesP", "imageHoughCircles", "imageContour", "imageLineSegmentDetector", "imageFastLineDetector", "imageBlob", "imageEdgeDrawing", "imageHull", "imageLeastSquaresCircleFitting"]
    def __init__(self, parent):
        super().__init__(parent)

        m_radioBox2Choices = [ _(u"HoughLinesP(霍夫线检测)"), _(u"HoughCircles(霍夫圆检测)"), _(u"Contour(轮廓)"), _(u"LSD(直线段检测)"), \
                              _(u"FLD(快速直线检测))"), _(u"Blob(斑点)"),_(u"EdgeDrawing(ED)"), _(u"Hull(凸包)"), _(u"LeastSquaresCircleFitting(最小二乘拟合圆)")]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"边缘检测算法"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 4, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageGeometricShapeOnRadioBox )

    def imageGeometricShapeOnRadioBox( self, event ):
        self.run_algorithm(self.m_radioBox2.GetSelection())
        event.Skip()
    def imageHoughLinesP(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr         = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
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

            # 4. 绘制检测到的线段
            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line
                    cv2.line(img_gray, (x1, y1), (x2, y2), (0, 255, 0), 2)
            self.finish(img_gray)

    def imageHoughCircles(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr         = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
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
            # 显示画好圆的 BGR 结果图（此前误显示灰度图，检测圆不可见）
            self.finish(img_bgr)

    def imageContour(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr             = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray            = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)         
            # 2. 二值化（黑底白物）
            ret, binary         = cv2.threshold(img_gray, 127, 255, cv2.THRESH_BINARY)

            # 3. 查找轮廓
            contours, hierarchy = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # 4. 在原图上画出所有轮廓
            cv2.drawContours(img_bgr, contours, -1, (0, 255, 0), 2)

            self.finish(img_bgr)


    def imageLineSegmentDetector(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr             = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
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

            self.finish(result)


    def imageFastLineDetector(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr             = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray            = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)        
            # 3. 创建FLD检测器（参数可调）
            # length_threshold: 线段最小长度，小于该值被丢弃
            # distance_threshold: 点到假设线段的距离超过该值视为异常点
            # canny_th1/canny_th2: Canny边缘检测的双阈值
            # do_merge: 是否合并短线段
            fld = cv2.ximgproc.createFastLineDetector(
                length_threshold=10,
                distance_threshold=1.41421356,
                canny_th1=50,
                canny_th2=50,
                canny_aperture_size=3,
                do_merge=False
            )

            # 4. 检测直线
            lines = fld.detect(img_gray)
            print(f"检测到 {len(lines)} 条直线")

            # 5. 在原图上绘制检测结果
            drawn_img = fld.drawSegments(img_bgr, lines)
            # 或者手动绘制（可以自定义颜色和粗细）
            # for line in lines:
            #     x0, y0, x1, y1 = line
            #     cv2.line(drawn_img, (int(x0), int(y0)), (int(x1), int(y1)), (0, 255, 0), 1)
            # 6. 转换为PIL Image格式（关键步骤：BGR → RGB）
            self.finish(drawn_img)

    def imageBlob(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr             = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
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

            # 5. 把 Blob 画在原图上（红色圆圈，大小对应 Blob 半径）
            result = cv2.drawKeypoints(
                img_gray, keypoints, np.array([]), (0, 0, 255),
                cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS
            )
            self.finish(result)

    def imageEdgeDrawing(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr             = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray            = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

            # 3. 创建 EdgeDrawing 对象并设置参数
            ed                              = cv2.ximgproc.createEdgeDrawing()            
            #params                          = cv2.ximgproc.EdgeDrawing_Params()
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
            logging.info(type(lines))
            logging.info(len(lines))
            ellipses = ed.detectEllipses() #包含椭圆中心x坐标、中心y坐标、长半轴长度、短半轴长度、椭圆长轴与水平轴的旋转角度、椭圆的置信度
            logging.info(type(ellipses))
            logging.info(len(ellipses))

            # 6. 把结果画到原图上
            result   = img_bgr.copy()

            # 画边缘线段（随机颜色）
            if segments is not None:
                for seg in segments:
                    color = tuple(np.random.randint(0, 256, 3).tolist())
                    cv2.polylines(result, [seg], False, color, 1, cv2.LINE_8)

                for line in lines:
                    x1, y1, x2, y2 = map(int, line)
                    cv2.line(result, (x1, y1), (x2, y2), (0, 0, 255), 2)


            # 画直线（红色）
            if lines is not None:
                lines = np.uint16(np.around(lines))
                for line in lines:
                    x1, y1, x2, y2 = map(int, line)
                    cv2.line(result, (x1, y1), (x2, y2), (0, 0, 255), 1, cv2.LINE_AA)

            # 画椭圆/圆（绿色=圆，红色=椭圆）
            if ellipses is not None:
                ellipses = np.uint16(np.around(ellipses))
                for ellipse in ellipses:
                    x_center, y_centor, long_length, short_length, x_angle, _ = map(int, ellipse)
                    center = (x_center, y_centor)
                    axes   = (x_center + long_length, y_centor + short_length)
                    angle  = x_angle

                    if abs(long_length - short_length) < 5: #圆
                        color = (0, 0, 255)  # 红色
                    else:
                        color = (0, 255, 0)  # 绿色
                
                    cv2.ellipse(result, center, axes, angle, 0, 360, color, 2, cv2.LINE_AA)

            self.finish(result)

    def imageHull(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr             = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
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

            self.finish(result)

    def imageLeastSquaresCircleFitting(self):
        pass

class MovingObjectDetectionPanel(AlgorithmPanelBase):
    ALGORITHM_METHODS = ["imageHaar", "imageMatchTemplate", "imageHOG"]
    def __init__(self, parent):
        super().__init__(parent)

        m_radioBox2Choices = [ _(u"Harr级联分类器)"), _(u"模板匹配"), _(u"HOG特征提取")]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"目标检测算法"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 4, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageMODOnRadioBox )

    def imageMODOnRadioBox( self, event ):
        self.run_algorithm(self.m_radioBox2.GetSelection())
        event.Skip()
    def imageHaar(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr             = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
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
            self.finish(img_bgr)

    def imageMatchTemplate(self):        
        pil_img             = self.parent_frame.original_pil_image
        pil_img_template    = self.parent_frame.processed_pil_image
        if pil_img: 
            # 1. 读取原图和模板
            # 待匹配的大图          
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度）
            # 模板图，以灰度模式读取
            pil_img_template_bgr    = cv2.cvtColor(np.asarray(pil_img_template), cv2.COLOR_RGB2BGR)
            pil_img_template_gray   = cv2.cvtColor(pil_img_template_bgr, cv2.COLOR_BGR2GRAY)

            # 3. 执行模板匹配
            # 常用方法：cv2.TM_CCOEFF_NORMED（推荐）、cv2.TM_SQDIFF、cv2.TM_CCORR_NORMED
            result = cv2.matchTemplate(img_gray, pil_img_template_gray, cv2.TM_CCOEFF_NORMED)
            print(result)

            # 4. 获取最佳匹配位置
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            # 对于 TM_SQDIFF 系列，值越小越好；其他方法值越大越好
            if cv2.TM_SQDIFF in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                top_left = min_loc
            else:
                top_left = max_loc
            
            # 5. 在原图上画矩形框标记匹配区域
            h, w = pil_img_template_gray.shape[:2]
            print(type(top_left))
            print(top_left)
            print(w)
            print(h)
            bottom_right = (top_left[0] + w, top_left[1] + h )
            cv2.rectangle(img_bgr, top_left, bottom_right, (0, 0, 255), 2)

            # 6. 将 OpenCV 的 BGR 图转为 PIL Image
            # 关键：必须先把 BGR 转成 RGB，否则颜色会失真
            self.finish(img_bgr)

    def imageHOG(self):
        pil_img = self.parent_frame.original_pil_image
        if pil_img:           
            img_bgr             = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
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
            self.finish(img_bgr)

class ObjectDetectionPanel(AlgorithmPanelBase):
    ALGORITHM_METHODS = ["imageBackgroundSubstraction", "imageFrameDifferencing", "imageOpticalFlow"]
    def __init__(self, parent):
        super().__init__(parent)

        m_radioBox2Choices = [ _(u"背景减除法(Background Subtraction)"), _(u"帧差法(Frame Differencing)"), _(u"光流法(Optical Flow)"), _(u"深度学习扩展")]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"目标检测算法"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 4, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageMODOnRadioBox )

    def imageMODOnRadioBox( self, event ):
        self.run_algorithm(self.m_radioBox2.GetSelection())
        event.Skip()
    def imageBackgroundSubstraction(self):
        pass

    def imageFrameDifferencing(self):
        pass
        
    def imageOpticalFlow(self):
        pass

class WatershedPanel(AlgorithmPanelBase):
    def __init__(self, parent,):
        super().__init__(parent)

        self.imageWatershed      = wx.Button( self, wx.ID_ANY, _(u"分水岭算法生成白底图"), wx.DefaultPosition, wx.DefaultSize, 0 )
        self.imageWatershedCoins = wx.Button( self, wx.ID_ANY, _(u"分水岭算法分割硬币"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.HORIZONTAL )        
        controlPanelSizer.Add( self.imageWatershed, 0, wx.ALL, 5 )
        controlPanelSizer.Add( self.imageWatershedCoins, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageWatershed.Bind( wx.EVT_BUTTON, self.imageWatershedBtnClick )
        self.imageWatershedCoins.Bind( wx.EVT_BUTTON, self.imageWatershedCoinsBtnClick )

    def imageWatershedBtnClick( self, event ):
        self.imageWatershedGetWhiteBackground()
        self.fire_display_event()  # 触发事件  
        event.Skip()

    def imageWatershedCoinsBtnClick( self, event ):
        self.imageWatershedCoinsPro()
        self.fire_display_event()  # 触发事件  
        event.Skip()

    def imageWatershedGetWhiteBackground(self):
        pil_img             = self.parent_frame.original_pil_image
        pil_img_template    = self.parent_frame.processed_pil_image
        if pil_img: 
            # 1. 读取原图和模板
            # 待匹配的大图          
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
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

            self.finish(result)

    def imageWatershedCoinsPro(self):
        pil_img             = self.parent_frame.original_pil_image
        pil_img_template    = self.parent_frame.processed_pil_image
        if pil_img: 
            # 1. 读取原图和模板
            # 待匹配的大图          
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
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
            self.finish(img_bgr)
     

class PyramidPanel(AlgorithmPanelBase):
    ALGORITHM_METHODS = ["imageGaussianPyramid", "imageLaplusPyramid", "imageLaplacianPyramidReconstruction"]
    def __init__(self, parent):
        super().__init__(parent)

        m_radioBox2Choices = [ _(u"高斯金字塔)"), _(u"拉普拉斯金字塔"), _(u"从拉普拉斯金字塔重建图像")]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"金字塔算法"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 4, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imagePyramidOnRadioBox )

    def imagePyramidOnRadioBox( self, event ):
        self.run_algorithm(self.m_radioBox2.GetSelection())
        event.Skip()
    def build_gaussian_pyramid(self, img, levels=3):
        """构建高斯金字塔（下采样）"""
        pyramid = [img.copy()]
        for i in range(levels):
            img = cv2.pyrDown(img)
            pyramid.append(img)
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
        for i in range(levels - 1):
            img = cv2.pyrDown(img)
            gaussian_pyramid.append(img)

        # 2. 构建拉普拉斯金字塔
        laplacian_pyramid = []
        for i in range(levels - 1):
            size = (gaussian_pyramid[i].shape[0], gaussian_pyramid[i].shape[0])
            expanded = cv2.pyrUp(gaussian_pyramid[i + 1], dstsize=size)
            lap = cv2.subtract(gaussian_pyramid[i], expanded)
            laplacian_pyramid.append(lap)

        # 最后一级直接保留高斯金字塔顶层
        laplacian_pyramid.append(gaussian_pyramid[-1])
        return laplacian_pyramid

    def reconstruct_from_laplacian(self, laplacian_pyramid):
        """
        从拉普拉斯金字塔重建原始图像
        """
        current = laplacian_pyramid[-1]
        for i in range(len(laplacian_pyramid) - 2, -1, -1):
            size = (laplacian_pyramid[i].shape[0], laplacian_pyramid[i].shape[0])
            current = cv2.pyrUp(current, dstsize=size)
            current = cv2.add(current, laplacian_pyramid[i])
        return current

    def cv2_to_pil(self, img):
        """OpenCV BGR 转 PIL RGB"""
        if len(img.shape) == 2:  # 灰度图
            return Image.fromarray(img)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)

    def imageGaussianPyramid(self):
        pil_img             = self.parent_frame.original_pil_image  
        if pil_img: 
            # 1. 读取原图并转灰度图        
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度）

            # 2. 构建高斯金字塔
            gaussian_pyr = self.build_gaussian_pyramid(img_bgr, levels=4)

            # 3. 转 PIL 
            for i, g_img in enumerate(gaussian_pyr):
                self.finish(g_img)
                logging.info(f"高斯金字塔第{i}层尺寸: {g_img.shape}x{g_img.shape}")

    def imageLaplusPyramid(self):
        pil_img             = self.parent_frame.original_pil_image  
        if pil_img: 
            # 1. 读取原图并转灰度图     
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度）
            
            # 2. 构建拉普拉斯金字塔
            laplacian_pyr = self.build_laplacian_pyramid(img_bgr)

            # 3. 转 PIL 
            for i, l_img in enumerate(laplacian_pyr):
                self.finish(l_img)
                logging.info(f"拉普拉斯金字塔第{i}层尺寸: {l_img.shape}x{l_img.shape}") 

    def imageLaplacianPyramidReconstruction(self):
        pil_img             = self.parent_frame.original_pil_image  
        if pil_img: 
            # 1. 读取原图并转灰度图        
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度）

            # 2. 构建拉普拉斯金字塔
            laplacian_pyr = self.build_laplacian_pyramid(img_bgr, levels=4)

            # 3、重建测试
            re_img = self.reconstruct_from_laplacian(laplacian_pyr)
            self.finish(re_img)        


class AaffineTransformationPanel(AlgorithmPanelBase):
    ALGORITHM_METHODS = ["imageTranslation", "imageRotate", "imageScaling", "imageShear", "imageCombinationTransformation"]
    def __init__(self, parent):
        super().__init__(parent)

        m_radioBox2Choices = [ _(u"平移"), _(u"旋转"), _(u"缩放"), _(u"错切"), _(u"组合变换")]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"仿射变换"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 5, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageAaffineTransformationOnRadioBox )

    def imageAaffineTransformationOnRadioBox( self, event ):
        self.run_algorithm(self.m_radioBox2.GetSelection())
        event.Skip()
    def imageTranslation(self):
        pil_img             = self.parent_frame.original_pil_image  
        if pil_img: 
            # 1. 读取原图并转灰度图     
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度
        h, w = img_bgr.shape[:2]

        tx, ty = 100, 50  # 向右100像素，向下50像素
        M = np.float32([[1, 0, tx], [0, 1, ty]])

        dst = cv2.warpAffine(img_bgr, M, (w, h))

        self.finish(dst)

    def rotate_arbitrary(self, img, angle, fill_color=(255, 255, 255)):
        h, w = img.shape[:2]
        center = (w/2, h/2)
        
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # 计算旋转后外接矩形尺寸
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])
        new_w = int(h * sin + w * cos)
        new_h = int(h * cos + w * sin)
        
        # 补偿平移，让图像居中
        M[0, 2] += (new_w - w) / 2
        M[1, 2] += (new_h - h) / 2
        
        return cv2.warpAffine(img, M, (new_w, new_h),
                              borderMode=cv2.BORDER_CONSTANT,
                              borderValue=fill_color)

    def imageRotate(self):
        pil_img             = self.parent_frame.original_pil_image  
        if pil_img: 
            # 1. 读取原图并转灰度图     
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度)
        h, w = img_bgr.shape[:2]

        # 以图像中心为旋转中心，逆时针旋转45度，不缩放
        # M = cv2.getRotationMatrix2D((w/2, h/2), 45, 1.0)
        # rotated = cv2.warpAffine(img_bgr, M, (w, h))
        rotated = self.rotate_arbitrary(img_bgr, 45)

        self.finish(rotated)

    def affine_scale(self, img, sx, sy):
        """
        仿射变换缩放
        :param img: OpenCV 图像 (BGR 或灰度)
        :param sx: x 方向缩放因子
        :param sy: y 方向缩放因子
        :return: 缩放后的 OpenCV 图像
        """
        h, w = img.shape[:2]
        # 构造 2x3 仿射变换矩阵
        M = np.float32([[sx, 0, 0],
                        [0, sy, 0]])
        # 计算输出尺寸
        dsize = (int(w * sx), int(h * sy))
        # 执行仿射变换，双线性插值，白色填充
        dst = cv2.warpAffine(img, M, dsize, 
                             flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_CONSTANT,
                             borderValue=(255, 255, 255))
        return dst

    def imageScaling(self):
        pil_img             = self.parent_frame.original_pil_image  
        if pil_img: 
            # 1. 读取原图并转灰度图     
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度)

        img_scaled = self.affine_scale(img_bgr, 2, 2)

        self.finish(img_scaled)

    def imageShear(self):
        pil_img             = self.parent_frame.original_pil_image  
        if pil_img: 
            # 1. 读取原图并转灰度图     
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度)

            h, w = img_bgr.shape[:2]

            # 2. 构造错切矩阵（水平错切 30 度）
            theta = np.radians(30)
            M = np.float32([[1, np.tan(theta), 0],
                            [0, 1, 0]])

            # 3. 计算新画布尺寸，避免裁剪
            new_w = int(w + abs(np.tan(theta)) * h)
            new_h = h
            # 平移修正，让图像居中显示
            M[0, 2] += (new_w - w) / 2

            # 4. 应用仿射变换
            sheared = cv2.warpAffine(img_bgr, M, (new_w, new_h), 
                                      flags=cv2.INTER_LINEAR, 
                                      borderMode=cv2.BORDER_CONSTANT, 
                                      borderValue=(255, 255, 255))
            self.finish(sheared)

    def combined_affine(self, image, rotate_angle=0, scale=1.0, translate=(0, 0), center=None):
        h, w = image.shape[:2]
        if center is None:
            center = (w // 2, h // 2)
        
        # 1. 旋转+缩放矩阵（2x3）
        M_rot_scale = cv2.getRotationMatrix2D(center, rotate_angle, scale)
        # 2. 平移矩阵（2x3）
        print(translate, type(translate))
        M_translate = np.float32([[1, 0, translate[0]], [0, 1, translate[1]]])
        
        # 3. 补成 3x3 齐次坐标形式，才能矩阵相乘
        M_rot_scale_h = np.vstack([M_rot_scale, [0, 0, 1]])
        M_translate_h = np.vstack([M_translate, [0, 0, 1]])
            # 4. 矩阵相乘（注意顺序：先旋转缩放，再平移）
        M_combined_h = M_translate_h @ M_rot_scale_h
        M_combined = M_combined_h[:2]  # 取回 2x3
        
        # 5. 一次性执行仿射变换
        result = cv2.warpAffine(image, M_combined, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
        return result, M_combined

    def imageCombinationTransformation(self):
        pil_img             = self.parent_frame.original_pil_image  
        if pil_img: 
            # 1. 读取原图并转灰度图     
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度)

            result,_ = self.combined_affine(img_bgr, 30, 2, (100,100))
            self.finish(result)


class PerspectiveTransformationPanel(AlgorithmPanelBase):
    def __init__(self, parent):
        super().__init__(parent)

        self.imagePerspectiveTransformation      = wx.Button( self, wx.ID_ANY, _(u"透视变换算法"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.HORIZONTAL )        
        controlPanelSizer.Add( self.imagePerspectiveTransformation, 0, wx.ALL, 5 )
        
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imagePerspectiveTransformation.Bind( wx.EVT_BUTTON, self.imagePerspectiveTransformationBtnClick )        

    def imagePerspectiveTransformationBtnClick( self, event ):
        self.imagePerspectiveTransformationPro()
        self.fire_display_event()  # 触发事件  
        event.Skip()

    def imagePerspectiveTransformationPro(self):
        pil_img             = self.parent_frame.original_pil_image  
        if pil_img: 
            # 1. 读取原图并转灰度图     
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
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
            self.finish(warped)


class FourierTransformationPanel(AlgorithmPanelBase):
    ALGORITHM_METHODS = ["imageFourierSpectrum", "imageFourierRestored"]
    def __init__(self, parent):
        super().__init__(parent)

        m_radioBox2Choices = [ _(u"频谱图"), _(u"逆变换原图")]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"傅里叶变换算法"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 5, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageFourierTransformationOnRadioBox )

    def imageFourierTransformationOnRadioBox( self, event ):
        self.run_algorithm(self.m_radioBox2.GetSelection())
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
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
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
            self.finish(magnitude_uint8)  # 频谱图

    def imageFourierRestored(self):
        
        pil_img             = self.parent_frame.original_pil_image  
        if pil_img: 
            # 1. 读取原图并转灰度图     
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
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
            
            self.finish(img_back)     # 逆变换还原图

class FloodFillPanel(AlgorithmPanelBase):
    def __init__(self, parent):
        super().__init__(parent)

        self.imageFloodFill      = wx.Button( self, wx.ID_ANY, _(u"漫水填充算法"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.HORIZONTAL )        
        controlPanelSizer.Add( self.imageFloodFill, 0, wx.ALL, 5 )
        
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageFloodFill.Bind( wx.EVT_BUTTON, self.imageFloodFillOnBtnClick )        

    def imageFloodFillOnBtnClick( self, event ):
        self.imageFloodFillOnBtnClickPro()
        self.fire_display_event()  # 触发事件  
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
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
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
            self.finish(img_bgr)

class RemappingPanel(AlgorithmPanelBase):
    ALGORITHM_METHODS = ["imageHorizontalMirror", "imageVerticalMirror", "imageFlipAroundXYAxis", "imageCompressYAxisByHalf", "imageCompressXAxisByHalf", "imageCompressEachXAndYAxesByHalf"]
    def __init__(self, parent):
        super().__init__(parent)

        m_radioBox2Choices = [ _(u"水平镜像"), _(u"垂直镜像"),_(u"绕XY轴翻转"),_(u"Y轴压缩一半"),_(u"X轴压缩一半"),_(u"XY轴各压缩一半"),]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"重映像算法"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 6, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageRemappingOnRadioBox )

    def imageRemappingOnRadioBox( self, event ):
        self.run_algorithm(self.m_radioBox2.GetSelection())
        event.Skip()
    def imageHorizontalMirror(self):
        """
        关键说明:
        1、映射矩阵类型：map_x 和 map_y 必须是 np.float32，否则 cv2.remap() 会报错。
        2、坐标含义    ：map_x[y, x] 存的是目标图 (x, y) 处像素取自原图的 x 坐标，map_y 同理存 y 坐标。
        3、向量化优化  ：双重循环慢，可用 NumPy 向量化替代。
        4、其他常用映射规则
            垂直镜像：map_y[y, x] = h - 1 - y，x 不变。
            绕 XY 轴翻转：x 和 y 坐标都反转。
            压缩一半：map_y[y, x] = 2 * y，图像在 y 方向缩小一半
        """
        pil_img             = self.parent_frame.original_pil_image
        if pil_img: 
            # 1. 读取原图并转灰度图     
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度)

            # OpenCV 默认 BGR 格式            
            h, w = img_bgr.shape[:2]

            # 2. 构建映射矩阵（水平镜像：x 坐标翻转，y 坐标不变）
            map_x = np.zeros((h, w), dtype=np.float32)
            map_y = np.zeros((h, w), dtype=np.float32)
            # 水平镜像算法
            for y in range(h):
                for x in range(w):
                    map_x[y, x] = w - 1 - x
                    map_y[y, x] = y
            # 垂直镜像算法
            # for y in range(h):
            #     for x in range(w):
            #         map_x[y, x] = x
            #         map_y[y, x] = h -1 -y
            # 绕 XY 轴翻转：x 和 y 坐标都反转
            # for y in range(h):
            #     for x in range(w):
            #         map_x[y, x] = w -1 -x
            #         map_y[y, x] = h -1 -y
            # 压缩一半：map_y[y, x] = 2 * y，图像在 y 方向缩小一半
            # for y in range(h):
            #     for x in range(w):
            #         map_x[y, x] =  x
            #         map_y[y, x] =  2 * y

            # 3. 应用重映射
            remapped = cv2.remap(img_bgr, map_x, map_y, interpolation=cv2.INTER_LINEAR)
            # 4. 转成 PIL Image（BGR -> RGB）            
            self.finish(remapped)
    
    def imageVerticalMirror(self):
        pil_img             = self.parent_frame.original_pil_image
        if pil_img: 
            # 1. 读取原图并转灰度图     
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度)

            # OpenCV 默认 BGR 格式            
            h, w = img_bgr.shape[:2]

            # 2. 构建映射矩阵（水平镜像：x 坐标翻转，y 坐标不变）
            map_x = np.zeros((h, w), dtype=np.float32)
            map_y = np.zeros((h, w), dtype=np.float32)           
            #垂直镜像算法
            for y in range(h):
                for x in range(w):
                    map_x[y, x] = x
                    map_y[y, x] = h -1 -y
            # 绕 XY 轴翻转：x 和 y 坐标都反转
            # for y in range(h):
            #     for x in range(w):
            #         map_x[y, x] = w -1 -x
            #         map_y[y, x] = h -1 -y
            # 压缩一半：map_y[y, x] = 2 * y，图像在 y 方向缩小一半
            # for y in range(h):
            #     for x in range(w):
            #         map_x[y, x] =  x
            #         map_y[y, x] =  2 * y

            # 3. 应用重映射
            remapped = cv2.remap(img_bgr, map_x, map_y, interpolation=cv2.INTER_LINEAR)
            # 4. 转成 PIL Image（BGR -> RGB）            
            self.finish(remapped)

    def imageFlipAroundXYAxis(self):
        pil_img             = self.parent_frame.original_pil_image
        if pil_img: 
            # 1. 读取原图并转灰度图     
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度)

            # OpenCV 默认 BGR 格式            
            h, w = img_bgr.shape[:2]

            # 2. 构建映射矩阵（水平镜像：x 坐标翻转，y 坐标不变）
            map_x = np.zeros((h, w), dtype=np.float32)
            map_y = np.zeros((h, w), dtype=np.float32)
            #绕 XY 轴翻转：x 和 y 坐标都反转
            for y in range(h):
                for x in range(w):
                    map_x[y, x] = w -1 -x
                    map_y[y, x] = h -1 -y
            # 压缩一半：map_y[y, x] = 2 * y，图像在 y 方向缩小一半
            # for y in range(h):
            #     for x in range(w):
            #         map_x[y, x] =  x
            #         map_y[y, x] =  2 * y

            # 3. 应用重映射
            remapped = cv2.remap(img_bgr, map_x, map_y, interpolation=cv2.INTER_LINEAR)
            # 4. 转成 PIL Image（BGR -> RGB）            
            self.finish(remapped)

    def imageCompressXAxisByHalf(self):
        pil_img             = self.parent_frame.original_pil_image
        if pil_img: 
            # 1. 读取原图并转灰度图     
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度)

            # OpenCV 默认 BGR 格式            
            h, w = img_bgr.shape[:2]

            # 2. 构建映射矩阵（水平镜像：x 坐标翻转，y 坐标不变）
            map_x = np.zeros((h, w), dtype=np.float32)
            map_y = np.zeros((h, w), dtype=np.float32)
            #绕 XY 轴翻转：x 和 y 坐标都反转                
            #压缩一半：map_y[y, x] = 2 * y，图像在 y 方向缩小一半
            for y in range(h):
                for x in range(w):
                    map_x[y, x] =  x
                    map_y[y, x] =  2 * y

            # 3. 应用重映射
            remapped = cv2.remap(img_bgr, map_x, map_y, interpolation=cv2.INTER_LINEAR)
            # 4. 转成 PIL Image（BGR -> RGB）            
            self.finish(remapped)

    def imageCompressYAxisByHalf(self):
        pil_img             = self.parent_frame.original_pil_image
        if pil_img: 
            # 1. 读取原图并转灰度图     
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度)

            # OpenCV 默认 BGR 格式            
            h, w = img_bgr.shape[:2]

            # 2. 构建映射矩阵（水平镜像：x 坐标翻转，y 坐标不变）
            map_x = np.zeros((h, w), dtype=np.float32)
            map_y = np.zeros((h, w), dtype=np.float32)
            #绕 XY 轴翻转：x 和 y 坐标都反转                
            #压缩一半：map_y[y, x] = 2 * y，图像在 y 方向缩小一半
            for y in range(h):
                for x in range(w):
                    map_x[y, x] =  2 * x
                    map_y[y, x] =  y

            # 3. 应用重映射
            remapped = cv2.remap(img_bgr, map_x, map_y, interpolation=cv2.INTER_LINEAR)
            # 4. 转成 PIL Image（BGR -> RGB）            
            self.finish(remapped)

    def imageCompressEachXAndYAxesByHalf(self):
        pil_img             = self.parent_frame.original_pil_image
        if pil_img: 
            # 1. 读取原图并转灰度图     
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度)

            # OpenCV 默认 BGR 格式            
            h, w = img_bgr.shape[:2]

            # 2. 构建映射矩阵（水平镜像：x 坐标翻转，y 坐标不变）
            map_x = np.zeros((h, w), dtype=np.float32)
            map_y = np.zeros((h, w), dtype=np.float32)
            #绕 XY 轴翻转：x 和 y 坐标都反转                
            #压缩一半：map_y[y, x] = 2 * y，图像在 y 方向缩小一半
            for y in range(h):
                for x in range(w):
                    map_x[y, x] =  2 * x
                    map_y[y, x] =  2 * y

            # 3. 应用重映射
            remapped = cv2.remap(img_bgr, map_x, map_y, interpolation=cv2.INTER_LINEAR)
            # 4. 转成 PIL Image（BGR -> RGB）            
            self.finish(remapped)

class BackProjectionPanel(AlgorithmPanelBase):
    def __init__(self, parent):
        super().__init__(parent)

        self.imageBackProjection      = wx.Button( self, wx.ID_ANY, _(u"反向投影算法"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.HORIZONTAL )        
        controlPanelSizer.Add( self.imageBackProjection, 0, wx.ALL, 5 )
        
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageBackProjection.Bind( wx.EVT_BUTTON, self.imageBackProjectionOnBtnClick )        

    def imageBackProjectionOnBtnClick( self, event ):
        self.imageBackProjectionOnBtnClickPro()
        self.fire_display_event()  # 触发事件  
        event.Skip()

    def imageBackProjectionOnBtnClickPro(self):
        roi_img             = self.parent_frame.original_pil_image
        target_img          = self.parent_frame.processed_pil_image
        if roi_img: 
            # 1. 读取原图
            target_bgr = cv2.cvtColor(np.asarray(target_img), cv2.COLOR_RGB2BGR)

            # 2. 转 HSV 色彩空间（只用 H 和 S 通道，减弱光照影响）
            roi_hsv     = cv2.cvtColor(np.asarray(roi_img), cv2.COLOR_BGR2HSV)
            target_hsv  = cv2.cvtColor(np.asarray(target_img), cv2.COLOR_BGR2HSV)
            
            # 3. 计算模板的 2D 直方图（H: 0-180, S: 0-256）
            roi_hist    = cv2.calcHist([roi_hsv], [0, 1], None, [180, 256], [0, 180, 0, 256])
            
            # 4. 归一化直方图到 0~255，这一步很关键
            cv2.normalize(roi_hist, roi_hist, 0, 255, cv2.NORM_MINMAX)
            
            # 5. 反向投影：把模板直方图“投影”到目标图上
            back_proj   = cv2.calcBackProject([target_hsv], [0, 1], roi_hist, [0, 180, 0, 256], 1)
            
            # 6. 用椭圆核做卷积，把离散的点连成片（可选但推荐）
            kernel      = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            back_proj   = cv2.filter2D(back_proj, -1, kernel)
            
            # 7. 阈值二值化，只保留匹配度高的区域
            _, thresh   = cv2.threshold(back_proj, 50, 255, cv2.THRESH_BINARY)
            
            # 8. 把结果从 OpenCV 的 BGR 格式转成 PIL Image
            # 反向投影结果是单通道灰度图，先转成 PIL 直接可用
            back_proj_pil   = Image.fromarray(back_proj)  # 灰度图直接转
            thresh_pil      = Image.fromarray(thresh)     # 二值图直接转
            
            # 如果想看彩色结果（原图上标出匹配区域），可以这样做：
            # 把二值图合并成 3 通道，再与原图做按位与
            thresh_3ch = cv2.merge([thresh, thresh, thresh])
            result     = cv2.bitwise_and(target_bgr, thresh_3ch)
            result_pil = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))

            self.parent_frame.processed_pil_image = result_pil

class CameraPanel(AlgorithmPanelBase):
    def __init__(self, parent):
        super().__init__(parent)

class CoordinateCalibrationPanel(AlgorithmPanelBase):
    def __init__(self, parent):
        super().__init__(parent)

class OcrPanel(AlgorithmPanelBase):
    def __init__(self, parent):
        super().__init__(parent)

        self.imageOcr      = wx.Button( self, wx.ID_ANY, _(u"光学字符识别算法"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.HORIZONTAL )        
        controlPanelSizer.Add( self.imageOcr, 0, wx.ALL, 5 )
        
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageOcr.Bind( wx.EVT_BUTTON, self.imageOcrOnBtnClick )        

    def imageOcrOnBtnClick( self, event ):
        self.imageOcrOnBtnClickPro()
        self.fire_display_event()  # 触发事件  
        event.Skip()

    def imageOcrOnBtnClickPro(self):
        pil_img             = self.parent_frame.original_pil_image  
        if pil_img: 
            # 1. 读取原图并转灰度图     
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度)

            binary = cv2.adaptiveThreshold(img_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY, 31, 10)

            # 3. 识别文字（直接传 numpy 数组给 pytesseract 也可以）
            #    这里演示传入二值化后的图像
            pytesseract.pytesseract.tesseract_cmd = r'D:\Tesseract-OCR\tesseract.exe'
            custom_config = r'--oem 3 --psm 6 -l chi_sim+eng'
            text = pytesseract.image_to_string(binary, config=custom_config)
            self.parent_frame.imageInfoStaticText.SetLabel(f"识别结果:{text}")
            logging.info(f"识别结果:{text}")

            # 可以把二值化结果转成 PIL 灰度图
            self.parent_frame.processed_pil_image = Image.fromarray(binary)


class VehicleLicensePlateRecognitionPanel(AlgorithmPanelBase):
    def __init__(self, parent):
        super().__init__(parent)

        self.imageVLPR      = wx.Button( self, wx.ID_ANY, _(u"车牌号识别算法"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.HORIZONTAL )        
        controlPanelSizer.Add( self.imageVLPR, 0, wx.ALL, 5 )
        
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageVLPR.Bind( wx.EVT_BUTTON, self.imageVLPROnBtnClick )        

    def imageVLPROnBtnClick( self, event ):
        self.imageVLPROnBtnClickPro()
        self.fire_display_event()  # 触发事件  
        event.Skip()

    def locate_license_plate(self, edged, img):
        """定位车牌区域：形态学闭运算 + 轮廓筛选"""
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 5))
        closed = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(closed.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours    = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
        
        for contour in contours:
            peri   = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / float(h)
                # 车牌宽高比一般在 2~5 之间
                if 2 < aspect_ratio < 5:
                    return (x, y, w, h), approx
        
        return None, None

    def segment_characters(self, plate_img):
        """分割车牌字符：二值化 + 垂直投影"""
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        return binary

    def recognize_with_tesseract(self, char_img):
        """用 Tesseract OCR 识别字符（需安装 pytesseract）"""
        import pytesseract
        pil_img = Image.fromarray(char_img)
        config = '--psm 8 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        text = pytesseract.image_to_string(pil_img, config=config)
        return text.strip()

    def imageVLPROnBtnClickPro(self):
        pil_img             = self.parent_frame.original_pil_image  
        if pil_img: 
            # 1. 读取原图并转灰度图     
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度)
            blurred                 = cv2.GaussianBlur(img_gray, (5, 5), 0)
            edged                   = cv2.Canny(blurred, 50, 150)

            # 2. 定位车牌
            plate_rect, plate_contour = self.locate_license_plate(edged, img_bgr)
            
            if plate_rect is None:
                print("未检测到车牌区域")
                return None
            
            x, y, w, h = plate_rect
            plate_img  = img_bgr[y:y+h, x:x+w]
            
            # 3. 字符分割
            char_binary = self.segment_characters(plate_img)
            
            # 4. 字符识别（可选，需安装 pytesseract）
            plate_text = self.recognize_with_tesseract(char_binary)
            print(f"识别结果: {plate_text}")
            
            # 5. 在原图上画框
            result_img = img_bgr.copy()
            cv2.rectangle(result_img, (x, y), (x+w, y+h), (0, 255, 0), 3)

            self.parent_frame.processed_pil_image = Image.fromarray(result_img)

class QRCodeRecognizationPanel(AlgorithmPanelBase):
    def __init__(self, parent):
        super().__init__(parent)

        self.imageQRCodeRecognization      = wx.Button( self, wx.ID_ANY, _(u"二维码识别算法"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.HORIZONTAL )        
        controlPanelSizer.Add( self.imageQRCodeRecognization, 0, wx.ALL, 5 )
        
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageQRCodeRecognization.Bind( wx.EVT_BUTTON, self.imageQRCodeRecognizationOnBtnClick )        

    def imageQRCodeRecognizationOnBtnClick( self, event ):
        self.imageQRCodeRecognizationOnPro()
        self.fire_display_event()  # 触发事件  
        event.Skip()

    def imageQRCodeRecognizationOnPro(self):
        pil_img             = self.parent_frame.original_pil_image  
        if pil_img: 
            # 1. 读取原图并转灰度图     
            img_bgr                 = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            img_gray                = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2. 将原图转为灰度图（模板匹配要求灰度)

            _, binary = cv2.threshold(img_gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

            # 3. pyzbar 识别二维码
            from pyzbar.pyzbar import decode
            decoded_objects = decode(binary)

            # 4. 在图上画框并打印结果
            for obj in decoded_objects:
                data = obj.data.decode('utf-8')
                print(f"识别内容: {data}")
                print(f"码制类型: {obj.type}")

                # 画多边形框
                points = obj.polygon
                if points:
                    pts = np.array(points, dtype=np.int32)
                    cv2.polylines(img_bgr, [pts], True, (0, 255, 0), 3)

                # 显示文字
                x, y, w, h = obj.rect
                cv2.putText(img_bgr, data, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX,0.7, (0, 255, 0), 2)
                self.parent_frame.processed_pil_image = Image.fromarray(img_bgr)