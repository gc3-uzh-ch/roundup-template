
def add_keywords(db, cl, nodeid, newvalues):
    """add keywords if they are not added"""
    log = db.get_logger()

    log.debug("add_keywords: called with newvalues: %s, nodeid: %s" % (newvalues, nodeid))
    
    if not newvalues.has_key('extra_keywords') or not newvalues['extra_keywords']:
        return

    log.debug('add_keywords: extra_keywords: %s' % newvalues.get('extra_keywords'))
    newkeywords = [k.strip() for k in newvalues.get('extra_keywords','').split(',')]
    if 'keywords' not in newvalues:
        if nodeid:
            issue = db.issue.getnode(nodeid)
            newvalues['keywords'] = issue.keywords
        else:
            newvalues['keywords'] = []
    for keyword in newkeywords:
        # Hacker extension: If the keyword begins with '-', it means
        # we want to *remove* it from the list of keywords.
        try:
            if keyword.startswith('-'):
                keyword_id = db.keyword.lookup(keyword[1:])
                if keyword_id in newvalues['keywords']:
                    newvalues['keywords'].remove(keyword_id)
            else:
                newvalues['keywords'].append(db.keyword.lookup(keyword))
        except KeyError:
            # Key not found. Create one
            log.debug("add_keywords: creating new keyword %s" % keyword)
            newid = db.keyword.create(name=keyword)
            newvalues['keywords'].append(newid)
            log.debug("add_keywords: new keyword %s has id %s" % (keyword, newid))

    newvalues['extra_keywords'] = ''
    log.debug("add_keywords: new `newvalues`: %s" % newvalues)

def init(db):
    db.issue.audit('create', add_keywords)
    db.issue.audit('set', add_keywords)

