
def audit_html_files(db, cl, nodeid, newvalues):
    if newvalues.has_key('type') and newvalues['type'] == 'text/html':
        newvalues['type'] = 'text/plain'
    

def init(db):
    db.file.audit('set', audit_html_files)
    db.file.audit('create', audit_html_files)
#SHA: 5f08595cf1a9a422940e1a25ba357c2c9c82b0fb
