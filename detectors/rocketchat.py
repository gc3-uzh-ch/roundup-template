#!/usr/bin/env python
# -*- coding: utf-8 -*-#
#
#
# Copyright (C) 2018, S3IT, University of Zurich. All rights reserved.
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
"""
This reactor will notify a Rocket.Chat room every time an issue is created or modified.

Configuration is needed for this detector, in `detectors/config.ini`:

[rocketchat]
base_url = <base url of hipchat api>
user = <username>
token = <token/password>
room_id = <room id>
channel = <channel with #>
"""

__docformat__ = 'reStructuredText'
__author__ = 'Pim Witlox <pim.witlox@uzh.ch>'

import json
import urllib2


def notify_rocket(db, msg, color=None):
    log = db.get_logger().getChild('rocketchat')
    try:
        cfg = db.config.detectors
        base_url = cfg['ROCKETCHAT_BASE_URL']
        user = cfg['ROCKETCHAT_USER']
        token = cfg['ROCKETCHAT_TOKEN']
        room_id = cfg['ROCKETCHAT_ROOM_ID']
        channel = cfg['ROCKETCHAT_CHANNEL']
    except Exception as ex:
        log.error("Config options not found. Check detectors/config.ini for rocketchat options")
        return

    try:
        headers = {"Content-Type": "application/json"}
        login_uri = "{0}/api/v1/login".format(base_url)
        logout_uri = "{0}/api/v1/logout".format(base_url)
        post_message_uri = "{0}/api/v1/chat.postMessage".format(base_url)

        login_data = {
            "username": user,
            "password": token
        }
        login_response = json.loads(urllib2.urlopen(urllib2.Request(login_uri, data=json.dumps(login_data), headers=headers)))
        if login_response["status"] == "success":
            log.debug("successfully logged in on {0}".format(base_url))
        else:
            raise Exception("failed to login on {0}: {1}".format(base_url, login_response))
        auth_token = login_response["data"]["authToken"]
        user_id = login_response["data"]["userId"]

        headers["X-Auth-Token"] = auth_token
        headers["X-User-Id"] = user_id

        issue_data = {
            "roomId": room_id,
            "channel": channel,
            "text": msg,
            "attachments": []
        }
        if color is not None:
            issue_data["attachments"]["color"] = color
        issue_response = json.loads(urllib2.urlopen(urllib2.Request(post_message_uri, data=json.dumps(issue_data), headers=headers)))
        if issue_response["status"] == "success":
            log.debug("successfully sent message {0} to {1} ({2})".format(issue_data, base_url, channel))
        else:
            raise Exception("failed send message to {0} ({1}): {2}".format(base_url, channel, issue_response))

        del headers["Content-Type"]

        logout_response = json.loads(urllib2.urlopen(urllib2.Request(logout_uri, headers=headers)))
        if logout_response["status"] == "success":
            log.debug("successfully logged out of {0}".format(base_url))
        else:
            raise Exception("failed to logout from {0}: {1}".format(base_url, logout_response))

    except Exception as ex:
        log.warning("Unable to send message to rocketchat. Message was :%s, error: %s", msg, ex)


def newissue(db, cl, nodeid, oldvalues):
    issue = db.issue.getnode(nodeid)

    msg = """NEW <a href="{0}issue{1}">issue{1}</a> has been created by {2}.
"<i>{3}</i>" """.format(db.config.TRACKER_WEB,
              nodeid,
              db.user.get(issue.creator, 'username'),
              issue.title)

    notify_rocket(db, msg, color='red')


def issueupdate(db, cl, nodeid, oldvalues):
    issue = db.issue.getnode(nodeid)
    allmsg = []

    color = None
    if db.status.get(issue.status, 'name') == 'solved':
        color = 'green'
    elif db.status.get(issue.status, 'name') == 'new':
        color = 'red'

    actor = db.user.get(issue.actor, 'username')
    actorname = db.user.get(issue.actor, 'realname')

    if issue.title != oldvalues['title']:
        allmsg.append('title: "<i>%s</i>" -> "<i>%s</i>"' % (oldvalues['title'], issue.title))

    if issue.assignee != oldvalues['assignee']:
        if oldvalues['assignee']:
            olduid = db.user.get(oldvalues['assignee'], 'username')
            oldname = db.user.get(oldvalues['assignee'], 'realname')
            old = '%s (%s)' % (olduid, oldname)
        else:
            old = 'None'

        if issue.assignee:
            newuid = db.user.get(issue.assignee, 'username')
            newname = db.user.get(issue.assignee, 'realname')
            new = '%s (%s)' % (newuid, newname)
        else:
            new = 'None'
        allmsg.append("%s (%s) changed assignee: %s -> %s" % (actor, actorname, old, new))

    if issue.status != oldvalues['status']:
        old = db.status.get(oldvalues['status'], 'name')
        new = db.status.get(issue.status, 'name')
        allmsg.append("%s (%s) changed status: %s -> %s" % (actor, actorname, old, new))

    if issue.messages != oldvalues['messages']:
        msgid = issue.messages[-1]
        msg = db.msg.getnode(msgid)
        creator = db.user.get(msg.creator, 'username')
        creatorname = db.user.get(msg.creator, 'realname')
        allmsg.append("followup message from %s (%s)" % (creator, creatorname))

    if issue.topics != oldvalues['topics']:
        old = [db.topic.get(topicid, 'name') for topicid in oldvalues['topics']]
        new = [db.topic.get(topicid, 'name') for topicid in issue.topics]
        allmsg.append("%s (%s) changed topics: %s -> %s" % (actor, actorname, str.join(', ', old), str.join(', ', new)))

    if issue.nosy != oldvalues['nosy']:
        old = [db.user.get(userid, 'username') for userid in oldvalues['nosy']]
        new = [db.user.get(userid, 'username') for userid in issue.nosy]
        allmsg.append("%s (%s) changed subscribers: %s -> %s" % (actor, actorname, str.join(', ', old), str.join(', ', new)))

    # Actually send notification, if needed.
    if allmsg:
        # Prepend link to the issue
        issuelink = """<a href="{0}issue{1}">issue{1} ({2})</a>: """.format(db.config.TRACKER_WEB, nodeid, issue.title)
        # add "newlines"
        text = str.join('<br />', [issuelink + msg for msg in allmsg])
        notify_rocket(db, text, color=color)


def init(db):
    db.issue.react('create', newissue)
    db.issue.react('set', issueupdate)
    
