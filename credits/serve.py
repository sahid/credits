#
# Credits - Firefly contributors credits
#
# Copyright (C) 2014 Sahid Orentino Ferdjaoui <sahid.ferdjaoui@gmail.com>
#
# This is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 2.1, as published by the Free Software 
# Foundation.  See file COPYING.

import logging
import optparse
import os
import re
import sys
import itertools
from subprocess import call
from string import Template

import gevent
import yaml
import web
import web.http
import web.net
import git
import pbr.version


USAGE = "usage: %prog repos.yaml [options]"
URLS = ("/", "index",
        '/(.*)/reviews', 'reviews',
        '/(.*)', 'project')
CACHE = {} # All stay in memory...
DEFAULT_SYNC=3600
DEFAULT_ADDR="127.0.0.1"
DEFAULT_PORT=8080
DEFAULT_EXPIRES=500

application = web.application(URLS, globals()).wsgifunc()
config = None

TPL_INDEX = Template("""
<html>
  <h1>Credits</h1>
  <ul>
    $li_list
  </ul>
  </hr>
  <em>
    Version: $version -
    <a href="https://github.com/sahid/credits">
      Add you project here - https://github.com/sahid/credits
    </a>
  </em>
</html>
""")
TPL_INDEX_LILINK = Template("""
<li>
  <a href="/$name">$title</a>
</li>
""")

TPL_PROJECT_REVIEWS = Template("""
<html>
  <h1>Credits</h1>
  <h2>Reviews by authors</h2>
  <h3>$name</h3>
  <em>$title</em> &bullet; <a href="/">back</a>
  <ul>
    <li><a href="/$name">Commits by authors</a></li>
    <li><a href="/$name/reviews">Reviews by authors</a></li>
  </ul>
  <pre>
  #\tReviews\tAuthor
  $tr_list
  </pre>
  </hr>
  <em>
    Version: $version -
    <a href="https://github.com/sahid/credits">
      Add you project here - https://github.com/sahid/credits
    </a>
  </em>
</html>
""")
TPL_PROJECT_COMMITS = Template("""
<html>
  <h1>Credits</h1>
  <h2>Commits by authors</h2>
  <h3>$name</h3>
  <em>$title</em> &bullet; <a href="/">back</a>
  <ul>
    <li><a href="/$name">Commits by authors</a></li>
    <li><a href="/$name/reviews">Reviews by authors</a></li>
  </ul>
  <pre>
  #\tCommits\tAuthor
  $tr_list
  </pre>
  </hr>
  <em>
    Version: $version -
    <a href="https://github.com/sahid/credits">
      Add you project here - https://github.com/sahid/credits
    </a>
  </em>
</html>
""")

TPL_PROJECT_TR = Template("""
  $rank\t$misc\t$author
""")


class index(object):
    def GET(self):
        web.http.expires(config.get("expires", DEFAULT_EXPIRES))
        return CACHE.get("index", "generating...")

class project(object):
    def GET(self, name):
        web.http.expires(config.get("expires", DEFAULT_EXPIRES))
        return CACHE.get("project/%s" % name, "generating...")

class reviews(object):
    def GET(self, name):
        web.http.expires(config.get("expires", DEFAULT_EXPIRES))
        return CACHE.get("project/%s/reviews" % name, "generating...")

def get_version():
    return pbr.version.VersionInfo('credits').version_string()

def antispam(s):
    return re.sub("@.*>", "@xxx.org>", s)

def git_authors(name):
    r = config['repos'][name]
    g = git.Repo(r["path"]).git
    g.pull("origin", r["branch"])
    content = g.log(pretty='%aN <%aE>').decode("utf-8").split("\n")
    content = [antispam(s) for s in content]
    content = [(len(list(x)), a)for a, x in itertools.groupby(sorted(content))]
    return sorted(content, reverse=True)

def git_reviews(name):
    r = config['repos'][name]
    g = git.Repo(r["path"]).git
    g.pull("origin", r["branch"])
    content = g.log(pretty='%b').decode("utf-8")
    content = re.findall('Reviewed-by:\s*(.*<.*>)', content, re.I)
    content = [antispam(s) for s in content]
    content = [(len(list(x)), a) for a, x in itertools.groupby(sorted(content))]
    return sorted(content, reverse=True)

def sync():
    while True:
        sync_index()
        for name, repo in config['repos'].iteritems():
            if not os.path.exists(repo['path']):
                call(["git", "clone", repo["git"], repo['path']])
            sync_project(name)
            sync_reviews(name)
        gevent.sleep(config.get('sync', DEFAULT_SYNC))

def sync_index():
    li_list = "".join(
        [TPL_INDEX_LILINK.substitute(repo) for name, repo in config['repos'].iteritems()])
    version = get_version()
    CACHE["index"] = TPL_INDEX.substitute(locals())

def sync_project(name):
    title = config["repos"][name].get("title", "no title...")
    version = get_version()
    tr_list = []
    for i, contrib in enumerate(git_authors(name)):
        tr_list.append(TPL_PROJECT_TR.substitute({
                    'rank': i+1,
                    'author': web.net.websafe(contrib[1]),
                    'misc': int(contrib[0])}))
    tr_list = "".join(tr_list)
    CACHE["project/%s" % name] = TPL_PROJECT_COMMITS.substitute(locals())

def sync_reviews(name):
    title = config["repos"][name].get("title", "no title...")
    version = get_version()
    tr_list = []
    for i, contrib in enumerate(git_reviews(name)):
        tr_list.append(TPL_PROJECT_TR.substitute({
                    'rank': i+1,
                    'author': web.net.websafe(contrib[1]),
                    'misc': int(contrib[0])}))
    tr_list = "".join(tr_list)
    CACHE["project/%s/reviews" % name] = TPL_PROJECT_REVIEWS.substitute(locals())

def main():
    global config

    if len(sys.argv) < 2:
        parser.print_help()
        exit()

    stream = file(sys.argv[1])
    config = yaml.load(stream)

    parser = optparse.OptionParser(usage=USAGE)
    parser.add_option("-i", "--init",
                      dest="init",
                      action="store_true",
                      help="Initializes git clone.",
                      default=False)
    parser.add_option("-a", "--address",
                      dest="address",
                      help="Address to bind",
                      default=config.get("address", DEFAULT_ADDR))
    parser.add_option("-p", "--port",
                      dest="port",
                      type="int",
                      help="Port to bind",
                      default=config.get("port", DEFAULT_PORT))
    parser.add_option("-c", "--concurrency",
                      dest="concurrency",
                      type="int",
                      help="Number of concurrent connections",
                      default=config.get("concurrency", 1))
    (options, args) = parser.parse_args()

    if getattr(options, "init"):
        init_repos()
        exit()

    from gevent.pool import Pool
    from gevent.wsgi import WSGIServer

    gevent.spawn(sync)

    WSGIServer((options.address, options.port),
               application,
               spawn=Pool(options.concurrency),
               ).serve_forever()

if __name__ == '__main__':
    from gevent import monkey; monkey.patch_all()
    main()
