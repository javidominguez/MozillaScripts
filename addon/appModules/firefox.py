# -*- coding: UTF-8 -*-

# Mozilla Firefox Scripts version 1.0.1dev (august 2016)
# Author Javi Dominguez <fjavids@gmail.com>

from nvdaBuiltin.appModules.firefox import *
import appModuleHandler
import addonHandler
import scriptHandler
import controlTypes
import api
import ui
import winUser
import gui
import wx

addonHandler.initTranslation()

class AppModule(appModuleHandler.AppModule):
	tbDialog = None

	def script_status(self, gesture):
		fg = api.getForegroundObject()
		for group in filter(lambda o: o.role == controlTypes.ROLE_GROUPING, fg.children):
			for propertyPage in filter(lambda o: o.role == controlTypes.ROLE_PROPERTYPAGE, group.children):
				try:
					obj = filter(lambda o: o.role == controlTypes.ROLE_STATUSBAR, propertyPage.children)[0]
				except IndexError:
					pass
		try:
			ui.message(_("Status bar: %s") % obj.name)
		except NameError:
			ui.message (_("Status bar not found"))
		else:
			if scriptHandler.getLastScriptRepeatCount() == 1:
				if api.copyToClip(obj.name):
					ui.message(_("Copied to clipboard"))
	# Translators: Message presented in input help mode.
	script_status.__doc__ = _("Reads the status bar. If pressed twice quickly, copies it to clipboard.")

	def script_url(self, gesture):
		fg = api.getForegroundObject()
		for bar in filter(lambda o: o.role == controlTypes.ROLE_TOOLBAR, fg.children):
			try:
				if bar.children[2].role == controlTypes.ROLE_COMBOBOX and bar.children[2].children[0].role == controlTypes.ROLE_BUTTON and bar.children[2].children[1].role == controlTypes.ROLE_EDITABLETEXT:
					url = bar.children[2].children[1].value
					securInfo = bar.children[2].children[0].description
			except (IndexError, AttributeError):
				pass
		try:
			ui.message(_("Page address is: %s (%s)") % (url, securInfo))
		except NameError:
			ui.message (_("Address not found"))
		else:
			if scriptHandler.getLastScriptRepeatCount() == 1:
				if api.copyToClip(url):
					ui.message(_("Copied to clipboard"))
	# Translators: Message presented in input help mode.
	script_url.__doc__ = _("Reads the page address. If pressed twice quickly, copies it to clipboard.")

	def script_toolsBar(self, gesture):
		if not self.tbDialog:
			self.tbDialog = toolsBarDialog(gui.mainFrame)
		if scriptHandler.getLastScriptRepeatCount() == 0:
			items, title = self.getTabsDialog()
			title = "%d %s" % (len(items), title)
		elif scriptHandler.getLastScriptRepeatCount() == 1: 
			items, title = self.getButtonsDialog()
		self.tbDialog.update(items, title)
		if not self.tbDialog.IsShown():
			gui.mainFrame.prePopup()
			self.tbDialog.Show()
			self.tbDialog.Centre()
			gui.mainFrame.postPopup()
	# Translators: Message presented in input help mode.
	script_toolsBar.__doc__ = _("Shows a list of opened tabs. If pressed twice quickly, shows buttons of tool bar.")

	def getTabsDialog(self):
		fg = api.getForegroundObject()
		for toolBar in filter(lambda o: o.role == controlTypes.ROLE_TOOLBAR, fg.children):
			try:
				tabControl = filter(lambda o: o.role == controlTypes.ROLE_TABCONTROL, toolBar.children)[0]
			except IndexError:
				pass
			else:
				tabs = filter(lambda o: o.role == controlTypes.ROLE_TAB, tabControl.children)
				allTabsCount = len(tabs)
				tabs = filter(lambda o: controlTypes.STATE_OFFSCREEN not in o.states, tabs)
				# Tabs in end left and end right are excluded when they are partially hidden
				if tabs[0].location[0] < 0:
					tabs = tabs[1:]
				try:
					if tabs[-1].location[0]+tabs[-1].location[2] > tabControl.parent.children[1].location[0]:
						tabs = tabs[:-1]
				except IndexError:
					pass
				showedTabsCount = len(tabs)
				# Add button Show all tabs to list when there are tabs offscreen
				if allTabsCount > showedTabsCount:
					tabs.append(tabControl.parent.children[2])
		return(tabs, _("Opened tabs"))

	def getButtonsDialog(self):
		fg = api.getForegroundObject()
		buttons = []
		for toolBar in filter(lambda o: o.role == controlTypes.ROLE_TOOLBAR, fg.children):
			buttons = buttons + filter(lambda o: o.role == controlTypes.ROLE_BUTTON, toolBar.children)
		return(buttons, _("Tool Bar Buttons"))

	__gestures = {
		"kb:NVDA+numpad3": "status",
		"kb:NVDA+End": "status",
		"kb:NVDA+F8": "toolsBar",
		"kb(desktop):NVDA+A": "url",
		"kb(laptop):NVDA+Control+A": "url"
	}

class toolsBarDialog(wx.Dialog):

	def __init__(self, parent):
		super(toolsBarDialog, self).__init__(parent, title="")
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		self.listBox = wx.ListBox(self, wx.NewId(), style=wx.LB_SINGLE, size=(300, 150))
		mainSizer.Add(self.listBox)
		self.Bind(wx.EVT_LISTBOX, self.onListBox, self.listBox)
		buttonsSizer = wx.BoxSizer(wx.HORIZONTAL)
		goButtonID = wx.NewId()
		self.goButton = wx.Button(self, goButtonID, _("&Go"))
		buttonsSizer.Add(self.goButton)
		self.Bind( wx.EVT_BUTTON, self.onGoButton, id=goButtonID)
		optionsButtonID = wx.NewId()
		self.optionsButton = wx.Button(self, optionsButtonID, _("&Options"))
		buttonsSizer.Add(self.optionsButton)
		self.Bind( wx.EVT_BUTTON, self.onOptionsButton, id=optionsButtonID)
		cancelButton = wx.Button(self, wx.ID_CANCEL, _("Close"))
		buttonsSizer.Add(cancelButton)
		mainSizer.Add(buttonsSizer)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)
		self.goButton.SetDefault()

	def update(self, items, title):
		self.items = items
		self.SetTitle(title)
		self.listBox.SetItems([item.name for item in self.items])
		self.listBox.SetFocus()

	def getObjectFromList(self):
		index = self.listBox.GetSelections()
		if index is not None:
			obj = self.items[index[0]]
			return(obj)

	def onListBox(self, event):
		if self.getObjectFromList().role == controlTypes.ROLE_BUTTON:
			self.optionsButton.Enabled = False
		else:
			self.optionsButton.Enabled = True

	def onGoButton(self, event):
		self.Hide()
		if self.moveMouseToObj():
			winUser.mouse_event(winUser.MOUSEEVENTF_LEFTDOWN,0,0,None,None)
			winUser.mouse_event(winUser.MOUSEEVENTF_LEFTUP,0,0,None,None)

	def onOptionsButton(self, event):
		self.Hide()
		if self.moveMouseToObj():
			winUser.mouse_event(winUser.MOUSEEVENTF_RIGHTDOWN,0,0,None,None)
			winUser.mouse_event(winUser.MOUSEEVENTF_RIGHTUP,0,0,None,None)

	def moveMouseToObj(self):
		obj = self.getObjectFromList()
		if obj:
			api.moveMouseToNVDAObject(obj)
			api.setMouseObject(obj)
			return (True)
		return(False)
