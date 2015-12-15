#!/usr/bin/env python
# -*- coding: utf-8 -*-#
# @(#)mergeaction.py
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

# Took from http://www.roundup-tracker.org/cgi-bin/moin.cgi/MergeIssues

from roundup.cgi.exceptions import Redirect
from roundup.cgi import actions

class MergeAction(actions.Action):
    def handle(self):
        source_issue = self.nodeid
        # find out if the form has a target issue edit field
        if self.form.has_key('target_issue'):
            # yes it does. Get the value.
            target_issue = self.form['target_issue'].value.strip()
            if target_issue.startswith('issue'):
                # target_issue should be the issue id
                target_issue = target_issue[5:]
        else:
            # nope
            target_issue = None
        if not target_issue or target_issue == '':
            self.client.error_message.append('Unknown target issue')
            return
        elif target_issue == source_issue:
            self.client.error_message.append('Cannot merge issue %s into myself (%s)' % (target_issue, source_issue))
            return

        # get the message lists of the two issues
        source_messages = self.db.issue.get(source_issue, 'messages')
        target_messages = self.db.issue.get(target_issue, 'messages')
        # merge them
        for msg in source_messages:
            target_messages.append(msg)
        # update the target issue message list
        self.db.issue.set(target_issue, messages=target_messages)

        # get the file lists of the two issues
        source_files = self.db.issue.get(source_issue, 'files')
        target_files = self.db.issue.get(target_issue, 'files')
        # merge them
        for file in source_files:
            target_files.append(file)
        # update the target issue file list
        self.db.issue.set(target_issue, files=target_files)

# uncomment this if you're using timelogs
#        # get the timelog lists of the two issues
#        source_timelog = self.db.issue.get(source_issue, 'timelog')
#        target_timelog = self.db.issue.get(target_issue, 'timelog')
#        # merge them
#        for time in source_timelog:
#            target_timelog.append(time)
#        # update the target issue time list
#        self.db.issue.set(target_issue, timelog=target_timelog)

        # store the 'merged-into' issue id
        self.db.issue.set(source_issue, merged=target_issue)
        # retire the source issue
        self.db.issue.retire(source_issue)
        # commit all database changes
        self.db.commit()
        # confirm the merge and redirect to the target issue
        raise Redirect, """{0}issue{1}?@ok_message=Merging of issue {2} into issue {1} successful""".format(
            self.base, target_issue, source_issue)

class UnmergeAction(actions.Action):
    def handle(self):
        merged = self.db.issue.get(self.nodeid, 'merged')
        if merged:
            self.db.issue.restore(self.nodeid)
            self.db.issue.set(self.nodeid, merged=None)
            self.db.commit()

def init(instance):
    instance.registerAction('merge', MergeAction)
    instance.registerAction('unmerge', UnmergeAction)
