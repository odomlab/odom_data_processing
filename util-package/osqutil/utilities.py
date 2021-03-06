#!/usr/bin/env python
#
# Copyright 2018 Odom Lab, CRUK-CI, University of Cambridge
#
# This file is part of the osqutil python package.
#
# The osqutil python package is free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# The osqutil python package is distributed in the hope that it will
# be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the osqutil python package.  If not, see
# <http://www.gnu.org/licenses/>.


# Written originally by Gordon Brown.
# Extensive edits and additions made by Tim Rayner and Margus Lukk.


'''A collection of frequently unrelated functions used elsewhere in the code.'''

import os
import time
import os.path
import sys
import re
from tempfile import TemporaryFile
import stat
import grp
import gzip
import bz2
from contextlib import contextmanager
import hashlib
from subprocess import Popen, CalledProcessError, PIPE
from distutils import spawn
import threading
import socket
from .config import Config
from .setup_logs import configure_logging
from functools import wraps

###########################################################################
# N.B. we want no dependencies on the postgresql database in this
# module; it needs to be loadable on the cluster.
#

DBCONF = Config()
LOGGER = configure_logging('utilities')

###########################################################################
# Now for the rest of the utility functions...

def is_zipped(fname):
  '''
  Test whether a file is zipped or not, based on magic number with an
  additional check on file suffix. Assumes that the fname argument
  points directly to the file in question, and that the file is
  readable. Returns True/False accordingly.
  '''
  suff = os.path.splitext(fname)[1]
  if open(fname).read(2) == '\x1f\x8b': # gzipped file magic number.

    # Some files are effectively zipped but don't have a .gz
    # suffix. We model them in the repository as uncompressed, hence
    # we return False here. The main file type this affects is bam.
    if suff in ('.bam',):
      return False

    if suff != DBCONF.gzsuffix:
      LOGGER.warn("Gzipped file detected without %s suffix: %s",
                  DBCONF.gzsuffix, fname)

    return True
  else:
    if suff == DBCONF.gzsuffix:
      LOGGER.warn("Uncompressed file masquerading as gzipped: %s", fname)
    return False

def is_bzipped(fname):
  '''
  Test whether a file is bzipped or not, based on magic number with an
  additional check on file suffix. Assumes that the fname argument
  points directly to the file in question, and that the file is
  readable. Returns True/False accordingly.
  '''
  suff = os.path.splitext(fname)[1]
  if open(fname).read(3) == 'BZh': # bzip2 file magic number.

    if suff != '.bz2':
      LOGGER.warn("Bzipped file detected without '.bz2' suffix: %s",
                  fname)

    return True
  else:
    if suff == '.bz2':
      LOGGER.warn("Uncompressed file masquerading as bzipped: %s", fname)
    return False

def unzip_file(fname, dest=None, delete=True, overwrite=False):
  '''
  Unzip a file. If a destination filename is not supplied, we strip
  the suffix from the gzipped file, raising an error if the filename
  doesn't match our expectations.
  '''
  if not is_zipped(fname):
    raise ValueError("Attempted to unzip an already uncompressed file: %s"
                     % (fname,))

  # Derive the destination filename assuming a consistent filename
  # pattern.
  if dest is None:
    fnparts = os.path.splitext(fname)
    if fnparts[1] == DBCONF.gzsuffix:
      dest = os.path.splitext(fname)[0]
    else:
      raise ValueError("Unexpected gzipped file suffix: %s" % (fname,))

  # We refuse to overwrite existing output files.
  if os.path.exists(dest):
    if overwrite:
      os.unlink(dest)
    else:
      raise IOError("Gzip output file already exists; cannot continue: %s"
                    % (dest,))

  # We use external gzip where available
  LOGGER.info("Uncompressing gzipped file: %s", fname)
  if spawn.find_executable('gzip', path=DBCONF.hostpath):
    cmd = 'gzip -dc %s > %s' % (bash_quote(fname), bash_quote(dest))
    call_subprocess(cmd, shell=True, path=DBCONF.hostpath)

  else:

    # External gzip unavailable, so we use the (slower) gzip module.
    LOGGER.warning("Using python gzip module, which may be quite slow.")
    with open(dest, 'wb') as out_fd:
      with gzip.open(fname, 'rb') as gz_fd:
        for line in gz_fd:
          out_fd.write(line)

  if delete:
    os.unlink(fname)

  return dest

