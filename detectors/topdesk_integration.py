#!/usr/bin/env python
# -*- coding: utf-8 -*-# 
# @(#)topdesk_integration.py
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

import re
from roundup import roundupdb
from roundup.mailer import SMTPConnection

re_forwarded = re.compile(
    r'Forwarding Incident (I-[0-9]+-[0-9]+) from TOPdesk@UZH:', re.I)

replymessage_template = """\
From: %(mail_from)s
Subject: %(mail_subject)s

Dear %(username)s,

Your ticket has been transferred from TOPDesk to RoundUp: 

    %(issue_url)s

---------------------------------------------------------------------------

%(message)s

---------------------------------------------------------------------------
"""

def topdesk_integration(db, cl, nodeid, oldvalues):
    """Perform roundup-TOPDesk integration

    https://www.s3it.uzh.ch/help/issue630

    If:

    * Body of the email starts with
      `Forwarding Incident I-[0-9]+-[0-9]+ from TOPdesk@UZH:`
      where `I-[0-9]+-[0-9]+` is the incident number in TOPDesk

    a mail should be sent to support@id.uzh.ch to close the
    ticket. The reply email should have:

    * `From:` field equal to `help@s3it.uzh.ch`
    * `To:` is equal to `support@id.uzh.ch`
    * `Subject:` must contains the incident ID. Even better, we just
      leave the original subject and prepend Re:, as it was a reply
      from a regular user.

    Content of the email will include:

    Your ticket was transfered to RoundUp: http://....

    and possibly the content of the ticket.

    """

    log = db.get_logger()
    log.debug("TOPDesk-RoundUp integration - new issue %s created", nodeid)

    # Check if this issue comes from TOPDesk
    msgids = cl.get(nodeid, 'messages')

    # one and only one message should be here.
    if len(msgids) > 1:
        log.warning("Issue %s (forwarded from TOPDesk) has more than one"
                    " message, which is wrong. Only parsing first message.",
                    nodeid)
    elif len(msgids) == 0:
        raise roundupdb.DetectorError(
            "Issue %s (forwarded from TOPDesk) has no messages."
            " NOT sending a reply to TOPDesk" % nodeid)

    msgid = msgids[0]
    msg = db.msg.getnode(msgid)
    content = msg.content
    firstline = content.strip().split('\n')[0]

    if re_forwarded.match(firstline):
        # Send a reply to support@id.uzh.ch

        # Get the URL of the roundup issue
        base = self.db.config.TRACKER_WEB
        if not base.endswith('/'):
            base = base + '/'
        issue_url = base + cl.classname + issueid

        # Get the requestor name
        userid = cl.get(nodeid, 'creator')
        username = db.user.get(userid, 'realname')

        # Get the ID of the issue on TOPDesk
        topdesk_id = re_forwarded.search(firstline).group(1)

        # Mail from is fixed
        mail_from = 'help@s3it.uzh.ch'

        # Mail to is fixed
        mail_to = 'support@id.uzh.ch'

        # Subject is took from the original subject, that is now the
        # title of the issue
        mail_subject = cl.get(nodeid, 'title')

        # Build the reply message.
        # Please note that this message will be sent from TOPDesk to the user
        message = msg.content
        
        mail_body = replymessage_template % {
            'mail_from': mail_from,
            'mail_subject': mail_subject,
            'username': username,
            'issue_url': issue_url,
            'message': message,
        }

        try:
            smtp = SMTPConnection(db.config)
            smtp.smtp_send(mail_to, mail_body, sender=mail_from)
        except Exception as ex:
            raise roundupdb.DetectorError(
                "Error sending reply message for TOPDesk issue %s "
                "(RoundUp issue %s): %s",
                topdesk_id, nodeid, ex)


def init(db):
    db.issue.react('create', topdesk_integration)
