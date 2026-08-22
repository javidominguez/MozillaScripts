
* Improved resilience against Firefox and Thunderbird accessibility tree changes. The add-on now locates the Firefox address field and Thunderbird message recipients using a more robust search strategy, preventing breakage caused by internal UI restructuring in newer Mozilla releases. This also restores compatibility with Firefox 151+ and fixes the Firefox 152 address bar detection issue.
* Fixed a crash when opening the Thunderbird settings panel on recent versions of NVDA/wxPython.
* Fixed a crash in Thunderbird caused by objects exposing no IA2 relations.
* Updated translations.
* Implemented @hxebolax resource updater. From now the localization files will be updated automatically as soon as they are available.
Thanks to all contributors for their improvements and fixes.