def rezip_file(fname, dest=None, delete=True, compresslevel=6, overwrite=False):
  '''
  Compress a file using gzip.
  '''
  if is_zipped(fname):
    raise ValueError("Trying to rezip an already-zipped file: %s" % (fname,))

  # Default gzip package compression level is 9; gzip executable default is 6.
  if not compresslevel in range(1,10):
    raise ValueError("Inappropriate compresslevel specified: %s" % (str(compresslevel),))

  if dest is None:
    dest = fname + DBCONF.gzsuffix

  # Check the gzipped file doesn't already exist (can cause gzip to
  # hang waiting for user confirmation).
  if os.path.exists(dest):
    if overwrite:
      os.unlink(dest)
    else:
      raise StandardError(
        "Output gzipped file already exists. Will not overwrite %s." % dest)

  # Again, using external gzip where available but falling back on the
  # (really quite slow) built-in gzip module where necessary.
  LOGGER.info("GZip compressing file: %s", fname)
  if spawn.find_executable('gzip', path=DBCONF.hostpath):
    cmd = 'gzip -%d -c %s > %s' % (compresslevel, bash_quote(fname), bash_quote(dest))
    call_subprocess(cmd, shell=True, path=DBCONF.hostpath)
  else:
    LOGGER.warning("Using python gzip module, which may be quite slow.")
    with gzip.open(dest, 'wb', compresslevel) as gz_fd:
      with open(fname, 'rb') as in_fd:
        for line in in_fd:
          gz_fd.write(line)

  if delete:
    os.unlink(fname)

  return dest

@contextmanager
def flexi_open(filename, *args, **kwargs):
  '''
  Simple context manager function to seamlessly handle gzipped and
  uncompressed files.
  '''
  if is_zipped(filename):
    handle = gzip.open(filename, *args, **kwargs)
  elif is_bzipped(filename):
    handle = bz2.BZ2File(filename, *args, **kwargs)
  else:
    handle = open(filename, *args, **kwargs)

  yield handle

  handle.close()

def _checksum_fileobj(fileobj, blocksize=65536):
  '''
  Use the hashlib.md5() function to calculate MD5 checksum on a file
  object, in a reasonably memory-efficient way.
  '''
  hasher = hashlib.md5()
  buf = fileobj.read(blocksize)
  while len(buf) > 0:
    hasher.update(buf)
    buf = fileobj.read(blocksize)

  return hasher.hexdigest()

def checksum_file(fname, unzip=True):
  '''
  Calculate the MD5 checksum for a file. Handles gzipped files by
  decompressing on the fly (i.e., the returned checksum is of the
  uncompressed data, to avoid gzip timestamps changing the MD5 sum).
  '''
  # FIXME consider piping from external gzip (where available) rather
  # than using gzip module?
  if unzip and is_zipped(fname):
    with gzip.open(fname, 'rb') as fileobj:
      md5 = _checksum_fileobj(fileobj)
  else:
    with open(fname, 'rb') as fileobj:
      md5 = _checksum_fileobj(fileobj)
  return md5

def parse_repository_filename(fname):
  '''
  Retrieve key information from a given filename.
  '''
  fname   = os.path.basename(fname)
  fnparts = os.path.splitext(fname)
  if fnparts[1] == DBCONF.gzsuffix:
    fname = fnparts[0]
  # N.B. don't add a bounding '$' as this doesn't match the whole
  # filename for e.g. *.mga.pdf. The terminal \. is important, in that
  # the MGA files will match but fastq will not. This match is dumped
  # as pipeline, which is semantically wrong but used consistently
  # elsewhere. FIXME to correctly return file type!
  name_pattern = re.compile(
    r"([a-zA-Z]+\d+)_.*_([A-Z]+)(\d+)(p[12])?(_chr21)?(\.[a-z]+)?\.")
  matchobj = name_pattern.match(fname)
  if matchobj:
    label = matchobj.group(1)
    fac = matchobj.group(2)
    lane = int(matchobj.group(3))
    if not matchobj.group(6):
      pipeline = 'chipseq' # default pipeline. Not elegant!
    else:
      pipeline = matchobj.group(6)[1:]
  else:
    LOGGER.warning("parse_repository_filename: failed to parse '%s'", fname)
    label = fac = lane = pipeline = None
  return (label, fac, lane, pipeline)

