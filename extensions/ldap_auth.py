#!/usr/bin/env python
# -*- coding: utf-8 -*-# 
# @(#)ldap_auth.py
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
"""
    This is an adpated MoinMoin - LDAP / Active Directory authentication to
    fit the needs for roundup ldap authentification. It first tries to login
    via LDAP (AD). In case this fails it tries to login against the roundup
    database. If a user is authenticated the first time via LDAP his
    attributes are copied over to the roundup database, including the
    password.  Therefore even if later on the LDAP login does not succeed a
    local login would require a password for authentication. If the user exist
    both in LDAP and in the local database, all the non-empty attributes which
    are empty in the local database are copied over.

    This code only creates a user object, the session will be established by
    moin automatically.

    python-ldap needs to be at least 2.0.0pre06 (available since mid 2002) for
    ldaps support - some older debian installations (woody and older?) require
    libldap2-tls and python2.x-ldap-tls, otherwise you get ldap.SERVER_DOWN:
    "Can't contact LDAP server" - more recent debian installations have tls
    support in libldap2 (see dependency on gnu2tls) and also in python-ldap.

    TODO: allow more configuration (alias name, ...) by using callables as
    parameters

    @copyright: 2006-2008 MoinMoin:ThomasWaldmann,
                2006 Nick Phillips
                2009 Andreas Floeter: adpatation for roundup done
    @license: GNU GPL, see COPYING for details.
"""

__docformat__ = 'reStructuredText'
__author__ = 'Antonio Messina <antonio.s.messina@gmail.com>'

# From http://www.roundup-tracker.org/cgi-bin/moin.cgi/LDAPLogin2
import logging
import os
import sys

import ldap

from roundup import password as PW
from roundup.cgi import exceptions
from roundup.cgi.actions import LoginAction
from roundup.i18n import _

LOGIN_FAILED = 0
LOGIN_SUCCEDED = 1

DEFAULT_VALS = {
    'use_local_auth' : None,
    # ldap / active directory server URI use ldaps://server:636 url for
    # ldaps, use ldap://server for ldap without tls (and set start_tls to
    # 0), use ldap://server for ldap with tls (and set start_tls to 1 or
    # 2).
    'server_uri' : 'ldap://localhost',
    # We can either use some fixed user and password for binding to LDAP.
    # Be careful if you need a % char in those strings - as they are used
    # as a format string, you have to write %% to get a single % in the
    # end.

    #'bind_dn' : 'binduser@example.org' # (AD)
    #'bind_dn' : 'cn=admin,dc=example,dc=org' # (OpenLDAP)
    #'bind_pw' : 'secret'
    # or we can use the username and password we got from the user:
    #'bind_dn' : '%(username)s@example.org'
    # DN we use for first bind (AD)
    #'bind_pw' : '%(password)s' # password we use for first bind
    # or we can bind anonymously (if that is supported by your directory).
    # In any case, bind_dn and bind_pw must be defined.
    'bind_dn' : '',
    'bind_pw' : '',
    # base DN we use for searching
    #base_dn : 'ou=SOMEUNIT,dc=example,dc=org'
    'base_dn' : '',
    # scope of the search we do (2 == ldap.SCOPE_SUBTREE)
    'scope' : ldap.SCOPE_SUBTREE,
    # LDAP REFERRALS (0 needed for AD)
    'referrals' : 0,
    # ldap filter used for searching:
    #search_filter : '(sAMAccountName=%(username)s)' # (AD)
    #search_filter : '(uid=%(username)s)' # (OpenLDAP)
    # you can also do more complex filtering like:
    # "(&(cn=%(username)s)(memberOf=CN=WikiUsers,OU=Groups,\
    #  DC=example,DC=org))"
    'search_filter' : '(uid=%(username)s)',
    # dn and pw to use to access info on the user, in case the ldap
    # server do not allow binding as user _and_ reading information.
    'search_bind_dn': '',
    'search_bind_pw': '',
    # some attribute names we use to extract information from LDAP:
    # ('givenName') ldap attribute we get the first name from
    'givenname_attribute' : None,
    # ('sn') ldap attribute we get the family name from
    'surname_attribute' : None,
    # ('displayName') ldap attribute we get the aliasname from
    'aliasname_attribute' : None,
    # ('mail') ldap attribute we get the email address from
    'email_attribute' : None,
    # called to make up email address
    'email_callback' : None,
    # coding used for ldap queries and result values
    'coding' : 'utf-8',
    # how long we wait for the ldap server [s]
    'timeout' : 10,
    # 0 = No, 1 = Try, 2 = Required
    'start_tls' : 0,
    'tls_cacertdir' : None,
    'tls_cacertfile' : None,
    'tls_certfile' : None,
    'tls_keyfile' : None,
    # 0 == ldap.OPT_X_TLS_NEVER (needed for self-signed certs)
    'tls_require_cert' : 0,
    # set to True to only do one bind - useful if configured to bind as
    # the user on the first attempt
    'bind_once' : False,
    # set to True if you want to autocreate user profiles
    'autocreate' : False,
    }

