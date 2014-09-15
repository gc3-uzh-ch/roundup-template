import re

from roundup.mailgw import parseContent
import roundup.hyperdb

def properties_parser(db, cl, nodeid, newvalues):
    """This function will:
    * parse the content of the message for command lines
    * move command lines into the `messagecommands` field
    * update the content of the message
    """
    if 'content' not in newvalues:
        return

    log = db.get_logger().getChild('messageproperties')
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
            log.info("No more line to process in content body")
            break
        elif match.group('prop').lower() not in db.issue.properties:
            # Possibly a mispelled property. Just skip it
            continue

        mailcommands.append(line)
        contentlines.remove(line)

    # Update message values
    newvalues['mailcommands'] = str.join('\n', mailcommands)
    newvalues['content'] = str.join('\n', contentlines).strip()
    newvalues['summary'] = contentlines[0]

def properties_updater(db, cl, nodeid, oldvalues):
    """This function scans the content of an email for special fields to
    be used to update the properties of an issue.

    It scans the beginning of a message, each line starting with:

        <property_name>: <property_value>

    is interpreted as: set the property `property_name` of the related issue to `property_value`.
    
    `property_value` must be the "name" of the property, so that you can write:

        Status: open

    and this function will look into the specific database for the correct id corresponding to that name.

    If the property is a `Multilink` (i.e. its a link to multiple
    objects) the `property_value` will be split into multiples names
    using comma (,) as field separator, and the resulting value will
    be a list of IDs corresponding to these names. For instance, if you write:

        Topics: Topic1, Topic2

    and your issue class definition looks like:

        issue = IssueClass(db, "issue",
                           topics=Multilink('topic'),
                           ...)

    then the property will be set to the list of IDs corresponding to 'Topic1' and 'Topic2'.

    For Multilink properties, you can also add or remove specific
    elements, by prefixing '+' or '-'. For instance:

        Topics: +Topic3, -Topic2

    will add `Topic3` and remove `Topic2` to the list of topics.

    """
    log = db.get_logger().getChild('messageproperties')
    log.debug("called with nodeid: %s" % nodeid)
    if not nodeid:
        return

    msg = db.msg.getnode(nodeid)
    issues = db.issue.find(messages=nodeid)
    if not issues:
        # No issues found for this message! How is that possible?
        log.error("No issue related to msg %s!!! Stopping processing",
                  nodeid)
        return

    issue = db.issue.getnode(issues[0])

    contentlines = msg.mailcommands.split('\n')

    for line in contentlines:
        match = re.search('^(?P<prop>[^:]*):\s*(?P<value>.*)', line, re.I)
        
        if not match or match.group('prop').lower() not in db.issue.properties:
            # We are done parsing the input
            log.info("No more line to process in content body")
            break

        log.debug("Processing content line '%s'", line)
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

            log.debug("Setting property %s to %s.",
                      propname, str.join(', ', set(cur_list)))
            issue[propname] = list(set(cur_list))
        elif isinstance(propclass, roundup.hyperdb.Link):
            propdb = db.getclass(propclass.classname)
            propvalue = propdb.stringFind(**{propdb.key: match.group('value')})
            if propvalue:
                log.debug("Setting property %s to %s.", propname, propvalue[0])
                issue[propname] = propvalue[0]
        elif isinstance(propclass, roundup.hyperdb.Date):
            # Date is a special case
            try:
                propvalue = propclass.from_raw(match.group('value'), db)
                if propvalue:
                    log.debug("Setting property %s to %s.", propname, propvalue)
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
                log.error("Invalid date format '%s'. Should be in yyyy[-mm[-dd]], mm-dd, hh:mm:ss or [\dsmywd]+" % match.group('value'))
        else:
            propvalue = propclass.from_raw(match.group('value'))
            log.debug("Setting property %s to %s.", propname, propvalue)
            issue[propname] = propvalue
            
    # This is useful only to update old tickets!
    # Relates to issue 235: https://www.s3it.uzh.ch/help/issue235
    if not issue.status and not oldvalues.get('status', False):
        try:
            issue['status'] = db.status.lookup('new')
        except KeyError:
            log.error("No status `new` available. Can't set default status.")

    # This is useful only to update old tickets!
    # Relates to issue 233: https://www.s3it.uzh.ch/help/issue233
    if not issue.priority and not oldvalues.get('priority', False):
        try:
            issue['priority'] = db.priority.lookup('normal')
        except KeyError:
            log.error("No priority `normal` available. Can't set default priority.")


def init(db):
    # fire before changes are made
    db.msg.audit('set', properties_parser)
    db.msg.react('set', properties_updater)

# vim: set filetype=python ts=4 sw=4 et si
#SHA: 4dc3c37fa69612010a9684a544585aabe836bf35