def get_filename_libcode(fname):
  '''Extract the library code from a given filename.'''

  # Takes first part of the filename up to the first underscore or period.
  name_pattern = re.compile(r"^([^\._]+)")
  matchobj = name_pattern.match(fname)
  return matchobj.group(1)

def set_file_permissions(group, path):
  '''
  Set a file group ownership, with appropriate read and write privileges.
  '''
  gid = grp.getgrnam(group).gr_gid
  try:
    os.chown(path, -1, gid)
    os.chmod(path,
             stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP)
  except OSError:
    LOGGER.warn("Failed to set ownership or permissions on '%s'."
                 + " Please fix manually.", path)

def bash_quote(string):
  '''Quote a string (e.g. a filename) to allow its use with bash and
  bash-related commands such as bsub, scp etc.'''

  # The following are all legal characters in a file path.
  bash_re = re.compile('(?=[^-+0-9a-zA-Z_,./\n])')
  return bash_re.sub('\\\\', string)

# Currently unused, we're keeping this in case it's useful in future.
def split_to_codes(string):
  # By Margus.
  # Date: 2012.10.29
  #
  # Todo: better error handling.

  """Splits string of comma separated DO numbers to a list of DO
  numbers. E.g. String: do234,do50-1,do500-do501,do201-198 would
  return do234, do50, do51, do500, do501, do198, do199, do200, do20"""
  codes = []
  string = string.lower()
  string = string.replace(' ', '')
  nums = string.split(',') # split by comma, continue working with substrings.
  for num in nums:
    # define some regexps
    rgx_complex = re.compile(r'^do.*\d+$')
    rgx_simple  = re.compile(r'^do\d+$')
    rgx_range   = re.compile(r'^do\d+-.*\d+$')
    rgx_digits  = re.compile(r'^\d+$')
    if re.match(rgx_complex, num):
      if re.match(rgx_simple, num):
        codes.append(num)
      elif re.match(rgx_range, num):
        splits = num.split('-')
        range_start = splits[0]
        range_end   = splits[1]
        if re.match(rgx_simple, range_start):
          # substring left of '-' is code
          num1 = range_start[2:]
          if re.match(rgx_simple, range_end):
            # substring right of '-' is code
            num2 = range_end[2:]
            if num2 >= num1:
              for i in range (int(num1), int(num2)+1):
                codes.append("do%d" % i)
            else:
              for i in range (int(num2), int(num1)+1):
                codes.append("do%d" % i)
          elif re.match(rgx_digits, range_end):
            # substring right of '-' is a number
            num2 = range_end
            length1 = len(num1)
            length2 = len(num2)
            if length1 <= length2:
              if num2 >= num1:
                for i in range (int(num1), int(num2)+1):
                  codes.append("do%d" % i)
              else:
                for i in range (int(num2), int(num1)+1):
                  codes.append("do%d" % i)
            else:
              num2rep = num1[:(length1-length2)] + num2
              if num2rep >= num1:
                for i in range (int(num1), int(num2rep)+1):
                  codes.append("do%d" % i)
              else:
                for i in range (int(num2rep), int(num1)+1):
                  codes.append("do%d" % i)
          else:
            # Dysfunctional substring! Generate error. Print what can be printed
            codes.append(range_start)
            # print "substr right from - did not match anything"
        else:
          # Dysfunctional substring! Generate error. Print what can be printed
          if range_end.match(rgx_simple):
            codes.append(range_end)
#           print "range_start did not match do*"
#     else:
#      # Dysfunctional substring! Generate an error. Print what can be printed
#      print " - not found in str"
#   else:
#    # Dysfunctional substring! Generate an error. Print what can be printed
#    print "matchobj match for ^do*.\d+$"
  return codes

def _write_stream_to_file(stream, fname):
  '''Simple function used internally to pipe a stream to a file.'''
  for data in stream:
    fname.write(data)

