
#
# TRACKER SCHEMA
#

# Class automatically gets these properties:
#   creation = Date()
#   activity = Date()
#   creator = Link('user')
#   actor = Link('user')




# Topic
topic = Class(db, 'topic',
                  name=String(),
                  description=String(),
                  order=Number(),
                  assign_to=Link('user'))
topic.setkey('name')



# Priority
priority = Class(db, 'priority',
                 name=String(),
                 description=String(),
                 order=Number())
priority.setkey('name')

# Status
status = Class(db, "status",
               name=String(),
               description=String(),
               order=Number())
status.setkey("name")

# Keyword
keyword = Class(db, "keyword",
                name=String(),
                description=String())
keyword.setkey("name")
                

# User-defined saved searches
query = Class(db, "query",
              klass=String(),
              name=String(),
              url=String(),
              private_for=Link('user'))

# add any additional database schema configuration here

user = Class(db, "user",
             username=String(),
             password=Password(),
             address=String(),
             realname=String(),
             phone=String(),
             organisation=String(),
             alternate_addresses=String(),
             queries=Multilink('query'),
             roles=String(),     # comma-separated string of Role names
             timezone=String(),)

user.setkey("username")


# FileClass automatically gets this property in addition to the Class ones:
#   content = String()    [saved to disk in <tracker home>/db/files/]
#   type = String()       [MIME type of the content, default 'text/plain']
msg = FileClass(db, "msg",
                author=Link("user", do_journal='no'),
                recipients=Multilink("user", do_journal='no'),
                date=Date(),
                summary=String(),
                files=Multilink("file"),
                messageid=String(),
                inreplyto=String())

# File
file = FileClass(db, "file",
                name=String(),
                description=String(indexme='yes'))


# IssueClass automatically gets these properties in addition to the Class ones:
#   title = String()
#   messages = Multilink("msg")
#   files = Multilink("file")
#   nosy = Multilink("user")
#   superseder = Multilink("issue")
issue = IssueClass(db, "issue",
                 topics=Multilink('topic'),
                 priority=Link('priority'),
                 dependencies=Multilink('issue'),
                 assignee=Link('user'),
                 status=Link('status'),
                 superseder=Link('issue'),
                 keywords=Multilink('keyword'))


#
# TRACKER SECURITY SETTINGS
#
# See the configuration and customisation document for information
# about security setup.

db.security.addRole(name='Operator', description='An Operator')

#
# REGULAR USERS
#
# Give the regular users access to the web and email interface
for r in 'User', 'Operator':
    db.security.addPermissionToRole(r, 'Web Access')
    db.security.addPermissionToRole(r, 'Email Access')

##########################
# User permissions
##########################

for cl in ('topic',
           'priority', 'status', 'issue', 
           'keyword', 'file', 'msg'):
    db.security.addPermissionToRole('User', 'View', cl)

for cl in ('topic',
           'priority', 'status',
           'issue', 'file', 'msg'):
    db.security.addPermissionToRole('User', 'Create', cl)
    

def checker(klass):
    def check(db, userid, itemid, klass=klass):
        return db.getclass(klass).get(itemid, 'creator') == userid
    return check

p = db.security.addPermission(name='Edit', klass='file', check=checker('file'),
    description="User is allowed to remove their own files")
db.security.addPermissionToRole('User', p)

p = db.security.addPermission(name='Create', klass='issue',
                              properties=('title',
                                          'topics',
                                          'messages', 'files', 'nosy'),
                              description='User can report and discuss issues')
db.security.addPermissionToRole('User', p)

p = db.security.addPermission(name='Edit', klass='issue',
                              properties=('title', 'topics', 'status',
                                          'messages', 'files', 'nosy'),
                              description='User can report and discuss issues',
                              check=checker('issue'))
db.security.addPermissionToRole('User', p)

# but can add comments to other people's issue
p = db.security.addPermission(name='Edit', klass='issue',
                              properties=('messages', 'files', 'nosy'),
                              description='User can report and discuss issues')
db.security.addPermissionToRole('User', p)

