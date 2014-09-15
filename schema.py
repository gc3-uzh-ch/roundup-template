
#
# TRACKER SCHEMA
#

# Class automatically gets these properties:
#   creation = Date()
#   activity = Date()
#   creator = Link('user')
#   actor = Link('user')

# regexp used by S3ITIssueClass
import re


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

# Projects
project = Class(db, "project",
                name=String(),
                description=String())
project.setkey("name")
                

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
                inreplyto=String(),
 )

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

class S3ITIssueClass(IssueClass):
    """This class overrides `generateChangeNote` and `generateCreateNote`.

    It is way too hackish, but it's a quick and dirty solution to use
    the real name of the users in the assignee and nosy fields, in the email we send.

    Basically, we call the methods of the parent, and we *parse the
    output*, replacing `username` with `realname (username)`
    """

    # Override generateChangeNote, to address S3IT issue384
    def __fix_usernames_in_change_note(self, text):
        lines = text.splitlines()
        newlines = []
        assignee_change_re = re.compile('assignee:\s+(?P<old>[^\s]+)\s+->\s+(?P<new>[^\s]+)')
        assignee_create_re = re.compile('assignee:\s+(?P<old>[^\s]+)\s+')
        nosy_re = re.compile('nosy:\s+(.*)')
        for line in lines:
            if assignee_change_re.match(line):
                # Matches change in assignee
                old, new = assignee_change_re.search(line).groups()
                try:
                    oldname = db.user.get(db.user.lookup(old), 'realname', old)
                    newname = db.user.get(db.user.lookup(new), 'realname', new)
                    newlines.append('assignee: {} ({}) -> {} ({})'.format(
                        oldname, old, newname, new))
                except KeyError:
                    newlines.append(line)
            elif assignee_create_re.match(line):
                # Matches new assignee
                assignee = assignee_create_re.search(line).group(1)
                try:
                    realname = db.user.get(db.user.lookup(assignee), 'realname', assignee)
                    newlines.append('assignee: {} ({})'.format(
                        assignee, realname))
                except KeyError:
                    newlines.append(line)
            elif nosy_re.match(line):
                # Matches changes in the nosy list
                nosy = [i.strip() for i in nosy_re.search(line).group(1).split(',')]
                newnosy = []
                for user in nosy:
                    username = user.strip('-+')
                    prefix = user[0] if user[0] in '-+' else ''
                    try:
                        userid = db.user.lookup(username)
                        realname = db.user.get(userid, 'realname', username)
                        newnosy.append('{}{} ({})'.format(prefix, realname, username))
                    except KeyError:
                        newnosy.append(user)
                # We also rename 'nosy' with 'subscribers'
                newlines.append('subscribers: %s' % ', '.join(newnosy))
            else:
                newlines.append(line)
        return '\n'.join(newlines)

    def generateChangeNote(self, issueid, oldvalues):
        m = IssueClass.generateChangeNote(self, issueid, oldvalues)
        return self.__fix_usernames_in_change_note(m)

    def generateCreateNote(self, issueid):
        m = IssueClass.generateCreateNote(self, issueid)
        return self.__fix_usernames_in_change_note(m)


issue = S3ITIssueClass(db, "issue",
                   topics=Multilink('topic'),
                   priority=Link('priority'),
                   dependencies=Multilink('issue'),
                   assignee=Link('user'),
                   status=Link('status'),
                   superseder=Link('issue'),
                   keywords=Multilink('keyword'),
                   projects=Multilink('project'),
                   deadline=Date(),
                   public=Boolean(default_value=False),
                   extra_keywords=String(),
                   merged=Link("issue"),
)


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

def public_or_owned_issue(db, userid, itemid):
    item = db.issue.getnode(itemid)
    return item.public or item.creator == userid or userid in item.nosy

p = db.security.addPermission(name='View', klass='issue', check=public_or_owned_issue,
    description="User is allowed to view its own issues, or public issues only.")
db.security.addPermissionToRole('User', p)


def public_or_owned_msg_file(klass):
    attribute = {'msg': 'messages',
                 'file': 'files'}.get(klass)
    def belongs_to_public_issue(db, userid, itemid):
        issueids = db.issue.find(**{attribute:str(itemid)})
        if not issueids: return None

        issue=db.issue.getnode(issueids[0])
        return issue.public or issue.creator == userid or userid in issue.nosy
    return belongs_to_public_issue

for klass in ['msg', 'file']:
    p = db.security.addPermission(name='View', klass=klass, check=public_or_owned_msg_file(klass),
        description="User is allowed messages and files of public issues or issues owned by him.")
    db.security.addPermissionToRole('User', p)


for cl in ('topic',
           'priority', 'status',
           'keyword',
):
    db.security.addPermissionToRole('User', 'View', cl)

for cl in ('topic',
           'priority', 'status',
           'issue', 'file', 'msg'):
    db.security.addPermissionToRole('User', 'Create', cl)

def checker(klass):
    attributes = {'msg': 'messages',
                  'file': 'files',}

    def creator_or_public_issue(db, userid, itemid):
        item = db.issue.getnode(itemid)
        return item.public or item.creator == userid or userid in item.nosy

    def check_creator(db, userid, itemid, klass=klass):
        return db.getclass(klass).get(itemid, 'creator') == userid

    if klass in attributes:
        attribute = attributes[klass]
        def belongs_to_public_issue(db, userid, itemid):
            issueids = db.issue.find(**{attribute:str(itemid)})
            if not issueids: return None

            issue=db.issue.getnode(issueids[0])
            return issue.public or issue.creator == userid

        return check_creator
    else:
        return creator_or_public_issue

p = db.security.addPermission(name='Edit', klass='file', check=checker('file'),
    description="User is allowed to remove their own files")
db.security.addPermissionToRole('User', p)

p = db.security.addPermission(name='Create', klass='issue',
                              properties=('title',
                                          'topics', 'status', 'priority',
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
for cl in ('topic', 'priority', 'status', 'issue', 'file', 'msg', 'project'):
    db.security.addPermissionToRole('Operator', 'View', cl)
    db.security.addPermissionToRole('Operator', 'Edit', cl)
    db.security.addPermissionToRole('Operator', 'Create', cl)

# May users view other user information? Comment these lines out
# if you don't want them to
db.security.addPermissionToRole('User', 'View', 'user')
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
db.security.addPermissionToRole('User', p)

p = db.security.addPermission(name='Search', klass='query')
db.security.addPermissionToRole('User', p)

# This search permission is needed to search issues.
p = db.security.addPermission(name='Search', klass='issue')
db.security.addPermissionToRole('User', p)

p = db.security.addPermission(name='Edit', klass='query', check=edit_query,
    description="User is allowed to edit their queries")
for r in 'User', 'Operator':
    db.security.addPermissionToRole(r, p)

p = db.security.addPermission(name='Retire', klass='query', check=edit_query,
    description="User is allowed to retire their queries")
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
db.security.addPermissionToRole('Anonymous', 'Email Access')

# Assign the appropriate permissions to the anonymous user's Anonymous
# Role. Choices here are:
db.security.addPermission(name='Register', klass='user')
db.security.addPermissionToRole('Anonymous', 'Register', 'user')
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

