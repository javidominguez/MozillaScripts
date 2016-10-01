# Mozilla Thunderbird Scripts version 1.0.2 (Sept 2016)
# Author Javi Dominguez <fjavids@gmail.com>
# License GNU GPL

from nvdaBuiltin.appModules.thunderbird import *
from speech import pauseSpeech
from time import time
from NVDAObjects.IAccessible.mozilla import BrokenFocusedState
import appModuleHandler
import addonHandler
import controlTypes
import api
import ui
import scriptHandler
import winUser

addonHandler.initTranslation()

class AppModule(appModuleHandler.AppModule):
	lastIndex = 0

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		if obj.role == controlTypes.ROLE_EDITABLETEXT:
			try:
				if obj.IA2Attributes["xml-roles"] == "searchbox":
					setattr(obj, "pointedObj", None)
					obj.description = _("(Press down arrow to display more options)")
					clsList.insert(0, SearchBox)
			except KeyError, AttributeError:
				pass
		if obj.role == controlTypes.ROLE_TREEVIEWITEM:
			try:
				if obj.parent.IA2Attributes["id"] == "threadTree":
					setattr(obj, "getDocument", self.isDocument)
					clsList.insert(0, ThreadTree)
			except KeyError, AttributeError:
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
	# Translators: Message presented in input help mode.
	script_readAddressField.__doc__ = _("Reads the sender and recipients of the message. If pressed twice quickly, opens the options menu.")

	def script_messageSubject (self, gesture):
		if self.isDocument():
			obj = filter(lambda o: o.role == controlTypes.ROLE_UNKNOWN, self.getPropertyPage().children)[1]
			try:
				ui.message(obj.children[0].name)
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

	def addressField(self, index, rightClick):
		if self.isDocument():
			fields = []
			for item in filter(lambda o: o.role == controlTypes.ROLE_UNKNOWN, self.getPropertyPage().children):
				try:
					fields.append(item.children[0].children[0])
				except IndexError:
					pass
			if index >= len(fields):
				return()
			try:
				ui.message(",".join([o.name for o in fields[index].parent.children]))
			except (IndexError, AttributeError):
				ui.message(_("Not found"))
			if rightClick:
				api.moveMouseToNVDAObject(fields[index].children[0].children[1])
				api.setMouseObject(fields[index].children[0].children[1])
				winUser.mouse_event(winUser.MOUSEEVENTF_RIGHTDOWN,0,0,None,None)
				winUser.mouse_event(winUser.MOUSEEVENTF_RIGHTUP,0,0,None,None)
				pauseSpeech(True)
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
		"kb:Control+Shift+6": "messageDate"
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
				self.pointedObj = self.parent.parent.firstChild
				gesture.send()
				return()
		self.readCheckButton()

	def script_previousOption(self, gesture):
		if not self.pointedObj:
			api.setNavigatorObject(self)
			ui.message(controlTypes.roleLabels[self.role])
			if self.value:
				ui.message(self.value)
			return()
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
			except:
				pass
			try:
				if not self.pointedObj or self.pointedObj == self.parent.parent.firstChild or "titlebar" in self.pointedObj.IA2Attributes["id"]:
					self.pointedObj = self.parent.parent.firstChild
					gesture.send()
					return()
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

	def readPreviewPane(self, obj):
		obj = obj.firstChild
		while obj and time() < self.timeout:
			if obj.firstChild:
				self.readPreviewPane(obj)
			elif obj.name:
				ui.message(obj.name)
			obj = obj.next

	__gestures = {
		"kb:Space": "readPreviewPane"
	}
	