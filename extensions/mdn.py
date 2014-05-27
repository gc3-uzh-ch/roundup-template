# import markdown as markdown_module

# def markdown(text):
#   return markdown_module.markdown(text, 
#                                   ['codehilite', 'extra', 'nl2br'])

import markdown2 as markdown_module
import re


link_patterns = [
    (re.compile(r'\b(issue\d+)\b'), r'/help/\1'),
    (re.compile(r'''(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))'''), r'\1'),
  ]

def markdown(text):
  return markdown_module.markdown(
      text, extras=['footnotes', 'fenced-code-blocks', 'link-patterns'],
      link_patterns=link_patterns)

def init(instance):
  instance.registerUtil('markdown', markdown)
