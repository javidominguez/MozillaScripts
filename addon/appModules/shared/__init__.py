# Mozilla Scripts version 1.4 (Dec-2017)
# Shared code for both appmodules
# Author Javi Dominguez <fjavids@gmail.com>
# License GNU GPL

from datetime import datetime, timedelta
from threading import Timer
import speech
import controlTypes
import api
import addonHandler

addonHandler.initTranslation()

def focusAlertPopup(alertPopup, SETFOCUS = True):
	if alertPopup.role != controlTypes.ROLE_ALERT:
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

def getAlertText(alertPopup):
	alertText = alertPopup.name if alertPopup.name else alertPopup.description if alertPopup.description else alertPopup.displayText if alertPopup.displayText else ""
	for obj in alertPopup.recursiveDescendants:
		objText = obj.name if obj.name else obj.description if obj.description else obj.displayText if obj.displayText else ""
		if not obj.isFocusable and objText not in alertText:
			alertText = "%s %s" % (alertText, objText)
	return alertText
	