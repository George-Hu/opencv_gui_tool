# -*- coding: utf-8 -*-
"""界面模板层（template）—— 只负责控件摆放，不含任何算法逻辑。

代码由 wxFormBuilder 生成的界面描述整理而来，结构与 opencvTool.fbp 一致：
    * cvToolTemplate      : 主窗口骨架（菜单 / 按钮 / 图像显示区 / 参数区 / 状态栏）
    * XxxPanelTemplate    : 各算法面板的控件布局，事件只绑定到占位方法

约定：
    * 本文件不要写 OpenCV 算法，算法全部放在 opencvTool_control.py
    * 需要改界面时优先改这里（或直接用 wxFormBuilder 重新生成）
    * 占位方法只是 `event.Skip()`，真正的响应在控制层同名方法里重写
"""

import wx

import gettext
_ = gettext.gettext

# 1、定义事件类
class TriggrRightPanelDisplayEvent(wx.PyCommandEvent):
    def __init__(self, evtType, id):
        wx.PyCommandEvent.__init__(self, evtType, id)
# 2、 创建一个事件类型
myEVT_RIGHT_DISPLAY = wx.NewEventType() 
# 3、 创建一个绑定器对象
EVT_RIGHT_DISPLAY = wx.PyEventBinder(myEVT_RIGHT_DISPLAY, 1)

###########################################################################
## 主窗口模板
###########################################################################

class cvToolTemplate ( wx.Frame ):
    """主窗口骨架，只搭界面，不含业务逻辑。"""

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

        self.leftImagePanel = wx.Panel( self, wx.ID_ANY, wx.DefaultPosition, wx.Size( -1,-1 ), wx.BORDER_SIMPLE )
        self.leftImagePanel.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOW ) )
        self.leftImagePanel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOW ) )
        self.leftImagePanel.SetMinSize( wx.Size( 800,600 ) )
        imageSizer.Add( self.leftImagePanel, 1, wx.ALIGN_BOTTOM|wx.ALIGN_CENTER_HORIZONTAL, 5 )

        self.rightImagePanel = wx.Panel( self, wx.ID_ANY, wx.DefaultPosition, wx.Size( -1,-1 ), wx.BORDER_SIMPLE )
        self.rightImagePanel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOW ) )
        self.rightImagePanel.SetMinSize( wx.Size( 800,600 ) )
        imageSizer.Add( self.rightImagePanel, 1, wx.ALIGN_BOTTOM|wx.ALIGN_LEFT, 5 )

        frameSizer.Add( imageSizer, 0, 0, 5 )
        self.parameterStaticText = wx.StaticText( self, wx.ID_ANY, _(u"算法选择与参数调整"), wx.DefaultPosition, wx.Size( -1,30 ), 0  )
        self.parameterStaticText.Wrap( -1 )
        self.parameterStaticText.SetFont( wx.Font( 20, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, wx.EmptyString ) )
        self.parameterStaticText.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BACKGROUND ) )
        self.parameterStaticText.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_ACTIVECAPTION ) )
        self.parameterStaticText.SetMaxSize( wx.Size( 1600,30 ) )
        frameSizer.Add( self.parameterStaticText, 0, wx.ALL|wx.EXPAND, 5 )

        # 算法面板由视图层创建（见 cvToolView._build_panels）
        self._build_panels( frameSizer )

        self.SetSizer( frameSizer )
        self.Layout()
        frameSizer.Fit( self )
        self.statusBar = self.CreateStatusBar( 1, wx.STB_SIZEGRIP, wx.ID_ANY )
        self.Centre( wx.BOTH )

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

    # ---------------------------------------------------------------- 占位
    def _build_panels( self, frameSizer ):
        """由视图层实现：创建并挂载各算法面板。"""
        raise NotImplementedError

    def openImageclick( self, event ):
        event.Skip()

    def exampleImageClick( self, event ):
        event.Skip()

    def leftPanelOnPaint( self, event ):
        event.Skip()

    def rightPanelOnPaint( self, event ):
        event.Skip()

    def OnDoRightPanelImageDisplayEvent( self, event ):
        event.Skip()