GC3_CONFIG_VALS = {'referrals' : 0,
               'use_local_auth' : None,
               'server_uri' : 'ldap://192.168.160.35',
               'base_dn' : 'dc=gc3,dc=uzh,dc=ch',
               'bind_dn': 'uid=%(username)s,ou=People,dc=gc3,dc=uzh,dc=ch',
               'bind_pw': '%(password)s',
               'search_filter' : '(uid=%(username)s)',
               'givenname_attribute' : 'cn',
               'surname_attribute' : 'cn',
               'aliasname_attribute' : 'cn',
               # 'email_attribute' : 'mail',
               'autocreate' : True
               }

CONFIG_VALS = {'referrals' : 0,
               'use_local_auth' : None,
               'server_uri' : 'ldaps://ldapauth.uzh.ch',
               'base_dn' : 'ou=People,ou=WebPass,ou=id,dc=uzh,dc=ch',
               'bind_dn': 'uid=%(username)s,ou=People,ou=WebPass,ou=id,dc=uzh,dc=ch',
               'bind_pw': '%(password)s',
               'search_filter' : '(uid=%(username)s)',
               'givenname_attribute' : 'givenName',
               'surname_attribute' : 'sn',
               'aliasname_attribute' : 'cn',
               'email_attribute' : 'mail',
               'autocreate' : True,
               }

class LDAPLoginAction(LoginAction):
    """ get authentication data from form, authenticate against LDAP (or Active
        Directory), fetch some user infos from LDAP and create a user object
        for that user. The session is kept by moin automatically.
    """
    def __init__(self, *args):
        self.set_values(DEFAULT_VALS)
        # self.use_local_auth = use_local_auth

        # self.server_uri = server_uri
        # self.bind_dn = bind_dn
        # self.bind_pw = bind_pw
        # self.base_dn = base_dn
        # self.scope = scope
        # self.referrals = referrals
        # self.search_filter = search_filter

        # self.givenname_attribute = givenname_attribute
        # self.surname_attribute = surname_attribute
        # self.aliasname_attribute = aliasname_attribute
        # self.email_attribute = email_attribute
        # self.email_callback = email_callback

        # self.coding = coding
        # self.timeout = timeout

        # self.start_tls = start_tls
        # self.tls_cacertdir = tls_cacertdir
        # self.tls_cacertfile = tls_cacertfile
        # self.tls_certfile = tls_certfile
        # self.tls_keyfile = tls_keyfile
        # self.tls_require_cert = tls_require_cert

        # self.bind_once = bind_once
        # self.autocreate = autocreate
        LoginAction.__init__(self, *args)
        self.LOG = self.db.get_logger()

    def ldap_login(self, username='', password=''):
        """Perform a login against LDAP."""
        self.auth_method = 'ldap'

        # we require non-empty password as ldap bind does a anon (not password
        # protected) bind if the password is empty and SUCCEEDS!
        if not password:
            msg = _('Empty password for user "%s"') % self.client.user
            self.LOG.debug(msg)
            self.client.error_message.append(msg)
            return LOGIN_FAILED
        try:
            try:
