#!/usr/bin/env python
# -*- coding: utf-8 -*-# 
# @(#)newissuecopy.py
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


# from http://www.roundup-tracker.org/cgi-bin/moin.cgi/NewIssueCopy

from roundup import roundupdb

def newissuecopy(db, cl, nodeid, oldvalues):
    ''' Copy a message about new issues to a team address.
    '''
    # so use all the messages in the create
    change_note = cl.generateCreateNote(nodeid)

    # send a copy to the nosy list
    log = db.get_logger()
    log.debug("messages for newly created issue %s: %s", nodeid, cl.get(nodeid, 'messages'))
    
    for msgid in cl.get(nodeid, 'messages'):
        try:
            log.debug("Issue %s: trying to send message %s by email to %s",
                      nodeid, msgid, db.config.DISPATCHER_EMAIL)
            # note: last arg must be a list
            cl.send_message(nodeid, msgid, change_note, [db.config.DISPATCHER_EMAIL])
        except roundupdb.MessageSendError, message:
            raise roundupdb.DetectorError, message

def init(db):
    db.issue.react('create', newissuecopy)
