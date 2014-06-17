#
# Credits - Firefly contributors credits
#
# Copyright (C) 2014 Sahid Orentino Ferdjaoui <sahid.ferdjaoui@gmail.com>
#
# This is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 2.1, as published by the Free Software 
# Foundation.  See file COPYING.


import re

import pbr.version


def get_version():
    """Returns de software version"""
    return pbr.version.VersionInfo('credits').version_string()

def antispam(s):
    """Returns a new spammable email"""
    return re.sub("@.*>", "@xxx.org>", s)