#                u = None
                dn = None
                coding = self.coding
                self.LOG.debug("Setting misc. ldap options...")
                # ldap v2 is outdated
                ldap.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)
                ldap.set_option(ldap.OPT_REFERRALS, self.referrals)
                ldap.set_option(ldap.OPT_NETWORK_TIMEOUT, self.timeout)

                if hasattr(ldap, 'TLS_AVAIL') and ldap.TLS_AVAIL:
                    for option, value in (
                        (ldap.OPT_X_TLS_CACERTDIR, self.tls_cacertdir),
                        (ldap.OPT_X_TLS_CACERTFILE, self.tls_cacertfile),
                        (ldap.OPT_X_TLS_CERTFILE, self.tls_certfile),
                        (ldap.OPT_X_TLS_KEYFILE, self.tls_keyfile),
                        (ldap.OPT_X_TLS_REQUIRE_CERT, self.tls_require_cert),
                        (ldap.OPT_X_TLS, self.start_tls),
                        #(ldap.OPT_X_TLS_ALLOW, 1),
                    ):
                        if value is not None:
                            self.LOG.debug("Setting LDAP option %s to %s",
                                      option, value)
                            ldap.set_option(option, value)

                server = self.server_uri
                self.LOG.debug("Trying to initialize %r." % server)
                l = ldap.initialize(server)
                self.LOG.debug("Connected to LDAP server %r." % server)

                if self.start_tls and server.startswith('ldap:'):
                    self.LOG.debug("Trying to start TLS to %r." % server)
                    try:
                        l.start_tls_s()
                        self.LOG.debug("Using TLS to %r." % server)
                    except (ldap.SERVER_DOWN, ldap.CONNECT_ERROR), err:
                        self.LOG.warning("Couldn't establish TLS to %r (err: %s)." %\
                                        (server, str(err)))
                        return LOGIN_FAILED

                # you can use %(username)s and %(password)s here to get the
                # stuff entered in the form:
                binddn = self.bind_dn % locals()
                bindpw = self.bind_pw % locals()
                self.LOG.debug("Binding as %s" % (binddn.encode(coding)))
                l.simple_bind_s(binddn.encode(coding),
                                bindpw.encode(coding))
                self.LOG.debug("Bound with binddn %r" % binddn)
                if self.search_bind_dn:
                    self.LOG.debug("Binding as %s for searching attrs",
                              binddn.encode(coding))
                    l.simple_bind_s(self.search_bind_dn.encode(coding),
                                   self.search_bind_pw.encode(coding))
                    self.LOG.debug("Bound with binddn %r" % self.search_bind_dn)

                # you can use %(username)s here to get the stuff entered in
                # the form:
                filterstr = self.search_filter % locals()
                self.LOG.debug("Searching %r" % filterstr)
                attrs = [getattr(self, attr) for attr in [
                                         'email_attribute',
                                         'aliasname_attribute',
                                         'surname_attribute',
                                         'givenname_attribute',
                                         ] if getattr(self, attr) is not None]
                lusers = l.search_st(self.base_dn, self.scope,
                                     filterstr.encode(coding), attrlist=attrs,
                                     timeout=self.timeout)
                # we remove entries with dn == None to get the real result list:
                lusers = [(dn, ldap_dict) for dn, ldap_dict in lusers \
                              if dn is not None]
                for dn, ldap_dict in lusers:
                    self.LOG.debug("dn:%r" % dn)
                    for key, val in ldap_dict.items():
                        self.LOG.debug("    %r: %r" % (key, val))

                result_length = len(lusers)
                if result_length != 1:
                    if result_length > 1:
                        self.LOG.warning("Search found more than one (%d) matches \
for %r." % (result_length, filterstr))
                    if result_length == 0:
                        self.LOG.debug("Search found no matches for %r." % \
                                      (filterstr, ))
                    msg = _("Invalid username or password.")
                    self.LOG.debug(msg)
                    self.client.error_message.append(msg)
                    return LOGIN_FAILED

                dn, ldap_dict = lusers[0]
                if not self.bind_once:
                    self.LOG.debug("DN found is %r, trying to bind with pw" % dn)
                    l.simple_bind_s(dn, password.encode(coding))
                    self.LOG.debug("Bound with dn %r (username: %r)" % \
                                  (dn, username))

                if self.email_callback is None:
                    if self.email_attribute:
                        email = ldap_dict.get(self.email_attribute, [''])[0].\
decode(coding)
                    else:
                        email = None
                else:
                    email = self.email_callback(ldap_dict)

                aliasname = ''
                try:
                    aliasname = ldap_dict[self.aliasname_attribute][0]
                except (KeyError, IndexError):
                    pass
                if not aliasname:
                    sn = ldap_dict.get(self.surname_attribute, [''])[0]
                    gn = ldap_dict.get(self.givenname_attribute, [''])[0]
                    if sn and gn:
                        aliasname = "%s, %s" % (sn, gn)
                    elif sn:
                        aliasname = sn
                aliasname = aliasname.decode(coding)

                self.LOG.debug("User data [%r, %r, %r] " % \
                              (username, email, aliasname))
                if not email:
                    email = '%s@s3it.uzh.ch' % username
                self.add_attr_local_user(username=username,
                                         password=password,
                                         address=email,
                                         realname=aliasname)
                msg = "Login succeded with LDAP authentication for user '%s'." \
