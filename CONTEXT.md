# CONTEXT — Mozilla Apps Enhancements

Domain glossary for this NVDA add-on. The add-on reads Firefox and Thunderbird
UI by walking their IAccessible2 (a11y) trees. Those trees are **not** a stable
interface — Mozilla restructures them between releases — so the recurring domain
problem is "navigate an a11y subtree whose shape changed."

Use these terms (not synonyms) in code, tests, issues, and proposals.

## Glossary

### address field
The element in Firefox's toolbar that bears the page URL — the `#urlbar-input`
combobox. "Find the address field" is a single piece of version/DOM knowledge
with one home: `addressField(foreground, ffVersion)` in
`addon/appModules/firefox.py` (with `getURL()` as a thin reader over it). Both
`script_url` (the NVDA+A "read address bar" command) and `event_alert` (which
tags notifications with the page domain) locate it through that function — they
must not re-encode the path themselves.

From Firefox 133 on, the address field is located resiliently: anchor on the
stable `#urlbar`, then `findInSubtree` for `#urlbar-input` at any depth. This
survives Mozilla inserting wrapper elements between `#urlbar` and the input —
e.g. `.urlbar-input-box` (FF133–150) and `.urlbar-input-container` (introduced
in FF151, the change that broke NVDA+A and prompted this work). Pre-133 Firefox
trees genuinely differ and keep explicit version paths.

### anchored descendant search
The resilient navigation primitive: `findInSubtree(anchor, predicate)` in
`addon/appModules/shared/__init__.py`. Given a **stable anchor** object and a
predicate, it returns the first descendant (depth-first) that matches, at any
depth — tolerating wrapper elements inserted between anchor and target. Contrast
with `searchObject(path)`, the rigid sibling primitive that matches a fixed
sequence of **direct-child** milestones and fails the moment a wrapper appears.
Build predicates with `byIA2Attribute(key, value)` (exact match — so searching
for id `urlbar-input` never matches `urlbar-input-container`) or
`byIA2Class(value)` (CSS class-token membership, since an IA2 `class` attribute
can hold several space-separated tokens).

Two adapters use this primitive: the Firefox **address field** above, and the
Thunderbird **message header recipients** below.

### message header recipients
The sender, To and CC address fields in a Thunderbird message header, located by
`messageHeaderRecipients(messageHeader)` in `addon/appModules/thunderbird.py`.
The message header (a LANDMARK) is the stable anchor; the sender's
`#fromRecipient0` is found at any depth, and each recipient row (`#expandedtoRow`
/ `#expandedccRow`) then its `.recipients-list` within. This replaced rigid
direct-child paths up to five levels deep — the same brittleness class as the
Firefox address field, and the second adapter that proves the
[anchored descendant search](#anchored-descendant-search) seam.
