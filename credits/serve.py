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
import sys
from subprocess import call
from string import Template

import gevent
import yaml
import web
import git

from credits import api
from credits import util

USAGE = "usage: %prog repos.yaml [options]"
URLS = ("/", "index",
        '/(.*)/reviews', 'reviews',
        '/(.*)', 'project')
DEFAULT_SYNC=3600
DEFAULT_ADDR="127.0.0.1"
DEFAULT_PORT=8080
DEFAULT_EXPIRES=500

CACHE = {} # All stay in memory...


class index(object):
    def GET(self):
        web.http.expires(config.get("expires", DEFAULT_EXPIRES))
        return render.index(config['repos'])

class project(object):
    def GET(self, name):
        if name not in config['repos']:
            return web.notfound()

        data = CACHE.get("project/%s" % name, [])
        web.http.expires(config.get("expires", DEFAULT_EXPIRES))
        return render.project(name, data)

class reviews(object):
    def GET(self, name):
        if name not in config['repos']:
            return web.notfound()

        data = CACHE.get("project/%s/reviews" % name, [])
        web.http.expires(config.get("expires", DEFAULT_EXPIRES))
        return render.reviews(name, data)


def sync(forground=False):
    sync_cache = not forground
    while True:
        for name, repo in config['repos'].iteritems():
            if not os.path.exists(repo['path']):
                call(["git", "clone", repo["git"], repo['path']])
            if sync_cache:
                sync_project(name)
                sync_reviews(name)
        if forground: return
        gevent.sleep(config.get('sync', DEFAULT_SYNC))

def sync_project(name):
    rpos = config["repos"]
    data = [(i+1, contrib[1], int(contrib[0])) \
                for i, contrib in enumerate(api.git_authors(rpos[name]))]
    CACHE["project/%s" % name] = data

def sync_reviews(name):
    rpos = config["repos"]
    data = [(i+1, contrib[1], int(contrib[0])) \
                for i, contrib in enumerate(api.git_reviews(rpos[name]))]
    CACHE["project/%s/reviews" % name] = data

config = None
application = web.application(URLS, globals()).wsgifunc()
t_globals = {
    'version': util.get_version(),
}
render = web.template.render('templates', base='base', globals=t_globals)

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
        sync(forground=True)
        exit()

    from gevent.pool import Pool
    from gevent.wsgi import WSGIServer

    gevent.spawn(sync)

    print "Starting server on %s:%d, threads=%d..." %\
        (options.address, options.port, options.concurrency)
    WSGIServer((options.address, options.port),
               application,
               spawn=Pool(options.concurrency),
               ).serve_forever()

if __name__ == '__main__':
    from gevent import monkey; monkey.patch_all()
    main()
