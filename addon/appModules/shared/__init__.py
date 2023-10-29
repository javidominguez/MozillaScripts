# Mozilla Apps Enhancements add-on for NVDA
#This file is covered by the GNU General Public License.
#See the file COPYING.txt for more details.
#Copyright (C) 2017 Javi Dominguez <fjavids@gmail.com>

from datetime import datetime, timedelta
from gui import guiHelper
from NVDAObjects.IAccessible import IAccessible
from threading import Timer
import addonHandler
import api
import controlTypes
import gui
import re
import speech
import wx

addonHandler.initTranslation()

def focusAlertPopup(alertPopup, SETFOCUS = True):
	if alertPopup.role != controlTypes.Role.ALERT:
		return False
	obj = alertPopup.firstChild
	while obj and not obj.isFocusable:
		obj = obj.next
	if obj:
		if api.getFocusObject() == obj:
			return True
		if SETFOCUS: # Else returns True to indicate that popup is focusable but does not perform the action.
			obj.scrollIntoView()
			obj.setFocus()
			api.setFocusObject(obj)
		speech.speakObject(alertPopup)
		Timer(0.05, speech.cancelSpeech)
		return True
	return False

def elapsedFromTimestamp(timestamp):
	delta = datetime.now()-timestamp
	d = delta.days
	if d == 1:
		#TRANSLATORS: an event happened yesterday
		return _("Yesterday")
	if d > 1:
		#TRANSLATORS: an event happened %d days ago
		return _("%d days ago") % d
	h, r = divmod(delta.seconds, 3600)
	m, s = divmod(r, 60)
	if h == 1:
		#TRANSLATORS: an event happened an hour ago
		return _("About an hour ago")
	elif h > 1:
		#TRANSLATORS: an event happened %d hours ago
		return _("About %d hours ago") % h
	if m == 1:
		#TRANSLATORS: an event happened a minute ago
		return _("About a minute ago")
	elif m > 1:
		#TRANSLATORS: an event happened %d minutes ago
		return _("About %d minutes ago") % m
	if s == 1:
		#TRANSLATORS: an event happened a second ago
		return _("a second ago")
	elif s > 1:
		#TRANSLATORS: an event happened %d seconds ago
		return _("%d seconds ago") % s

def getAlertText(alertPopup):
	alertText = alertPopup.name if alertPopup.name else alertPopup.description if alertPopup.description else alertPopup.displayText if alertPopup.displayText else ""
	extendedAlertText = alertText
	for obj in alertPopup.recursiveDescendants:
		objText = obj.name if obj.name else obj.description if obj.description else obj.displayText if obj.displayText else ""
		extendedAlertText = "%s %s" % (extendedAlertText, objText)
		if obj.role == controlTypes.Role.STATICTEXT and objText not in alertText:
			alertText = "%s %s" % (alertText, objText)
	#TRANSLATORS: the notification text could not be read
	return alertText if alertText else extendedAlertText if extendedAlertText else _("Couldn't capture the text of this notification")

def searchObject(path, startAtObject=None):
	obj = startAtObject if startAtObject else api.getForegroundObject()
	for milestone in path:
		obj = searchAmongTheChildren(milestone, obj)
		if not obj:
			return
	return obj

def searchAmongTheChildren(id, into):
	if not into:
		return(None)
	key, value = id
	obj = into.firstChild
	if hasattr(obj, "IA2Attributes") and key in obj.IA2Attributes.keys():
		if re.match(value, obj.IA2Attributes[key]):
			return(obj)
	while obj:
		if hasattr(obj, "IA2Attributes") and key in obj.IA2Attributes.keys():
			if re.match(value, obj.IA2Attributes[key]):
				break
		obj = obj.next
	return(obj)

