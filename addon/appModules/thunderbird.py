# Mozilla Apps Enhancements add-on for NVDA
#This file is covered by the GNU General Public License.
#See the file COPYING.txt for more details.
#Copyright (C) 2017 Javi Dominguez <fjavids@gmail.com>

from .py3compatibility import *
from nvdaBuiltin.appModules import thunderbird
from time import time, sleep
from datetime import datetime
from NVDAObjects.IAccessible.mozilla import BrokenFocusedState
from tones import beep
import addonHandler
import controlTypes
import api
import ui
import scriptHandler
import winUser
import speech
import gui
import wx
import globalCommands
from . import shared

addonHandler.initTranslation()

class AppModule(thunderbird.AppModule):

	#TRANSLATORS: category for Thunderbird input gestures
	scriptCategory = _("mozilla Thunderbird")

	def __init__(self, *args, **kwargs):
		super(thunderbird.AppModule, self).__init__(*args, **kwargs)
		self.lastIndex = 0
		self.Dialog = None

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		# Overlay search box in fast filtering bar
		if obj.role == controlTypes.ROLE_EDITABLETEXT:
			try:
				if ("xml-roles" in obj.IA2Attributes and obj.IA2Attributes["xml-roles"] == "searchbox") or ("class" in obj.parent.IA2Attributes  and obj.parent.IA2Attributes["class"] == "searchBox"):
					setattr(obj, "pointedObj", None)
					#TRANSLATORS: additional description for the search field
					obj.description = _("(Press down arrow to display more options)")
					clsList.insert(0, SearchBox)
			except AttributeError:
				pass
		# Overlay list of messages
		if obj.role == controlTypes.ROLE_TREEVIEWITEM or obj.role == controlTypes.ROLE_TABLEROW:
			try:
				if obj.parent:
					if obj.parent.IA2Attributes["id"] == "threadTree":
						setattr(obj, "getDocument", self.isDocument)
						clsList.insert(0, ThreadTree)
			except KeyError:
				pass
			except AttributeError:
				pass

	def event_alert(self, obj, nextHandler):
		if obj.role == controlTypes.ROLE_ALERT:
			alertText = obj.name if obj.name else obj.description if obj.description else obj.displayText if obj.displayText else ""
			if shared.focusAlertPopup(obj, False if  self.isComposing() else True):
				return
			notificationLog = (datetime.now(), alertText)
			if notificationLog not in shared.notificationsDialog.history["Thunderbird"]:
				# Sometimes there are duplicate notifications. Is checked before storing in the history.
				shared.notificationsDialog.registerThunderbirdNotification(notificationLog )
		nextHandler()

	def script_readAddressField(self, gesture):
		try:
			index = int(gesture.keyName[-1])-1
		except AttributeError:
			index = int(gesture.mainKeyName[-1])-1
		twice = True if scriptHandler.getLastScriptRepeatCount() == 1 and index == self.lastIndex else False
		if self.isComposing():
			self.addressFieldOnComposing(index, twice)
		else:
			self.addressField(index, twice)
		self.lastIndex = index

	def script_messageSubject (self, gesture):
		if self.isComposing():
			subject = shared.searchObject((
			("id","MsgHeadersToolbar"),
			("id","msgSubject"),
			("class","textbox-input")))
			if scriptHandler.getLastScriptRepeatCount() == 1:
				subject.setFocus()
			else:
				ui.message("%s %s" % (subject.name, subject.value if subject.value else _("empty")))
			return
		if self.isDocument():
			obj = filter(lambda o: o.role == controlTypes.ROLE_UNKNOWN, self.getPropertyPage().children)[1]
			try:
				ui.message(obj.firstChild.name)
			except (IndexError, AttributeError):
				#TRANSLATORS: cannot find subject
				ui.message(_("Not found"))
		else:
			#TRANSLATORS: message spoken if you try to read the subject out of a message window
			ui.message(_("you are not in a message window"))
	#TRANSLATORS: message shown in Input gestures dialog for this script
	script_messageSubject.__doc__ = _("Reads the subject of the message.")

	def script_messageDate (self, gesture):
		if self.isComposing():
			return
		if self.isDocument():
			try:
				obj = filter(lambda o: o.role == controlTypes.ROLE_EDITABLETEXT and controlTypes.STATE_READONLY in o.states, self.getPropertyPage().children)[0]
				ui.message(obj.value)
			except (IndexError, AttributeError):
				#TRANSLATORS: cannot find date
				ui.message(_("Not found"))
		else:
			#TRANSLATORS: message spoken if you try to read the date out of a message window
			ui.message(_("you are not in a message window"))
	#TRANSLATORS: message shown in Input gestures dialog for this script
	script_messageDate.__doc__ = _("Reads date of the message.")

	def script_manageColumns(self, gesture):
		try:
			columnHeaders = filter(lambda o: o.role == controlTypes.ROLE_TABLE, self.getPropertyPage().children)[0].firstChild.children
		except IndexError:
			try:
				columnHeaders = filter(lambda o: o.role == controlTypes.ROLE_TREEVIEW, self.getPropertyPage().children)[-1].firstChild.children
			except IndexError:
				#TRANSLATORS: message spoken if you want to manage columns out of messages list
				ui.message(_("You are not in a list of messages"))
				return
		if len(columnHeaders) == 1:
			#TRANSLATORS: this is a message list without column headers
			ui.message(_("Column headers not found"))
			return
		if not self.Dialog:
			self.Dialog = manageColumnsDialog(gui.mainFrame)
		self.Dialog.update(columnHeaders[:-1], columnHeaders[-1])
		if not self.Dialog.IsShown():
			gui.mainFrame.prePopup()
			self.Dialog.Show()
			self.Dialog.Centre()
			gui.mainFrame.postPopup()
	#TRANSLATORS: message shown in Input gestures dialog for this script
	script_manageColumns.__doc__ = _("Allows you to change the order of the columns in the messages list")

	def script_attachments (self, gesture):
		doc = self.isDocument()
		if doc and controlTypes.STATE_READONLY in doc.states:
			try:
				attachmentToggleButton = filter(lambda o: o.IA2Attributes["id"] == "attachmentToggle", self.getPropertyPage().children)[0]
			except IndexError:
				#TRANSLATORS: there are no attachments in this message
				ui.message(_("There are No attachments"))
				return
			ui.message(attachmentToggleButton.next.name)
			if controlTypes.STATE_PRESSED not in attachmentToggleButton.states:
				api.moveMouseToNVDAObject(attachmentToggleButton)
				winUser.mouse_event(winUser.MOUSEEVENTF_LEFTDOWN,0,0,None,None)
				winUser.mouse_event(winUser.MOUSEEVENTF_LEFTUP,0,0,None,None)
			else:
				self.getPropertyPage().children[-1].firstChild.setFocus()
			return
		gesture.send()
	#TRANSLATORS: message shown in Input gestures dialog for this script
	script_attachments.__doc__ = _("Brings the focus to the list of attachments, if any.")

	def script_focusDocument(self, gesture):
		try:
			self.isDocument().setFocus()
		except:
			pass
	#TRANSLATORS: message shown in Input gestures dialog for this script
	script_focusDocument.__doc__ = _("Brings the focus to the text of the open message.")

	def script_notifications(self, gesture):
		obj = self.getPropertyPage().simpleLastChild.simplePrevious
		if obj.role == controlTypes.ROLE_ALERT:
			if api.getFocusObject().parent == obj: # Already focused
				ui.message(shared.getAlertText(obj))
				speech.speakObject(api.getFocusObject())
				return
			if shared.focusAlertPopup(obj):
				return
		if not shared.notificationsDialog.isEmpty():
			if scriptHandler.getLastScriptRepeatCount() == 1:
				# Gesture repeated twice shows the complete history in a dialog box.
				shared.notificationsDialog.thunderbirdPage()
				return
			else:
				# Gesture once says the last notification
				if shared.notificationsDialog.history["Thunderbird"]:
					timestamp, message = shared.notificationsDialog.history["Thunderbird"][0]
					ui.message("%s, %s" % (shared.elapsedFromTimestamp(timestamp), message))
					return
		# There is no notification in Firefox or Thunderbird
		ui.message(_("There is no notification"))
	#TRANSLATORS: message shown in Input gestures dialog for this script
	script_notifications.__doc__ = _("Reads the last notification and it takes the system focus to it if it is possible. By pressing two times quickly shows the history of notifications.")

	def addressField(self, index, rightClick):
		if self.isDocument():
			fields = []
			for item in filter(lambda o: o.role == controlTypes.ROLE_UNKNOWN, self.getPropertyPage().children):
				try:
					fields.append(item.children[0].children[0])
				except IndexError:
					pass
			if index >= len(fields):
				return
			try:
				if int(self.productVersion.split(".")[0]) >= 68:
					ui.message(fields[index].parent.parent.name)
				ui.message(",".join([o.name for o in fields[index].parent.children]))
			except (IndexError, AttributeError):
				#TRANSLATORS: cannot find sender address
				ui.message(_("Not found"))
			if rightClick:
				if int(self.productVersion.split(".")[0]) < 68:
					obj = fields[index].firstChild.firstChild.next
				else:
					obj = fields[index].firstChild.firstChild
				api.moveMouseToNVDAObject(obj)
				api.setMouseObject(obj)
				winUser.mouse_event(winUser.MOUSEEVENTF_RIGHTDOWN,0,0,None,None)
				winUser.mouse_event(winUser.MOUSEEVENTF_RIGHTUP,0,0,None,None)
				speech.pauseSpeech(True)
		else:
			#TRANSLATORS: message spoken if you try to read the sender address out of a message window
			ui.message(_("you are not in a message window"))

	def addressFieldOnComposing(self, index, focus):
		sender = shared.searchObject((
		("id","MsgHeadersToolbar"),
		("id","msgIdentity")))
		if index == 0:
			if focus:
				api.moveMouseToNVDAObject(sender)
				winUser.mouse_event(winUser.MOUSEEVENTF_LEFTDOWN,0,0,None,None)
				winUser.mouse_event(winUser.MOUSEEVENTF_LEFTUP,0,0,None,None)
			else:
				ui.message("%s %s, %s" % (sender.name, sender.value, sender.keyboardShortcut))
		else:
			addressingWidget = shared.searchObject((
			("id","MsgHeadersToolbar"),
			("id","addressingWidget")))
			recipients = filter(lambda o: o.role == controlTypes.ROLE_COMBOBOX and o.firstChild.role == controlTypes.ROLE_EDITABLETEXT, addressingWidget.recursiveDescendants)
			if index > len(recipients):
				return
			if focus and controlTypes.STATE_FOCUSED not in recipients[index-1].firstChild.states:
				if controlTypes.STATE_EXPANDED in sender.states:
				# When the list of senders is expanded it cover the recipient widget. It must be collapsed before click in recipients.
					api.moveMouseToNVDAObject(sender)
					winUser.mouse_event(winUser.MOUSEEVENTF_LEFTDOWN,0,0,None,None)
					winUser.mouse_event(winUser.MOUSEEVENTF_LEFTUP,0,0,None,None)
				api.moveMouseToNVDAObject(recipients[index-1])
				winUser.mouse_event(winUser.MOUSEEVENTF_LEFTDOWN,0,0,None,None)
				winUser.mouse_event(winUser.MOUSEEVENTF_LEFTUP,0,0,None,None)
			else:
				ui.message("%s %s" % (recipients[index-1].name, recipients[index-1].firstChild.value if recipients[index-1].firstChild.value else _("empty")))

	def isDocument(self):
		doc = None
		for frame in filter(lambda o: o.role == controlTypes.ROLE_INTERNALFRAME, self.getPropertyPage().children):
			try:
				doc = filter(lambda o: o.role == controlTypes.ROLE_DOCUMENT, frame.children)[0]
			except IndexError:
				pass
		return doc

	def isComposing(self):
		return True if shared.searchAmongTheChildren(("id",".*compose.*"), api.getForegroundObject()) else False

	def getPropertyPage(self):
		fg = api.getForegroundObject()
		try:
			propertyPages = filter(lambda o: o.role == controlTypes.ROLE_PROPERTYPAGE, filter(lambda o: o.role == controlTypes.ROLE_GROUPING, fg.children)[0].children)
			return propertyPages[0]
		except IndexError:
			# When message is opened in a new window there are not a property page. Address fields hang directly from foreground.
			return fg

	__gestures = {
		"kb:Control+Shift+1": "readAddressField",
		"kb:Control+Shift+2": "readAddressField",
		"kb:Control+Shift+3": "readAddressField",
		"kb:Control+Shift+4": "readAddressField",
		"kb:Control+Shift+5": "messageSubject",
		"kb:Control+Shift+6": "messageDate",
		"kb:NVDA+H": "manageColumns",
		"kb:Control+Shift+A": "attachments",
		"kb:NVDA+F6": "focusDocument",
		"kb:NVDA+Control+N": "notifications"
	}

