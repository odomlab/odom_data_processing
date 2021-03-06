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

from osqpipe.pipeline.hicup import HiCUP

if __name__ == '__main__':
    
    import argparse

    PARSER = argparse.ArgumentParser(
        description='Runs HiCUP on read file or file pair. Note that the program leaves results in cluster. Use together with cs_run_hicup_postprocess.py.')
    PARSER.add_argument('--fq1', dest='fq1', type=str,
                        help='Fastq of pair1', required=True)
    PARSER.add_argument('--fq2', dest='fq2', type=str, default=None,
                        help='Fastq of pair2')
    PARSER.add_argument('--genome', dest='genome', type=str, required=True,
                     help='Reference genome name.')
    PARSER.add_argument('--enzyme', dest='enzyme', type=str, required=True,
                        help='Name of the restriction enzyme which was used in the HiC assay.')

    ARGS = PARSER.parse_args()


    HC = HiCUP(fq1=ARGS.fq1, genome=ARGS.genome, enzyme=ARGS.enzyme, fq2=ARGS.fq2)
    HC.write_hicup_config()
    HC.run_hicup()