def call_subprocess(cmd, shell=False, tmpdir=DBCONF.tmpdir, path=None,
                    **kwargs):

  '''Generic wrapper around subprocess calls with handling of failed
  calls. This function starts threads to read stdout and stderr from
  the child process. In so doing it avoids deadlocking issues when
  reading large quantities of data from the stdout of the child
  process.'''

  # Credit to the maintainer of python-gnupg, Vinay Sajip, for the
  # original design of this function.

  # Set our PATH environmental var to point to the desired location.
  oldpath = os.environ['PATH']
  if path is not None:
    if type(path) is list:
      path = ":".join(path)
    os.environ['PATH'] = path
  else:
    LOGGER.warn("Subprocess calling external executable using undefined $PATH.")

  # We have **kwargs here mainly so we can support shell=True.
  kid = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=shell, **kwargs)

  stdoutfd = TemporaryFile(dir=tmpdir)
  stderrfd = TemporaryFile(dir=tmpdir)

  # We store streams in our own variables to avoid unexpected pitfalls
  # in how the subprocess object manages its attributes.

  # We disable this pylint error concerning missing Popen object
  # attributes because it's clearly bogus (subprocess is a core
  # module!).

  # pylint: disable=E1101
  stderr = kid.stderr
  err_read = threading.Thread(target=_write_stream_to_file,
                              args=(stderr, stderrfd))
  err_read.setDaemon(True)
  err_read.start()

  stdout = kid.stdout
  out_read = threading.Thread(target=_write_stream_to_file,
                              args=(stdout, stdoutfd))
  out_read.setDaemon(True)
  out_read.start()

  out_read.join()
  err_read.join()

  retcode = kid.wait()

  stderr.close()
  stdout.close()

  stdoutfd.seek(0, 0)

  os.environ['PATH'] = oldpath

  if retcode != 0:

    stderrfd.seek(0, 0)

    sys.stderr.write("\nSubprocess STDOUT:\n")
    for line in stdoutfd:
      sys.stderr.write("%s\n" % (line,))

    sys.stderr.write("\nSubprocess STDERR:\n")
    for line in stderrfd:
      sys.stderr.write("%s\n" % (line,))

    if type(cmd) == list:
      cmd = " ".join(cmd)

    raise CalledProcessError(kid.returncode, cmd)

  return stdoutfd

def munge_cruk_emails(emails):

  '''This is a (hopefully temporary) function needed to munge our new
  cruk.cam.ac.uk address lists to add in the old cancer.org.uk
  addresses as well. In principle this may be discardable with the
  move to a new LIMS.'''

  email_re = re.compile('@cruk.cam.ac.uk')
  return emails + [ email_re.sub('@cancer.org.uk', x) for x in emails ]

def read_file_to_key_value(fname, sep):
  """Reads text file (fname) to associated list. Key and value on the
  first and second column in each file are separated by sep."""
  keyvalue = {}
  with open(fname) as tabfh:
    for fline in tabfh:
      fline = fline.strip()   # remove surrounding whitespace
      try:
        key, value = fline.split(sep, 1)
      except ValueError:
        continue
      keyvalue[key] = value
  return keyvalue

# A central location for our default Fastq file naming scheme.
def build_incoming_fastq_name(sample_id, flowcell, flowlane, flowpair):

  '''Create a fastq filename according to the conventions used in
  cs_fetchFQ2.py.'''

  # N.B. This is typically called using the output of
  # parse_incoming_fastq_name, below.

  # Keep this in sync with the regex in parse_incoming_fastq_name.
  dst = "%s.%s.s_%s.r_%d.fq" % (sample_id, flowcell, flowlane, int(flowpair))
  return dst

def parse_incoming_fastq_name(fname, ext='.fq'):

  '''Parses the fastq filenames used by the pipeline during the
  initial download and demultiplexing process. The values matched by
  the regex are: library code (or list of library codes as stored in
  the LIMS); flowcell ID; flowcell lane; flow pair (1 or 2 at
  present). The ext argument can contain a regex fragment if desired.'''

  # Keep this in sync with the output of build_incoming_fastq_name.
  # Pattern altered to match the new filenames coming in from the
  # Genologics LIMS. Includes MiSeq naming.
  fq_re = re.compile(r'^([^\.]+)\.([\.\w-]+)\.s_(\d+)\.r_(\d+)%s$' % (ext,))
  matchobj = fq_re.match(fname)
  if matchobj is None:
    raise StandardError("Incoming file name structure not recognised: %s"
                        % fname)
  return (matchobj.group(*range(1, 5)))

def sanitize_samplename(samplename):
  '''
  Quick convenience function to remove potentially problematic
  characters from sample names (for use in bam file read groups, file
  names etc.).
  '''
  if samplename is None:
    return None
  sanity_re = re.compile(r'([ \\\/\(\)\"\*:;&|<>]+)')
  return(sanity_re.sub('_', samplename))

