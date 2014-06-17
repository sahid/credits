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
import itertools
import re

import git

from credits import util


def git_authors(repo):
    """Returns a list contributors by commits"""
    g = git.Repo(repo["path"]).git
    g.pull("origin", repo["branch"])
    content = g.log(pretty='%aN <%aE>').decode("utf-8").split("\n")
    content = [util.antispam(s) for s in content]
    content = [(len(list(x)), a)for a, x in itertools.groupby(sorted(content))]
    return sorted(content, reverse=True)


def git_reviews(repo):
    """Returns a list contributors by reviews"""
    g = git.Repo(repo["path"]).git
    g.pull("origin", repo["branch"])
    content = g.log(pretty='%b').decode("utf-8")
    content = re.findall('Reviewed-by:\s*(.*<.*>)', content, re.I)
    content = [util.antispam(s) for s in content]
    content = [(len(list(x)), a) for a, x in itertools.groupby(sorted(content))]
    return sorted(content, reverse=True)
