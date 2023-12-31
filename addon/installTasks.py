# -*- coding: UTF-8 -*-

# (C) 2023 Javi Dominguez https://github.com/javidominguez/
# License GPL2 https://www.gnu.org/licenses/old-licenses/gpl-2.0.html#SEC1

def onInstall() -> None:
	# Checks which modules have been disabled and keeps them disabled after upgrading.
	import addonHandler
	addons = filter(lambda a: a.name == "Mozilla" and a.isInstalled, addonHandler.getAvailableAddons())
	try:
		installedAddon = next(addons)
		import os
		pendingInstallAppModulesDir = os.path.abspath(os.path.join(os.path.dirname(__file__), "appModules"))
		for module in ("firefox.py","thunderbird.py"):
			if not os.path.exists(os.path.join(installedAddon.path,"appModules",module)):
				path = os.path.join(pendingInstallAppModulesDir,module)
				os.rename(path, path+"_")
	except StopIteration:
		pass