def determine_readlength(fastq):
  '''
  Guess the length of the reads in the fastq file. Assumes that the
  first read in the file is representative.
  '''
  # Currently just assumes that the second line is the first read, and
  # that it is representative.
  LOGGER.debug("Finding read length from fastq file %s...", fastq)
  rlen = None
  with flexi_open(fastq) as reader:
    for _num in range(2):
      line = reader.next()
    rlen = len(line.rstrip('\n'))

  return rlen

def memoize(func):
  '''
  Convenience function to memoize functions as necessary. May be of
  interest as a decorator for use with e.g. is_zipped(),
  checksum_file() etc. so that they can be called multiple times in
  defensively-written code but only actually read the file once.

  See
  https://technotroph.wordpress.com/2012/04/05/memoize-it-the-python-way/
  for discussion. Also note that python 3.2 and above have built-in
  memoization (functools.lru_cache).
  '''
  cache = {}
  @wraps(func)
  def wrap(*args):
    if args not in cache:
      cache[args] = func(*args)
    return cache[args]
  return wrap

def write_to_remote_file(txt, remotefname, user, host, append=False, sshkey=None):

  a = ''
  if append:
    a = '>'

  if sshkey is None:
    sshcmd = 'ssh'
  else:
    sshcmd = 'ssh -i %s' % sshkey
  cmd = "%s -o StrictHostKeyChecking=no %s@%s 'cat - %s> %s'" % (sshcmd, user, host, a, remotefname)
  p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
  p.stdin.write(txt)
  
  (stdout, stderr) = p.communicate()
  retcode = p.wait()

  if retcode != 0:
    if stdout is not None:
      sys.stdout.write("STDOUT:\n")
      sys.stdout.write(stdout)
    if stderr is not None:
      sys.stdout.write("STDERR:\n")
      sys.stderr.write(stderr)
    # Examples of common errors in STDERR:
    # bash: ...: No such file or directory
    # bash: ...: Permission denied
    # ssh: Could not resolve hostname ...: Temporary failure in name resolution
    
  return retcode

def create_remote_dir(user, host, folder):

  # Create folder in remote host
  cmd = "ssh -o StrictHostKeyChecking=no %s@%s 'mkdir -p %s'" % (user, host, folder)
  subproc = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
  (stdout, stderr) = subproc.communicate()
  retcode = subproc.wait()
  if retcode != 0:    
    if stdout is not None or stdout != "":
      LOGGER.info("STDOUT:")
      LOGGER.info(sys.stdout.write(stdout))
    if stderr is not None or stderr != "":
      LOGGER.error("STDERR:")
      LOGGER.error(sys.stderr.write(stderr))
      LOGGER.error("Failed to execute '%s'\n\n" % cmd)
      sys.exit(1)

def get_my_ip():
    return socket.gethostbyname(socket.getfqdn())

def get_my_hostname():
    return socket.gethostname()

def run_in_communication_host(argv):
  '''Runs list passed from sys.argv in communication host specified in configuration file over ssh.'''
  ## Example: place run_in_communication_host(sys.argv) in the start of any program/script that needs to be run
  ## in communication host.
  
  # Pass running the command if we are already in communication host
  my_name = get_my_hostname()
  if my_name == DBCONF.communicationhost:
    return None

  if argv[0].startswith('./'):
    argv[0] = argv[0].lstrip('./')

  LOGGER.warn("Running '%s' over ssh in %s", argv[0], DBCONF.communicationhost)

  cmd = ' '.join(argv)
  # if cmd.startswith('./'):
  #  cmd = cmd.lstrip('./')

  ssh_cmd = "ssh -o StrictHostKeyChecking=no %s@%s %s" % (DBCONF.user, DBCONF.communicationhost, cmd)
  # NB! Not using call_subprocess here as we just want to pass on the result written to stdout and stderr.
  # call_subprocess(ssh_cmd, shell=True, path=self.conf.hostpath)
  subproc = Popen(ssh_cmd, stdout=PIPE, stderr=PIPE, shell=True)
  (stdout, stderr) = subproc.communicate()
  retcode = subproc.wait()
  sys.stdout.write(stdout)
  sys.stderr.write(stderr)    
  
  sys.exit(retcode)

