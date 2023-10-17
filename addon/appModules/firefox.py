# Mozilla Apps Enhancements add-on for NVDA
#This file is covered by the GNU General Public License.
#See the file COPYING.txt for more details.
#~ #Copyright (C) 2017-2019 Javi Dominguez <fjavids@gmail.com>

from logHandler import log
import addonHandler
try: # Compatibility with the DeveloperToolkit addon
	dtk = next(filter(lambda a: a.name == "DeveloperToolkit", addonHandler.getRunningAddons()))
except StopIteration: # DeveloperToolkit is not running. Then, the firefox class is imported from the core
	try:
		from nvdaBuiltin.appModules.firefox import AppModule
	except ModuleNotFoundError:
		from appModuleHandler import AppModule
else: # DeveloperToolkit is running. Try to import the class from the DeveloperToolkit folder.
	log.warning("The Developer toolkit addon has been detected.")
	import appModules
	appModules.__path__.insert(0, dtk.path+"\\appModules")
	try:
		from dtkFirefox import AppModule
		log.warning("Compatibility OK")
	except ImportError: # The version of DeveloperToolkit that is running is not ready for compatibility with this addon.
		from nvdaBuiltin.appModules.firefox import AppModule
		raise Warning ("Compatibility failed. Not found dtkFirefox from Developer toolkit\nIt is likely that Mozilla Apps Enhancements and Developer's toolkit does not work well together")
	appModules.__path__.pop(0)

try:
	from NVDAObjects.IAccessible.mozilla import Dialog, IAccessible
except ImportError:
	from NVDAObjects.IAccessible import Dialog, IAccessible
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
from urllib.parse  import urlparse
import re
from . import shared

addonHandler.initTranslation()

class AppModule(AppModule):

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
			for propertyPage in filter(lambda o: o.role == controlTypes.Role.PROPERTYPAGE, group.children):
				try:
					obj = next(filter(lambda o: o.role == controlTypes.Role.STATUSBAR, propertyPage.children))
					break
				except StopIteration:
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
		ffVersion = int(self.productVersion.split(".")[0])
		if ffVersion < 70:
			path = (("id", "nav-bar"), ("id", "urlbar"), ("id", "identity-box",))
		elif ffVersion < 76:
			path = (("id", "nav-bar"), ("id", "identity-box"), ("id", "identity-icon"))
		elif ffVersion < 87:
			path = (("id", "nav-bar"), ("id", "identity-box"))
		else:
			path = (("id", "nav-bar"), ("class","urlbar-input-box"), ("id","urlbar-input"))
		secInfoButton = shared.searchObject(path)
		if secInfoButton:
			securInfo = secInfoButton.description # This has changed in FF 57. Keeping this line for compatibility with earlier versions.
			try: # This one is for FF 57 and later.
				try: # FF 57 to 69
					securInfo = secInfoButton.firstChild.next.name if secInfoButton.firstChild.next.IA2Attributes["id"] == "connection-icon" else ""
					if securInfo:
						owner = " ".join([o.name for o in filter(lambda o: o.role == controlTypes.Role.STATICTEXT, secInfoButton.recursiveDescendants)])
						securInfo = "%s, %s" % (owner, securInfo) if owner else securInfo
				except AttributeError: # FF 70 and above 
					securInfo = secInfoButton.name
			except:
				pass
			#TRANSLATORS: this connection is using http, not https
			securInfo  = _("Insecure connection") if not securInfo   else securInfo  
			if ffVersion < 76:
				url = secInfoButton.next.value if ffVersion < 70 else secInfoButton.parent.next.firstChild.value
				ui.message("%s (%s)" % (url, securInfo))
			elif ffVersion < 87:
				url = secInfoButton.next.firstChild.value
				ui.message(url)
			else:
				url = secInfoButton.value
				ui.message(url)
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
		if scriptHandler.getLastScriptRepeatCount() == 0:
			self.showToolbarDialog(False)
		elif scriptHandler.getLastScriptRepeatCount() == 1:
			self.showToolbarDialog(True)
	#TRANSLATORS: documentation shown in the input gestures dialog for this script
	script_toolsBar.__doc__ = _("Shows a list of opened tabs. If pressed twice quickly, shows buttons of tool bar.")

	def script_toolsBar2(self, gesture):
		self.showToolbarDialog(True)
	#TRANSLATORS: documentation shown in the input gestures dialog for this script
	script_toolsBar2.__doc__ = _("Shows buttons of tool bar.")

	def showToolbarDialog(self, twice):
		if not self.inMainWindow() and api.getForegroundObject().appModule.productName != "NVDA":
			#TRANSLATORS: message spoken by NVDA when the focus is not in the main Firefox window
			ui.message(_("Not available here"))
			return
		if not self.tbDialog:
			self.tbDialog = toolsBarDialog(gui.mainFrame)
		if twice:
			items, title = self.getButtonsDialog()
		else:
			items, title = self.getTabsDialog()
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

	def script_notifications(self, gesture):
		obj = api.getForegroundObject().simpleFirstChild
		if obj.role == controlTypes.Role.ALERT:
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
			for propertyPage in filter(lambda o: o.role == controlTypes.Role.PROPERTYPAGE, group.children):
				try:
					doc = filter(lambda o: o.role == controlTypes.Role.INTERNALFRAME and controlTypes.State.FOCUSABLE in o.states, propertyPage.children)[0].children[0]
					break
				except IndexError:
					pass
			try:
				api.setFocusObject(doc)
				try:
					doc.treeInterceptor.passThrough = False
				except AttributeError:
					pass
				ui.message("%s %s" % (controlTypes.role._roleLabels[doc.role], doc.name))
			except NameError:
				pass
	#TRANSLATORS: documentation shown in the input gestures dialog for this script
	script_focusDocument.__doc__ = _("Brings the focus to the document")

	def getTabsDialog(self):
		tabs = ""
		fg = api.getForegroundObject()
		for toolBar in filter(lambda o: o.role == controlTypes.Role.TOOLBAR, fg.children):
			try:
				tabControl = next(filter(lambda o: o.role == controlTypes.Role.TABCONTROL, toolBar.children))
			except StopIteration:
				pass
			else:
				tabs = list(filter(lambda o: o.role == controlTypes.Role.TAB, tabControl.children))
		#TRANSLATORS: opened tabs in tabs dialog
		return tabs, "%d %s" % (len(tabs), _("Opened tabs"))

	def getButtonsDialog(self):
		fg = api.getForegroundObject()
		buttons = []
		for toolBar in filter(lambda o: o.role == controlTypes.Role.TOOLBAR and "id" in o.IA2Attributes and o.IA2Attributes["id"] != "TabsToolbar", fg.children):
			buttons = buttons + list(filter(lambda o: o.role == controlTypes.Role.BUTTON and controlTypes.State.OFFSCREEN not in o.states, toolBar.children))
		#TRANSLATORS: Toolbar buttons dialog
		return buttons, _("Tool Bar Buttons")

	def inMainWindow(self):
		fg = api.getForegroundObject()
		try:
			if fg.IA2Attributes["id"] == "main-window":
				return True
		except (AttributeError, KeyError):
			pass
		# As of Firefox 72, the IA2Attributes["id"]:"main-window" is no longer used
		try:
			if fg.IA2Attributes["tag"] == "body":
				return True
		except (AttributeError, KeyError):
			pass

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
			selected = [controlTypes.State.SELECTED in item.states for item in self.items].index(True)
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
		if self.getObjectFromList().role == controlTypes.Role.BUTTON:
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
