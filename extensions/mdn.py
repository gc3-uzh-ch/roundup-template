# import markdown as markdown_module

# def markdown(text):
#   return markdown_module.markdown(text, 
#                                   ['codehilite', 'extra', 'nl2br'])

import markdown2 as markdown_module
import re


# link_patterns = [
#     (re.compile(r'\b(issue\d+)\b'), r'/help/\1'),
#     (re.compile(r'''(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))'''), r'\1'),
#   ]

link_patterns = [
  # issueNNN --> /help/issueNNN
  (re.compile(r'\b(issue)\s*(\d+)\b'), r'/help/\g<1>\g<2>'),
  # web URL
  (re.compile(r'''(?xi)
  (?<!['"])                               (?# not preceded by a quotes, avoid recursive processing of href="..." )
\b
( (?# Capture group 1: entire matched URL)
  (?:ftp|https?)://                       (?# URL schema)
  (?:                                     (?# optional userinfo part: )
    [a-z0-9._~\-%!$&'()*+,;=:]+             (?# see RFC 3986, sec. 3.2.1 )
    @                                       (?# literal '@' mark )
  )?
  (?:                                     (?# host, either one of the following: )
    [a-z0-9][a-z0-9.-]+\.(?:[a-z][a-z]+)    (?# looks like an FQDN )
    |
    [0-9]+(?:\.[0-9]+){3}                   (?# IPv4 dotted-quad )
    |
    \[ [0-9a-f]+(?::[0-9a-f]+){7} \]        (?# IPv6 full address literal )
    |
    \[ ([0-9a-f]+(?: :[0-9a-f]+ )* )? :: ([0-9a-f]+(?: :[0-9a-f]+)* ) \]
                                            (?# looks like an IPv6 abbreviated address literal )
  )
  (?: :[0-9]+ )?                          (?# optional port number )
  (?:                                     (?# optional path: )
    /                                       (?# literal slash )
    [a-z0-9._~\-%!$&'()*+,;=:@]*            (?# see RFC 3986, sec. 2.2, 2.3, and 3.3 )
  )*                                        (?# repeat zero or more times )
  (?:                                     (?# optional query part: )
    [?]                                     (?# literal question mark )
    [a-z0-9._~\-%!$&'()*+,;=:@?/]*          (?# see RFC 3986, sec. 2.2, 2.3, and 3.4 )
  )?                                        (?# at most once )
  (?:                                     (?# optional fragment part: )
    [#]                                     (?# literal hash mark )
    [a-z0-9._~\-%!$&'()*+,;=:@?/]*          (?# see RFC 3986, sec. 2.2, 2.3, and 3.5 )
  )?                                        (?# at most once )
)
  '''), r'\g<1>'),
  # "naked" domain, assume `http://` URL
  (re.compile(r'''(?xi)
  (?<!/)                       (?# not preceded by a /, avoid matching http://example.com )
  (?<!\.)                      (?# not preceded by a ., avoid matching just `com` in example.com )
  (?<!@)                       (?# not preceded by a @, avoid matching foo@_gmail.com_ )
  \b
  ( (?# capture group 1: domain name)
    [a-z0-9][a-z0-9.-]+\.(?:[a-z][a-z]+) (?# looks like a domain name )
    /?                           (?# optional slash )
    (?!@)                        (?# not followed by a @, avoid matching "foo.na" in "foo.na@example.com" )
  )
  \b
  '''), r'http://\g<1>')
]



def markdown(text):
  html = markdown_module.markdown(
      text, extras=['footnotes', 'fenced-code-blocks', 'link-patterns', 'footnotes'],
      link_patterns=link_patterns)
  # Ensure the code is converted to utf-8
  try:
    return html.encode('utf-8')
  except UnicodeEncodeError:
    return html.encode('ascii', 'xmlcharrefreplace')

def init(instance):
  instance.registerUtil('markdown', markdown)