###########################################################################
## ColorExtractionPanel
###########################################################################

class ColorExtractionPanelTemplate ( wx.Panel ):
    """ColorExtractionPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)  # 只调用了父类 wx.Panel 的构造函数
        self.parent_frame = parent  # 保存 Frame 引用
        
        m_radioBox2Choices  = [ _(u"BGR2GRAY"), _(u"BGR2HSV"), _(u"RGB2BGR"), _(u"BGR2YCrCb") ]
        self.m_radioBox2    = wx.RadioBox( self, wx.ID_ANY, _(u"选择转换色彩空间"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 4, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer   = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        controlPanelSizer.SetMinSize(wx.Size(-1,30))
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageProcessOnRadioBox )
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageProcessOnRadioBox( self, event ):
        event.Skip()


###########################################################################
## ImageDifferencePanel
###########################################################################

class ImageDifferencePanelTemplate ( wx.Panel ):
    """ImageDifferencePanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent,):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        self.imageDiff = wx.Button( self, wx.ID_ANY, _(u"计算图像差"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )        
        controlPanelSizer.Add( self.imageDiff, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageDiff.Bind( wx.EVT_BUTTON, self.imageDiffBtnClick )
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageDiffBtnClick( self, event ):
        event.Skip()


###########################################################################
## ImageStitchingPanel
###########################################################################

class ImageStitchingPanelTemplate ( wx.Panel ):
    """ImageStitchingPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        self.imageStitch  = wx.Button( self, wx.ID_ANY, _(u"开始图像拼接"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )        
        controlPanelSizer.Add( self.imageStitch, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageStitch.Bind( wx.EVT_BUTTON, self.imageStitchBtnClick )
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageStitchBtnClick( self, event ):
        event.Skip()


###########################################################################
## HistogramPanel
###########################################################################

class HistogramPanelTemplate ( wx.Panel ):
    """HistogramPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):  # 定义构造方法，parent 是外部传入的父对象
        super().__init__(parent) # 调用父类的构造方法，并把 parent 传进去。这样父类能完成自身初始化，比如设置 Qt/C++ 层面的父子关系
        self.parent_frame = parent  # 保存 Frame 引用

        self.imageHist = wx.Button( self, wx.ID_ANY, _(u"生成直方图"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )        
        controlPanelSizer.Add( self.imageHist, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageHist.Bind( wx.EVT_BUTTON, self.imageHistBtnClick )
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageHistBtnClick( self, event ):
        event.Skip()


###########################################################################
## ColorSpaceAndChannelExtractionPanel
###########################################################################

class ColorSpaceAndChannelExtractionPanelTemplate ( wx.Panel ):
    """ColorSpaceAndChannelExtractionPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        m_radioBox2Choices = [ _(u"BGR图片提取B通道"), _(u"BGR图片提取G通道"), _(u"BGR图片提取R通道"), _(u"HSV图片提取H通道"), _(u"HSV图片提取S通道"), _(u"HSV图片提取V通道") ]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"算法选择"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 6, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageProcessChannelExtraction )
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageProcessChannelExtraction( self, event ):
        event.Skip()


###########################################################################
## EqualizationPanel
###########################################################################

class EqualizationPanelTemplate ( wx.Panel ):
    """EqualizationPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        self.imageProcess = wx.Button( self, wx.ID_ANY, _(u"图像均衡化处理"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )        
        controlPanelSizer.Add( self.imageProcess, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageProcess.Bind( wx.EVT_BUTTON, self.imageEqualizationBtnClick )
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageEqualizationBtnClick( self, event ):
        event.Skip()


###########################################################################
## ThresholdProcessingPanel
###########################################################################

class ThresholdProcessingPanelTemplate ( wx.Panel ):
    """ThresholdProcessingPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

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
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageThresholdOnRadioBox( self, event ):
        event.Skip()


###########################################################################
## FilteringPanel
###########################################################################

class FilteringPanelTemplate ( wx.Panel ):
    """FilteringPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)  # 只调用了父类 wx.Panel 的构造函数
        self.parent_frame = parent  # 保存 Frame 引用
        
        m_radioBox2Choices = [ _(u"均值Blur"), _(u"方框BoxBlur"), _(u"高斯GaussianBlur"), _(u"中值MedianBlur") , _(u"双边Bilateral")]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"选择滤波算法"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 5, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageFilteringOnRadioBox )
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageFilteringOnRadioBox( self, event ):
        event.Skip()


###########################################################################
## MorphologicalOperationPanel
###########################################################################

class MorphologicalOperationPanelTemplate ( wx.Panel ):
    """MorphologicalOperationPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        m_radioBox2Choices = [ _(u"Erosion(腐蚀)"), _(u"Dilation(膨胀)"), _(u"Opening(开运算)"), _(u"Closing(闭运算)"),\
        _(u"Gradient(形态学梯度)"),  _(u"Top-hat(顶帽)"), _(u"Black-hat(黑帽)")]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"阈值处理"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 7, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageMorphologicalOnRadioBox )
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageMorphologicalOnRadioBox( self, event ):
        event.Skip()


###########################################################################
## ROIPanel
###########################################################################

class ROIPanelTemplate ( wx.Panel ):
    """ROIPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        self.imageDiff = wx.Button( self, wx.ID_ANY, _(u"自动感兴趣区域ROI人脸检测算法"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )        
        controlPanelSizer.Add( self.imageDiff, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageDiff.Bind( wx.EVT_BUTTON, self.imageAutoROIBtnClick )
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageAutoROIBtnClick( self, event ):
        event.Skip()


###########################################################################
## CornerDetectionPanel
###########################################################################

class CornerDetectionPanelTemplate ( wx.Panel ):
    """CornerDetectionPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        m_radioBox2Choices = [ _(u"Harris"), _(u"Shi-Tomasi"), _(u"ORB"), _(u"FAST"), _(u"SIFT")]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"阈值处理"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 5, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageCornerDetectionOnRadioBox )
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageCornerDetectionOnRadioBox( self, event ):
        event.Skip()


###########################################################################
## EdgeDetectionPanel
###########################################################################

class EdgeDetectionPanelTemplate ( wx.Panel ):
    """EdgeDetectionPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        m_radioBox2Choices = [ _(u"Canny"), _(u"Sobel"), _(u"Laplacian"), _(u"Scharr")]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"边缘检测算法"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 4, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageEdgeDetectionOnRadioBox )
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageEdgeDetectionOnRadioBox( self, event ):
        event.Skip()


###########################################################################
## GeometricShapePanel
###########################################################################

class GeometricShapePanelTemplate ( wx.Panel ):
    """GeometricShapePanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        m_radioBox2Choices = [ _(u"HoughLinesP(霍夫线检测)"), _(u"HoughCircles(霍夫圆检测)"), _(u"Contour(轮廓)"), _(u"LSD(直线段检测)"), \
                              _(u"FLD(快速直线检测))"), _(u"Blob(斑点)"),_(u"EdgeDrawing(ED)"), _(u"Hull(凸包)"), _(u"LeastSquaresCircleFitting(最小二乘拟合圆)")]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"边缘检测算法"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 4, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageGeometricShapeOnRadioBox )
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageGeometricShapeOnRadioBox( self, event ):
        event.Skip()


###########################################################################
## MovingObjectDetectionPanel
###########################################################################

class MovingObjectDetectionPanelTemplate ( wx.Panel ):
    """MovingObjectDetectionPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        m_radioBox2Choices = [ _(u"Harr级联分类器)"), _(u"模板匹配"), _(u"HOG特征提取")]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"目标检测算法"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 4, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageMODOnRadioBox )
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageMODOnRadioBox( self, event ):
        event.Skip()


###########################################################################
## ObjectDetectionPanel
###########################################################################

class ObjectDetectionPanelTemplate ( wx.Panel ):
    """ObjectDetectionPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        m_radioBox2Choices = [ _(u"背景减除法(Background Subtraction)"), _(u"帧差法(Frame Differencing)"), _(u"光流法(Optical Flow)"), _(u"深度学习扩展")]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"目标检测算法"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 4, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageMODOnRadioBox )
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageMODOnRadioBox( self, event ):
        event.Skip()


###########################################################################
## WatershedPanel
###########################################################################

class WatershedPanelTemplate ( wx.Panel ):
    """WatershedPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent,):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        self.imageWatershed      = wx.Button( self, wx.ID_ANY, _(u"分水岭算法生成白底图"), wx.DefaultPosition, wx.DefaultSize, 0 )
        self.imageWatershedCoins = wx.Button( self, wx.ID_ANY, _(u"分水岭算法分割硬币"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.HORIZONTAL )        
        controlPanelSizer.Add( self.imageWatershed, 0, wx.ALL, 5 )
        controlPanelSizer.Add( self.imageWatershedCoins, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageWatershed.Bind( wx.EVT_BUTTON, self.imageWatershedBtnClick )
        self.imageWatershedCoins.Bind( wx.EVT_BUTTON, self.imageWatershedCoinsBtnClick )
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageWatershedBtnClick( self, event ):
        event.Skip()

    def imageWatershedCoinsBtnClick( self, event ):
        event.Skip()


###########################################################################
## PyramidPanel
###########################################################################

class PyramidPanelTemplate ( wx.Panel ):
    """PyramidPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        m_radioBox2Choices = [ _(u"高斯金字塔)"), _(u"拉普拉斯金字塔"), _(u"从拉普拉斯金字塔重建图像")]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"金字塔算法"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 4, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imagePyramidOnRadioBox )
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imagePyramidOnRadioBox( self, event ):
        event.Skip()


###########################################################################
## AaffineTransformationPanel
###########################################################################

class AaffineTransformationPanelTemplate ( wx.Panel ):
    """AaffineTransformationPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        m_radioBox2Choices = [ _(u"平移"), _(u"旋转"), _(u"缩放"), _(u"错切"), _(u"组合变换")]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"仿射变换"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 5, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageAaffineTransformationOnRadioBox )
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageAaffineTransformationOnRadioBox( self, event ):
        event.Skip()


###########################################################################
## PerspectiveTransformationPanel
###########################################################################

class PerspectiveTransformationPanelTemplate ( wx.Panel ):
    """PerspectiveTransformationPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        self.imagePerspectiveTransformation      = wx.Button( self, wx.ID_ANY, _(u"透视变换算法"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.HORIZONTAL )        
        controlPanelSizer.Add( self.imagePerspectiveTransformation, 0, wx.ALL, 5 )
        
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imagePerspectiveTransformation.Bind( wx.EVT_BUTTON, self.imagePerspectiveTransformationBtnClick )        
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imagePerspectiveTransformationBtnClick( self, event ):
        event.Skip()


###########################################################################
## FourierTransformationPanel
###########################################################################

class FourierTransformationPanelTemplate ( wx.Panel ):
    """FourierTransformationPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        m_radioBox2Choices = [ _(u"频谱图"), _(u"逆变换原图")]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"傅里叶变换算法"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 5, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageFourierTransformationOnRadioBox )
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageFourierTransformationOnRadioBox( self, event ):
        event.Skip()


###########################################################################
## FloodFillPanel
###########################################################################

class FloodFillPanelTemplate ( wx.Panel ):
    """FloodFillPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        self.imageFloodFill      = wx.Button( self, wx.ID_ANY, _(u"漫水填充算法"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.HORIZONTAL )        
        controlPanelSizer.Add( self.imageFloodFill, 0, wx.ALL, 5 )
        
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageFloodFill.Bind( wx.EVT_BUTTON, self.imageFloodFillOnBtnClick )        
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageFloodFillOnBtnClick( self, event ):
        event.Skip()


###########################################################################
## RemappingPanel
###########################################################################

class RemappingPanelTemplate ( wx.Panel ):
    """RemappingPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        m_radioBox2Choices = [ _(u"水平镜像"), _(u"垂直镜像"),_(u"绕XY轴翻转"),_(u"Y轴压缩一半"),_(u"X轴压缩一半"),_(u"XY轴各压缩一半"),]
        self.m_radioBox2 = wx.RadioBox( self, wx.ID_ANY, _(u"重映像算法"), wx.DefaultPosition, wx.Size( 1600,160 ), m_radioBox2Choices, 6, wx.RA_SPECIFY_COLS )
        self.m_radioBox2.SetSelection( 0 )
        controlPanelSizer = wx.BoxSizer( wx.VERTICAL )
        controlPanelSizer.Add( self.m_radioBox2, 0, wx.ALL, 5 )
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.m_radioBox2.Bind( wx.EVT_RADIOBOX, self.imageRemappingOnRadioBox )
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageRemappingOnRadioBox( self, event ):
        event.Skip()


###########################################################################
## BackProjectionPanel
###########################################################################

class BackProjectionPanelTemplate ( wx.Panel ):
    """BackProjectionPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        self.imageBackProjection      = wx.Button( self, wx.ID_ANY, _(u"反向投影算法"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.HORIZONTAL )        
        controlPanelSizer.Add( self.imageBackProjection, 0, wx.ALL, 5 )
        
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageBackProjection.Bind( wx.EVT_BUTTON, self.imageBackProjectionOnBtnClick )        
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageBackProjectionOnBtnClick( self, event ):
        event.Skip()


###########################################################################
## CameraPanel
###########################################################################

class CameraPanelTemplate ( wx.Panel ):
    """CameraPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent


###########################################################################
## CoordinateCalibrationPanel
###########################################################################

class CoordinateCalibrationPanelTemplate ( wx.Panel ):
    """CoordinateCalibrationPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent


###########################################################################
## OcrPanel
###########################################################################

class OcrPanelTemplate ( wx.Panel ):
    """OcrPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        self.imageOcr      = wx.Button( self, wx.ID_ANY, _(u"光学字符识别算法"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.HORIZONTAL )        
        controlPanelSizer.Add( self.imageOcr, 0, wx.ALL, 5 )
        
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageOcr.Bind( wx.EVT_BUTTON, self.imageOcrOnBtnClick )        
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageOcrOnBtnClick( self, event ):
        event.Skip()


###########################################################################
## VehicleLicensePlateRecognitionPanel
###########################################################################

class VehicleLicensePlateRecognitionPanelTemplate ( wx.Panel ):
    """VehicleLicensePlateRecognitionPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        self.imageVLPR      = wx.Button( self, wx.ID_ANY, _(u"车牌号识别算法"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.HORIZONTAL )        
        controlPanelSizer.Add( self.imageVLPR, 0, wx.ALL, 5 )
        
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageVLPR.Bind( wx.EVT_BUTTON, self.imageVLPROnBtnClick )        
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageVLPROnBtnClick( self, event ):
        event.Skip()


###########################################################################
## QRCodeRecognizationPanel
###########################################################################

class QRCodeRecognizationPanelTemplate ( wx.Panel ):
    """QRCodeRecognizationPanel 的界面模板：控件 + 事件绑定，算法在控制层同名类中实现。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_frame = parent  # 保存 Frame 引用

        self.imageQRCodeRecognization      = wx.Button( self, wx.ID_ANY, _(u"二维码识别算法"), wx.DefaultPosition, wx.DefaultSize, 0 )
        controlPanelSizer = wx.BoxSizer( wx.HORIZONTAL )        
        controlPanelSizer.Add( self.imageQRCodeRecognization, 0, wx.ALL, 5 )
        
        self.SetSizer( controlPanelSizer )
        controlPanelSizer.Fit( self )

        self.imageQRCodeRecognization.Bind( wx.EVT_BUTTON, self.imageQRCodeRecognizationOnBtnClick )        
        self.evt = TriggrRightPanelDisplayEvent(myEVT_RIGHT_DISPLAY, self.GetId())

    # ---- 事件占位：由控制层重写 ----
    def imageQRCodeRecognizationOnBtnClick( self, event ):
        event.Skip()