def transfer_file(source, destination, attempts = 2, sleeptime = 2, set_ownership=False):
  '''Transfers file from source to destination using rsync. Either source or destination can be a foreign host,
  in which case the string is expected to contain username@host:path.'''

  # NOTE: double-quoting for spaces etc. in file names has to be taken care of upstream

  retcode = 0
  
  sshflag = ''
  if ':' in source or ':' in destination:
    sshflag = '-e \"ssh -o StrictHostKeyChecking=no -c aes128-cbc\"'

  # cmd used to have -R option as well, not sure why it was included. Removed by lukk01 24/07  
  # Following has been commented out as rsync in slurm cluster is behind in versions and does not have --chown option.
  if set_ownership:
    cmd = "rsync -a --chmod=Du=rwx,Dg=r,Do=,Fu=rw,Fg=r,Fo= --chown=%s:%s %s %s %s" % (DBCONF.user, DBCONF.group, sshflag, source, destination)
  else:
    cmd = "rsync -a --chmod=Du=rwx,Dg=r,Do=,Fu=rw,Fg=r,Fo= %s %s %s" % (sshflag, source, destination)
  LOGGER.debug(cmd)

  a = attempts
  while a > 0:
    subproc = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    (stdout, stderr) = subproc.communicate()
    retcode = subproc.wait()
    # We write stdout and stderr where they belong in case these need to be parsed upstream
    if stdout is not None:
      sys.stdout.write(stdout)
    if stderr is not None:
      sys.stderr.write(stderr)
    if retcode == 0:
      break
    else:
      a -= 1           
      if a <= 0:
        break
      time.sleep(sleeptime)
  if retcode != 0:
    LOGGER.error("Failed to transfer %s to %s in %d attempts. Exiting!\n", source, destination, attempts)
    sys.exit(1)

  # This is a backup in case the rsync --chown option fails to work
  # (required to provide web access to files).
  if set_ownership and ':' not in destination: # i.e. destination is a local file
    set_file_permissions(DBCONF.group, destination)

def dorange_to_dolist(dorange):

    '''Takes string with (comma separated) range(s) of donumbers and transforms this to a list of donumbers in return.'''

    codelist = []
    
    commaranges = dorange.split(',')

    code_pattern = re.compile("^(do|DO)\d+$")
    number_pattern = re.compile("^\d+$")
    
    for commarange in commaranges:

        if '-' in commarange:
            (start,end) = commarange.split('-')
        else:
            start = end = commarange
        # For each comma separated range pair, check if start and end values can be interpreted
        end_is_do = True
        if not code_pattern.match(start):
            LOGGER.error("[ERROR] '%s' in input string '%s' not recognized as donumber. Exiting!" % (start, dorange))
            sys.exit(1)
        startnumber = start[2:]
        endnumber = None
        if code_pattern.match(end):
            endnumber = end[2:]
        elif number_pattern.match(end):
            endnumber = end
            end_is_do = False
        else:
            LOGGER.error("[ERROR]'%s' in input string '%s' not recognized as donumber. Exiting!" % (start, dorange))
            sys.exit(1)

        if len(endnumber) < len(startnumber):
            if end_is_do:
                LOGGER.error("[ERROR] Do number ranges should be ascending. Exiting!")
                sys.exit(1)
            newend = list(startnumber)
            startpos = len(newend)
            endpos = len(endnumber)
            while(endpos > 0):
                newend[startpos-1] = endnumber[endpos-1]
                startpos -= 1
                endpos -= 1
            endnumber = ''.join(newend)

        if int(startnumber) > int(endnumber):
            LOGGER.error("[ERROR] Do number ranges should be ascending. Exiting!")
            sys.exit(1)
        
        LOGGER.warn("[INFO] Processing range do%s-do%s" % (startnumber, endnumber))
        if startnumber == endnumber:
            codelist.append("do%s" % startnumber)
        else:
            for i in range(int(startnumber), int(endnumber)):
                code = "do%d" %i
                codelist.append(code)

    return codelist

