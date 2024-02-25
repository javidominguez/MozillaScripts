# Mozilla Apps Enhancements add-on for NVDA
#This file is covered by the GNU General Public License.
#See the file COPYING.txt for more details.
#Copyright (C) 2017 - 2023 Javi Dominguez <fjavids@gmail.com>

from nvdaBuiltin.appModules import thunderbird
from scriptHandler import script
from time import time, sleep
from comtypes.gen.ISimpleDOM import ISimpleDOMDocument
from datetime import datetime
from keyboardHandler import KeyboardInputGesture
from gui import NVDASettingsDialog
from gui.settingsDialogs import SettingsPanel
from tones import beep

try:
	from NVDAObjects.IAccessible.mozilla import BrokenFocusedState as IAccessible
except ImportError:
	from NVDAObjects.IAccessible import IAccessible

import addonHandler
import api
import config
import controlTypes
import globalCommands
import globalVars
import gui
import scriptHandler
import speech
import treeInterceptorHandler
import ui
import winUser
import wx

from . import shared

confspec = {
	"automaticMessageReading": "boolean(default=True)"
}
config.conf.spec['thunderbird']=confspec

addonHandler.initTranslation()

class AppModule(thunderbird.AppModule):

	#TRANSLATORS: category for Thunderbird input gestures
	scriptCategory = _("mozilla Thunderbird")

	speechOnDemand = {"speakOnDemand": True} if hasattr(speech.speech.SpeechMode, "onDemand") else {}

	def __init__(self, *args, **kwargs):
		super(thunderbird.AppModule, self).__init__(*args, **kwargs)
		self.lastIndex = 0
		self.Dialog = None
		self.messageHeadersCache = dict()
		self.docCache = None
		self.previewPane = None
		NVDASettingsDialog.categoryClasses.append(ThunderbirdPanel)

		if int(self.productVersion.split(".")[0]) < 115:
			self.terminate()
			raise RuntimeError(_("The addon Mozilla Apps Enhancements is not compatible with this version of Thunderbird. The application module will be temporarily disabled."))

	def terminate(self):
		NVDASettingsDialog.categoryClasses.remove(ThunderbirdPanel)

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		# Overlay list of messages
		if obj.role == controlTypes.Role.TREEVIEWITEM or obj.role == controlTypes.Role.TABLEROW:
			try:
				if obj.parent:
					if obj.parent.IA2Attributes["xml-roles"] == "treegrid":
						clsList.insert(0, ThreadTree)
			except KeyError:
				pass
			except AttributeError:
				pass
		elif  obj.role == controlTypes.Role.LISTITEM:
			try:
				if obj.IA2Attributes["id"].startswith("threadTree-row"):
					clsList.insert(0, ThreadTree)
			except (KeyError, AttributeError):
				pass
		# Tabs
		elif obj.role == controlTypes.Role.TAB:
			if obj.parent.role == controlTypes.Role.TABCONTROL:
				if hasattr(obj.parent, "IA2Attributes") and "id" in obj.parent.IA2Attributes:
					if obj.parent.IA2Attributes["id"] in ("tabmail-tabs","event-grid-tabs"):
						clsList.insert(0, Tab)
		elif obj.role == 8:
			if obj.parent and hasattr(obj.parent, "IA2Attributes") and "id" in obj.parent.IA2Attributes and obj.parent.IA2Attributes["id"] == "quickFilterBarContainer":
				clsList.insert(0, QuickFilter)

	def _get_statusBar(self):
		return shared.searchObject((("container-live-role","status"),))

	def event_nameChange(self, obj, nextHandler):
		if obj.role == controlTypes.Role.DOCUMENT:
			self.previewPane = obj
		nextHandler()

	def event_gainFocus(self, obj, nextHandler):
		if obj.role == controlTypes.Role.BUTTON and obj.parent.role == controlTypes.Role.TABLECOLUMNHEADER:
				try:
					if "id" in obj.IA2Attributes:
						#TRANSLATORS: Indicates the table column in which the focused control is located
						obj.description = _("Column {pos}").format(
							pos = int(obj.parent.IA2Attributes["table-cell-index"])+1
						)
				except:
					pass
		nextHandler()

	def event_focusEntered(self, obj, nextHandler):
		if obj.role == controlTypes.Role.TOOLBAR and obj.firstChild.role == controlTypes.Role.TABCONTROL:
			obj.isPresentableFocusAncestor = False
		# Presentation of the table header where the columns are managed
		if obj.role == controlTypes.Role.GROUPING:
			obj.isPresentableFocusAncestor = False
		if obj.role == controlTypes.Role.TABLE:
			if hasattr(obj, "IA2Attributes") and "class" in obj.IA2Attributes and obj.IA2Attributes["class"] == "tree-table some-selected":
				obj.isPresentableFocusAncestor = False
		if obj.role == controlTypes.Role.TABLECOLUMNHEADER and obj.firstChild.role == controlTypes.Role.BUTTON:
			obj.isPresentableFocusAncestor = False
		if obj.role == controlTypes.Role.TABLEROW:
			focus = api.getFocusObject()
			if focus.role == controlTypes.Role.BUTTON and focus.parent.role == controlTypes.Role.TABLECOLUMNHEADER:
				obj.role = controlTypes.Role.TABLEHEADER
				obj.isPresentableFocusAncestor = True
		# End of table header presentation
		try:
			if set(["containingDocument","containingApplication"]) < set([r.relationType for r in obj._IA2Relations]):
				if obj.objectWithFocus().role == controlTypes.Role.DOCUMENT:
					speech.cancelSpeech()
		except NotImplementedError:
			pass
		if obj.role == controlTypes.Role.SECTION and hasattr(obj, "IA2Attributes") and "id" in obj.IA2Attributes and obj.IA2Attributes["id"] == "quickFilterBarContainer":
			obj.role = controlTypes.Role.FORM
			obj.isPresentableFocusAncestor = True
		if obj.role == controlTypes.Role.LIST and hasattr(obj, "IA2Attributes") and "id" in obj.IA2Attributes and obj.IA2Attributes["id"] == "unifiedToolbarContent":
			obj.isPresentableFocusAncestor = False
		nextHandler()

	def event_documentLoadComplete(self, obj, nextHandler):
		focus = api.getFocusObject()
		if isinstance(focus, ThreadTree) and controlTypes.State.COLLAPSED not in focus.states and config.conf["thunderbird"]["automaticMessageReading"]:
			api.setFocusObject(obj)
			treeInterceptor = treeInterceptorHandler.getTreeInterceptor(obj)
			api.setFocusObject(focus)
			if treeInterceptor:
				try:
					info = treeInterceptor.makeTextInfo("all")
				except:
					pass
				else:
					ui.message(
					text=info.text,
					brailleText="\n".join((api.getFocusObject().name, info.text)))
		nextHandler()

	def event_alert(self, obj, nextHandler):
		if obj.role == controlTypes.Role.ALERT:
			alertText = obj.name if obj.name else obj.description if obj.description else obj.displayText if obj.displayText else ""
			if shared.focusAlertPopup(obj, False if  self.isComposing() else True):
				return
			notificationLog = (datetime.now(), alertText)
			if notificationLog not in shared.notificationsDialog.history["Thunderbird"]:
				# Sometimes there are duplicate notifications. Is checked before storing in the history.
				shared.notificationsDialog.registerThunderbirdNotification(notificationLog )
		nextHandler()

	@script(**speechOnDemand)
	def script_toggleAutomaticMessageReading(self, gesture):
		config.conf["thunderbird"]["automaticMessageReading"] = not config.conf["thunderbird"]["automaticMessageReading"]
		ui.message(_("Automatic reading of the message is {state}").format(
		state = _("on") if config.conf["thunderbird"]["automaticMessageReading"] else _("off")))
	#TRANSLATORS: message shown in Input gestures dialog for this script
	script_toggleAutomaticMessageReading.__doc__ = _("On/off automatic reading of the message preview panel.")

	@script(**speechOnDemand)
	def script_readAddressField(self, gesture):
		try:
			index = int(gesture.keyName[-1])-1
		except AttributeError:
			index = int(gesture.mainKeyName[-1])-1
		twice = True if (scriptHandler.getLastScriptRepeatCount() == 1 and index == self.lastIndex) or "alt" in gesture.modifierNames else False
		if  self.isComposing():
			self.addressFieldOnComposing(index, twice)
		else:
			self.addressField(index, twice)
		self.lastIndex = index

	def script_attachments (self, gesture):
		doc = self.isDocument()
		if doc and controlTypes.State.READONLY in doc.states:
			try:
				attachmentToggleButton = next(filter(lambda o: o.role == controlTypes.Role.TOGGLEBUTTON, doc.parent.parent.children))
			except StopIteration:
				#TRANSLATORS: there are no attachments in this message
				ui.message(_("There are No attachments"))
				return
			ui.message(attachmentToggleButton.next.name)
			if controlTypes.State.PRESSED not in attachmentToggleButton.states:
				attachmentToggleButton.doAction()
			else:
				obj = attachmentToggleButton.next
				while obj:
					if obj.role == controlTypes.Role.LIST:
						obj.firstChild.doAction()
						return
					obj = obj.next
			return
		gesture.send()
	#TRANSLATORS: message shown in Input gestures dialog for this script
	script_attachments.__doc__ = _("Brings the focus to the list of attachments, if any.")

	def script_focusDocument(self, gesture):
		try:
			self.isDocument().setFocus()
		except:
			try:
				if self.previewPane and self.previewPane.role == controlTypes.Role.DOCUMENT:
					self.previewPane.setFocus()
			except:
				pass
	#TRANSLATORS: message shown in Input gestures dialog for this script
	script_focusDocument.__doc__ = _("Brings the focus to the text of the open message.")

	@script(**speechOnDemand)
	def script_notifications(self, gesture):
		obj = self.getPropertyPage().simpleLastChild.simplePrevious
		if obj.role == controlTypes.Role.ALERT:
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
		if self.docCache and self.docCache.name:
			doc = self.docCache
		else:
			doc = self.isDocument()
			self.docCache = doc
		if doc:
			url = doc.IAccessibleObject.QueryInterface(ISimpleDOMDocument).url
			if (url, doc.IA2UniqueID) in self.messageHeadersCache:
				addresses = self.messageHeadersCache[(url, doc.IA2UniqueID)]
			else:
				try:
					messageHeader = next(filter(lambda o: o.role == controlTypes.Role.LANDMARK, doc.parent.parent.children))
				except StopIteration:
					ui.message(_("Not found"))
					return
				sender = shared.searchObject((
				('id', 'headerSenderToolbarContainer'),
				('id', 'expandedfromRow'),
				('class', 'multi-recipient-row'),
				('class', 'recipients-list'),
				('id', 'fromRecipient0')),
				messageHeader)
				toRecipients = shared.searchObject((
				('id', 'expandedtoRow'),
				('id', 'expandedtoBox'),
				('class', 'recipients-list')),
				messageHeader)
				addresses = [sender]+toRecipients.children if toRecipients else [sender]
				ccRecipients = shared.searchObject((
				('id', 'expandedccRow'),
				('id', 'expandedccBox'),
				('class', 'recipients-list')),
				messageHeader)
				addresses = addresses+ccRecipients.children if ccRecipients else addresses
				if addresses[0]: self.messageHeadersCache[(url, doc.IA2UniqueID)] = addresses
			try:
				o = addresses[index]
			except IndexError:
				ui.message(_("There are no more recipients"))
				return
			if o:
				ui.message ("{} {}".format(o.parent.name, o.simpleFirstChild.name))
			else:
				ui.message(_("Not found"))
			if rightClick:
				api.moveMouseToNVDAObject(o)
				api.setMouseObject(o)
				winUser.mouse_event(winUser.MOUSEEVENTF_RIGHTDOWN,0,0,None,None)
				winUser.mouse_event(winUser.MOUSEEVENTF_RIGHTUP,0,0,None,None)
				speech.pauseSpeech(True)

	def addressFieldOnComposing(self, index, focus):
		headers = shared.searchObject((
		('id', 'composeContentBox'),
		('id', 'MsgHeadersToolbar')))
		if not headers:
			ui.message(_("Not found"))
			return
		addresses = []
		obj = headers.firstChild
		while obj:
			try:
				if obj.labeledBy: addresses.append(obj)
				if obj.labeledBy.IA2Attributes['id'] == 'subjectLabel': addresses.pop(-1)
			except:
				pass
			try:
				if obj.IA2Attributes['id'] == 'extraAddressRowsArea': addresses.extend(obj.children)
			except:
				pass
			obj = obj.next
		if index >= len(addresses):
			ui.message(_("There are no more recipients"))
			return
		if focus:
			obj = addresses[index]
			try:
				if addresses[index].previous.IA2Attributes['tag'] == 'mail-address-pill':
					obj = addresses[index].previous
			except:
				pass
			api.moveMouseToNVDAObject(obj)
			winUser.mouse_event(winUser.MOUSEEVENTF_LEFTDOWN,0,0,None,None)
			winUser.mouse_event(winUser.MOUSEEVENTF_LEFTUP,0,0,None,None)
		else:
			speech.speakObject(addresses[index], reason=controlTypes.OutputReason.FOCUS)
		return

	def isDocument(self):
		for ancestor in filter(lambda o: o.role == 56, globalVars.focusAncestors):
			try:
				frame = next(filter(lambda o: o.role == 115 and o.firstChild.role == controlTypes.Role.DOCUMENT, ancestor.children))
				return frame.firstChild
			except StopIteration:
				pass
		return None

	def isComposing(self):
		identity = shared.searchObject((
		('id', 'composeContentBox'),
		('id', 'MsgHeadersToolbar'),
		('id', 'msgIdentity')))
		return True if identity else False

	def getPropertyPage(self):
		fg = api.getForegroundObject()
		propertyPage = shared.searchObject((
		("id","tabpanelcontainer"),
		("id","mailContent")))
		if propertyPage : 				return propertyPage 
		# When message is opened in a new window there are not a property page. Address fields hang directly from foreground.
		return fg

	__gestures = {
		"kb:Control+Shift+1": "readAddressField",
		"kb:Control+Shift+2": "readAddressField",
		"kb:Control+Shift+3": "readAddressField",
		"kb:Control+Shift+4": "readAddressField",
		"kb:Control+Shift+5": "readAddressField",
		"kb:Control+Shift+6": "readAddressField",
		"kb:Control+Shift+7": "readAddressField",
		"kb:Control+Shift+8": "readAddressField",
		"kb:Control+Shift+9": "readAddressField",
		"kb:Alt+Control+Shift+1": "readAddressField",
		"kb:Alt+Control+Shift+2": "readAddressField",
		"kb:Alt+Control+Shift+3": "readAddressField",
		"kb:Alt+Control+Shift+4": "readAddressField",
		"kb:Alt+Control+Shift+5": "readAddressField",
		"kb:Alt+Control+Shift+6": "readAddressField",
		"kb:Alt+Control+Shift+7": "readAddressField",
		"kb:Alt+Control+Shift+8": "readAddressField",
		"kb:Alt+Control+Shift+9": "readAddressField",
		"kb:Control+Shift+A": "attachments",
		"kb:NVDA+F6": "focusDocument",
		"kb:NVDA+Control+N": "notifications"
	}