class TabPanel(wx.Panel):

	def __init__(self, parent, lbLabel):
		wx.Panel.__init__(self, parent=parent)
		sizer = guiHelper.BoxSizerHelper(self, wx.VERTICAL)
		self.listBox  = sizer.addLabeledControl(lbLabel, wx.ListBox, size=(300,60))
		self.text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(300, 75), value = "")
		sizer.addItem(self.text)
		self.listBox.Bind(wx.EVT_LISTBOX, self.onListBox)
		self.listBox.Bind(wx.EVT_KEY_DOWN, self.onKeyDown)
		self.text.Bind(wx.EVT_KEY_DOWN, self.onKeyDown)
		self.Parent.Bind(wx.EVT_KEY_DOWN, self.onKeyDown)
		self.TopLevelParent.Bind(wx.EVT_ACTIVATE, self.onActivate)

	def onMenuRefresh(self, event):
		self.updateList()

	def onMenuDelete(self, event):
		self._deleteCurrentItem()

	def onMenuClear(self, event):
		self.TopLevelParent.history[self.Parent.GetPageText(self.Parent.Selection)] = []
		self.updateList()

	def onActivate(self, event):
		if event.GetActive():
			self.updateList()
		event.Skip()

	def onKeyDown(self, event):
		# Refresh list
		if event.GetKeyCode() == wx.WXK_F5:
			self.updateList()
		# Context menu
		elif event.GetKeyCode() == wx.WXK_WINDOWS_MENU and event.EventObject == self.listBox:
			menu = wx.Menu()
			item = menu.Append(wx.ID_ANY, _("Refresh	F5"))
			self.Bind(wx.EVT_MENU, self.onMenuRefresh, item)
			item = menu.Append(wx.ID_ANY, _("Delete item	Supr"))
			self.Bind(wx.EVT_MENU, self.onMenuDelete, item)
			item = menu.Append(wx.ID_ANY, _("Clear all"))
			self.Bind(wx.EVT_MENU, self.onMenuClear, item)
			self.listBox.PopupMenu(menu, self.listBox.ScreenPosition)
		# Delete list item
		elif event.GetKeyCode() == wx.WXK_DELETE and event.EventObject == self.listBox:
			self._deleteCurrentItem()
		# Close window
		elif event.GetKeyCode() == wx.WXK_ESCAPE:
			self.TopLevelParent.Hide()
		event.Skip()

	def onListBox(self, event):
		index = self.listBox.Selection
		self.text.Clear()
		try:
			self.text.SetValue(self.TopLevelParent.history[self.Parent.GetPageText(self.Parent.Selection)][index][1])
		except IndexError:
			pass

	def updateList(self):
		if not self.TopLevelParent.history[self.Parent.GetPageText(self.Parent.Selection)]:
			self.listBox.SetItems([_("There is no notification")])
			self.text.Clear()
			self.text.Enabled = False
		else:
			self.listBox.SetItems(["%s, %s" % (elapsedFromTimestamp(i[0]), i[1].split("\n")[0]) for i in self.TopLevelParent.history[self.Parent.GetPageText(self.Parent.Selection)]])
			self.text.Enabled = True
		self.text.SetValue(self.TopLevelParent.history[self.Parent.GetPageText(self.Parent.Selection)][0][1])
		self.listBox.SetSelection(0)
		self.listBox.SetFocus()

	def _deleteCurrentItem(self):
		index = self.listBox.Selection
		try:
			self.TopLevelParent.history[self.Parent.GetPageText(self.Parent.Selection)].pop(index)
		except IndexError:
			pass
		self.listBox.Delete(index)
		self.text.Clear()
		try:
			self.listBox.SetSelection(index)
		except:
			index = index-1
			self.listBox.SetSelection(index)
		if self.listBox.IsEmpty():
			self.updateList()
		else:
			self.text.SetValue(self.TopLevelParent.history[self.Parent.GetPageText(self.Parent.Selection)][index][1])

class NotificationsHistoryDialog(wx.Dialog):

	def __init__(self, parent):
		super(NotificationsHistoryDialog, self).__init__(parent, title=_("Mozilla notifications"))
		self.history = {"Firefox":[], "Thunderbird":[]}
		self.notebook = wx.Notebook(self, style=wx.NB_TOP)
		firefoxPage = TabPanel(self.notebook, lbLabel = _("Firefox notifications"))
		self.notebook.AddPage(firefoxPage, "Firefox")
		thunderbirdPage = TabPanel(self.notebook, lbLabel = _("Thunderbird notifications"))
		self.notebook.AddPage(thunderbirdPage, "Thunderbird")
		sizer = guiHelper.BoxSizerHelper(self, wx.VERTICAL)
		sizer.addItem(self.notebook)
		self.notebook.SetSelection(0)
		self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.onPageChanged)
		# The dialog is created but remains hidden until it is invoked.
		self.Show(False)

	def onPageChanged(self, event):
		self.notebook.CurrentPage.updateList()
		event.Skip()

	def registerFirefoxNotification(self, item):
		if item not in self.history["Firefox"]:
			self.history["Firefox"].insert(0, item)
			return True
		return False

	def registerThunderbirdNotification(self, item):
		if item not in self.history["Thunderbird"]:
			self.history["Thunderbird"].insert(0, item)
			return True
		return False

	def isEmpty(self):
		for k in self.history:
			if self.history[k]: return False
		return True

	def firefoxPage(self):
		self._showPage(0)

	def thunderbirdPage(self):
		self._showPage(1)

	def _showPage(self, page=0):
		self.notebook.SetSelection(page)
		gui.mainFrame.prePopup()
		self.Show(True)
		self.Centre()
		gui.mainFrame.postPopup()

notificationsDialog = NotificationsHistoryDialog(gui.mainFrame)
