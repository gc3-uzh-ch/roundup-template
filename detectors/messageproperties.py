"""This file allows you to modify the fields of an issue by adding
some special *command lines* to the content of a message of the issue.

Usage
-----

A "command line" is a line in the form::

    <property>: <value>

where ``<property>`` is a property of the issue.

Only the first part of message content is scanned for command
lines. After the first non-command line is found, parsing of the
content is stopped, and the remaining text is used as the content of
the message. Also note that:

* property names are always converted to lowercase therefore, it will only
  work if the issue properties are all lowercase!

* empty lines are ignored, so that the following text::

      status: solved
      
      topics: T1,T2,T3

  has the same effect than::

      status: solved      
      topics: T1,T2,T3

* If the property is a ``Multilink`` (i.e. it's a link to multiple
  objects, like ``messages`` field), then ``<value>`` is split using
  commas (,) as field separator, leading and trailing spaces are
  removed from single fields, and the name is used to find the
  corresponding value. 

  For instance, if your ``issue`` class is defined as::

        issue = IssueClass(db, "issue",
                           topics=Multilink('topic'),
                           ...)

  and the following command line is found::

      Topics: Topic1, Topic2

  then the property will be set using the IDs corresponding to ``Topic1`` and ``Topic2`` fields, using code like::

      fields = value.split(',')
      issue.topics = [db.topic.lookup(fld) for fld in fields]

  Also, you can *add* or *remove* specific fields without setting all
  the fields, using the following syntax::

      topics: +Topic1, -Topic2

  will add `Topic3` and remove `Topic2` to the list of topics, but
  leave untouched all the other values.

* If the property is a ``Date``, then the standard RoundUp date
  parsing is performed.

* Boolean `True` values can be set using either `true`, `True` or
`1`. Boolean `False` values can be inserted using `false`, `False` or
`0`.

Implementation note
-------------------

When a new issue is created, *first* are created the messages, and
*then* the issue is created. This means that the issue a message
refers may not be created when the auditor ``db.msg.audit('set',...)``
is created, therefore we cannot modify the issue with an *auditor*.

However, we want to remove the command lines from the content of the
message, but this cannot be done in a *reactor*, because otherwise we
will fire up the detector over and over again, and will get a `Maximum
Recursion Depth Exceeded` error.

In order to solve this issue, the message must have a *fake* field
`mailcommands`::

    msg = FileClass(db, "msg",
                    ...
                    mailcommands=String(),
    )

then, the ``properties_parser`` **auditor** is called first: this will
parse the content and add command lines to `mailcommands`, and remove
them from the `content` of the message.

At this point, we can call the ``properties_updater`` **reactor**,
which is called on **set** action though, instead of **create**. This
reactor reads `mailcommands` value and updating the issue.

Finally, we *must* clear the `mailcommands` field, in order to avoid
that updating the text of the message will update again the issue
using old, stale values. This is done by calling
``clear_mailcommands`` **reactor**, but with priority 110 (deafult is
100), to ensure it is called *after* ``priorities_updater``. This
reactor is always called **twice**, but since it's very easy to make
it idempotent it's not a big deal.
"""

import re
import roundup.hyperdb

def properties_parser(db, cl, nodeid, newvalues):
    """Prase the content of the message, identify "command lines" and
    update `mailcommands`, `content` and `summary`.

    """
    if 'content' not in newvalues:
        # Nothing to parse
        return

    log = db.get_logger()
    # The following is a bit tricky:
    # We need to ignore any *set* coming from a "real" set, 

    contentlines = newvalues['content'].split('\n')
    mailcommands = []

    for line in contentlines[:]:
        if not line:
            # Empty line, just skip it
            continue
        match = re.search('^(?P<prop>[^:]*):\s*(?P<value>.*)', line, re.I)
        
        if not match:
            # We are done parsing the input, this is a "regular"
            # comment line
            break
        elif match.group('prop').lower() not in db.issue.properties:
            # Possibly a mispelled property. Just skip it
            continue


        log.debug("messageproperties.properties_parser: found a new command-line: '%s'" % line)
        mailcommands.append(line)
        contentlines.remove(line)

    # Update message values
    newvalues['mailcommands'] = str.join('\n', mailcommands)
    newvalues['content'] = str.join('\n', contentlines).strip()
    newvalues['summary'] = contentlines[0]

