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

import os
import sys
from subprocess import Popen, PIPE
import shutil

import django
django.setup()

from osqpipe.models import Restrictome, Genome, Program

from osqutil.cluster import ClusterJobSubmitter
from osqutil.utilities import write_to_remote_file, transfer_file, checksum_file, create_remote_dir
from osqutil.config import Config

from osqutil.setup_logs import configure_logging
from logging import INFO, DEBUG
LOGGER = configure_logging('hicup')

class HiCUP(object):
    
    def __init__(self, fq1, genome=None, enzyme=None, fq2=None):
        
        self.fq1 = fq1
        self.fq2 = fq2
        self.genome = genome
        self.genome_index = None
        self.enzyme = enzyme
        self.restriction_file = None

        self._check_file(fq1)
        self._check_file(fq2)

        self.alignment_program = 'bowtie2'
        
        self.conf = Config()

        self.hicup_output_dir = os.path.join(self.conf.clusterworkdir, os.path.basename(self.fq1) + "_hicup")
        create_remote_dir(self.conf.clusteruser, self.conf.cluster, self.hicup_output_dir)
        
        # self.hicup_conf_fname = os.path.join(self.conf.clusterworkdir, os.path.basename(self.fq1) + "_hicup.conf")
        self.hicup_conf_fname = os.path.join(self.hicup_output_dir, os.path.basename(self.fq1) + "_hicup.conf")
        if self.fq1.endswith('p1.fq.gz'):
            report_name = self.fq1.replace('p1.fq.gz','')
        else:
            report_name = self.fq1.replace('.fq.gz','')
        self.hicup_report_fname = os.path.join(self.conf.clusterworkdir, report_name + ".hicup.html")
        self.hicup_report_bam = os.path.join(self.conf.clusterworkdir, report_name + ".bam")
        # Get genome_file
        if self.genome is not None:
            self.genome_index = self._genome_index_path(genome)
            if enzyme is not None:
                self.restriction_file = self._restriction_file_path(genome, enzyme)
                
    def add_genome_file(self, genome_file):
        self._check_file(genome_file)
        self.genome_file = genome_file

    def add_restriction_file(self, restriction_file):
        self._check_file(restriction_file)
        self.restriction_file = restriction_file
        
    def _check_file(self, fname):

        if fname is not None:
            if not os.path.isfile(fname):
                LOGGER.error("%s not found or accessible! Exiting!", fname)
                sys.exit(1)

    def _genome_index_path(self, genome):
        '''Alternatively to the code below, one could use genome_fasta_path from .bwa_runner'''
        
        try:
            genome_obj = Genome.objects.get(code=genome)
        except Genome.DoesNotExist:
            LOGGER.error("Genome '%s' not found!", genome)
            sys.exit(1)
        try:
            prog_obj = Program.objects.get(program=self.alignment_program, current=True)
        except Program.DoesNotExist:
            LOGGER.error("Program '%s' not found!", self.alignment_program)
            sys.exit(1)

        sciname = genome_obj.species.scientific_name
        sciname = sciname.replace(" ", "_")
        sciname = sciname.lower()
        if self.alignment_program == "bowtie2":
            indexdir = "bowtie-%s" % prog_obj.version
        else:
            indexdir = "%s-%s" % (self.alignment_program, prog_obj.version)

        index_path = os.path.join(self.conf.clustergenomedir, sciname,
                                  genome_obj.code, indexdir, genome_obj.code)

        return index_path

    def _restriction_file_path(self, genome, enzyme):

        program = 'hicup'
        
        try:
            genome_obj = Genome.objects.get(code=genome)
        except Genome.DoesNotExist:
            LOGGER.error("Genome '%s' not found!", genome)
            sys.exit(1)
        try:
            prog_obj = Program.objects.get(program=program, current=True)
        except Program.DoesNotExist:
            LOGGER.error("Program '%s' not found!" % program)
            sys.exit(1)        
        try:
            r = Restrictome.objects.get(genome=genome_obj, enzyme=enzyme, program=prog_obj)
        except Restrictome.DoesNotExist:
            LOGGER.error("No restrictome for genome '%s' and enzyme '%s' for HiCUP", self.genome, self.enzyme)
            sys.exit(1)
        sciname = genome_obj.species.scientific_name
        sciname = sciname.replace(" ", "_")
        sciname = sciname.lower()
        indexdir = "%s-%s" % (program,prog_obj.version)
        # E.g. /scratchb/user/fnc-odompipe/genomes/mus_musculus/mm10/hicup-0.5.10/Digest_mm10_HindIII_None_16-49-06_29-11-2017.txt
        rfile_path = os.path.join(self.conf.clustergenomedir, sciname, genome_obj.code, indexdir, r.filename)

        return rfile_path

    def write_hicup_config(self):

        LOGGER.info("Creating hicup config in cluster: %s" % self.hicup_conf_fname)
        threads = int(int(self.conf.num_threads)/2)
        if self.fq2 is None:
            threads = self.conf.num_threads
        
        conf_txt =  "Outdir: %s\n" % self.hicup_output_dir
        conf_txt += "Threads: %s\n" % threads
        conf_txt += "Quiet:0\n"
        conf_txt += "Keep:0\n"
        conf_txt += "Zip:1\n"
        conf_txt += "Bowtie2: %s\n" % self.alignment_program
        conf_txt += "Index: %s\n" % self.genome_index
        conf_txt += "Digest: %s\n" % self.restriction_file
        conf_txt += "Format: Sanger\n"
        conf_txt += "Longest: 800\n"
        conf_txt += "Shortest: 150\n"
        conf_txt += "%s\n" % self.fq1
        if self.fq2 is not None:
            conf_txt += "%s\n" % self.fq2

        try:
            sshkey = self.conf.clustersshkey
        except AttributeError, _err:
            sshkey = None
            
        write_to_remote_file(conf_txt, self.hicup_conf_fname, self.conf.clusteruser,
                             self.conf.cluster, append=False, sshkey=sshkey)
        
    def run_hicup(self):
        
        # Copy files
        # NB! There is vulnerability in below as we asssume input file follows odom lab convention
        code = self.fq1.split('_')[0]
        # destination = "%s@%s:%s" % (self.conf.user, self.conf.cluster, self.conf.clusterworkdir)
        destination = "%s@%s:%s" % (self.conf.user, self.conf.cluster, self.hicup_output_dir)
        LOGGER.info("Copying %s to cluster ..." % self.fq1)
        transfer_file(self.fq1, destination)        
        if self.fq2 is not None:
            LOGGER.info("Copying %s to cluster ..." % self.fq2)
            transfer_file(self.fq2, destination)

        # Send bsub for running hicup with correct number of thread request
        submitter = ClusterJobSubmitter()
        
        # FIX ME: Yes, its bad practice to hard code dependencies but this is a temporary fix as in some reason hicup can not be found even though in path
        #         Moreover, in some reason softlinking hicup to bin does not seem to be enough, probably beacuse the way dependencies in hicup main program are implemented.        