class SearchBox(BrokenFocusedState):

	def script_nextOption(self, gesture):
		if not self.pointedObj:
			self.pointedObj = self.parent.parent.firstChild
		self.pointedObj = self.pointedObj.simpleNext
		isToolBarButton = False
		try:
			if self.pointedObj.IA2Attributes["tag"] == "toolbarbutton":
				isToolBarButton = True
				if "qfb-qs-" in self.pointedObj.IA2Attributes["id"]:
					self.pointedObj.name = _("Search in ")+self.pointedObj.name
		except (KeyError, AttributeError):
			pass
		while not isToolBarButton :
			try:
				self.pointedObj = self.pointedObj.simpleNext
				if self.pointedObj.IA2Attributes["tag"] == "toolbarbutton":
					isToolBarButton = True
					if "qfb-qs-" in self.pointedObj.IA2Attributes["id"]:
						self.pointedObj.name = _("Search in ")+self.pointedObj.name
			except:
				pass
			if not self.pointedObj or self.pointedObj.role == controlTypes.ROLE_TREEVIEW:
				#TRANSLATORS: message spoken when leaving the search box in Thunderbird
				ui.message(_('Leaving search box'))
				self.pointedObj = self.parent.parent.firstChild
				gesture.send()
				return
		self.readCheckButton()

	def script_previousOption(self, gesture):
		if not self.pointedObj:
			api.setNavigatorObject(self)
			ui.message(controlTypes.roleLabels[self.role])
			if self.value:
				ui.message(self.value)
			return
		self.pointedObj = self.pointedObj.simplePrevious
		isToolBarButton = False
		try:
			if self.pointedObj.IA2Attributes["tag"] == "toolbarbutton":
				isToolBarButton = True
				if "qfb-qs-" in self.pointedObj.IA2Attributes["id"]:
					self.pointedObj.name = _("Search in ")+self.pointedObj.name
		except (KeyError, AttributeError):
			pass
		while not isToolBarButton :
			try:
				self.pointedObj = self.pointedObj.simplePrevious
				if self.pointedObj.IA2Attributes["tag"] == "toolbarbutton":
					isToolBarButton = True
					if "qfb-qs-" in self.pointedObj.IA2Attributes["id"]:
						#TRANSLATORS: Thunderbird search box name
						self.pointedObj.name = _("Search in ")+self.pointedObj.name
			except KeyError:
				pass
			except AttributeError:
				pass
			try:
				if not self.pointedObj or self.pointedObj == self.parent.parent.firstChild or "titlebar" in self.pointedObj.IA2Attributes["id"]:
					self.pointedObj = self.parent.parent.firstChild
					gesture.send()
					return
			except KeyError:
				pass
		self.readCheckButton()

	def script_pressButton(self, gesture):
		if self.pointedObj:
			if controlTypes.STATE_PRESSED in self.pointedObj.states:
				#TRANSLATORS: a button has been unchecked
				ui.message(_("uncheck"))
			else:
				#TRANSLATORS: a button has been checked
				ui.message(_("check"))
			ui.message(self.pointedObj.name)
			api.moveMouseToNVDAObject(self.pointedObj)
			api.setMouseObject(self.pointedObj)
			winUser.mouse_event(winUser.MOUSEEVENTF_LEFTDOWN,0,0,None,None)
			winUser.mouse_event(winUser.MOUSEEVENTF_LEFTUP,0,0,None,None)

	def readCheckButton(self):
		if controlTypes.STATE_PRESSED in self.pointedObj.states:
			#TRANSLATORS: a button is checked
			state = _("checked")
		else:
			#TRANSLATORS: a button is not checked
			state = _("not checked")
		if self.pointedObj.description:
			ui.message("%s, %s, %s" % (self.pointedObj.name, state, self.pointedObj.description))
		else:
			ui.message("%s, %s" % (self.pointedObj.name, state))
		api.setNavigatorObject(self.pointedObj)

	def event_caret(self):
		if self.pointedObj:
			api.setNavigatorObject(self)
			self.pointedObj = None
			ui.message(controlTypes.roleLabels[self.role])

	__gestures = {
	"kb:downArrow": "nextOption",
	"kb:upArrow": "previousOption",
	"kb:Enter": "pressButton"
	}

