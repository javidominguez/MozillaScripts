# Lightweight fake NVDAObject trees for exercising the a11y-tree search helpers.
#
# A real NVDAObject exposes a sprawling COM-backed interface; the search helpers
# only ever touch .firstChild, .next, .IA2Attributes, .value, .name and .role.
# FakeObj implements exactly that surface over a plain list of children, so a
# test fixture is just a literal tree -- no NVDA, no Firefox, no COM.

_MISSING = object()


class FakeObj:
	"""A stand-in NVDAObject.

	ia2:   dict of IA2Attributes (id / class / tag). Pass ia2=None to model a
	       node that has *no* IA2Attributes attribute at all -- the helpers must
	       tolerate that (real trees contain such nodes).
	"""

	def __init__(self, ia2=_MISSING, value=None, name=None, role=None, children=None):
		if ia2 is _MISSING:
			ia2 = {}
		if ia2 is not None:
			self.IA2Attributes = ia2
		# else: deliberately leave IA2Attributes unset.
		self.value = value
		self.name = name
		self.role = role
		self.parent = None
		self._children = list(children or [])
		self.next = None
		previous = None
		for child in self._children:
			child.parent = self
			if previous is not None:
				previous.next = child
			previous = child

	@property
	def firstChild(self):
		return self._children[0] if self._children else None

	@property
	def children(self):
		return list(self._children)

	@property
	def recursiveDescendants(self):
		for child in self._children:
			yield child
			yield from child.recursiveDescendants

	def __repr__(self):
		ident = getattr(self, "IA2Attributes", {})
		label = ident.get("id") or ident.get("class") or ident.get("tag") or "?"
		return "<FakeObj %s>" % label


# The URL that lives on the address field across all fixtures.
URL = "docs.google.com/document/d/abc123/edit"


def firefox151_tree():
	"""Ground-truth FF151 urlbar subtree (from the live NVDA log in the handoff).

	#urlbar-input now sits under a new `.urlbar-input-container` wrapper; the old
	`.urlbar-input-box` is gone. This is the exact shape that broke NVDA+A.
	"""
	urlbar_input = FakeObj(
		ia2={"id": "urlbar-input", "class": "urlbar-input textbox-input"},
		value=URL,
		name=URL,
		role="COMBOBOX",
		children=[FakeObj(ia2={}, name=URL, role="STATICTEXT")],
	)
	urlbar = FakeObj(
		ia2={"id": "urlbar", "tag": "moz-urlbar"},
		role="GROUPING",
		children=[
			FakeObj(ia2={"class": "urlbar-background"}, role="SECTION"),
			FakeObj(
				ia2={"class": "urlbar-input-container"},
				role="SECTION",
				children=[
					FakeObj(ia2={"id": "trust-icon-container", "class": "secure"}, role="BUTTON"),
					FakeObj(ia2={"id": "identity-permission-box"}, role="BUTTON"),
					urlbar_input,
					FakeObj(ia2={"class": "textbox-contextmenu"}, role="POPUPMENU"),
					FakeObj(ia2={"id": "star-button-box", "class": "urlbar-page-action"}, role="BUTTON"),
				],
			),
		],
	)
	nav_bar = FakeObj(ia2={"id": "nav-bar"}, role="TOOLBAR", children=[urlbar])
	foreground = FakeObj(ia2={"id": "main-window"}, children=[nav_bar])
	return foreground, urlbar, urlbar_input


def firefox_pre151_tree():
	"""Pre-FF151 (e.g. FF140) shape: #urlbar-input nested under the old
	`.urlbar-input-box` wrapper, itself under #urlbar. The anchored descendant
	search must find #urlbar-input through this different wrapper too."""
	urlbar_input = FakeObj(
		ia2={"id": "urlbar-input", "class": "urlbar-input textbox-input"},
		value=URL,
		name=URL,
		role="COMBOBOX",
	)
	urlbar = FakeObj(
		ia2={"id": "urlbar", "tag": "moz-urlbar"},
		role="GROUPING",
		children=[
			FakeObj(ia2={"class": "urlbar-background"}, role="SECTION"),
			FakeObj(
				ia2={"class": "urlbar-input-box"},
				value=URL,
				role="SECTION",
				children=[urlbar_input],
			),
		],
	)
	nav_bar = FakeObj(ia2={"id": "nav-bar"}, role="TOOLBAR", children=[urlbar])
	foreground = FakeObj(ia2={"id": "main-window"}, children=[nav_bar])
	return foreground, urlbar, urlbar_input


