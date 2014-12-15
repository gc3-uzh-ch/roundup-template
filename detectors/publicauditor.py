# Set `public` field to 0 if no value is selected.
# By default new issues must be private
# Fixes issue 267: https://www.s3it.uzh.ch/help/issue267
def preset_private(db, cl, nodeid, newvalues):
    """ Make sure the status is set on new bugs"""

    if newvalues.has_key('public') and newvalues['public'] is not None:
        return

    newvalues['public'] = 0


def init(db):
    # fire before changes are made
    db.issue.audit('create', preset_private)

