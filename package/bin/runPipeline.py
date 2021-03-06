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

'''Script intended for automated use via e.g. a cron job; it calls
each part of the pipeline in turn, handling any errors which may
arise.'''

from osqutil.setup_logs import configure_logging
from logging import INFO
LOGGER = configure_logging(level=INFO)

# New in Django 1.7 and above.
import django
django.setup()

from django.db import transaction

from osqpipe.pipeline.upstream_lims import Lims
from osqpipe.pipeline.lims_watcher import LimsWatcher
from osqpipe.pipeline.flowcell import FlowCellQuery, FlowCellProcess
from osqpipe.pipeline.file_processor import FileProcessingManager
from osqutil.utilities import parse_incoming_fastq_name
from osqpipe.pipeline.smtp import email_admins, send_email
from osqpipe.models import Facility, Status, Lane

from osqutil.config import Config
CONFIG = Config()
LIMS   = Lims()

def process_run(run):

  # Check for empty sets; these are cases where we need to fix the
  # library record in the repository. We really need to do this before
  # processing the rest of the run because at this stage we're
  # downloading all the run data at once (FIXME maybe call
  # FlowCellProcess one lane at a time?).
  fcq = FlowCellQuery(run, lims=LIMS)
  nolibrary = [ lane for (lane, libs) in fcq.lane_library.iteritems() if len(libs) == 0 ]
  if len(nolibrary) > 0:
    raise ValueError("Libraries not found for some lanes: %s" % ", ".join(nolibrary))

  # This should mark the ready lanes as being in-process.
  proc     = FlowCellProcess(lims=LIMS)
  fq_files = proc.run(run, fcq=fcq)

  # We have to detect paired-end here, as well as facility.
  paired = {}
  for fname in fq_files:
    (libcode, _flowcell, flowlane, flowpair) = parse_incoming_fastq_name(fname)
    if flowpair not in (1,2):
      raise ValueError("Unexpected flowpair value: %d" % flowpair)
    pairset = paired.setdefault("%s:%d" % (libcode, flowlane), [None, None])
    if pairset[flowpair-1] is not None:
      pairset[flowpair-1] = fname
    else:
      raise StandardError("Duplicate flowpair value found for %s (lane %d)."
                          % (libcode, flowlane))

  for pairset in paired.itervalues():
    # FIXME add options below as well?
    FPM = FileProcessingManager(facility=CONFIG.core_facility_code)

    # This call should update Lane.status.
    FPM.run([ x for x in pairset if x is not None ])
      
  # At this point we relinquish control to the cluster, which will
  # eventually call back and fork cs_processAlignmentBwa.py processes
  # once the alignment is done (FIXME!) Update: perhaps better to set
  # a status in the repository rather than forking large processes
  # into the background? If so, how do we match up alignment bam files
  # with lanes?

def missing_library_email_body(libs):

  text = """\
Data for the following libraries is available in the LIMS, but the
library has not yet been entered in the repository:
%s
""" % "\n".join(sorted(libs))

  return text

@transaction.atomic
def _retrieve_and_mark_ready_lanes(recent_only=False):

  # Run a query of the Genologics LIMS REST API
  # for things which completed since the last run.
  watcher = LimsWatcher(lims=LIMS)
  ready_lanes = watcher.find_ready_lanes()

  # Run a query against the database for "status=ready" lanes to catch
  # previously-failed processing runs. The alternative is to only
  # retrieve lanes completed within the past few days (see the
  # limswatcher code).
  if not recent_only:
    facility = Facility.objects.get(code=CONFIG.core_facility_code)
    ready    = Status.objects.get(code=CONFIG.core_ready_status,
                                  authority=facility)
    ready_lanes = Lane.objects.get(status=ready)

  # It's important to mark the lanes as ready for processing *within*
  # this transaction; otherwise we risk a race condition.
  marked = Status.objects.get(code='marked for processing')
  for lane in ready_lanes:
    lane.status = marked
    lane.save()
  
  if len(watcher.missing_libraries) > 0:

    # Email admins to alert them to missing libraries
    email_admins("Libraries to be loaded",
                missing_library_email_body(watcher.missing_libraries))

  return ready_lanes

def process_ready_lanes(recent_only=False):

  ready_lanes = _retrieve_and_mark_ready_lanes(recent_only)

  # Run the actual process.
  for run_id in set([ x.runnumber for x in ready_lanes ]):
    process_run(run_id)

  # FIXME compose email to admins + recent.user_emails to let everyone
  # know the current pipeline status. Note that we could use all the
  # emails from ready_lanes but for 'stuck' lanes this would generate
  # a lot of unnecessary emails to users.
#  send_email(subj, body, recent.user_emails, include_admins=True)

def process_ready_alignments():

  # Completed alignments should set the appropriate lane status in the
  # repository. We detect that here and carry the resulting alignment
  # files into the repository (FIXME how do we know which files these
  # are???).
  
  raise NotImplementedError()

if __name__ == '__main__':

  # FIXME do a standard run of importInventoryExcel.py first

  process_ready_lanes()
  process_ready_alignments()