def properties_updater(db, cl, nodeid, oldvalues):
    """This function parses the `mailcommands` field and will set issue
    properties accordingly.

    """
    if not nodeid:
        return

    log = db.get_logger()
    msg = db.msg.getnode(nodeid)
    issues = db.issue.find(messages=nodeid)
    if not issues:
        # No issues found for this message! How is that possible?
        log.error("messageproperties.properties_updater: No issue related to msg %s!!! Stopping processing",
                  nodeid)
        return

    issue = db.issue.getnode(issues[0])

    if not msg.mailcommands:
        return

    contentlines = msg.mailcommands.split('\n')

    for line in contentlines:
        match = re.search('^(?P<prop>[^:]*):\s*(?P<value>.*)', line, re.I)
        
        if not match or match.group('prop').lower() not in db.issue.properties:
            # We are done parsing the input
            log.info("messageproperties.properties_updater: No more line to process in content body")
            break

        log.debug("messageproperties.properties_updater: Processing content line '%s'", line)
        propname = match.group('prop').lower()
        propclass = db.issue.properties[propname]
        
        if isinstance(propclass, roundup.hyperdb.Multilink):
            propdb = db.getclass(propclass.classname)
            # If at least one property name starts with +, all properties will be
            # added. 
            # Any property staritng with - will be removed.
            all_props = [p.strip() for p in match.group('value').split(',')]
            prop_del = sum([propdb.stringFind(**{propdb.key: p[1:]}) for p in all_props if p[0] == '-'],
                           [])
            prop_add = sum([propdb.stringFind(**{propdb.key: p[1:]}) for p in all_props if p[0] == '+'],
                           [])
            prop_set = sum([propdb.stringFind(**{propdb.key: p}) for p in all_props if p[0] not in ('+', '-')],
                           [])

            cur_list = issue[propname]
            for i in prop_del:
                cur_list.remove(i)
            if prop_del or prop_add:
                for i in prop_add + prop_set:
                    cur_list.append(i)
            else:
                cur_list = prop_add + prop_set

            log.debug("messageproperties.properties_updater: Setting property '%s' of issue%s to '%s'.",
                      propname, issue.id, str.join(', ', set(cur_list)))
            issue[propname] = list(set(cur_list))
        elif isinstance(propclass, roundup.hyperdb.Link):
            propdb = db.getclass(propclass.classname)
            propvalue = propdb.stringFind(**{propdb.key: match.group('value')})
            if propvalue:
                log.debug("messageproperties.properties_updater: Setting property '%s' of issue%s to '%s'.", propname, issue.id, propvalue[0])
                issue[propname] = propvalue[0]
        elif isinstance(propclass, roundup.hyperdb.Date):
            # Date is a special case
            try:
                propvalue = propclass.from_raw(match.group('value'), db)
                if propvalue:
                    log.debug("messageproperties.properties_updater: Setting property '%s' of issue%s to '%s'.", propname, issue.id, propvalue)
                    issue[propname] = propvalue
            except KeyError:
                # An invalid date raises a KeyError value. Don't ask me why...
                # >>> from roundup.hyperdb import Date
                # >>> Date().from_raw('01/02/2014', db)
                # Traceback (most recent call last):
                #   File "<stdin>", line 1, in <module>
                #   File "/usr/local/roundup-env/local/lib/python2.7/site-packages/roundup/hyperdb.py", line 103, in from_raw
                #     'date (%s)')%(kw['propname'], value, message)
                # KeyError: 'propname'
                # >>> Date().from_raw('asd', db)
                # Traceback (most recent call last):
                #   File "<stdin>", line 1, in <module>
                #   File "/usr/local/roundup-env/local/lib/python2.7/site-packages/roundup/hyperdb.py", line 103, in from_raw
                #     'date (%s)')%(kw['propname'], value, message)
                # KeyError: 'propname'
                # >>> Date().from_raw('2014-01-02', db)
                # <Date 2014-01-02.00:00:00.000>
                log.error("messageproperties.properties_updater: Invalid date format '%s'. Should be in yyyy[-mm[-dd]], mm-dd, hh:mm:ss or [\dsmywd]+" % match.group('value'))
        else:
            propvalue = propclass.from_raw(match.group('value'))
            log.debug("messageproperties.properties_updater: Setting property '%s' of issue%s to '%s'.", propname, issue.id, propvalue)
            issue[propname] = propvalue
            
    # This is useful only to update old tickets!
    # Relates to issue 235: https://www.s3it.uzh.ch/help/issue235
    if not issue.status and not oldvalues.get('status', False):
        try:
            issue['status'] = db.status.lookup('new')
        except KeyError:
            log.error("messageproperties.properties_updater: No status `new` available. Can't set default status.")

    # This is useful only to update old tickets!
    # Relates to issue 233: https://www.s3it.uzh.ch/help/issue233
    if not issue.priority and not oldvalues.get('priority', False):
        try:
            issue['priority'] = db.priority.lookup('normal')
        except KeyError:
            log.error("messageproperties.properties_updater: No priority `normal` available. Can't set default priority.")

def clear_mailcommands(db, cl, nodeid, oldvalues):
    """Used to remove mailcommands after properties_updater is done"""
    msg = db.msg.getnode(nodeid)
    if not msg.mailcommands:
        db.get_logger().debug("messageproperties.clear_mailcommands: mailcommands from msg%s is empty" % nodeid)
        return
    db.get_logger().debug("messageproperties.clear_mailcommands: Clearing mailcommands from msg%s" % nodeid)
    msg.mailcommands = ''

def init(db):
    # fire before changes are made
    db.msg.audit('create', properties_parser)
    db.msg.react('set', properties_updater, priority=100)
    db.msg.react('set', clear_mailcommands, priority=110)

# vim: set filetype=python ts=4 sw=4 et si
#SHA: 4dc3c37fa69612010a9684a544585aabe836bf35
