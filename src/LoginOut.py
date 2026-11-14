import wx
import json
import os
import hashlib

from opencvTool import cvTool

class UserManager:
    """用户数据管理类，负责用户信息的存储、注册和登录验证"""
    def __init__(self):
        # 用户数据文件路径，与脚本同目录
        self.data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.json')
        # 初始化数据文件
        if not os.path.exists(self.data_path):
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump({}, f)
    
    def _hash_password(self, password):
        """密码SHA256哈希加密，避免明文存储（生产环境建议加盐）"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def load_users(self):
        """加载所有用户数据"""
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def save_users(self, users):
        """保存用户数据到文件"""
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    
    def register_user(self, username, password, email):
        """注册新用户，返回(是否成功, 提示消息)"""
        users = self.load_users()
        # 检查用户名是否已存在
        if username in users:
            return False, "该用户名已被注册，请更换用户名"
        # 保存用户信息
        users[username] = {
            'password': self._hash_password(password),
            'email': email
        }
        self.save_users(users)
        return True, "注册成功，请登录"
    
    def validate_login(self, username, password):
        """验证登录信息，返回(是否成功, 提示消息)"""
        users = self.load_users()
        if username not in users:
            return False, "用户名不存在，请先注册"
        if users[username]['password'] != self._hash_password(password):
            return False, "密码错误，请重新输入"
        return True, "登录成功"


class LoginFrame(wx.Frame):
    """登录窗口"""
    def __init__(self, parent, title, user_manager):
        super(LoginFrame, self).__init__(parent, title=title, size=(400, 300))
        self.user_manager = user_manager
        self.init_ui()
        self.Centre()  # 窗口居中显示
    
    def init_ui(self):
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 标题
        title_label = wx.StaticText(panel, label="用户登录", style=wx.ALIGN_CENTER)
        title_font = wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title_label.SetFont(title_font)
        main_sizer.Add(title_label, 0, wx.ALL | wx.EXPAND, 20)
        
        # 用户名输入行
        username_sizer = wx.BoxSizer(wx.HORIZONTAL)
        username_label = wx.StaticText(panel, label="用户名：", size=(60, -1))
        self.username_input = wx.TextCtrl(panel)
        username_sizer.Add(username_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)
        username_sizer.Add(self.username_input, 1, wx.ALL | wx.EXPAND, 10)
        main_sizer.Add(username_sizer, 0, wx.EXPAND)
        
        # 密码输入行
        pwd_sizer = wx.BoxSizer(wx.HORIZONTAL)
        pwd_label = wx.StaticText(panel, label="密  码：", size=(60, -1))
        self.pwd_input = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        pwd_sizer.Add(pwd_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)
        pwd_sizer.Add(self.pwd_input, 1, wx.ALL | wx.EXPAND, 10)
        main_sizer.Add(pwd_sizer, 0, wx.EXPAND)
        
        # 按钮区域
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.login_btn = wx.Button(panel, label="登录")
        self.register_btn = wx.Button(panel, label="注册新账号")
        btn_sizer.Add(self.login_btn, 0, wx.ALL, 10)
        btn_sizer.Add(self.register_btn, 0, wx.ALL, 10)
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER)
        
        panel.SetSizer(main_sizer)
        
        # 绑定事件
        self.login_btn.Bind(wx.EVT_BUTTON, self.on_login)
        self.register_btn.Bind(wx.EVT_BUTTON, self.on_register)
        self.login_btn.SetDefault()  # 回车默认触发登录
        self.username_input.SetFocus()  # 初始焦点在用户名输入框
    
    def on_login(self, event):
        """登录按钮点击事件"""
        username = self.username_input.GetValue().strip()
        password = self.pwd_input.GetValue()
        
        # 非空验证
        if not username or not password:
            wx.MessageBox("用户名和密码不能为空", "提示", wx.OK | wx.ICON_WARNING)
            return
        
        # 验证登录信息
        success, msg = self.user_manager.validate_login(username, password)
        if success:
            wx.MessageBox(msg, "成功", wx.OK | wx.ICON_INFORMATION)
            self.Close()
            # 登录成功打开主界面
            #main_frame = MainFrame(None, title="系统主页", username=username)
            main_frame  = cvTool(None)
            main_frame.Show()
        else:
            wx.MessageBox(msg, "错误", wx.OK | wx.ICON_ERROR)
            self.pwd_input.SetValue("")
            self.pwd_input.SetFocus()
    
    def on_register(self, event):
        """注册按钮点击事件，切换到注册窗口"""
        self.Hide()
        register_frame = RegisterFrame(
            None, title="用户注册", 
            login_frame=self, 
            user_manager=self.user_manager
        )
        register_frame.Show()


class RegisterFrame(wx.Frame):
    """注册窗口"""
    def __init__(self, parent, title, login_frame, user_manager):
        super(RegisterFrame, self).__init__(parent, title=title, size=(450, 420))
        self.login_frame = login_frame
        self.user_manager = user_manager
        self.init_ui()
        self.Centre()
        # 绑定窗口关闭事件，点击右上角X时返回登录窗口
        self.Bind(wx.EVT_CLOSE, self.on_close)
    
    def init_ui(self):
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 标题
        title_label = wx.StaticText(panel, label="用户注册", style=wx.ALIGN_CENTER)
        title_font = wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title_label.SetFont(title_font)
        main_sizer.Add(title_label, 0, wx.ALL | wx.EXPAND, 20)
        
        # 用户名输入
        username_sizer = wx.BoxSizer(wx.HORIZONTAL)
        username_label = wx.StaticText(panel, label="用户名：", size=(80, -1))
        self.username_input = wx.TextCtrl(panel)
        username_sizer.Add(username_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)
        username_sizer.Add(self.username_input, 1, wx.ALL | wx.EXPAND, 10)
        main_sizer.Add(username_sizer, 0, wx.EXPAND)
        
        # 密码输入
        pwd_sizer = wx.BoxSizer(wx.HORIZONTAL)
        pwd_label = wx.StaticText(panel, label="密  码：", size=(80, -1))
        self.pwd_input = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        pwd_sizer.Add(pwd_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)
        pwd_sizer.Add(self.pwd_input, 1, wx.ALL | wx.EXPAND, 10)
        main_sizer.Add(pwd_sizer, 0, wx.EXPAND)
        
        # 确认密码输入
        confirm_pwd_sizer = wx.BoxSizer(wx.HORIZONTAL)
        confirm_pwd_label = wx.StaticText(panel, label="确认密码：", size=(80, -1))
        self.confirm_pwd_input = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        confirm_pwd_sizer.Add(confirm_pwd_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)
        confirm_pwd_sizer.Add(self.confirm_pwd_input, 1, wx.ALL | wx.EXPAND, 10)
        main_sizer.Add(confirm_pwd_sizer, 0, wx.EXPAND)
        
        # 邮箱输入
        email_sizer = wx.BoxSizer(wx.HORIZONTAL)
        email_label = wx.StaticText(panel, label="邮  箱：", size=(80, -1))
        self.email_input = wx.TextCtrl(panel)
        email_sizer.Add(email_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)
        email_sizer.Add(self.email_input, 1, wx.ALL | wx.EXPAND, 10)
        main_sizer.Add(email_sizer, 0, wx.EXPAND)
        
        # 提示文字
        tip_label = wx.StaticText(panel, label="提示：用户名不能重复，密码长度至少6位", style=wx.ALIGN_CENTER)
        tip_label.SetForegroundColour(wx.Colour(128, 128, 128))
        main_sizer.Add(tip_label, 0, wx.ALL, 5)
        
        # 按钮区域
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.register_btn = wx.Button(panel, label="立即注册")
        self.back_btn = wx.Button(panel, label="返回登录")
        btn_sizer.Add(self.register_btn, 0, wx.ALL, 10)
        btn_sizer.Add(self.back_btn, 0, wx.ALL, 10)
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER)
        
        panel.SetSizer(main_sizer)
        
        # 绑定事件
        self.register_btn.Bind(wx.EVT_BUTTON, self.on_register)
        self.back_btn.Bind(wx.EVT_BUTTON, self.on_back)
        self.register_btn.SetDefault()
        self.username_input.SetFocus()
    
    def on_register(self, event):
        """注册提交事件"""
        username = self.username_input.GetValue().strip()
        password = self.pwd_input.GetValue()
        confirm_pwd = self.confirm_pwd_input.GetValue()
        email = self.email_input.GetValue().strip()
        
        # 输入验证
        if not username:
            wx.MessageBox("用户名不能为空", "提示", wx.OK | wx.ICON_WARNING)
            self.username_input.SetFocus()
            return
        if not password or not confirm_pwd:
            wx.MessageBox("密码和确认密码不能为空", "提示", wx.OK | wx.ICON_WARNING)
            self.pwd_input.SetFocus()
            return
        if len(password) < 6:
            wx.MessageBox("密码长度不能少于6位", "提示", wx.OK | wx.ICON_WARNING)
            self.pwd_input.SetValue("")
            self.confirm_pwd_input.SetValue("")
            self.pwd_input.SetFocus()
            return
        if password != confirm_pwd:
            wx.MessageBox("两次输入的密码不一致", "提示", wx.OK | wx.ICON_WARNING)
            self.confirm_pwd_input.SetValue("")
            self.confirm_pwd_input.SetFocus()
            return
        if not email or '@' not in email:
            wx.MessageBox("请输入有效的邮箱地址", "提示", wx.OK | wx.ICON_WARNING)
            self.email_input.SetFocus()
            return
        
        # 执行注册
        success, msg = self.user_manager.register_user(username, password, email)
        if success:
            wx.MessageBox(msg, "成功", wx.OK | wx.ICON_INFORMATION)
            self.clear_inputs()
            self.Close()
            self.login_frame.Show()
        else:
            wx.MessageBox(msg, "错误", wx.OK | wx.ICON_ERROR)
            self.username_input.SetFocus()
    
    def on_back(self, event):
        """返回登录按钮事件"""
        self.clear_inputs()
        self.Close()
        self.login_frame.Show()
    
    def on_close(self, event):
        """窗口关闭事件处理"""
        self.login_frame.Show()
        self.Destroy()
    
    def clear_inputs(self):
        """清空所有输入框"""
        self.username_input.SetValue("")
        self.pwd_input.SetValue("")
        self.confirm_pwd_input.SetValue("")
        self.email_input.SetValue("")


class MainFrame(wx.Frame):
    """登录成功后的主窗口"""
    def __init__(self, parent, title, username):
        super(MainFrame, self).__init__(parent, title=title, size=(500, 300))
        self.username = username
        self.init_ui()
        self.Centre()
    
    def init_ui(self):
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 欢迎信息
        welcome_label = wx.StaticText(panel, label=f"欢迎您，{self.username}！", style=wx.ALIGN_CENTER)
        welcome_font = wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        welcome_label.SetFont(welcome_font)
        main_sizer.Add(welcome_label, 0, wx.ALL | wx.EXPAND, 50)
        
        tip_label = wx.StaticText(panel, label="您已成功登录系统", style=wx.ALIGN_CENTER)
        tip_font = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        tip_label.SetFont(tip_font)
        main_sizer.Add(tip_label, 0, wx.ALL | wx.EXPAND, 10)
        
        # 退出登录按钮
        self.logout_btn = wx.Button(panel, label="退出登录")
        main_sizer.Add(self.logout_btn, 0, wx.ALIGN_CENTER | wx.ALL, 30)
        
        panel.SetSizer(main_sizer)
        self.logout_btn.Bind(wx.EVT_BUTTON, self.on_logout)
    
    def on_logout(self, event):
        """退出登录，返回登录窗口"""
        self.Close()
        app = wx.GetApp()
        login_frame = LoginFrame(None, title="用户登录", user_manager=app.user_manager)
        login_frame.Show()