class ThreadTree(IAccessible):
	#TRANSLATORS: category for Thunderbird input gestures
	scriptCategory = _("mozilla Thunderbird")

	speechOnDemand = {"speakOnDemand": True} if hasattr(speech.speech.SpeechMode, "onDemand") else {}

	@property
	def document(self):
		doc = self.appModule.previewPane
		if not doc or not doc.role:
			return None
		else:
			return doc

	def initOverlayClass(self):
		self.setConversation()

	def setConversation(self):
		if controlTypes.State.COLLAPSED in self.states:
			state = _("Collapsed conversation")
		elif controlTypes.State.EXPANDED in self.states:
			state = _("Expanded conversation")
		else:
			state = None
		if state:
			self.name = "{}, {}".format(
				state,
				super(ThreadTree, self).name)

	def event_stateChange(self):
		self.setConversation()
		super(ThreadTree, self).event_stateChange()

	def event_nameChange(self):
		self.setConversation()
		super(ThreadTree, self).event_nameChange()

	@script(**speechOnDemand)
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
		api.setNavigatorObject(obj)
		if obj.firstChild:
			obj.value = obj.firstChild.name
		obj.states = set()
		speech.speakObject(obj, reason=controlTypes.OutputReason.FOCUS)

	@script(**speechOnDemand)
	def script_readPreviewPane(self, gesture):
		doc = self.document
		if doc:
			self.readPreviewPane(doc)
		else:
			if controlTypes.State.COLLAPSED in self.states:
				#TRANSLATORS: The conversation is collapsed, the user is prompted to expand it to read the messages
				ui.message(_("Expand the conversation to read the messages"))
			else:
				#TRANSLATORS: the preview pane is not available yet
				ui.message(_("Preview pane is not active or message has not been loaded yet"))
	#TRANSLATORS: message shown in Input gestures dialog for this script
	script_readPreviewPane.__doc__ = _("In message list, reads the selected message without leaving the list.")

	def readPreviewPane(self, obj):
		api.setFocusObject(obj)
		api.setFocusObject(self)
		try:
			info= obj.treeInterceptor.makeTextInfo("all")
		except:
			pass
		else:
			ui.message("{title}{body}".format(
			title = obj.name+"\n" if controlTypes.State.COLLAPSED in self.states else "",
			body=info.text))

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

class Tab(IAccessible):

	@script(gesture="kb:rightArrow")
	def script_nextTab(self, gesture):
		obj = self.next
		if not obj: obj = self.parent.firstChild
		obj.doAction()

	@script(gesture="kb:leftArrow")
	def script_previousTab(self, gesture):
		obj = self.previous
		if not obj: obj = self.parent.lastChild
		obj.doAction()

class QuickFilter(IAccessible):

	@script(gesture="kb:Enter")
	def script_enterKey(self, gesture):
		KeyboardInputGesture.fromName("F6").send()

class ThunderbirdPanel(SettingsPanel):
	#TRANSLATORS: Settings panel title
	title=_("Mozilla Thunderbird")
	def makeSettings(self, sizer):
		self.automaticMessageReading =wx.CheckBox(self, wx.NewId(), label=_("Automatically read message preview pane"))
		self.automaticMessageReading.SetValue(config.conf["thunderbird"]["automaticMessageReading"])
		sizer.Add(self.automaticMessageReading,border=10,flag=wx.BOTTOM)

	def onSave(self):
		config.conf["thunderbird"]["automaticMessageReading"] = self.automaticMessageReading.GetValue()
