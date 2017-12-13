# Mozilla Firefox Scripts version 1.4.1 (Dec-2017)
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
from datetime import datetime
from threading import Timer
import shared

addonHandler.initTranslation()

class AppModule(firefox.AppModule):

	tbDialog = None
	notificationHistory = []

	scriptCategory = _("mozilla Firefox")

	def event_alert(self, obj, nextHandler):
		try:
			if obj.IA2Attributes["id"] == "customizationui-widget-panel":
				# Firefox add-on panel
				speech.cancelSpeech()
				api.setFocusObject(obj.simpleFirstChild)
				nextHandler()
				return
		except (KeyError, AttributeError):
			pass
		try:
			isNotification = "notification" in "".join(obj.IA2Attributes.values()).lower()\
			or "alert" in "".join(obj.IA2Attributes.values()).lower()
		except:
			isNotification = False
		if isNotification:
			try:
				isPopup = obj.IA2Attributes["id"] == "notification-popup"
			except (KeyError, AttributeError):
				isPopup = False
			if self.inMainWindow() and isPopup:
				if shared.focusAlertPopup(obj):
					Timer(0.75, nextHandler)
					return
			alertText = "%s" % shared.getAlertText(obj)
			notificationLog = (datetime.now(), alertText.replace("\n", "\t"))
			if notificationLog not in self.notificationHistory:
				self.notificationHistory.append(notificationLog)
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
			securInfo = secInfoButton.description # This has changed in FF 57. Keeping this line for compatibility with earlier versions.
			try: # This one is for FF 57 and later.
				securInfo = secInfoButton.getChild(1).name if secInfoButton.getChild(1).IA2Attributes["id"] == "connection-icon" else ""
				if securInfo:
					owner = " ".join([o.name for o in filter(lambda o: o.role == controlTypes.ROLE_STATICTEXT, secInfoButton.recursiveDescendants)])
					securInfo = "%s, %s" % (owner, securInfo) if owner else securInfo
			except:
				pass
			securInfo  = _("Insecure connection") if not securInfo   else securInfo  
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


	def script_notifications(self, gesture):
		obj = api.getForegroundObject().simpleFirstChild
		if obj.role == controlTypes.ROLE_ALERT:
			if api.getFocusObject().parent == obj: # Already focused
				speech.speakObject(obj)
				speech.speakObject(api.getFocusObject())
				return
			if shared.focusAlertPopup(obj):
				speech.speakObject(api.getFocusObject())
				return
		if self.notificationHistory:
			if scriptHandler.getLastScriptRepeatCount() == 1:
				ui.browseableMessage("\n".join(["%s: %s" % (shared.elapsedFromTimestamp(notification[0]), notification[1]) for notification in self.notificationHistory]), "%s - Firefox" % _("Notification History"))
			else:
				ui.message(_("Last alert, %s: %s") % (shared.elapsedFromTimestamp(self.notificationHistory[-1][0]), self.notificationHistory[-1][1]))
		else:
			ui.message(_("There is no notification"))
	script_notifications.__doc__ = _("Reads the last notification and it takes the system focus to it if it is possible. By pressing two times quickly shows the history of notifications.")

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
		return tabs, "%d %s" % (len(tabs), _("Opened tabs"))

	def getButtonsDialog(self):
		fg = api.getForegroundObject()
		buttons = []
		for toolBar in filter(lambda o: o.role == controlTypes.ROLE_TOOLBAR, fg.children):
			buttons = buttons + filter(lambda o: o.role == controlTypes.ROLE_BUTTON, toolBar.children)
		return buttons, _("Tool Bar Buttons")

	def searchObject(self, path):
		obj = api.getForegroundObject()
		for milestone in path:
			obj = self.searchAmongTheChildren(milestone, obj)
			if not obj:
				return
		return obj

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
				return False
		except (AttributeError, KeyError):
			return False
		return True

	__gestures = {
		"kb(desktop):NVDA+End": "status",
		"kb(laptop):NVDA+Shift+End": "status",
		"kb:NVDA+F8": "toolsBar",
		"kb(desktop):NVDA+A": "url",
		"kb(laptop):NVDA+Control+A": "url",
		"kb:NVDA+Control+N": "notifications",
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
			return True
		return False
