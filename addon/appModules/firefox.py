# Mozilla Firefox Scripts version 1.0.4 (Oct 2016)
# Author Javi Dominguez <fjavids@gmail.com>
# License GNU GPL

from nvdaBuiltin.appModules import firefox
from NVDAObjects.IAccessible.mozilla import Dialog, IAccessible
import addonHandler
import scriptHandler
import globalCommands
import controlTypes
import api
import ui
import winUser
import speech
import gui
import wx
from datetime import datetime, timedelta
from threading import Timer

addonHandler.initTranslation()

class AppModule(firefox.AppModule):

	tbDialog = None
	notificationHistory = []

	scriptCategory = _("mozilla Firefox")

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		if obj.role == controlTypes.ROLE_ALERT:
			alertText = ""
			for child in obj.recursiveDescendants:
				if child.name:
					if not child.isFocusable and child.name not in alertText:
						alertText = "%s %s" % (alertText, child.name)
			obj.description = alertText
			clsList.insert(0, alertPopup)

	def event_alert(self, obj, nextHandler):
		alertText = obj.name if obj.name else obj.description if obj.description else obj.displayText if obj.displayText else _("Couldn't capture the text of this notification")
		if self.inMainWindow():
			if self.focusAlertPopup(obj):
				Timer(0.5, nextHandler)
				return
		self.notificationHistory.append((datetime.now(), alertText))
		nextHandler()

	def script_status(self, gesture):
		if not self.inMainWindow():
			ui.message(_("Not available here"))
			return
		group = self.searchAmongTheChildren(("tag", "tabpanels"), api.getForegroundObject())
		if group:
			for propertyPage in filter(lambda o: o.role == controlTypes.ROLE_PROPERTYPAGE, group.children):
				try:
					obj = filter(lambda o: o.role == controlTypes.ROLE_STATUSBAR, propertyPage.children)[0]
					break
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
			return
		ui.message (_("Status bar not found"))
	script_status.__doc__ = _("Reads the status bar. If pressed twice quickly, copies it to clipboard.")

	def script_url(self, gesture):
		if not self.inMainWindow():
			ui.message(_("Not available here"))
			return
		path = (("id", "nav-bar"), ("id", "urlbar"), ("id", "identity-box",))
		secInfoButton = self.searchObject(path)
		if secInfoButton:
			securInfo = secInfoButton.description
			url = secInfoButton.next.value
			ui.message(_("Page address is: %s (%s)") % (url, securInfo))
			if scriptHandler.getLastScriptRepeatCount() == 1:
				if api.copyToClip(url):
					ui.message(_("Copied to clipboard"))
			return
		ui.message (_("Address not found"))
	script_url.__doc__ = _("Reads the page address. If pressed twice quickly, copies it to clipboard.")

	def script_toolsBar(self, gesture):
		if not self.inMainWindow() and api.getForegroundObject().appModule.productName != "NVDA":
			ui.message(_("Not available here"))
			return
		if not self.tbDialog:
			self.tbDialog = toolsBarDialog(gui.mainFrame)
		if scriptHandler.getLastScriptRepeatCount() == 0:
			items, title = self.getTabsDialog()
		elif scriptHandler.getLastScriptRepeatCount() == 1: 
			items, title = self.getButtonsDialog()
		if items:
			self.tbDialog.update(items, title)
			if not self.tbDialog.IsShown():
				gui.mainFrame.prePopup()
				self.tbDialog.Show()
				self.tbDialog.Centre()
				gui.mainFrame.postPopup()
			return
		ui.message (_("Tool bar not found"))
	script_toolsBar.__doc__ = _("Shows a list of opened tabs. If pressed twice quickly, shows buttons of tool bar.")


	def script_openNotification(self, gesture):
		if not self.inMainWindow():
			ui.message(_("Not available here"))
			return
		obj = api.getForegroundObject().simpleFirstChild
		if obj.role == controlTypes.ROLE_ALERT:
			if api.getFocusObject().parent == obj: # Already focused
				ui.message(obj.description)
				speech.speakObject(api.getFocusObject())
				return
			if self.focusAlertPopup(obj):
				return
		if self.notificationHistory:
			def elapsedFromTimestamp(timestamp):
				delta = datetime.now()-timestamp
				d = -delta.days
				h, r = divmod(delta.seconds, 3600)
				m, s = divmod(r, 60)
				if d == 1:
					return "Yesterday"
				if d > 1:
					return "%d days ago" % d
				if h == 1:
					return _("About an hour ago")
				elif h > 1:
					return _("About %d hours ago") % h
				if m == 1:
					return _("About a minute ago")
				elif m > 1:
					return _("About %d minutes ago") % m
				if s == 1:
					return _("a second ago")
				elif s > 1:
					return _("%d seconds ago") % s
			if scriptHandler.getLastScriptRepeatCount() == 1:
				ui.browseableMessage("\n".join(["%s: %s" % (elapsedFromTimestamp(notification[0]), notification[1]) for notification in self.notificationHistory]), _("Notification History"))
			else:
				ui.message(_("Last alert, %s: %s") % (elapsedFromTimestamp(self.notificationHistory[-1][0]), self.notificationHistory[-1][1]))
		else:
			ui.message(_("There is no notification"))
	script_openNotification.__doc__ = _("Reads the last notification and it takes the system focus to it if it is possible. By pressing two times quickly shows the history of notifications.")

	def script_focusDocument(self, gesture):
		if not self.inMainWindow():
			ui.message(_("Not available here"))
			return
		group = self.searchAmongTheChildren(("tag", "tabpanels"), api.getForegroundObject())
		if group:
			for propertyPage in filter(lambda o: o.role == controlTypes.ROLE_PROPERTYPAGE, group.children):
				try:
					doc = filter(lambda o: o.role == controlTypes.ROLE_INTERNALFRAME and controlTypes.STATE_FOCUSABLE in o.states, propertyPage.children)[0].children[0]
					break
				except IndexError:
					pass
			try:
				api.setFocusObject(doc)
				try:
					doc.treeInterceptor.passThrough = False
				except AttributeError:
					pass
				ui.message("%s %s" % (controlTypes.roleLabels[doc.role], doc.name))
			except NameError:
				pass
	script_focusDocument.__doc__ = _("Brings the focus to the document")

	def focusAlertPopup(self, alertPopup):
		if True:
			obj = alertPopup.firstChild
			while obj and not obj.isFocusable:
				obj = obj.next
			if obj:
				obj.scrollIntoView()
				obj.setFocus()
				Timer(0.1, speech.cancelSpeech)
				return True
		return False

	def getTabsDialog(self):
		tabs = ""
		fg = api.getForegroundObject()
		for toolBar in filter(lambda o: o.role == controlTypes.ROLE_TOOLBAR, fg.children):
			try:
				tabControl = filter(lambda o: o.role == controlTypes.ROLE_TABCONTROL, toolBar.children)[0]
			except IndexError:
				pass
			else:
				tabs = filter(lambda o: o.role == controlTypes.ROLE_TAB, tabControl.children)
		return(tabs, "%d %s" % (len(tabs), _("Opened tabs")))

	def getButtonsDialog(self):
		fg = api.getForegroundObject()
		buttons = []
		for toolBar in filter(lambda o: o.role == controlTypes.ROLE_TOOLBAR, fg.children):
			buttons = buttons + filter(lambda o: o.role == controlTypes.ROLE_BUTTON, toolBar.children)
		return(buttons, _("Tool Bar Buttons"))

	def searchObject(self, path):
		obj = api.getForegroundObject()
		for milestone in path:
			obj = self.searchAmongTheChildren(milestone, obj)
			if not obj:
				return(None)
		return(obj)

	def searchAmongTheChildren(self, id, into):
		if not into:
			return(None)
		key, value = id
		obj = into.getChild(0)
		if key in obj.IA2Attributes.keys():
			if obj.IA2Attributes[key] == value:
				return(obj)
		while obj:
			if key in obj.IA2Attributes.keys():
				if obj.IA2Attributes[key] == value:
					break
			obj = obj.next
		return(obj)

	def inMainWindow(self):
		try:
			if api.getForegroundObject().IA2Attributes["id"] != "main-window":
				return(False)
		except (AttributeError, KeyError):
			return(False)
		return(True)

	__gestures = {
		"kb(desktop):NVDA+End": "status",
		"kb(laptop):NVDA+Shift+End": "status",
		"kb:NVDA+F8": "toolsBar",
		"kb(desktop):NVDA+A": "url",
		"kb(laptop):NVDA+Control+A": "url",
		"kb:NVDA+Control+N": "openNotification",
		"kb:NVDA+F6": "focusDocument"
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
		try:
			selected = [controlTypes.STATE_SELECTED in item.states for item in self.items].index(True)
		except ValueError:
			selected = 0
		self.listBox.Select(selected)
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
			obj.scrollIntoView()
			api.moveMouseToNVDAObject(obj)
			api.setMouseObject(obj)
			return (True)
		return(False)

class alertPopup(Dialog):
	pass

class alertPopupChild(IAccessible):

	def script_title(self, gesture):
		ui.message("titulo de la alerta")
		ui.message(self.container.description)

	__gestures = {
	filter(lambda g: g[1].__name__ == "script_title", globalCommands.commands._gestureMap.iteritems())[0][0]: "title"
	}