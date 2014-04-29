import re

from roundup.mailgw import parseContent
import roundup.hyperdb


def properties_updater(db, cl, nodeid, newvalues):
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
    if not nodeid:
        return

    msg = db.msg.getnode(nodeid)
    issues = db.issue.find(messages=nodeid)
    if not issues:
        # No issues found for this message! How is that possible?
        return

    issue = db.issue.getnode(issues[0])

    contentlines = msg.content.split('\n')

    for line in contentlines[:]:
        match = re.search('^(?P<prop>[^:]*):\s*(?P<value>.*)', line, re.I)
        
        if not match or match.group('prop').lower() not in db.issue.properties:
            # We are done parsing the input
            break

        contentlines.remove(line)
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

            cur_topics = issue.topics
            for i in prop_del:
                cur_topics.remove(i)
            if prop_del or prop_add:
                for i in prop_add + prop_set:
                    cur_topics.append(i)
            else:
                cur_topics = prop_add + prop_set

            issue[propname] = list(set(cur_topics))
        elif isinstance(propclass, roundup.hyperdb.Link):
            propdb = db.getclass(propclass.classname)
            propvalue = propdb.stringFind(**{propdb.key: match.group('value')})
            if propvalue:
                issue[propname] = propvalue[0]
        else:
            issue[propname] = propclass.from_raw(match.group('value'))
            
    newcontent = str.join('\n', contentlines).strip()

    if newcontent != msg.content:
        newvalues['content'] = newcontent
        msg.content = newcontent
        msg.summary = msg.content.split('\n')[0]

def init(db):
    # fire before changes are made
    db.msg.react('set', properties_updater)

# vim: set filetype=python ts=4 sw=4 et si
#SHA: 4dc3c37fa69612010a9684a544585aabe836bf35
