#!/usr/bin/env python
# -*- coding: utf-8 -*-# 
# @(#)ldapuserauditor.py
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

import os
import ldap
from ConfigParser import RawConfigParser

from roundup.exceptions import Reject

def ldapuserauditor(db, cl, nodeid, newvalues):
    """Search user in the database using its email address. If the user is
    not found, and update its username based on the 'uid' attribute of
    the ldap object.

    This auditor has been created to support creation of new issues
    via email from valid LDAP users that have never logged in the web
    interface, using their UZH `short name`, and at the same time
    to avoid spam.

    """
    if 'address' not in newvalues:
        return

    log = db.get_logger().getChild('ldapuserauditor')

    ldap_conf_file = os.path.join(db.config.ext['HOME'], 'ldap_config.ini')
    if not os.path.exists(ldap_conf_file):
        log.info("Ldap configuration file %s not found. Exiting", ldap_conf_file)
        raise Reject('Ldap not configured')

    cfg = RawConfigParser()
    cfg.read(ldap_conf_file)
    if not cfg.has_section('ldap'):
        log.info("No section 'ldap' in configuration file %s. Exiting", ldap_conf_file)
        raise Reject('Ldap not configured')

    for opt in ['server_uri', 'search_bind_dn', 'search_bind_pw', 'base_dn',
                'aliasname_attribute', 'surname_attribute',
                'givenname_attribute']:
        if not cfg.has_option('ldap', opt):
            log.info("Missing mandatory option `%s` in ldap configuration file %s",
                     opt, ldap_conf_file)
            raise Reject('Missing mandatory option %s in ldap configuration file' % opt)

    server_uri = cfg.get('ldap', 'server_uri')
    search_bind_dn = cfg.get('ldap', 'search_bind_dn')
    search_bind_pw = cfg.get('ldap', 'search_bind_pw')
    base_dn = cfg.get('ldap', 'base_dn')
    aliasname_attribute = cfg.get('ldap', 'aliasname_attribute')
    surname_attribute = cfg.get('ldap', 'surname_attribute')
    givenname_attribute = cfg.get('ldap', 'givenname_attribute')
    searchfilter = "mail=%s" % newvalues['address']

    ldap.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)
    ldap.set_option(ldap.OPT_REFERRALS, 0)

    log.debug("Preparing connection to ldap server %s", server_uri)
    l = ldap.initialize(server_uri)

    log.debug("Binding to ldap server using `%s`", server_uri)
    l.simple_bind_s(search_bind_dn, search_bind_pw)
    
    log.debug("Searching user with search filter '%s'", searchfilter)
    users = l.search_st(base_dn, ldap.SCOPE_SUBTREE, searchfilter)
    if not users:
        # Raise an exception
        log.error("User with email address %s not found in database",
                  newvalues['address'])
        raise Reject('User not found in LDAP database')
    
    user = users[0][1]
    newvalues['username'] = user['uid'][0]
    aliasname = ''
    if aliasname_attribute in user:
        aliasname = user[aliasname_attribute][0]
    if not aliasname:
        sn = user[surname_attribute][0]
        gn = user[givenname_attribute][0]
        if sn and gn:
            aliasname = "%s, %s" % (sn, gn)
        elif sn:
            aliasname = sn

    newvalues['realname'] = aliasname
    log.info("Updated realname (%s) and username (%s) for user with address %s.",
             newvalues['realname'], newvalues['username'], newvalues['address'])

def init(db):
    db.user.audit('create', ldapuserauditor)
