# Candidate B: anchored descendant search. These walk fake trees only -- the
# whole point is that the primitive tolerates wrapper elements inserted between
# a stable anchor and the target, which a direct-child path cannot.

import appModules.shared as shared
from fakes import FakeObj, firefox151_tree, firefox_pre151_tree


def test_finds_descendant_through_inserted_wrapper_ff151():
	# The regression that started this: #urlbar-input sits under the *new*
	# .urlbar-input-container wrapper. Anchoring on the stable #urlbar and
	# searching descendants must still reach it.
	foreground, urlbar, urlbar_input = firefox151_tree()
	found = shared.findInSubtree(urlbar, shared.byIA2Attribute("id", "urlbar-input"))
	assert found is urlbar_input


def test_finds_descendant_through_old_wrapper_pre151():
	# Same predicate, different wrapper (.urlbar-input-box). One primitive,
	# both DOM shapes -- that is the resilience.
	foreground, urlbar, urlbar_input = firefox_pre151_tree()
	found = shared.findInSubtree(urlbar, shared.byIA2Attribute("id", "urlbar-input"))
	assert found is urlbar_input


def test_returns_none_when_no_descendant_matches():
	foreground, urlbar, urlbar_input = firefox151_tree()
	found = shared.findInSubtree(urlbar, shared.byIA2Attribute("id", "does-not-exist"))
	assert found is None


def test_returns_none_for_missing_anchor():
	assert shared.findInSubtree(None, shared.byIA2Attribute("id", "anything")) is None


def test_tolerates_nodes_without_ia2attributes():
	# Real trees contain nodes that expose no IA2Attributes at all; the search
	# must skip them rather than crash.
	target = FakeObj(ia2={"id": "target"}, value="hit")
	bare = FakeObj(ia2=None)  # no IA2Attributes attribute
	anchor = FakeObj(ia2={"id": "anchor"}, children=[bare, target])
	found = shared.findInSubtree(anchor, shared.byIA2Attribute("id", "target"))
	assert found is target


def test_searches_descendants_not_the_anchor_itself():
	# The anchor matching the predicate must not short-circuit the search; we
	# want a descendant.
	anchor = FakeObj(ia2={"id": "urlbar-input"})
	assert shared.findInSubtree(anchor, shared.byIA2Attribute("id", "urlbar-input")) is None


def test_exact_match_does_not_confuse_container_with_input():
	# re.match-style prefix matching would wrongly return .urlbar-input-container
	# (visited first, depth-first) when searching for id "urlbar-input". The
	# predicate must match exactly.
	foreground, urlbar, urlbar_input = firefox151_tree()
	container = urlbar.firstChild.next  # .urlbar-input-container
	assert "urlbar-input" in container.IA2Attributes.get("class", "")
	found = shared.findInSubtree(urlbar, shared.byIA2Attribute("id", "urlbar-input"))
	assert found is urlbar_input


def test_depth_first_preorder_returns_first_match():
	deep = FakeObj(ia2={"id": "match", "class": "deep"})
	shallow = FakeObj(ia2={"id": "match", "class": "shallow"})
	anchor = FakeObj(
		ia2={"id": "anchor"},
		children=[FakeObj(ia2={"class": "wrapper"}, children=[deep]), shallow],
	)
	# Pre-order visits the first branch (and its descendant) before the second
	# sibling, so the deep match under the first child wins.
	found = shared.findInSubtree(anchor, shared.byIA2Attribute("id", "match"))
	assert found is deep
