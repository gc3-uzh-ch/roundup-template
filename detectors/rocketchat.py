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
import requests


def notify_rocket(db, issue_id, msgs, color, body):
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
        login_response = requests.post(login_uri, data=json.dumps(login_data), headers=headers)
        if login_response.status_code != 200:
            raise Exception("failed to login to {0} ({1}): {2}".format(
                login_uri, login_response.status_code, login_response.text))
        login_data = json.loads(login_response.text)
        if login_data["status"] == "success":
            log.debug("successfully logged in on {0}".format(base_url))
        else:
            raise Exception("failed to login on {0}: {1}".format(base_url, login_data))

        headers["X-Auth-Token"] = login_data["data"]["authToken"]
        headers["X-User-Id"] = login_data["data"]["userId"]

        issue_data = {
            "roomId": room_id,
            "channel": channel,
            "text": "{0}issue{1} *{2}*".format(db.config.TRACKER_WEB, issue_id, body),
            "attachments": [{
                "text": "\n".join(msgs),
                "color": color
            }]
        }

        issue_response = requests.post(post_message_uri, data=json.dumps(issue_data), headers=headers)
        if issue_response.status_code != 200:
            raise Exception("failed to post issue to {0} ({1}): {2}".format(
                post_message_uri, issue_response.status_code, issue_response.text))
        issue_data = json.loads(issue_response.text)
        if issue_data["success"]:
            log.debug("successfully sent message {0} to {1} ({2})".format(issue_data, base_url, channel))
        else:
            raise Exception("failed send message to {0} ({1}): {2}".format(base_url, channel, issue_data))

        del headers["Content-Type"]

        logout_response = requests.post(logout_uri, headers=headers)
        if logout_response.status_code != 200:
            raise Exception("failed to logout to {0} ({1}): {2}".format(
                logout_uri, logout_response.status_code, logout_response.text))
        logout_data = json.loads(logout_response.text)
        if logout_data["status"] == "success":
            log.debug("successfully logged out of {0}".format(base_url))
        else:
            raise Exception("failed to logout from {0}: {1}".format(base_url, logout_data))

    except Exception as ex:
        log.warning("Unable to send message to rocketchat. error: %s", ex)


def newissue(db, cl, nodeid, oldvalues):
    issue = db.issue.getnode(nodeid)

    msg = "NEW issue{0} has been created by {1}".format(nodeid, db.user.get(issue.creator, 'username'))

    notify_rocket(db, nodeid, [msg], "red", issue.title)


def issueupdate(db, cl, nodeid, oldvalues):
    issue = db.issue.getnode(nodeid)
    allmsg = []

    color = 'yellow'
    if db.status.get(issue.status, 'name') == 'solved':
        color = 'green'
    elif db.status.get(issue.status, 'name') == 'new':
        color = 'red'
    elif db.status.get(issue.status, 'name') == 'spam':
        color = 'white'
    elif db.status.get(issue.status, 'name') == 'wontfix':
        color = 'darkslateblue'
    elif db.status.get(issue.status, 'name') == 'invalid':
        color = 'darkorchid'
    elif db.status.get(issue.status, 'name') == 'waiting':
        color = 'deepskyblue'
    elif db.status.get(issue.status, 'name') == 'on hold':
        color = 'steelblue'

    actor = db.user.get(issue.actor, 'username')
    actorname = db.user.get(issue.actor, 'realname')

    if issue.title != oldvalues['title']:
        allmsg.append("title: {0} -> {1}".format(oldvalues['title'], issue.title))

    if issue.assignee != oldvalues['assignee']:
        if oldvalues['assignee']:
            olduid = db.user.get(oldvalues['assignee'], 'username')
            oldname = db.user.get(oldvalues['assignee'], 'realname')
            old = "{0} ({1})".format(olduid, oldname)
        else:
            old = 'None'

        if issue.assignee:
            newuid = db.user.get(issue.assignee, 'username')
            newname = db.user.get(issue.assignee, 'realname')
            new = "{0} ({1})".format(newuid, newname)
        else:
            new = 'None'
        allmsg.append("{0} ({1}) changed assignee: {2} -> {3}".format(actor, actorname, old, new))
        # When changing assignee change the notification body and append a mention
        body = "{0} assigned to @{1}".format(issue.title, newuid)
    else:
        body = issue.title

    if issue.status != oldvalues['status']:
        old = db.status.get(oldvalues['status'], 'name')
        new = db.status.get(issue.status, 'name')
        allmsg.append("{0} ({1}) changed status: {2} -> {3}".format(actor, actorname, old, new))
    elif db.status.get(issue.status, 'name') in ['solved', 'invalid', 'wontfix']:
        try:
            uid = db.user.get(issue.assignee, 'username')
        except:
            uid = 'None'
        body = ' @{0}: followup on closed issue "{1}" '.format(uid, issue.title)

    if issue.messages != oldvalues['messages']:
        msgid = issue.messages[-1]
        msg = db.msg.getnode(msgid)
        creator = db.user.get(msg.creator, 'username')
        creatorname = db.user.get(msg.creator, 'realname')
        allmsg.append("followup message from {0} ({1})".format(creator, creatorname))

    if issue.topics != oldvalues['topics']:
        old = [db.topic.get(topicid, 'name') for topicid in oldvalues['topics']]
        new = [db.topic.get(topicid, 'name') for topicid in issue.topics]
        allmsg.append("{0} ({1}) changed topics: {2} -> {3}".format(
            actor, actorname, str.join(', ', old), str.join(', ', new)))

    if issue.nosy != oldvalues['nosy']:
        old = [db.user.get(userid, 'username') for userid in oldvalues['nosy']]
        new = [db.user.get(userid, 'username') for userid in issue.nosy]
        allmsg.append("{0} ({1}) changed subscribers: {2} -> {3}".format(
            actor, actorname, str.join(', ', old), str.join(', ', new)))

    # Actually send notification, if needed.
    if allmsg:
        notify_rocket(db, nodeid, allmsg, color, body)


def init(db):
    db.issue.react('create', newissue)
    db.issue.react('set', issueupdate)
