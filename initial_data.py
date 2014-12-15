from roundup.password import Password

#
# TRACKER INITIAL PRIORITY AND STATUS VALUES
#

topic = db.getclass('topic')
topic.create(name="Hobbes", order="1")
topic.create(name="Schroedinger", order="2")
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
status.create(name='new', order = '1')
status.create(name='open', order='2')
status.create(name='closed', order='3')
status.create(name='invalid', order='4')
status.create(name='pending', description='user feedback required', order='5')
status.create(name='wontfix', order='6')

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
