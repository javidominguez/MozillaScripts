# Mozilla Apps Enhancements add-on for NVDA
#This file is covered by the GNU General Public License.
#See the file COPYING.txt for more details.
# Copyright (C) 2017-2019 Javi Dominguez <fjavids@gmail.com>

from gui import guiHelper, NVDASettingsDialog
from gui.settingsDialogs import SettingsPanel
from core import restart
import globalPluginHandler
import config
import wx
import os

class MozillaPanel(SettingsPanel):
	# TRANSLATORS: title for the Mozilla Apps Enhancements settings category
	title = _("Mozilla Apps Enhancements")

	def makeSettings(self, sizer):
		helper = guiHelper.BoxSizerHelper(self, sizer=sizer)

		label = wx.StaticText(self, wx.ID_ANY,
		# TRANSLATORS: Selecting appModules
		_("Select the application modules you want to load."))
		helper.addItem(label)
		sizerDir = wx.BoxSizer(wx.HORIZONTAL)
		fx, th = self.getPaths()
		self.checkboxFirefox = wx.CheckBox(self, wx.ID_ANY,
		# TRANSLATORS: Checkbox to select Firefox appModule
		label=_("Firefox"))
		self.checkboxFirefox.SetValue(os.path.exists(fx))
		sizerDir.Add(self.checkboxFirefox)
		self.checkboxThunderbird = wx.CheckBox(self, wx.ID_ANY,
		# TRANSLATORS: Checkbox to select Thunderbird appModule
		label=_("Thunderbird"))
		self.checkboxThunderbird.SetValue(os.path.exists(th))
		sizerDir.Add(self.checkboxThunderbird)
		helper.addItem(sizerDir)

	def getPaths(self):
		drive, addonDir = os.path.splitdrive(globalPluginHandler.globalPlugins.MozillaAppsEnhancements.__file__)
		addonDir = addonDir.split("\\")[:-2]
		fxDir = os.path.join(drive, "\\", *addonDir, "appModules", "firefox.py")
		thDir = os.path.join(drive, "\\", *addonDir, "appModules", "thunderbird.py")
		return fxDir, thDir

	def onSave(self):
		changes = False
		fx, th = self.getPaths()
		fx_, th_ = fx+"_", th+"_"
		if self.checkboxFirefox.GetValue() and not os.path.exists(fx):
			os.rename(fx_, fx)
			changes = True
		elif not self.checkboxFirefox.GetValue() and os.path.exists(fx):
			os.rename(fx, fx_)
			changes = True
		if self.checkboxThunderbird.GetValue() and not os.path.exists(th):
			os.rename(th_, th)
			changes = True
		elif not self.checkboxThunderbird.GetValue() and os.path.exists(th):
			os.rename(th, th_)
			changes = True
		if changes:
			if wx.MessageBox(_("Changes will not be applied until restart NVDA. Do you want to restart it now?"), _("Restart NVDA"), wx.YES_NO) == 2:
				restart()
		config.conf.profiles[-1].name = self.originalProfileName

	def onDiscard(self):
		config.conf.profiles[-1].name = self.originalProfileName

	def onPanelActivated(self):
		self.originalProfileName = config.conf.profiles[-1].name
		config.conf.profiles[-1].name = None
		self.Show()

	def onPanelDeactivated(self):
		config.conf.profiles[-1].name = self.originalProfileName
		self.Hide()

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self, *args, **kwargs):
		super(GlobalPlugin, self).__init__(*args, **kwargs)
		NVDASettingsDialog.categoryClasses.append(MozillaPanel)

	def terminate(self):
		try:
			NVDASettingsDialog.categoryClasses.remove(MozillaPanel)
		except:
			pass