% username
                self.LOG.debug(msg)
                # Determine whether the user has permission to log in. Base
                # behaviour is to check the user has "Web Access".
                rights = "Web Access"
                if not self.hasPermission(rights):
                    msg = _("You do not have permission '%s' to login" % rights)
                    self.LOG.debug("%s, %s, %s", msg, self.client.user, rights)
                    raise exceptions.LoginError, msg
                return LOGIN_SUCCEDED
            except ldap.INVALID_CREDENTIALS, err:
                self.LOG.debug("invalid credentials (wrong password?) for dn %r \
(username: %r)" % (dn, username))
                return LOGIN_FAILED
        except ldap.SERVER_DOWN, err:
            # looks like this LDAP server isn't working, so we just try the
            # next authenticator object in cfg.auth list (there could be some
            # second ldap authenticator that queries a backup server or any
            # other auth method).
            ## only one auth server supported for roundup, change it
            self.LOG.error("LDAP server %s failed (%s). Trying to authenticate \
with next auth list entry." % (server, str(err)))
            msg = "LDAP server %(server)s failed." % {'server': server}
            self.LOG.debug(msg)
            return LOGIN_FAILED
        except Exception, err:
            self.LOG.error("Couldn't establish TLS to %r (err: %s)." % (server,
                                                                     str(err)))
            self.LOG.exception("caught an exception, traceback follows...")
            return LOGIN_FAILED

    def set_values(self, props):
        for kprop, value in props.items():
            setattr(self, kprop, value)

    def local_user_exists(self):
        """Verify if the given user exists. As a side effect set the
        'client.userid'."""
        # make sure the user exists
        try:
            self.client.userid = self.db.user.lookup(self.client.user)
        except KeyError:
            msg = _("Unknown user '%s'") % self.client.user
            self.LOG.debug("__['%s'", msg)
            self.client.error_message.append(
                        _("Unknown user  '%s'") % self.client.user)
            return False
        return True

    def local_login(self, password):
        """Try local authentication."""
        self.auth_method = 'localdb'
        if not self.local_user_exists():
            return LOGIN_FAILED
        if not self.verifyPassword(self.client.userid, password):
            msg = _('Invalid password')
            self.LOG.debug("%s for userid=%s", msg, self.client.userid)
            self.client.error_message.append(msg)
            return LOGIN_FAILED

        # Determine whether the user has permission to log in. Base behaviour
        # is to check the user has "Web Access".
        rights = "Web Access"
        if not self.hasPermission(rights):
            msg = _("You do not have permission to login")
            self.LOG.debug("%s, %s, %s", msg, self.client.user, rights)
            raise exceptions.LoginError, msg
        return LOGIN_SUCCEDED

    def verifyLogin(self, username, password):
        """Verify the login of `username` with `password`. Try first LDAP if
        this is specified as authentication source, and then login against
        local database."""
        self.LOG.debug("username=%s password=%s", username, '*'*len(password))
        self.set_values(CONFIG_VALS)
        authenticated = False
        if not self.use_local_auth:
            self.LOG.debug("LDAP authentication")
            authenticated = self.ldap_login(username, password)
            if authenticated:
                self.LOG.debug("User '%s' authenticated against LDAP.",
                          username)
        if not authenticated:
            self.LOG.debug("Local database authentication")
            authenticated = self.local_login(password)
            if authenticated:
                self.LOG.debug("User '%s' authenticated against local database.",
                          username)
        if not authenticated:
            msg = _("Could not authenticate user '%s'" % username)
            self.LOG.debug(msg)
            raise exceptions.LoginError, msg
        return authenticated

    def add_attr_local_user(self, **props):
        """Add the attributes `props` for a user to the local database if
        those are still empty. If 'self.autocreate' is False then the user is
        considered a new user."""
        props['password'] = PW.Password(props['password'])
        self.db.journaltag = 'admin'
        try:
            self.client.userid = self.db.user.lookup(self.client.user)
            # update the empty values with LDAP values
            uid = self.client.userid
            if self.autocreate:
                for pkey, prop in props.items():
                    try:
                        self.LOG.debug("Look key '%s' for user '%s'", pkey, uid)
                        value = self.db.user.get(uid, pkey)
                        self.LOG.debug("Value %r for key,user '%s','%s'", value,
                                  pkey, uid)
                        if not value:
                            self.LOG.debug("Set value %r for property %r of user \
'%s'", props[pkey], pkey, self.client.user)
                            pair = {pkey : props[pkey]}
                            self.db.user.set(uid, **pair)
                    except Exception, err_msg:
                        self.LOG.exception("caught an exception, traceback follows.\
..")
        except KeyError:
            # add new user to local database
            props['roles'] = self.db.config.NEW_WEB_USER_ROLES
            self.userid = self.db.user.create(**props)
            self.db.commit()
            ## ?? why do we re-read the userid ??
            # self.client.userid = self.db.user.lookup(self.client.user)
            msg = u"New account created for user '%s'" % props['username']
            self.LOG.debug(msg)
            self.client.ok_message.append(msg)

def init(instance):
    """Register the roundup action 'login'."""
    instance.registerAction('login', LDAPLoginAction)
