from roundup.password import Password

#
# TRACKER INITIAL PRIORITY AND STATUS VALUES
#

component = db.getclass('component')
component.create(name="backend", order="1")
component.create(name="frontend", order="2")
component.create(name="documentation", order="3")
component.create(name="specification", order="4")

priority = db.getclass('priority')
priority.create(name='immediate', order='1')
priority.create(name='urgent', order='2')
priority.create(name='high', order='3')
priority.create(name='normal', order='4')
priority.create(name='low', order='5')

status = db.getclass('status')
status.create(name = "new", order = "1")
status.create(name='open', order='2')
status.create(name='closed', order='3')
status.create(name='pending', description='user feedback required', order='4')

resolution = db.getclass('resolution')
resolution.create(name='accepted', order='1')
resolution.create(name='duplicate', order='2')
resolution.create(name='fixed', order='3')
resolution.create(name='invalid', order='4')
resolution.create(name='later', order='5')
resolution.create(name='out of date', order='6')
resolution.create(name='postponed', order='7')
resolution.create(name='rejected', order='8')
resolution.create(name='remind', order='9')
resolution.create(name='wont fix', order='10')
resolution.create(name='works for me', order='11')

keyword = db.getclass("keyword")
keyword.create(name="patch", description="Contains patch")

#
# create the two default users
user = db.getclass('user')
user.create(username="admin", password=adminpw, address=admin_email, roles='Admin')
user.create(username="anonymous", roles='Anonymous')
user.create(username="user", roles='User', password=adminpw)
user.create(username="operator", roles='User, Operator', password=adminpw)
# user.create(username="coordinator", roles='User, Developer, Coordinator')

#SHA: ee91ee3b5f8f356f7f3c8f26d21eba2fc9f4e17f
