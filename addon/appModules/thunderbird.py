# Mozilla Thunderbird Scripts version 1.1.0 (apr 2017)
# Author Javi Dominguez <fjavids@gmail.com>
# License GNU GPL

from nvdaBuiltin.appModules import thunderbird
from time import time
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

addonHandler.initTranslation()

class AppModule(thunderbird.AppModule):
	scriptCategory = _("mozilla Thunderbird")
	lastIndex = 0
	Dialog = None

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		# Overlay search box in fast filtering bar
		if obj.role == controlTypes.ROLE_EDITABLETEXT:
			try:
				if obj.IA2Attributes["xml-roles"] == "searchbox":
					setattr(obj, "pointedObj", None)
					obj.description = _("(Press down arrow to display more options)")
					clsList.insert(0, SearchBox)
			except KeyError:
				pass
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

	def script_readAddressField(self, gesture):
		try:
			index = int(gesture.keyName[-1])-1
		except AttributeError:
			index = int(gesture.mainKeyName[-1])-1
		rightClick = False
		if scriptHandler.getLastScriptRepeatCount() == 1 and index == self.lastIndex:
			rightClick = True
		self.addressField(index, rightClick)
		self.lastIndex = index

	def script_messageSubject (self, gesture):
		if self.isDocument():
			obj = filter(lambda o: o.role == controlTypes.ROLE_UNKNOWN, self.getPropertyPage().children)[1]
			try:
				ui.message(obj.getChild(0).name)
			except (IndexError, AttributeError):
				ui.message(_("Not found"))
		else:
			ui.message(_("you are not in a message window"))
	# Translators: Message presented in input help mode.
	script_messageSubject.__doc__ = _("Reads the subject of the message.")

	def script_messageDate (self, gesture):
		if self.isDocument():
			try:
				obj = filter(lambda o: o.role == controlTypes.ROLE_EDITABLETEXT and controlTypes.STATE_READONLY in o.states, self.getPropertyPage().children)[0]
				ui.message(obj.value)
			except (IndexError, AttributeError):
				ui.message(_("Not found"))
		else:
			ui.message(_("you are not in a message window"))
	# Translators: Message presented in input help mode.
	script_messageDate.__doc__ = _("Reads date of the message.")

	def script_manageColumns(self, gesture):
		try:
			columnHeaders = filter(lambda o: o.role == controlTypes.ROLE_TABLE, self.getPropertyPage().children)[0].getChild(0).children
		except IndexError:
			try:
				columnHeaders = filter(lambda o: o.role == controlTypes.ROLE_TREEVIEW, self.getPropertyPage().children)[-1].getChild(0).children
			except IndexError:
				ui.message(_("You are not in a list of messages"))
				return
		if len(columnHeaders) == 1:
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
	# Translators: Message presented in input help mode.
	script_manageColumns.__doc__ = _("Allows you to change the order of the columns in the messages list")

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
				ui.message(",".join([o.name for o in fields[index].parent.children]))
			except (IndexError, AttributeError):
				ui.message(_("Not found"))
			if rightClick:
				api.moveMouseToNVDAObject(fields[index].getChild(0).getChild(1))
				api.setMouseObject(fields[index].getChild(0).getChild(1))
				winUser.mouse_event(winUser.MOUSEEVENTF_RIGHTDOWN,0,0,None,None)
				winUser.mouse_event(winUser.MOUSEEVENTF_RIGHTUP,0,0,None,None)
				speech.pauseSpeech(True)
		else:
			ui.message(_("you are not in a message window"))

	def isDocument(self):
		doc = None
		for frame in filter(lambda o: o.role == controlTypes.ROLE_INTERNALFRAME, self.getPropertyPage().children):
			try:
				doc = filter(lambda o: o.role == controlTypes.ROLE_DOCUMENT, frame.children)[0]
			except IndexError:
				pass
		return(doc)

	def getPropertyPage(self):
		fg = api.getForegroundObject()
		try:
			propertyPages = filter(lambda o: o.role == controlTypes.ROLE_PROPERTYPAGE, filter(lambda o: o.role == controlTypes.ROLE_GROUPING, fg.children)[0].children)
			return(propertyPages[0])
		except IndexError:
			# When message is opened in a new window there are not a property page. Address fields hang directly from foreground.
			return(fg)

	__gestures = {
		"kb:Control+Shift+1": "readAddressField",
		"kb:Control+Shift+2": "readAddressField",
		"kb:Control+Shift+3": "readAddressField",
		"kb:Control+Shift+4": "readAddressField",
		"kb:Control+Shift+5": "messageSubject",
		"kb:Control+Shift+6": "messageDate",
		"kb:NVDA+H": "manageColumns"
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
		except KeyError:
			pass
		except AttributeError:
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
		except KeyError:
			pass
		except AttributeError:
			pass
		while not isToolBarButton :
			try:
				self.pointedObj = self.pointedObj.simplePrevious
				if self.pointedObj.IA2Attributes["tag"] == "toolbarbutton":
					isToolBarButton = True
					if "qfb-qs-" in self.pointedObj.IA2Attributes["id"]:
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
				ui.message(_("uncheck"))
			else:
				ui.message(_("check"))
			ui.message(self.pointedObj.name)
			api.moveMouseToNVDAObject(self.pointedObj)
			api.setMouseObject(self.pointedObj)
			winUser.mouse_event(winUser.MOUSEEVENTF_LEFTDOWN,0,0,None,None)
			winUser.mouse_event(winUser.MOUSEEVENTF_LEFTUP,0,0,None,None)

	def readCheckButton(self):
		if controlTypes.STATE_PRESSED in self.pointedObj.states:
			state = _("checked")
		else:
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
	scriptCategory = _("mozilla Thunderbird")

	def script_moveToColumn(self, gesture):
		try:
			index = int(gesture.keyName[-1])-1
		except AttributeError:
			index = int(gesture.mainKeyName[-1])-1
		if index >= self.childCount:
			ui.message(_("There are not more columns"))
			return
		obj = self.getChild(index)
		if not obj.name:
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
				ui.message(_("Expand the conversation to display messages"))
			else:
				ui.message(_("Preview pane is not active or message has not been loaded yet"))
	# Translators: Message presented in input help mode.
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
		super(manageColumnsDialog, self).__init__(parent, title=_("Manage columns"))
		# Build interface
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		self.listBox = wx.ListBox(self, wx.NewId(), style=wx.LB_SINGLE, size=(100, 60))
		mainSizer.Add(self.listBox, proportion=8)
		buttonsSizer = wx.BoxSizer(wx.HORIZONTAL)
		upButtonID = wx.NewId()
		self.upButton = wx.Button(self, upButtonID, _("&up"))
		buttonsSizer.Add(self.upButton)
		downButtonID = wx.NewId()
		self.downButton = wx.Button(self, downButtonID, _("&down"))
		buttonsSizer.Add(self.downButton)
		optionsButtonID = wx.NewId()
		self.optionsButton = wx.Button(self, optionsButtonID, _("&options"))
		buttonsSizer.Add(self.optionsButton)
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
			ui.message(_("Can't move %s, it is already the first column.") % self.columns[c].name)
			return
		if self.dragAndDrop(c-1, c):
			self.listBox.SetSelection(c-1)
			self.upButton.SetFocus()
			self.Show()
			self.Center()
			ui.message(_("%s before %s") % (self.columns[c-1].name, self.columns[c].name))
		else:
			beep(150, 100)

	def onDownButton(self, event):
		c = self.listBox.GetSelections()[0]
		if c+1 == len(self.columns):
			ui.message(_("Can't move %s, it is already the last column.") % self.columns[c].name)
			return
		if self.dragAndDrop(c, c+1):
			self.listBox.SetSelection(c+1)
			self.downButton.SetFocus()
			self.Show()
			self.Center()
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
			ui.message(_("Folder has changed, return to %s to manage columns or restart this dialog") % self.folder[:-22])
			return False
		self.Hide()
		try:
			x = self.columns[hIndex1].location[0]+self.columns[hIndex1].location[2]/2
			y = self.columns[hIndex1].location[1]+self.columns[hIndex1].location[3]/2
		except TypeError:
			return False 
		if api.getDesktopObject().objectFromPoint(x,y) != self.columns[hIndex1]:
			return False
		winUser.setCursorPos(x, y)
		if winUser.getKeyState(winUser.VK_LBUTTON)&32768:
			winUser.mouse_event(winUser.MOUSEEVENTF_LEFTUP,0,0,None,None)
		winUser.mouse_event(winUser.MOUSEEVENTF_LEFTDOWN,0,1,None,None)
		x = self.columns[hIndex2].location[0]+self.columns[hIndex2].location[2]+1
		y = self.columns[hIndex2].location[1]+self.columns[hIndex2].location[3]/2
		winUser.setCursorPos(x, y)
		winUser.mouse_event(winUser.MOUSEEVENTF_LEFTUP,0,0,None,None)
		tmp = self.columns[hIndex1]
		self.columns[hIndex1] = self.columns[hIndex2]
		self.columns[hIndex2] = tmp
		self.update()
		return True