def dolist_to_dorange(codes):

    '''Takes list of do numbers and converts this to comma separated list
    of ranges of donumbers. Codes which are not proper donumbers are
    appended to the output list (example: Universal human reference
    RNA, which is occasionally included in the Genomics LIMS ID listing.
    '''
    # E.g. codes = ['do42','do12345','do124','do13','do43','do11','do45','do44'] is converted to "do11,do13,do42-do45,do124,do12345"
    
    dorange = None
    numbers = []
    others  = []
    for c in codes:
        ci = re.sub('^DO', '', c, flags=re.I)
        if re.match('^\d+$', ci):
          numbers.append(int(ci))
        else:
          others.append(c)
    numbers.sort()
    others.sort()
    
    ranges = []
    start = None
    previous = None
    for i in range(len(numbers)):
        if start == None:
            start = numbers[i]
            previous = None
        else:
            if previous == None:
                if (numbers[i]-start) != 1:
                    ranges.append("do%d" % (start))
                    ranges.append("do%d" % (numbers[i]))
                    start = None
                    continue
                else:
                    previous = numbers[i]
            else:
                end = numbers[i]
                if (end-previous) != 1:
                    ranges.append("do%d-do%d" % (start,previous))
                    start = numbers[i]
                    previous = None
                else:
                    previous = numbers[i]

    if previous is not None:
        ranges.append("do%d-do%d" % (start,previous))
    else:
        if start is not None:
            ranges.append("do%d" % (start))

    if len(others) > 0:
      ranges += others
                      
    dorange = ",".join(ranges)

    return dorange

def dostring_to_dorange(dostring):

    '''Takes comma separated string of donumbers and condenses it to comma separated list of ranges of donumbers.'''
    # E.g. dostring "do42 ,do12345, do124,do13,do43, do11 ,do45, do44" is converted to "do11,do13,do42-do45,do124,do12345"
    
    s = dostring.replace(' ','')
    codes = s.split(',')
    dorange = dolist_to_dorange(codes)

    LOGGER.warn("Condensing \"%s\" ---> \"%s\"." % (dostring, dorange))

    return dorange

def dorange_to_dostring(dorange):

    '''Takes comma separated string of donumber ranges and expands it to comma separated string of donumbers.'''
    # E.g. "do11,do13,do42-do45,do124,do12345" --> "do42 ,do12345, do124,do13,do43, do11 ,do45, do44"
    
    dolist = dorange_to_dolist(dorange)
    dostring = ",".join(dolist)
    LOGGER.warn("Expanding \"%s\" ---> \"%s\"." % (dorange, dostring))

    return dostring

class BamPostProcessor(object):

  __slots__ = ('input_fn', 'output_fn', 'cleaned_fn', 'rgadded_fn',
               'common_args', 'samplename', 'compress')

  def __init__(self, input_fn, output_fn, tmpdir=DBCONF.tmpdir, samplename=None, compress=False):

    self.input_fn    = input_fn
    self.output_fn = output_fn
    self.samplename  = samplename

    output_base = os.path.splitext(output_fn)[0]
    self.cleaned_fn  = "%s_cleaned.bam" % output_base
    self.rgadded_fn  = "%s_rg.bam" % output_base
    
    # Some options are universal. Consider also adding QUIET=true, VERBOSITY=ERROR
    self.common_args = ['VALIDATION_STRINGENCY=SILENT',
                        'TMP_DIR=%s' % tmpdir]
    # In case post processing intermediate files are expected to be uncompressed add COMPRESSION_LEVEL=0
    self.compress = compress
    if not compress:
      self.common_args = self.common_args + ('COMPRESSION_LEVEL=0')

  def clean_sam(self):

    # Run CleanSam
    cmd = ['picard', 'CleanSam',
           'INPUT=%s'  % self.input_fn,
           'OUTPUT=%s' % self.cleaned_fn] + self.common_args

    return cmd
  
  def add_or_replace_read_groups(self):

    (libcode, facility, lanenum, _pipeline) = parse_repository_filename(self.output_fn)
    if libcode is None:
      LOGGER.warn("Applying dummy read group information to output bam.")
      libcode  = os.path.basename(self.output_fn)
      facility = 'Unknown'
      lanenum  = 0

    sample = self.samplename if self.samplename is not None else libcode

    # Run AddOrReplaceReadGroups
    cmd = ['picard', 'AddOrReplaceReadGroups',
           'INPUT=%s'  % self.cleaned_fn,
           'OUTPUT=%s' % self.rgadded_fn,
           'RGLB=%s'   % libcode,
           'RGSM=%s'   % sample,
           'RGCN=%s'   % facility,
           'RGPU=%d'   % int(lanenum),
           'RGPL=illumina'] + self.common_args

    return cmd

  def fix_mate_information(self):

    # Run FixMateInformation
    cmd = ['picard', 'FixMateInformation',
           'INPUT=%s'  % self.rgadded_fn,
           'OUTPUT=%s' % self.output_fn] + self.common_args

    return cmd
