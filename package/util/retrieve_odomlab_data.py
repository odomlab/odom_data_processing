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
Simple client for Odom Lab repository REST API which can be used to
download data files to which the user has access.
'''

# NOTE that this script must contain *no dependencies* on
# osqpipe/osqutil modules.

import os
import sys

# Do this before importing requests, to work around the abysmally old
# software stack currently running on lcst01. If running on a newer
# system (anything post-2010 would probably be fine), you should
# comment out these two lines.
import ssl
ssl.HAS_SNI = False

import requests
import json
import logging
import gzip
import hashlib
from contextlib import contextmanager
from requests.exceptions import HTTPError

# The following are used below to trap the warnings generated by the
# HAS_SNI hack above.
import warnings
from requests.packages.urllib3.exceptions import SNIMissingWarning
from requests.packages.urllib3.connectionpool import InsecureRequestWarning

LOGGER = logging.getLogger()
LOGGER.addHandler(logging.StreamHandler())
LOGGER.handlers[0].setFormatter(\
  logging.Formatter("[%(asctime)s]dolab_%(levelname)s: %(message)s"))
LOGGER.setLevel(logging.INFO)

# Currently our repository website uses a self-signed certificate (the
# University requires a .cam.ac.uk domain for its certificate issuing
# service). If that ever changes, for example if we migrate to a
# public internet domain, this should be set to True.
VERIFY_SSL_CERT=False

################################################################################
class ApiSession(requests.Session):
  '''
  Session subclass which will automatically renew expired
  authentication tokens.
  '''
  def __init__(self, username, password,
               base_url='http://localhost:8000/repository',
               *args, **kwargs):
    super(ApiSession, self).__init__(*args, **kwargs)
    self._rest_base_url      = base_url.rstrip('/')
    self._rest_username      = username
    self._rest_password      = password

  def _update_token(self):

    # Retrieve the user token, to be embedded in all future requests.
    LOGGER.debug("Refreshing authorization token.")
    api_token_url = "%s/api-token-auth/" % self._rest_base_url
    with warnings.catch_warnings():
      warnings.filterwarnings('once', category=SNIMissingWarning)
      warnings.filterwarnings('once', category=InsecureRequestWarning)
      tokenresp = requests.post(api_token_url,
                                verify=VERIFY_SSL_CERT,
                                data={ 'username': self._rest_username,
                                       'password': self._rest_password, })
    if tokenresp.status_code != 200:
      raise HTTPError("Unable to log in: %s" % tokenresp.reason)
    api_token = json.loads(tokenresp.content)['token']
    self.headers.update({'Authorization': "Token %s" % api_token})

  def get(self, url, verify=VERIFY_SSL_CERT, *args, **kwargs):
    with warnings.catch_warnings():
      warnings.filterwarnings('once', category=SNIMissingWarning)
      warnings.filterwarnings('once', category=InsecureRequestWarning)
      resp = super(ApiSession, self).get(url, verify=verify, *args, **kwargs)

    ## Detect token expiry here and refresh if necessary.
    if resp.status_code == 401:
      self._update_token()
      resp = super(ApiSession, self).get(url, *args, **kwargs)

    return resp

  def api_metadata(self, url):
    resp = self.get(url)
    if resp.status_code != 200:
      raise HTTPError("Unable to retrieve metadata: %s" % resp.reason)
    return json.loads(resp.content)

  def rest_download_file(self, url, local_filename):

    # The stream=True parameter keeps memory usage low.
    resp = self.get(url, stream=True)
    if resp.status_code != 200:
      raise HTTPError("Unable to download file: %s" % resp.reason)
    with open(local_filename, 'wb') as outfh:
      for chunk in resp.iter_content(chunk_size=1024):
        if chunk: # filter out keep-alive new chunks
          outfh.write(chunk)
    return local_filename

################################################################################

@contextmanager
def flexi_open(filename, *args, **kwargs):
  '''
  Simple context manager function to seamlessly handle gzipped and
  uncompressed files.
  '''
  if os.path.splitext(filename)[1] == '.gz':
    handle = gzip.open(filename, *args, **kwargs)
  else:
    handle = open(filename, *args, **kwargs)

  yield handle

  handle.close()

def confirm_file_checksum(fname, checksum, blocksize=65536):

  LOGGER.debug("Confirming checksum for file %s", fname)
  with flexi_open(fname, 'rb') as fileobj:
    hasher = hashlib.md5()
    buf = fileobj.read(blocksize)
    while len(buf) > 0:
      hasher.update(buf)
      buf = fileobj.read(blocksize)

    if hasher.hexdigest() != checksum:
      LOGGER.warning("Local file checksum disagrees with repository: %s",
                     fname)
    else:
      LOGGER.info("Checksum good for file %s", fname)

class OdomDataRetriever(object):

  __slots__ = ('session', 'with_download', 'with_checksum', '_base_url',
               '_projdirs', 'filetype', '_filename_processed', '_mergedfiles')

  def __init__(self, download=True, checksum=True,
               base_url='http://localhost:8000/repository', project_dirs=None,
               filetype='fastq'):

    import getpass
    sys.stderr.write("Please enter your login credentials.\n")
    username = raw_input('Username: ')
    password = getpass.getpass('Password: ')

    # Create a session object for future requests.
    self.session = ApiSession(base_url = base_url,
                              username = username,
                              password = password )

    self.with_download = download
    self.with_checksum = checksum
    self._base_url     = base_url
    self._filename_processed = set()
    self._mergedfiles  = False

    if filetype is None:
      filetype = 'fastq'
    elif filetype[:6] == 'merged': # mergedbam and its ilk
      filetype = filetype[6:]
      self._mergedfiles = True
    self.filetype = filetype

    if project_dirs is None:
      project_dirs = []
    self._projdirs = project_dirs

  def _file_found(self, fname):
    '''
    Method tests for the existence of the file in the current
    working directory and any pre-existing project directories. A
    positive hit is also yielded for any uncompressed files (lacking a
    .gz suffix) that are found.
    '''
    to_test = [ fname ]
    parts   = os.path.splitext(fname)
    if parts[1] == '.gz':
      to_test += [ parts[0] ]

    for testname in to_test:
      if os.path.exists(testname):
        return testname
      for reldir in self._projdirs:
        relpath = os.path.join(reldir, testname)
        if os.path.exists(relpath):
          return relpath

    return False
      
  def process_liburl(self, url):

    libdict = self.session.api_metadata(url)
    LOGGER.info("Retrieved metadata for library %s", libdict['code'])
    for laneurl in libdict['lane_set']:
      self.process_laneurl(laneurl)

  def process_laneurl(self, url):

    lanedict = self.session.api_metadata(url)
    LOGGER.info("Retrieved metadata for lane %s (flowcell %s)",
                lanedict['flowlane'], lanedict['flowcell'])
    for filedict in lanedict['lanefile_set']:
      if filedict['filetype'] == self.filetype:
        self.download_datafile(filedict)

    for alnurl in lanedict['alignment_set']:
      self.process_alnurl(alnurl)

  def process_alnurl(self, url):

    alndict = self.session.api_metadata(url)
    LOGGER.debug("Retrieved metadata for aln against genome %s",
                 alndict['genome'])
    for filedict in alndict['alnfile_set']:
      if filedict['filetype'] == self.filetype:
        self.download_datafile(filedict)

    for merged_alnurl in alndict['mergedalignment_set']:
      self.process_merged_alnurl(merged_alnurl)

  def process_merged_alnurl(self, url):

    # Repeated tries at the same MergedAlnfile are detected and
    # ignored by download_datafile.
    merged_alndict = self.session.api_metadata(url)
    LOGGER.debug("Retrieved metadata for mergedaln (genome %s)",
                 merged_alndict['genome'])
    for filedict in merged_alndict['mergedalnfile_set']:
      if filedict['filetype'] == self.filetype:
        self.download_datafile(filedict, merged=True)

  def download_datafile(self, filedict, merged=False):

    # This makes the distinction between downloads of merged files
    # (e.g., bams) and unmerged files.
    if merged != self._mergedfiles:
      LOGGER.debug("Skipping download due to merge flag setting.")
      return

    dl_fname = filedict['filename_on_disk']

    if dl_fname in self._filename_processed:
      LOGGER.debug("Already processed file %s this session. Skipping.", dl_fname)
      return

    # Look for pre-existing file. This is a little more convoluted
    # than strictly necessary in case we want to continue supporting
    # post-hoc MD5 checksums.
    found_file = self._file_found(dl_fname)
    if found_file:
      LOGGER.info("Skipping download of pre-existing file %s", dl_fname)
      dl_fname = found_file # Could conceivably checksum this now.

    else:
      if self.with_download:
        LOGGER.info("Starting file download: %s", dl_fname)

        try:
          self.session.rest_download_file(filedict['download'], dl_fname)
        except HTTPError, err:
          LOGGER.error("Unable to download file: %s", err)
          return
        
        LOGGER.info("Completed file download: %s", dl_fname)
        if not os.path.exists(dl_fname):
          LOGGER.warning("Downloaded file appears to be missing: %s", dl_fname)
      else:
        LOGGER.debug("Skipping download as directed: %s", dl_fname)

      # Currently we only checksum newly-downloaded files; we may wish
      # to change that in future.
      if self.with_checksum:
        confirm_file_checksum(dl_fname, filedict['checksum'])

    # This is needed to prevent multiple downloads of MergedAlnfiles.
    self._filename_processed.add(dl_fname)

  def synchronise_datafiles(self, project=None):

    # Now we retrieve some actual metadata.
    rootdict = self.session.api_metadata("%s/api/" % self._base_url)
    projlist = self.session.api_metadata(rootdict['projects'])

    if project is not None:
      projlist = [ proj for proj in projlist
                   if proj['code'].lower() == project.lower() ]

    liburls = sorted(list(set([ url for proj in projlist
                                for url in proj['libraries'] ])))

    for url in liburls:
      self.process_liburl(url)

if __name__ == '__main__':

  from argparse import ArgumentParser

  PARSER = ArgumentParser(description=\
    'Download Odom lab data files with optional MD5 checksum confirmation.')

  PARSER.add_argument('--project', dest='project', type=str, required=False,
                      help='The optional name of the project to which downloads'
                      + ' will be restricted')

  PARSER.add_argument('--without-download', dest='no_download', action='store_true',
                      help='Omit the file download step; this may be used to execute'
                      + ' checksums without repeating the file download.')

  PARSER.add_argument('--without-checksum', dest='no_checksum', action='store_true',
                      help='Omit the file MD5 checksum confirmation step. This is'
                      + ' provided as an option to skip what can be a disk I/O and'
                      + ' computationally intensive step.')

  PARSER.add_argument('--base-url', dest='baseurl', type=str,
                      default='https://dolab-srv003.cri.camres.org/django/repository',
                      help='The base repository URL to use for queries.')

  PARSER.add_argument('--existing', dest='projdirs', type=str, nargs='+',
                      help='Existing project directories containing files whose'
                      + ' download is to be skipped.')

  PARSER.add_argument('--filetype', dest='filetype', type=str,
                      default='fastq', choices=['fastq','bed','bam','mergedbam','tar'],
                      help='The type of file to download. The default is fastq.')

  ARGS = PARSER.parse_args()

  RETRIEVER = OdomDataRetriever(download = not ARGS.no_download,
                                checksum = not ARGS.no_checksum,
                                base_url = ARGS.baseurl,
                                filetype = ARGS.filetype,
                                project_dirs = ARGS.projdirs)
  RETRIEVER.synchronise_datafiles(project  = ARGS.project)