class ThreadTree(BrokenFocusedState):
	#TRANSLATORS: category for Thunderbird input gestures
	scriptCategory = _("mozilla Thunderbird")

	def script_moveToColumn(self, gesture):
		try:
			index = int(gesture.keyName[-1])-1
		except AttributeError:
			index = int(gesture.mainKeyName[-1])-1
		if index >= self.childCount:
			#TRANSLATORS: message spoken when there aren't more columns in the tree
			ui.message(_("There are not more columns"))
			return
		obj = self.getChild(index)
		if not obj.name:
			#TRANSLATORS: empty object name
			obj.name = _("empty")
		obj.states = None
		api.setNavigatorObject(obj)
		speech.speakObject(obj, reason=controlTypes.REASON_FOCUS)

	def script_readPreviewPane(self, gesture):
		doc = self.getDocument()
		if doc:
			self.timeout = time() + 1.0
			self.readPreviewPane(doc)
		else:
			if controlTypes.STATE_COLLAPSED in self.states:
				#TRANSLATORS: message spoken when a conversation is collapsed
				ui.message(_("Expand the conversation to display messages"))
			else:
				#TRANSLATORS: the preview pane is not available yet
				ui.message(_("Preview pane is not active or message has not been loaded yet"))
	#TRANSLATORS: message shown in Input gestures dialog for this script
	script_readPreviewPane.__doc__ = _("In message list, reads the selected message without leaving the list.")


	def readPreviewPane(self, obj):
		obj = obj.firstChild
		while obj and time() < self.timeout:
			if obj.firstChild:
				self.readPreviewPane(obj)
			elif obj.name:
				ui.message(obj.name)
			obj = obj.next

	__gestures = {
		# read preview pane
		"kb(desktop):NVDA+downArrow": "readPreviewPane",
		"kb(laptop):NVDA+A": "readPreviewPane",
		# Move to column
		"kb:NVDA+Control+1": "moveToColumn",
		"kb:NVDA+Control+2": "moveToColumn",
		"kb:NVDA+Control+3": "moveToColumn",
		"kb:NVDA+Control+4": "moveToColumn",
		"kb:NVDA+Control+5": "moveToColumn",
		"kb:NVDA+Control+6": "moveToColumn",
		"kb:NVDA+Control+7": "moveToColumn",
		"kb:NVDA+Control+8": "moveToColumn",
		"kb:NVDA+Control+9": "moveToColumn"
	}

