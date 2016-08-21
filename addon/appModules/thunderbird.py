# -*- coding: UTF-8 -*-

# Mozilla Thunderbird Scripts version 1.0dev (august 2016)
# Author Javi Dominguez <fjavids@gmail.com>

from nvdaBuiltin.appModules.thunderbird import *
from speech import pauseSpeech
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
