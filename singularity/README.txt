Odom Lab Web Front End: Singularity Container

This container includes the software to run the web front end of the Odom-lab
sequencing data repository.  The repository consists of the actual files on
disk, and the PostgesQL database storing metadata.  These two components are
external to the container:

1) The data files are made accessible via a Singularity mapping from an
external directory to a particular mount point inside the container,
corresponding with the historical location of the repository on the
Odom-lab server dolab-srv006, by default "/data02/repository".

Locations of archived files can be set in the "archive_location" table, which
maps keywords to paths in the archive.  Since this container's data repository
includes everything, including archived material, these can all be set to
the location of the repository.

2) The database is external to the container; the connection parameters
will need to be set in the Django settings file.


Find the Container
==================

Check out from the Odom-lab git repository:

> git@github.com:odomlab/odom_data_processing.git


Build the Container
===================

Four files must be present in the current directory:

 - fnc-odompipe-key -- the private key for the fnc-odompipe user
                    -- purpose: to allow the build script to retrieve 
                       code from the Odom-lab repository.

 - httpd.conf -- the updated HTTP configuration file
              -- set up the virtual host that runs the server

 - setup.py -- modified version of the setup script for the repository
            -- sets the expected versions of required packages to the
               appropriate values

 - django_settings.py -- the Django setup file, with database settings.
                      -- Two versions in the repository have settings for
                         CRUK-CI and EBI.  Passwords are obfuscated, and
                         must be set after cloning the repo, but before
                         building the image.

It is usually convenient to create symbolic links to these files from the
checked-out git repo, in the directory where you build the container, so
you can keep everything in sync easily.


Run the Container
=================

To run the container, execute the usual Singularity run command.

> singularity run <container> 

Default values will be set for EBI:

> singularity run odom_singularity.sif 

Various directories must be mapped between the outside world and the container:

	/var/log
	/var/run/httpd
	/var/www/html/chipseq/tmp

export SINGULARITY_BINDPATH=var_log:/var/log,var_run_httpd:/var/run/httpd,var_www_html_chipseq_tmp:/var/www/html/chipseq/tmp

To run at the EBI, you will need a further mapping, from the repository at
/hps/research1/flicek/user/fnc-odompipe/repository to /data02/repository in the
container:

export SINGULARITY_BINDPATH=var_log:/var/log,var_run_httpd:/var/run/httpd,var_www_html_chipseq_tmp:/var/www/html/chipseq/tmp,/hps/research1/flicek/user/fnc-odompipe/repository:/data02/repository
