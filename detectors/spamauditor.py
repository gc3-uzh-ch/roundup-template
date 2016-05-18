def retire_issue_and_creator(db, cl, nodeid, oldvalues):
    # When status is set to "spam", the issue and its creator are retired.
    # No notification is sent to the creator.
    msg = db.issue.getnode(nodeid)
    spamstatus = db.status.lookup('spam')
    log = db.get_logger()
    if msg.status and msg.status == spamstatus:
        log.info("retire_issue_and_creator: Retiring issue %s and user %s",
                 nodeid, msg.creator)
        db.issue.retire(nodeid)
        db.user.retire(msg.creator)


def init(db):
    db.issue.react('set', retire_issue_and_creator)
