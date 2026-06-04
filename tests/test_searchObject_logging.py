# Candidate C: when searchObject misses a milestone, it should log which
# milestone failed and what ids/classes were actually present at that level --
# exactly the manual probe we hand-injected to diagnose the FF151 break.

import appModules.shared as shared
from conftest import log_recorder
from fakes import firefox151_tree


def setup_function(_):
	log_recorder.clear()


def test_logs_the_missing_milestone_and_present_siblings():
	# Search the *old* (<151) path against the FF151 tree: it gets through
	# nav-bar -> urlbar, then misses on .urlbar-input-box (now -container).
	foreground, urlbar, urlbar_input = firefox151_tree()
	old_path = (("id", "nav-bar"), ("id", "urlbar"), ("class", "urlbar-input-box"))
	result = shared.searchObject(old_path, startAtObject=foreground)
	assert result is None

	messages = [msg for _level, msg in log_recorder.records]
	assert messages, "expected a diagnostic log line on miss"
	blob = "\n".join(messages)
	# Names the milestone that missed...
	assert "urlbar-input-box" in blob
	# ...and reports what was actually there (the new wrapper).
	assert "urlbar-input-container" in blob


def test_no_log_on_success():
	foreground, urlbar, urlbar_input = firefox151_tree()
	good_path = (("id", "nav-bar"), ("id", "urlbar"))
	result = shared.searchObject(good_path, startAtObject=foreground)
	assert result is urlbar
	assert log_recorder.records == []
