# Set status to `new` if no status is set.
# Fixes issue 235: https://www.s3it.uzh.ch/help/issue235
def preset_new(db, cl, nodeid, newvalues):
    """ Make sure the status is set on new bugs"""

    if newvalues.has_key('status') and newvalues['status']:
        return

    new = db.status.lookup('new')
    newvalues['status'] = new


def init(db):
    # fire before changes are made
    db.issue.audit('create', preset_new)

