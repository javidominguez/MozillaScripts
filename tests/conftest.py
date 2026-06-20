# Test harness for the Mozilla Apps Enhancements add-on.
#
# The add-on's modules import the NVDA runtime (api, controlTypes, wx, gui, ...)
# at import time, and shared/__init__.py even instantiates a wx.Dialog. None of
# that exists outside NVDA. So before importing anything from the add-on we
# register permissive fake modules in sys.modules. The pieces under test --
# the a11y-tree search helpers -- only touch plain object attributes
# (.firstChild / .next / .IA2Attributes / .value), so faking the runtime is
# enough to exercise them against the fake trees in fakes.py.

import builtins
import os
import sys
import types

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPMODULES = os.path.join(REPO_ROOT, "addon", "appModules")

# The add-on calls the translation lookup `_` (and occasionally `pgettext`) at
# import time; NVDA installs them as builtins via addonHandler.initTranslation().
builtins._ = lambda s: s
builtins.pgettext = lambda context, s: s


class _Anything:
	"""A permissive stand-in: any attribute access, call, or iteration is benign.

	Returned for every attribute the add-on reads off a faked runtime module. It
	is callable (so `wx.TextCtrl(...)` works), attribute-transparent (so
	`speech.speech.SpeechMode` works), and iterates empty (so
	`next(filter(..., addonHandler.getRunningAddons()))` raises StopIteration).
	"""

	def __init__(self, *args, **kwargs):
		pass

	def __call__(self, *args, **kwargs):
		return _Anything()

	def __getattr__(self, name):
		return _Anything()

	def __iter__(self):
		return iter(())

	def __bool__(self):
		return True

	# wx style flags get OR'd together (wx.TE_MULTILINE | wx.TE_READONLY).
	def __or__(self, other):
		return _Anything()

	def __ror__(self, other):
		return _Anything()

	def __and__(self, other):
		return _Anything()

	def __rand__(self, other):
		return _Anything()

	# config.conf.spec['thunderbird'] = confspec (item assignment on a fake).
	def __getitem__(self, key):
		return _Anything()

	def __setitem__(self, key, value):
		pass


class _Base:
	"""A real, subclassable base for runtime classes the add-on inherits from
	(wx.Panel, wx.Dialog, appModuleHandler.AppModule). Instances answer any
	unknown attribute with _Anything so partially-constructed widgets don't
	explode during a faked __init__."""

	def __init__(self, *args, **kwargs):
		pass

	def __getattr__(self, name):
		return _Anything()


class _LogRecorder:
	"""Captures log calls so the observability tests (candidate C) can assert
	on what searchObject reported when a milestone went missing."""

	def __init__(self):
		self.records = []

	def _record(self, level, msg, *args):
		try:
			rendered = msg % args if args else msg
		except Exception:
			rendered = msg
		self.records.append((level, rendered))

	def info(self, msg, *args, **kwargs):
		self._record("info", msg, *args)

	def debug(self, msg, *args, **kwargs):
		self._record("debug", msg, *args)

	def warning(self, msg, *args, **kwargs):
		self._record("warning", msg, *args)

	def error(self, msg, *args, **kwargs):
		self._record("error", msg, *args)

	def clear(self):
		self.records.clear()


class _PermModule(types.ModuleType):
	"""A module whose every unknown attribute resolves to _Anything."""

	def __getattr__(self, name):
		return _Anything()


def _register(name, **attrs):
	module = _PermModule(name)
	for key, value in attrs.items():
		setattr(module, key, value)
	sys.modules[name] = module
	# Bind the submodule onto its parent package so `from pkg import sub`
	# resolves to it instead of the parent's permissive __getattr__ fallback.
	if "." in name:
		parent_name, _, child = name.rpartition(".")
		parent = sys.modules.get(parent_name)
		if parent is not None:
			setattr(parent, child, module)
	return module


# Shared singletons exposed to tests.
log_recorder = _LogRecorder()


def _install_fake_runtime():
	# Heavy GUI / runtime modules: permissive fakes.
	_register("gui")
	_register("speech")
	_register("ui")
	_register("api")
	_register("controlTypes")
	_register("winUser")
	_register("globalCommands")

	# wx: Panel and Dialog must be real classes (they get subclassed); the rest
	# (BoxSizer, ListBox, Button, constants, ...) come through __getattr__.
	_register("wx", Panel=_Base, Dialog=_Base)

	# NVDAObjects.IAccessible[.mozilla]: nested package of permissive fakes.
	# IAccessible / Dialog / BrokenFocusedState are real classes because
	# thunderbird.py subclasses them (ThreadTree, Tab, QuickFilter).
	_register("NVDAObjects")
	_register("NVDAObjects.IAccessible", IAccessible=_Base)
	_register(
		"NVDAObjects.IAccessible.mozilla",
		IAccessible=_Base,
		Dialog=_Base,
		BrokenFocusedState=_Base,
	)

	# Thunderbird's extra runtime surface.
	_register("config")
	_register("globalVars")
	_register("treeInterceptorHandler")
	_register("keyboardHandler")
	_register("tones")
	_register("comtypes", COMError=type("COMError", (Exception,), {}))
	_register("comtypes.gen")
	_register("comtypes.gen.ISimpleDOM")
	_register("gui.settingsDialogs", SettingsPanel=_Base)

	# nvdaBuiltin app-module bases: thunderbird.py subclasses
	# thunderbird.AppModule (a hard import, no fallback). Registering firefox
	# here too just means firefox.py takes its nvdaBuiltin branch instead of the
	# appModuleHandler fallback -- harmless for the tests.
	_register("nvdaBuiltin")
	_register("nvdaBuiltin.appModules")
	_register("nvdaBuiltin.appModules.firefox", AppModule=_Base)
	_register("nvdaBuiltin.appModules.thunderbird", AppModule=_Base)

	# addonHandler: initTranslation is a no-op; no DeveloperToolkit running, so
	# firefox.py falls through to the core AppModule import.
	_register(
		"addonHandler",
		initTranslation=lambda: None,
		getRunningAddons=lambda: [],
	)

	# scriptHandler: a real pass-through decorator keeps the @script-decorated
	# methods callable instead of replacing them with a fake.
	_register(
		"scriptHandler",
		script=lambda *a, **k: (lambda f: f),
		getLastScriptRepeatCount=lambda: 0,
	)

	# appModuleHandler: provides the base AppModule that firefox.py subclasses
	# (nvdaBuiltin isn't registered, so the ModuleNotFoundError fallback fires).
	_register("appModuleHandler", AppModule=_Base)

	# logHandler.log records into the shared recorder for candidate-C assertions.
	_register("logHandler", log=log_recorder)

	# Make `appModules` a namespace package pointing at the real add-on source,
	# so `import appModules.shared` works and firefox.py's `from . import shared`
	# resolves correctly.
	appmodules = types.ModuleType("appModules")
	appmodules.__path__ = [APPMODULES]
	sys.modules["appModules"] = appmodules


_install_fake_runtime()
