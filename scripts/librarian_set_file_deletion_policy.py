#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Team.
# Licensed under the BSD License.

"""Set the "deletion policy" of one instance of this file.

This script has been superseded by the `librarian set-file-deletion-policy` command.
It is kept here for backwards compatibility, and will be removed in a future
version.
"""
from __future__ import absolute_import, division, print_function

import os
import sys
import warnings
from hera_librarian.cli import main

if __name__ == "__main__":
    warnings.warn("This script has been supserseded by the `librarian set-file-deletion-policy` "
                  "command. This script is preserved for backwards compatibility, but "
                  "will be removed in a future version.")
    # fix up command-line args to behave correctly
    bindir = os.path.abspath(os.path.dirname(sys.argv[0]))
    librarian_script = os.path.join(bindir, "librarian")
    del sys.argv[0]
    sys.argv.insert(0, librarian_script)
    sys.argv.insert(1, "set-file-deletion-policy")
    sys.exit(main(*sys.argv))
