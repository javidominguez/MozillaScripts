# Candidate A: a single "address field" locator in firefox.py that both
# script_url and event_alert call, so the URL-finding knowledge lives in one
# place. The headline regression: the FF151 tree (where .urlbar-input-box is
# gone and #urlbar-input sits under .urlbar-input-container) must resolve to the
# URL -- the exact bug that started this work.

import appModules.firefox as firefox
from fakes import URL, firefox151_tree, firefox152_tree, firefox_pre151_tree, firefox_pre133_tree


def test_addressField_resolves_url_on_ff151():
	foreground, urlbar, urlbar_input = firefox151_tree()
	field = firefox.addressField(foreground, 151)
	assert field is urlbar_input
	assert field.value == URL


def test_getURL_returns_the_url_string_on_ff151():
	foreground, urlbar, urlbar_input = firefox151_tree()
	assert firefox.getURL(foreground, 151) == URL


def test_addressField_resolves_url_on_ff152_with_urlbar_context_menu():
	# FF152 has a direct #nav-bar child named #urlbarView-context-menu before
	# the actual #urlbar. id=urlbar must match the real anchor exactly, not the
	# first id with that prefix.
	foreground, urlbar, urlbar_input = firefox152_tree()
	field = firefox.addressField(foreground, 152)
	assert field is urlbar_input
	assert field.value == URL


def test_addressField_resolves_url_pre151():
	# FF140-style: same anchored search reaches #urlbar-input through the old
	# .urlbar-input-box wrapper.
	foreground, urlbar, urlbar_input = firefox_pre151_tree()
	field = firefox.addressField(foreground, 140)
	assert field is urlbar_input
	assert firefox.getURL(foreground, 140) == URL


def test_addressField_uses_legacy_path_pre133():
	# FF120-style: .urlbar-input-box is a direct child of #nav-bar, not under
	# #urlbar. The preserved legacy branch still finds #urlbar-input.
	foreground, input_box, urlbar_input = firefox_pre133_tree()
	field = firefox.addressField(foreground, 120)
	assert field is urlbar_input
	assert firefox.getURL(foreground, 120) == URL


def test_addressField_returns_none_when_absent():
	from fakes import FakeObj
	empty = FakeObj(ia2={"id": "main-window"})
	assert firefox.addressField(empty, 151) is None
	assert firefox.getURL(empty, 151) is None
