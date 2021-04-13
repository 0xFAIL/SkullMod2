import wx

from SkullModPy2.ui import MainForm


def main():
    app = wx.App(False)
    main_form = MainForm(None)
    main_form.Show()
    app.MainLoop()


if __name__ == '__main__':
    main()
