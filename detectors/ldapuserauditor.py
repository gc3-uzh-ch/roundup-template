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
    ldap_conf_file = os.path.join(db.config.ext['HOME'], 'ldap_config.ini')
    if not os.path.exists(ldap_conf_file):
        raise Reject('Ldap not configured')


    cfg = RawConfigParser()
    cfg.read(ldap_conf_file)
    if not cfg.has_section('ldap'):
        raise Reject('Ldap not configured')

    ldap.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)
    ldap.set_option(ldap.OPT_REFERRALS, 0)
    l = ldap.initialize(cfg.get('ldap', 'server_uri'))
    l.simple_bind_s(cfg.get('ldap', 'search_bind_dn'), cfg.get('ldap', 'search_bind_pw'))
    users = l.search_st(cfg.get('ldap', 'base_dn'), ldap.SCOPE_SUBTREE,
                'mail=%s' % newvalues['address'])
    if not users:
        # Raise an exception
        raise Reject('User not found in LDAP database')
    
    user = users[0][1]
    newvalues['username'] = user['uid'][0]
    aliasname = ''
    if cfg.get('ldap', 'aliasname_attribute') in user:
        aliasname = user[cfg.get('ldap', 'aliasname_attribute')][0]
    if not aliasname:
        sn = user[cfg.get('ldap', 'surname_attribute')][0]
        gn = user[cfg.get('ldap', 'givenname_attribute')][0]
        if sn and gn:
            aliasname = "%s, %s" % (sn, gn)
        elif sn:
            aliasname = sn
    newvalues['realname'] = aliasname

def init(db):
    db.user.audit('create', ldapuserauditor)
