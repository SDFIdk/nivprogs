import wx
def Hej(event):
	print event.GetKeyCode()
A=wx.Frame(None,title="hej",size=(200,200))
p=wx.Panel(A,size=(100,100),pos=(50,50),style=wx.WANTS_CHARS)
p.Bind(wx.EVT_CHAR,Hej)
p.SetBackgroundColour("blue")
app=wx.App()
A.Show()
app.MainLoop()