def firefox_pre133_tree():
	"""FF 87..132 shape: `.urlbar-input-box` is a direct child of #nav-bar (not
	under #urlbar), with #urlbar-input inside it. Exercises the preserved legacy
	path in addressField()."""
	urlbar_input = FakeObj(
		ia2={"id": "urlbar-input", "class": "urlbar-input textbox-input"},
		value=URL,
		name=URL,
		role="COMBOBOX",
	)
	input_box = FakeObj(
		ia2={"class": "urlbar-input-box"},
		role="SECTION",
		children=[urlbar_input],
	)
	nav_bar = FakeObj(ia2={"id": "nav-bar"}, role="TOOLBAR", children=[input_box])
	foreground = FakeObj(ia2={"id": "main-window"}, children=[nav_bar])
	return foreground, input_box, urlbar_input


def thunderbird_message_header(include_cc=True, extra_wrappers=False):
	"""A Thunderbird message-header subtree (a LANDMARK) holding sender, To and
	CC address fields, mirroring the rigid paths the add-on used to walk:

	    headerSenderToolbarContainer > expandedfromRow > .multi-recipient-row
	        > .recipients-list > #fromRecipient0
	    #expandedtoRow > #expandedtoBox > .recipients-list > #toRecipient*
	    #expandedccRow > #expandedccBox > .recipients-list > #ccRecipient0

	extra_wrappers=True inserts an additional wrapper element on the sender and
	To branches -- the Thunderbird analogue of the FF151 .urlbar-input-container
	insertion -- so a test can prove the anchored search survives it.

	Returns (message_header, sender, [to_recipients], cc_recipient_or_None).
	"""
	def recipient(rid, address):
		return FakeObj(ia2={"id": rid}, name=address)

	sender = recipient("fromRecipient0", "alice@example.com")
	sender_list = FakeObj(ia2={"class": "recipients-list"}, children=[sender])
	if extra_wrappers:
		sender_list = FakeObj(ia2={"class": "new-sender-wrapper"}, children=[sender_list])
	multi = FakeObj(ia2={"class": "multi-recipient-row"}, children=[sender_list])
	from_row = FakeObj(ia2={"id": "expandedfromRow"}, children=[multi])
	sender_container = FakeObj(ia2={"id": "headerSenderToolbarContainer"}, children=[from_row])

	to0 = recipient("toRecipient0", "bob@example.com")
	to1 = recipient("toRecipient1", "carol@example.com")
	# Multiple class tokens: exact-match would miss this; token-match must hit.
	to_list = FakeObj(ia2={"class": "recipients-list address-container"}, children=[to0, to1])
	to_inner = FakeObj(ia2={"id": "expandedtoBox"}, children=[to_list])
	if extra_wrappers:
		to_inner = FakeObj(ia2={"class": "to-wrapper"}, children=[to_inner])
	to_row = FakeObj(ia2={"id": "expandedtoRow"}, children=[to_inner])

	children = [sender_container, to_row]
	cc0 = None
	if include_cc:
		cc0 = recipient("ccRecipient0", "dan@example.com")
		cc_list = FakeObj(ia2={"class": "recipients-list"}, children=[cc0])
		cc_inner = FakeObj(ia2={"id": "expandedccBox"}, children=[cc_list])
		cc_row = FakeObj(ia2={"id": "expandedccRow"}, children=[cc_inner])
		children.append(cc_row)

	message_header = FakeObj(ia2={"id": "messageHeader"}, role="LANDMARK", children=children)
	return message_header, sender, [to0, to1], cc0


def thunderbird_sender_only_header():
	"""Message header with neither To nor CC rows (e.g. a draft) -- the locator
	must still return just the sender."""
	sender = FakeObj(ia2={"id": "fromRecipient0"}, name="alice@example.com")
	sender_list = FakeObj(ia2={"class": "recipients-list"}, children=[sender])
	from_row = FakeObj(ia2={"id": "expandedfromRow"}, children=[sender_list])
	container = FakeObj(ia2={"id": "headerSenderToolbarContainer"}, children=[from_row])
	message_header = FakeObj(ia2={"id": "messageHeader"}, role="LANDMARK", children=[container])
	return message_header, sender
