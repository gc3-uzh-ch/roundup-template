# Set priority to `normal` if none is selected.
# Fixes issue 233: https://www.s3it.uzh.ch/help/issue233
def preset_new(db, cl, nodeid, newvalues):
    """ Make sure the status is set on new bugs"""

    if newvalues.has_key('priority') and newvalues['priority']:
        return

    normal = db.priority.lookup('normal')
    newvalues['priority'] = normal


def init(db):
    # fire before changes are made
    db.issue.audit('create', preset_new)

