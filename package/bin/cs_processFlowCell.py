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

'''Script to query a given run ID for lanes of interest, download
the sequencing data (i.e. fastq file) and demultiplex if necessary.'''

from osqutil.setup_logs import configure_logging
from logging import INFO
LOGGER = configure_logging(level=INFO)

# New in Django 1.7 and above.
import django
django.setup()

# All script code moved into our main pipeline library namespace.
from osqpipe.pipeline.flowcell import FlowCellProcess

###############################################################################

if __name__ == '__main__':

  import argparse

  PARSER = argparse.ArgumentParser(
    description='Process a Sequencing Run from the LIMS.')

  PARSER.add_argument('-t', '--test', dest='testMode', action='store_true',
                      help='Turn on test mode (no filesystem changes).')

  PARSER.add_argument('-n', '--nocheck', dest='checkForLibInDB',
                      action='store_false',
                      help='Deactivate the check for library in repository DB.')

  PARSER.add_argument('run', metavar='<runID>', type=str,
                      help='The run ID (required).')

  PARSER.add_argument('flowLane', metavar='<flowLaneID>', type=int, nargs='?',
                      help='The flow lane ID (optional).')

  PARSER.add_argument('-f', '--force-primary', dest='forcePrimary',
                      action='store_true',
                      help='Start processing a flow cell which is only PRIMARY COMPLETE,'
                      + ' not SECONDARY COMPLETE. It is the user\'s responsibility to ensure'
                      + ' that the LIMS files are ready to be copied across.')
    
  PARSER.add_argument('--force-all', dest='forceAll',
                      action='store_true',
                      help='Start processing a flow cell which is still INCOMPLETE.'
                      + ' Once again, it is the user\'s responsibility to ensure'
                      + ' that the LIMS files are ready to be copied across.')

  PARSER.add_argument('--force-download', dest='forceDownload',
                      action='store_true',
                      help='Force download even if run has already been processed.')

  PARSER.add_argument('-d', '--destination-dir', dest='destdir', type=str,
                      help='Select a different destination directory for downloads'
                      + ' (default is the configured incoming directory).')

  PARSER.add_argument('--trust-lims-adapters', dest='trustAdapt', type=str, default=None,
                      help='If set to the name of a protocol (taken from the Adapter'
                      + ' table) then any empty adapter fields in the database'
                      + ' will be automatically filled using LIMS data. This'
                      + ' bypasses our usual consistency check so should only'
                      + ' be used when certain. It will not overwrite'
                      + ' previously-entered adapter metadata.')

  ARGS = PARSER.parse_args()

  PROC = FlowCellProcess(test_mode        = ARGS.testMode,
                         db_library_check = ARGS.checkForLibInDB,
                         force_primary    = ARGS.forcePrimary,
                         force_all        = ARGS.forceAll,
                         trust_lims_adapters = ARGS.trustAdapt,
                         force_download   = ARGS.forceDownload)

  PROC.run(ARGS.run, ARGS.flowLane, destdir = ARGS.destdir)