class manageColumnsDialog(wx.Dialog):
	def __init__(self, parent):
		#TRANSLATORS: manage columns dialog title
		super(manageColumnsDialog, self).__init__(parent, title=_("Manage columns"))
		# Build interface
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		self.listBox = wx.ListBox(self, wx.NewId(), style=wx.LB_SINGLE, size=(100, 60))
		mainSizer.Add(self.listBox, proportion=8)
		buttonsSizer = wx.BoxSizer(wx.HORIZONTAL)
		upButtonID = wx.NewId()
		#TRANSLATORS: up button in columns dialog
		self.upButton = wx.Button(self, upButtonID, _("&up"))
		buttonsSizer.Add(self.upButton)
		downButtonID = wx.NewId()
		#TRANSLATORS: down button in columns dialog
		self.downButton = wx.Button(self, downButtonID, _("&down"))
		buttonsSizer.Add(self.downButton)
		optionsButtonID = wx.NewId()
		#TRANSLATORS: options button in the columns dialog
		self.optionsButton = wx.Button(self, optionsButtonID, _("&options"))
		buttonsSizer.Add(self.optionsButton)
		#TRANSLATORS: close button in the columns dialog
		cancelButton = wx.Button(self, wx.ID_CANCEL, _("Close"))
		buttonsSizer.Add(cancelButton)
		mainSizer.Add(buttonsSizer)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)
		self.Bind( wx.EVT_BUTTON, self.onUpButton, id=upButtonID)
		self.Bind( wx.EVT_BUTTON, self.onDownButton, id=downButtonID)
		self.Bind( wx.EVT_BUTTON, self.onOptionsButton, id=optionsButtonID)

	def update(self, columns=None, optionsButton=None):
		if columns:
			self.columns = columns
			self.folder = columns[0].windowText # To prevent errors if the user changes the folder while the dialog is open
			# The objects are sorted by their position on the screen, which not always corresponds to its index in children
			self.columns.sort(key=lambda o: o.location[0])
		if optionsButton:
			self.options = optionsButton
		self.listBox.SetItems([item.name for item in self.columns])
		self.listBox.SetSelection(0)

	def onUpButton(self, event):
		c = self.listBox.GetSelections()[0]
		if c == 0:
			#TRANSLATORS: the column can't be moved, it is already in the first position
			ui.message(_("Can't move %s, it is already the first column.") % self.columns[c].name)
			return
		if self.dragAndDrop(c-1, c):
			self.listBox.SetSelection(c-1)
			self.upButton.SetFocus()
			self.Show()
			self.Center()
			#TRANSLATORS: the selected column moves before another column
			ui.message(_("%s before %s") % (self.columns[c-1].name, self.columns[c].name))
		else:
			beep(150, 100)

	def onDownButton(self, event):
		c = self.listBox.GetSelections()[0]
		if c+1 == len(self.columns):
			#TRANSLATOR: this is the last column and can't be moved
			ui.message(_("Can't move %s, it is already the last column.") % self.columns[c].name)
			return
		if self.dragAndDrop(c, c+1):
			self.listBox.SetSelection(c+1)
			self.downButton.SetFocus()
			self.Show()
			self.Center()
			#TRANSLATORS: a column goes after another column
			ui.message(_("%s after %s") % (self.columns[c+1].name, self.columns[c].name))
		else:
			beep(150, 100)

	def onOptionsButton(self, event):
		self.Hide()
		self.options.scrollIntoView()
		api.setNavigatorObject(self.options)
		try:
			scriptHandler.executeScript(globalCommands.commands.script_review_activate, None)
		except:
			beep(150, 100)

	def dragAndDrop(self, hIndex1, hIndex2):
		if self.columns[0].windowText != self.folder:
			#TRANSLATORS: the folder content has changed while this dialog was opened
			ui.message(_("Folder has changed, return to %s to manage columns or restart this dialog") % self.folder[:-22])
			return False
		self.Hide()
		try:
			x = int(self.columns[hIndex1].location[0]+self.columns[hIndex1].location[2]/2)
			y = int(self.columns[hIndex1].location[1]+self.columns[hIndex1].location[3]/2)
		except TypeError:
			return False 
		if api.getDesktopObject().objectFromPoint(x,y) != self.columns[hIndex1]:
			return False
		winUser.setCursorPos(x, y)
		if winUser.getKeyState(winUser.VK_LBUTTON)&32768:
			winUser.mouse_event(winUser.MOUSEEVENTF_LEFTUP,0,0,None,None)
		winUser.mouse_event(winUser.MOUSEEVENTF_LEFTDOWN,0,1,None,None)
		d = self.columns[hIndex2].location[0]+self.columns[hIndex2].location[2]+1
		# Move slowly because if it do not the Left mouse button will be unlocked before the cursor reaches the destination. 
		while x < d:
			x = d if x > d else x+20
			winUser.setCursorPos(x, y)
			sleep(0.002)
		winUser.mouse_event(winUser.MOUSEEVENTF_LEFTUP,0,0,None,None)
		tmp = self.columns[hIndex1]
		self.columns[hIndex1] = self.columns[hIndex2]
		self.columns[hIndex2] = tmp
		self.update()
		return True
