import os
import re

import multiprocessing # workaround for Python bug. See http://bugs.python.org/issue15881#msg170215

from setuptools import setup, find_packages

README  = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()
SCRIPTS = [ os.path.join('bin', x) for x in os.listdir('bin') if re.search('\.py$', x) ]

# I'm not planning on installing the util/*.py scripts by default.

# Allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
  name='osqpipe',
  version='0.3.1',
  packages=find_packages(),
  include_package_data=True,
  license='GPLv3 License',
  description='Sequencing data analysis pipeline code and management web application as used by the Odom lab.',
  long_description=README,
  url='http://openwetware.org/wiki/Odom_Lab',
  author='Tim Rayner',
  author_email='tim.rayner@cruk.cam.ac.uk',
  classifiers=[
    'Environment :: Web Environment',
    'Framework :: Django',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: GPLv3 License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
    'Topic :: Internet :: WWW/HTTP',
    'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
  ],
  test_suite='nose.collector',
  scripts=SCRIPTS,
  install_requires=[
    'osqutil>=0.2.0',    # Functions relying only on core python modules.
    'Django==1.8.7',
    'django-sitetree<1.10',
    'django-dbarray<=0.2',
    'django-auth-ldap<1.4',
    'djangorestframework<3.4',
#    'django-sitetree',
#    'django-dbarray',
#    'django-auth-ldap',
#    'djangorestframework',
	
    'psycopg2',
    'fuzzy',
    #'pysam',
    #'gnuplot-py', # N.B. package not on PyPI, so can't be auto-installed.
    #'numpy<=1.15',
    'requests',
    'beautifulsoup4<4.7',
    'lxml', 
    'xlrd',       # Excel spreadsheet support.
    'markdown<3.0',   # REST browseable API support
  ],
  zip_safe=False,  # Prevents zipping of the installed egg, important for accessing django templates.
)
