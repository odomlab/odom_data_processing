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

'''
Very simple script to check that all the raw data from a run
has been downloaded and loaded into the repository, and that each Lane
object is linked to at least one alignment. This script will also flag
up cases where alignment rates are lower than expected.
'''

from logging import INFO

# New in Django 1.7 and above.
import django
django.setup()

from osqpipe.models import Lane, Library
from osqpipe.pipeline.flowcell import FlowCellQuery
from osqpipe.pipeline.fastq_aligner import FastqBwaAligner, FastqTophatAligner

from osqutil.setup_logs import configure_logging
LOGGER = configure_logging(level=INFO)

###############################################################################

def confirm_complete(run, bwa_algorithm,
                     resubmit_alignments=False):
  '''
  Given a run ID, confirm completion of the pipeline. Returns
  True for complete, False for incomplete.
  '''
  # Suppress some of the more verbose output here, as it's likely to
  # no longer be of interest.
  fcq = FlowCellQuery(run_id = run, quiet = True)

  complete = True
  for ( flowlane, libcodeset ) in fcq.lane_library.iteritems():
    for libcode in sorted(list(libcodeset)):
      try:
        lane = Lane.objects.get(library__code=libcode,
                                runnumber=run,
                                flowlane=flowlane)
      except Lane.DoesNotExist:
        LOGGER.warning("Lane not found in repository: %s %s:%s",
                       libcode, run, flowlane)
        complete = False
        continue
      if lane.lanefile_set.filter(filetype__code__in=('fq','tar')).count() == 0:
        LOGGER.warning("Lane has no fastq files or tarballs: %s %s:%s",
                       libcode, run, flowlane)
        complete = False
        continue
      if lane.alignment_set.count() == 0:
        LOGGER.warning("Lane has no alignments: %s %s:%s",
                       libcode, run, flowlane)
        complete = False
        if resubmit_alignments:
          library = Library.objects.get(code=libcode)
          if library.libtype.code == 'rnaseq':
            aligner = FastqTophatAligner(samplename=library.sample.name)
          else:
            aligner = FastqBwaAligner(samplename=library.sample.name,
                                      bwa_algorithm=bwa_algorithm)

          aligner.align(library  = libcode,
                        facility = lane.facility.code,
                        lanenum  = lane.lanenum,
                        genome   = library.genome.code)

        continue
      for aln in lane.alignment_set.all():
        if aln.alnfile_set.filter(filetype__code='bam').count() == 0:
          LOGGER.warning("Alignment has no bam files: %s %s:%s (%s)",
                         libcode, run, flowlane, aln.genome)
          complete = False
        if aln.mapped_percent < 50:
          LOGGER.warning("Alignment has low mapping rate:"
                         + " %s %s:%s (%s): %d%%",
                         libcode, run, flowlane, aln.genome,
                         aln.mapped_percent)

  return complete

###############################################################################

if __name__ == '__main__':

  import argparse

  PARSER = argparse.ArgumentParser(\
    description='Confirm completion of Sequencing Run processing.')

  PARSER.add_argument('run', metavar='<runID>', type=str,
                      help='The run ID (required).')

  PARSER.add_argument('-r', '--resubmit', dest='resubmit', action='store_true',
                      help='Indicates that missing alignments should be'
                      + ' resubmitted against the standard configured genome'
                      + ' for the library. Output bam files will be written'
                      + ' to the current working directory.')

  PARSER.add_argument('--algorithm', type=str, dest='algorithm',
                      choices=('aln', 'mem'),
                      help='If --resubmit is specified, the bwa algorithm to'
                      + ' use (aln or mem). The default behaviour is to pick'
                      + ' the algorithm based on the read length in the fastq'
                      + ' files.')

  ARGS = PARSER.parse_args()

  if confirm_complete(run                 = ARGS.run,
                      resubmit_alignments = ARGS.resubmit,
                      bwa_algorithm       = ARGS.algorithm):
    LOGGER.info("Run processing complete.")
  else:
    LOGGER.warning("Run processing not yet complete.")
