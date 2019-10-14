### Odom Lab Web Front End: Singularity Container

This container includes the software to run the pipeline and web front end of the Odom-lab sequencing data repository.  The repository consists of the actual files on disk, and the PostgesQL database storing metadata.  These two components are external to the container:

1. The data files are made accessible via a Singularity mapping from an external directory to a particular mount point inside the container, corresponding with the historical location of the repository on the Odom-lab server dolab-srv006, by default <code>/data02/repository</code>.

2. The database is external to the container; the connection parameters will need to be set in the Django settings file when the container is built.

#### Find the Container

Check out from the Odom-lab git repository:

> git@github.com:odomlab/odom_data_processing.git

#### Build the Container

Three files (included in the Git repo) must be present in the current directory when building the container:

 * <code>httpd.conf</code> - the modified HTTP configuration file. This file configures the virtual host that runs the web server.

 * <code>setup.py</code> - a modified version of the setup script for the repository. This sets the expected versions of required packages to the appropriate values (among other things).

 * <code>settings.py</code> - the Django setup file, with database settings.  The Git repo includes versions for CRUK-CI and EBI; create a symbolic link <code>settings.py</code> to one or the other before building the container.  The versions in the repo have obfuscated passwords; these must be set appropriately before building the container.  BE CAREFUL: do not commit versions with the real passwords to the repo.

It is temporarily necessary to include a fourth file, <code>htslib-1.9.tar.bz2</code>, when building the container, because on-demand downloading of the file at container build time has been failing intermittently due to errors with some combination of GitHub and AWS.  Get this file from GitHub:

> https://github.com/samtools/htslib/releases/download/1.9/htslib-1.9.tar.bz2

#### Run the Container

Mappings must be set up between the host and the container, to make writeable areas inside the container:

 * <code>/var/log/httpd</code> - to write log files, obviously.
 * <code>/var/run/httpd</code> - for the Apache server to store its lock files.
 * <code>/var/www/html/chipseq/tmp</code> - for the web server to create and store on-the-fly created images.

In addition, if the repository (the data files, that is, not the code repo) is at some other location than <code>/data02/repository</code>, then an additional mapping must be made between the host location of the data files and <code>/data02/repository</code> in the container.

It is convenient to use the <code>SINGULARITY_BINDPATH</code> environment variable to set the mappings, rather than the tedious matter of setting them on the command line each time:

> export&nbsp;SINGULARITY_BINDPATH=var_log_httpd:/var/log/httpd,var_run_httpd:/var/run/httpd,var_www_html_chipseq_tmp:/var/www/html/chipseq/tmp

ensuring that the directories exist, and are world-writeable.

To run the container, execute the usual Singularity run command.

> singularity run --no-home <code>odom.sif</code>

(or whatever you've named the container).  The Apache server should now be listening on port 8080.  (The <code>--no-home</code> option tells Singularity not to mount your home directory; otherwise it will mount it, and possibly use your personal configuration files, write to your history, and so on.)  To test, try the following URL:

> http://localhost:8080/django/repository/

assuming you have started the container on your local host.  Use <code>wget</code> or similar to test the URL from the command line.