##########################
# Operator permissions
##########################
for cl in ('topic', 'priority', 'status', 'issue', 'file', 'msg'):
    db.security.addPermissionToRole('Operator', 'View', cl)
    db.security.addPermissionToRole('Operator', 'Edit', cl)
    db.security.addPermissionToRole('Operator', 'Create', cl)

# May users view other user information? Comment these lines out
# if you don't want them to
# db.security.addPermissionToRole('User', 'View', 'user')
db.security.addPermissionToRole('Operator', 'View', 'user')

# Allow Operator to edit any user, including their roles.
db.security.addPermissionToRole('Operator', 'Edit', 'user')
db.security.addPermissionToRole('Operator', 'Web Roles')

# Users should be able to edit their own details -- this permission is
# limited to only the situation where the Viewed or Edited item is their own.
def own_record(db, userid, itemid):
    '''Determine whether the userid matches the item being accessed.'''
    return userid == itemid
p = db.security.addPermission(name='View', klass='user', check=own_record,
    description="User is allowed to view their own user details")
for r in 'User', 'Operator':
    db.security.addPermissionToRole(r, p)
p = db.security.addPermission(name='Edit', klass='user', check=own_record,
    description="User is allowed to edit their own user details",
    properties=('username', 'password',
                'address', 'realname',
                'phone', 'organisation',
                'alternate_addresses',
                'queries',
                'timezone')) # Note: 'roles' excluded - users should not be able to edit their own roles. 
db.security.addPermissionToRole('User', p)

# Users should be able to edit and view their own queries. They should also
# be able to view any marked as not private. They should not be able to
# edit others' queries, even if they're not private
def view_query(db, userid, itemid):
    private_for = db.query.get(itemid, 'private_for')
    if not private_for: return True
    return userid == private_for
def edit_query(db, userid, itemid):
    return userid == db.query.get(itemid, 'creator')
p = db.security.addPermission(name='View', klass='query', check=view_query,
    description="User is allowed to view their own and public queries")
p = db.security.addPermission(name='Search', klass='query')
db.security.addPermissionToRole('User', p)
for r in 'User', 'Operator':
    db.security.addPermissionToRole(r, p)
p = db.security.addPermission(name='Edit', klass='query', check=edit_query,
    description="User is allowed to edit their queries")
for r in 'User', 'Operator':
    db.security.addPermissionToRole(r, p)
p = db.security.addPermission(name='Create', klass='query',
    description="User is allowed to create queries")
for r in 'User', 'Operator':
    db.security.addPermissionToRole(r, p)


#
# ANONYMOUS USER PERMISSIONS
#
# Let anonymous users access the web interface. Note that almost all
# trackers will need this Permission. The only situation where it's not
# required is in a tracker that uses an HTTP Basic Authenticated front-end.
db.security.addPermissionToRole('Anonymous', 'Web Access')

# Let anonymous users access the email interface (note that this implies
# that they will be registered automatically, hence they will need the
# "Create" user Permission below)
# This is disabled by default to stop spam from auto-registering users on
# public trackers.
#db.security.addPermissionToRole('Anonymous', 'Email Access')

# Assign the appropriate permissions to the anonymous user's Anonymous
# Role. Choices here are:
# - Allow anonymous users to register
# db.security.addPermissionToRole('Anonymous', 'Create', 'user')

# Allow anonymous users access to view issues (and the related, linked
# information).

# for cl in 'issue', 'severity', 'status', 'resolution', 'msg', 'file':
#     db.security.addPermissionToRole('Anonymous', 'View', cl)

# [OPTIONAL]
# Allow anonymous users access to create or edit "issue" items (and the
# related file and message items)
#for cl in 'issue', 'file', 'msg':
#   db.security.addPermissionToRole('Anonymous', 'Create', cl)
#   db.security.addPermissionToRole('Anonymous', 'Edit', cl)


# vim: set filetype=python sts=4 sw=4 et si :

#SHA: 72b50c5ab69aacd0269ba9a46c36297d40ae1e64
