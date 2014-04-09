
def init_severity(db, cl, nodeid, newvalues):
    """Make sure severity is set on new bugs"""
    if newvalues.has_key('severity') and newvalues['severity']:
        return

    normal = db.severity.lookup('normal')
    newvalues['severity'] = normal

def init(db): pass
    #db.bug.audit('create', init_severity)
#SHA: fb6ec9634bd06a164f2e0b1d7291ebfaa7571cbc
