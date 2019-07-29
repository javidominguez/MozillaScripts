# Mozilla Apps Enhancements add-on for NVDA
#This file is covered by the GNU General Public License.
#See the file COPYING.txt for more details.
#Copyright (C) 2017 Javi Dominguez <fjavids@gmail.com>

# Python3 compatibility fixes

import sys

py3flag = True if sys.version[:1] == "3" else False

if py3flag:
	__filter_class__ = filter

	def filter(*args):
		return [item for item in __filter_class__(*args)]
