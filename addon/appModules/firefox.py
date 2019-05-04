# Mozilla Apps Enhancements add-on for NVDA
#This file is covered by the GNU General Public License.
#See the file COPYING.txt for more details.
#Copyright (C) 2017 Javi Dominguez <fjavids@gmail.com>

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
from urlparse import urlparse
import re
import shared

addonHandler.initTranslation()

class AppModule(firefox.AppModule):

	tbDialog = None

	#TRANSLATORS: category for Firefox input gestures
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
		if re.match(".*notification.*|.*alert.*", ";".join(obj.IA2Attributes.values()).lower()):
			try:
				isPopup = obj.IA2Attributes["id"] == "notification-popup"
			except (KeyError, AttributeError):
				isPopup = False
			if self.inMainWindow() and isPopup:
				if shared.focusAlertPopup(obj):
					Timer(0.75, nextHandler)
					return
			alertText = shared.getAlertText(obj)
			# Appends the domain of the page where it was when the alert originated.
			path = (("id", "nav-bar"), ("id", "urlbar"), ("class", "urlbar-input textbox-input",))
			url = shared.searchObject(path)
			if url and url.value:
				url = url.value if "://" in url.value else "None://"+url.value
				domain = urlparse(url).hostname if url else ""
				if domain and domain not in alertText: alertText = "%s\n\n%s" % (alertText, domain)
			shared.notificationsDialog.registerFirefoxNotification((datetime.now(), alertText))
		nextHandler()

	def script_status(self, gesture):
		if not self.inMainWindow():
			#TRANSLATORS: message spoken by NVDA when the focus is not in the main Firefox window
			ui.message(_("Not available here"))
			return
		group = shared.searchAmongTheChildren(("tag", "tabpanels"), api.getForegroundObject())
		if group:
			for propertyPage in filter(lambda o: o.role == controlTypes.ROLE_PROPERTYPAGE, group.children):
				try:
					obj = filter(lambda o: o.role == controlTypes.ROLE_STATUSBAR, propertyPage.children)[0]
					break
				except IndexError:
					pass
			try:
				ui.message(obj.name)
			except NameError:
				#TRANSLATORS: message spoken when there is no status bar in Firefox
				ui.message (_("Status bar not found"))
			else:
				if scriptHandler.getLastScriptRepeatCount() == 1:
					if api.copyToClip(obj.name):
						#TRANSLATORS: message spoken when an item hast just been copied to the clipboard
						ui.message(_("Copied to clipboard"))
			return
		#TRANSLATORS: Firefox status bar not found
		ui.message (_("Status bar not found"))
	#TRANSLATORS: message shown in Input gestures dialog for this script
	script_status.__doc__ = _("Reads the status bar. If pressed twice quickly, copies it to clipboard.")

	def script_url(self, gesture):
		if not self.inMainWindow():
			#TRANSLATORS: message spoken by NVDA when the focus is not in the main Firefox window
			ui.message(_("Not available here"))
			return
		path = (("id", "nav-bar"), ("id", "urlbar"), ("id", "identity-box",))
		secInfoButton = shared.searchObject(path)
		if secInfoButton:
			securInfo = secInfoButton.description # This has changed in FF 57. Keeping this line for compatibility with earlier versions.
			try: # This one is for FF 57 and later.
				securInfo = secInfoButton.firstChild.next.name if secInfoButton.firstChild.next.IA2Attributes["id"] == "connection-icon" else ""
				if securInfo:
					owner = " ".join([o.name for o in filter(lambda o: o.role == controlTypes.ROLE_STATICTEXT, secInfoButton.recursiveDescendants)])
					securInfo = "%s, %s" % (owner, securInfo) if owner else securInfo
			except:
				pass
			#TRANSLATORS: this connection is using http, not https
			securInfo  = _("Insecure connection") if not securInfo   else securInfo  
			url = secInfoButton.next.value
			ui.message("%s (%s)" % (url, securInfo))
			if scriptHandler.getLastScriptRepeatCount() == 1:
				if api.copyToClip(url):
					#TRANSLATORS: message spoken when an item hast just been copied to the clipboard
					ui.message(_("Copied to clipboard"))
			return
		#TRANSLATORS: message spoken when addres bar could not be found
		ui.message (_("Address not found"))
	#TRANSLATORS: description shown in input gestures dialog for this script
	script_url.__doc__ = _("Reads the page address. If pressed twice quickly, copies it to clipboard.")

	def script_toolsBar(self, gesture):
		if not self.inMainWindow() and api.getForegroundObject().appModule.productName != "NVDA":
			#TRANSLATORS: message spoken by NVDA when the focus is not in the main Firefox window
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
		#TRANSLATORS: message spoken when Firefox toolbar is not found
		ui.message (_("Tool bar not found"))
	#TRANSLATORS: documentation shown in the input gestures dialog for this script
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
		if not shared.notificationsDialog.isEmpty():
			if scriptHandler.getLastScriptRepeatCount() == 1:
				# Gesture repeated twice shows the complete history in a dialog box.
				shared.notificationsDialog.firefoxPage()
				return
			else:
				# Gesture once says the last notification
				if shared.notificationsDialog.history["Firefox"]:
					timestamp, message = shared.notificationsDialog.history["Firefox"][0]
					ui.message("%s, %s" % (shared.elapsedFromTimestamp(timestamp), message))
					return
		# There is no notification in Firefox or Thunderbird
		ui.message(_("There is no notification"))
	#TRANSLATORS: documentation shown in the input gestures dialog for this script
	script_notifications.__doc__ = _("Reads the last notification and it takes the system focus to it if it is possible. By pressing two times quickly shows the history of notifications.")

	def script_focusDocument(self, gesture):
		if not self.inMainWindow():
			#TRANSLATORS: message spoken by NVDA when the focus is not in the main Firefox window
			ui.message(_("Not available here"))
			return
		group = shared.searchAmongTheChildren(("tag", "tabpanels"), api.getForegroundObject())
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
	#TRANSLATORS: documentation shown in the input gestures dialog for this script
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
		#TRANSLATORS: opened tabs in tabs dialog
		return tabs, "%d %s" % (len(tabs), _("Opened tabs"))

	def getButtonsDialog(self):
		fg = api.getForegroundObject()
		buttons = []
		for toolBar in filter(lambda o: o.role == controlTypes.ROLE_TOOLBAR, fg.children):
			buttons = buttons + filter(lambda o: o.role == controlTypes.ROLE_BUTTON, toolBar.children)
		#TRANSLATORS: Toolbar buttons dialog
		return buttons, _("Tool Bar Buttons")

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
		#TRANSLATORS: go button in toolbar buttons dialog
		self.goButton = wx.Button(self, goButtonID, _("&Go"))
		buttonsSizer.Add(self.goButton)
		self.Bind( wx.EVT_BUTTON, self.onGoButton, id=goButtonID)
		optionsButtonID = wx.NewId()
		#TRANSLATORS: options button in toolbar buttons dialog
		self.optionsButton = wx.Button(self, optionsButtonID, _("&Options"))
		buttonsSizer.Add(self.optionsButton)
		self.Bind( wx.EVT_BUTTON, self.onOptionsButton, id=optionsButtonID)
		#TRANSLATORS: close button in toolbar buttons dialog
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