#        cmd = "mkdir %s && sleep 1 && cd %s && ~/software/external/hicup_v0.5.10/hicup --config %s && rm %s && rm %s" % (self.hicup_output_dir, self.conf.clusterworkdir, self.hicup_conf_fname, self.fq2, self.hicup_conf_fname)
        cmd = "cd %s && ~/software/external/hicup_v0.5.10/hicup --config %s && rm %s" % (self.hicup_output_dir, self.hicup_conf_fname, self.fq2)
        jobid = submitter.submit_command(cmd=cmd, mem=self.conf.clustermem, auto_requeue=False, threads=self.conf.num_threads)
        LOGGER.info("Hicup execution job id = %s" % jobid)
        #
        cmd = "cd %s && cs_run_hicup_postprocess.py --fq1 %s" % (self.hicup_output_dir, self.fq1)
        jobid = submitter.submit_command(cmd=cmd, mem=self.conf.clustermem, auto_requeue=False, threads=self.conf.num_threads, depend_jobs=[jobid])
        LOGGER.info("Hicup post process job id = %s" % jobid)
        
    def postprocess_hicup(self):
        '''Post-processes hicup results. NB! The function is expected to run in cluster.'''
        
        # Find html report and bam file
        report_file = None
        bam_file = None
        if not os.path.isdir(self.hicup_output_dir):
            LOGGER.error("No report dir found! Expected %s.", self.hicup_output_dir)
            sys.exit(1)
        # Find report file
        for f in os.listdir(self.hicup_output_dir):
            if f.endswith('html'):
                report_file = f
        # Find bam file
        for f in os.listdir(self.hicup_output_dir):
            if f.endswith('bam'):
                bam_file = f

        if report_file is None:
            LOGGER.error("No html report found in %s.", self.hicup_output_dir)
            sys.exit(1)

        if bam_file is None:
            LOGGER.error("No bam output found in %s.", self.hicup_output_dir)
            sys.exit(1)
            
        # Rename report file
        os.rename(os.path.join(self.hicup_output_dir, report_file), self.hicup_report_fname)

        # Rename bam file
        os.rename(os.path.join(self.hicup_output_dir, bam_file), self.hicup_report_bam)

        # Copy report to repository
        # NB! Vulnerability below! We asssume file name following Odom lab convention which may not always be the case?!
        code = self.fq1.split('_')[0]
        dest_file = os.path.join(self.conf.repositorydir, code, os.path.basename(self.hicup_report_fname))
        destination = "%s@%s:%s/%s/" % (self.conf.user, self.conf.datahost, self.conf.repositorydir, code)
        transfer_file(self.hicup_report_fname, destination, set_ownership=False)

        # Set chgrp for the report file
        cmd2 = "ssh -o StrictHostKeyChecking=no %s@%s 'chgrp %s %s'" % (self.conf.user, self.conf.datahost, self.conf.group, dest_file)
        subproc = Popen(cmd2, stdout=PIPE, stderr=PIPE, shell=True)
        (stdout, stderr) = subproc.communicate()
        retcode = subproc.wait()
        if stdout is not None or stdout != "":
            LOGGER.info("STDOUT:")
            LOGGER.info(sys.stdout.write(stdout))
        if stderr is not None or stderr != "":
            LOGGER.error("STDERR:")
            LOGGER.error(sys.stderr.write(stderr))
        if retcode != 0:
            LOGGER.error("Failed to execute '%s'\n\n" % cmd)
            sys.exit(1)
        
        # Register report in repository
        md5 = checksum_file(self.hicup_report_fname, unzip=False)
        cmd = "cs_addFile.py --qcfile --program_name hicup -M %s %s" % (os.path.basename(self.hicup_report_fname), md5)

        subproc = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        (stdout, stderr) = subproc.communicate()
        retcode = subproc.wait()
        if stdout is not None or stdout != "":
            LOGGER.info("STDOUT:")
            LOGGER.info(sys.stdout.write(stdout))
        if stderr is not None or stderr != "":
            LOGGER.error("STDERR:")
            LOGGER.error(sys.stderr.write(stderr))
        if retcode != 0:
            if 'already exists' in stderr:
                LOGGER.info("%s already in repository!" % os.path.basename(self.hicup_report_fname))
            else:
                LOGGER.error("Failed to register %s in repository!\n\n" % os.path.basename(self.hicup_report_fname))

        # Copy bam over for processing
        bam_destination = os.path.join(self.conf.repositorydir,"incoming")
        dest_file = os.path.join(bam_destination, os.path.basename(self.hicup_report_bam))
        destination = "%s@%s:%s" % (self.conf.user, self.conf.datahost, bam_destination)
        transfer_file(self.hicup_report_bam, destination, set_ownership=False)

        # Set chgrp for bam (yes, this is not an elegant way of doing this!)        
        cmd2 = "ssh -o StrictHostKeyChecking=no %s@%s 'chgrp %s %s && touch %s.done'" % (self.conf.user, self.conf.datahost, self.conf.group, dest_file, dest_file)
        subproc = Popen(cmd2, stdout=PIPE, stderr=PIPE, shell=True)
        (stdout, stderr) = subproc.communicate()
        retcode = subproc.wait()
        if stdout is not None or stdout != "":
            LOGGER.info("STDOUT:")
            LOGGER.info(sys.stdout.write(stdout))
        if stderr is not None or stderr != "":
            LOGGER.error("STDERR:")
            LOGGER.error(sys.stderr.write(stderr))
        if retcode != 0:
            LOGGER.error("Failed to execute '%s'\n\n" % cmd)

        # Remove report dir
        shutil.rmtree(self.hicup_output_dir)
        # Remove hicup report
        os.remove(self.hicup_report_fname)
        # os.remove(self.hicup_report_bam)
