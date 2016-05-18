from roundup.password import Password

#
# TRACKER INITIAL PRIORITY AND STATUS VALUES
#

topic = db.getclass('topic')
topic.create(name="Hydra", order="3")
topic.create(name="GC3Pie", order="4")
topic.create(name="Elasticluster", order="5")
topic.create(name="Roundup", order="6")
topic.create(name="Generic request", order="7")

priority = db.getclass('priority')
priority.create(name='immediate', order='1')
priority.create(name='urgent', order='2')
priority.create(name='high', order='3')
priority.create(name='normal', order='4')
priority.create(name='low', order='5')

status = db.getclass('status')
status.create(name='new', order = '1', description='pending action from operator')
status.create(name='in progress', order='2', description='still working on it')
status.create(name='solved', order='3', description='issue has been successfully fixed')
status.create(name='invalid', order='4', description="invalid issue - issue does not exist")
status.create(name='pending', description='user feedback required, waiting', order='5')
status.create(name='wontfix', order='6', description="issue exists but will not be fixed")
status.create(name='on hold', order='7', description="we don't want or can't work on the issue right now, but will do it in the future")
status.create(name='spam', order='8', description="SPAM: retire issue and creator, do not send notification")

# keyword = db.getclass("keyword")
# keyword.create(name="patch", description="Contains patch")

#
# create the two default users
user = db.getclass('user')
user.create(username="admin", password=adminpw, address=admin_email, roles='Admin')
user.create(username="anonymous", roles='Anonymous')
user.create(username="user", roles='User', password=adminpw)
user.create(username="operator", roles='User, Operator', password=adminpw)
# user.create(username="coordinator", roles='User, Developer, Coordinator')

#SHA: 86d4a7d59b383c0063c7d1e5d411a6a92ad7e017
