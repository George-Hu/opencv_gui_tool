import wx
from LoginOut import LoginFrame,UserManager


class LoginApp(wx.App):
    """主应用程序"""
    def OnInit(self):
        self.user_manager = UserManager()
        login_frame = LoginFrame(None, title="OpenCV算法演示工具用户登录", user_manager=self.user_manager)
        login_frame.Show()
        return True

if __name__ == '__main__':
    app = LoginApp()
    app.MainLoop()