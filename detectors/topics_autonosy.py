#!/usr/bin/env python
# -*- coding: utf-8 -*-#
# @(#)topics_autonosy.py
#
#
# Copyright (C) 2014, GC3, University of Zurich. All rights reserved.
#
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

__docformat__ = 'reStructuredText'
__author__ = 'Antonio Messina <antonio.s.messina@gmail.com>'

def topic_autoassign_nosy(db, cl, nodeid, newvalues):
    # Again, a reactor that can goes in loop...

    if 'topics' not in newvalues:
        return

    for topicid in newvalues['topics']:
        nosylist = db.topic.get(topicid, 'autonosy')
        if nosylist:
            if 'nosy' not in newvalues:
                newvalues['nosy'] = []
            newvalues['nosy'] += nosylist


def init(db):
    db.issue.audit('create', topic_autoassign_nosy)
    db.issue.audit('set', topic_autoassign_nosy)
