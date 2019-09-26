#!/usr/bin/env python
#
# Copyright 2018 Odom Lab, CRUK-CI, University of Cambridge
#
# This file is part of the osqpipe python package.
#
# The osqpipe python package is free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# The osqpipe python package is distributed in the hope that it will
# be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the osqpipe python package.  If not, see
# <http://www.gnu.org/licenses/>.


import sys
import os
import os.path
import re
import argparse
from datetime import date

from osqutil.setup_logs import configure_logging
from logging import INFO
LOGGER = configure_logging(level=INFO)

# New in Django 1.7 and above.
import django
django.setup()

from osqpipe.models import Alignment
from osqutil.config import Config
from osqpipe.pipeline.alignmentqc import AlignmentCrossCorrReport

CONFIG = Config()

def compute_xcor_and_insert(aln):
  
  if aln.lane.library.libtype.code in CONFIG.xcor_libtypes:
    try:
      with AlignmentCrossCorrReport(target=aln,
                                    path=CONFIG.hostpath) as qcrep:
        qcrep.insert_into_repository()
    except Exception, err:
      LOGGER.warning("Cross-correlation report generation failed: %s", err)

  else:
    raise StandardError("Alignment is not from an appropriate library type: %s" % aln.lane.library.libtype.code)

################## M A I N ########################

if __name__ == '__main__':

  from argparse import ArgumentParser

  PARSER = argparse.ArgumentParser(
    description='Executes Cross-correlation report generation and insertion into repository.')

  PARSER.add_argument('-l', '--library', dest='library', required=True, type=str,
                      help='The library code. E.g. do123.')

  PARSER.add_argument('-f', '--facility', dest='facility', required=False, type=str,
                      help='The name of the facility. E.g. \"CRI\".')

  PARSER.add_argument('-n', '--lanenum', dest='lanenum', required=False, type=str,
                      help='The repository lane number. E.g. 1.')

  PARSER.add_argument('--force', dest='force', action='store_true',
                      help='Whether to add a new cross-correlation report to an alignment'
                      + ' which already has one. The old report will not be deleted.')

  ARGS = PARSER.parse_args()

  alignments = Alignment.objects.filter(lane__library__code=ARGS.library)

  if ARGS.facility is not None:
    alignments = alignments.filter(lane__facility__code=ARGS.facility)
    
  if ARGS.lanenum is not None:
    alignments = alignments.filter(lane__lanenum=ARGS.lanenum)
  
  for aln in alignments:
    if ARGS.force or aln.alignmentqc_set.count() == 0:
      compute_xcor_and_insert(aln)
