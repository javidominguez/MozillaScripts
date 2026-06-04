# The Thunderbird application of the same anchored descendant search that
# locates Firefox's address field. messageHeaderRecipients() collapses the old
# 5-level sender path (and the 3-level To/CC paths) to an anchor + predicate, so
# wrapper elements Thunderbird may insert are traversed rather than fatal.

import appModules.thunderbird as thunderbird
from fakes import thunderbird_message_header, thunderbird_sender_only_header


def test_locates_sender_to_and_cc():
	header, sender, to_recipients, cc = thunderbird_message_header()
	addresses = thunderbird.messageHeaderRecipients(header)
	assert addresses == [sender] + to_recipients + [cc]


def test_survives_inserted_wrappers():
	# extra_wrappers inserts a div between the landmarks and the targets -- the
	# Thunderbird analogue of the FF151 .urlbar-input-container break. The rigid
	# direct-child path would miss; the anchored search must not.
	header, sender, to_recipients, cc = thunderbird_message_header(extra_wrappers=True)
	addresses = thunderbird.messageHeaderRecipients(header)
	assert addresses == [sender] + to_recipients + [cc]


def test_to_recipients_matched_by_class_token_not_exact_string():
	# The To recipients-list carries multiple class tokens
	# ("recipients-list address-container"); a whole-string match would miss it.
	header, sender, to_recipients, cc = thunderbird_message_header()
	addresses = thunderbird.messageHeaderRecipients(header)
	assert to_recipients[0] in addresses
	assert to_recipients[1] in addresses


def test_header_without_cc():
	header, sender, to_recipients, cc = thunderbird_message_header(include_cc=False)
	assert cc is None
	addresses = thunderbird.messageHeaderRecipients(header)
	assert addresses == [sender] + to_recipients


def test_sender_only_header():
	header, sender = thunderbird_sender_only_header()
	addresses = thunderbird.messageHeaderRecipients(header)
	assert addresses == [sender]
