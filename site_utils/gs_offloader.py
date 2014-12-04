#!/usr/bin/python
#
# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Script to archive old Autotest results to Google Storage.

Uses gsutil to archive files to the configured Google Storage bucket.
Upon successful copy, the local results directory is deleted.
"""

import datetime
import logging
import logging.handlers
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

from optparse import OptionParser

import common
from autotest_lib.client.common_lib import utils

try:
    # Does not exist, nor is needed, on moblab.
    import psutil
except ImportError:
    psutil = None

import job_directories
from autotest_lib.client.common_lib import global_config
from autotest_lib.client.common_lib.cros.graphite import stats
from autotest_lib.scheduler import email_manager
from chromite.lib import parallel


GS_OFFLOADING_ENABLED = global_config.global_config.get_config_value(
    'CROS', 'gs_offloading_enabled', type=bool, default=True)

STATS_KEY = 'gs_offloader.%s' % socket.gethostname()

timer = stats.Timer(STATS_KEY)

# Nice setting for process, the higher the number the lower the priority.
NICENESS = 10

# Maximum number of seconds to allow for offloading a single
# directory.
OFFLOAD_TIMEOUT_SECS = 60 * 60

# Sleep time per loop.
SLEEP_TIME_SECS = 5

# Minimum number of seconds between e-mail reports.
REPORT_INTERVAL_SECS = 60 * 60

# Location of Autotest results on disk.
RESULTS_DIR = '/usr/local/autotest/results'

# Hosts sub-directory that contains cleanup, verify and repair jobs.
HOSTS_SUB_DIR = 'hosts'

LOG_LOCATION = '/usr/local/autotest/logs/'
LOG_FILENAME_FORMAT = 'gs_offloader_%s_log_%s.txt'
LOG_TIMESTAMP_FORMAT = '%Y%m%d_%H%M%S'
LOGGING_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# pylint: disable=E1120
NOTIFY_ADDRESS = global_config.global_config.get_config_value(
    'SCHEDULER', 'notify_email', default='')

ERROR_EMAIL_SUBJECT_FORMAT = 'GS Offloader notifications from %s'
ERROR_EMAIL_REPORT_FORMAT = '''\
gs_offloader is failing to offload results directories.

First failure       Count   Directory name
=================== ======  ==============================
'''
# --+----1----+----  ----+  ----+----1----+----2----+----3

ERROR_EMAIL_DIRECTORY_FORMAT = '%19s  %5d  %-1s\n'
ERROR_EMAIL_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

USE_RSYNC_ENABLED = global_config.global_config.get_config_value(
    'CROS', 'gs_offloader_use_rsync', type=bool, default=False)


class TimeoutException(Exception):
  """Exception raised by the timeout_handler."""
  pass


def timeout_handler(_signum, _frame):
  """Handler for SIGALRM when the offloading process times out.

  @param _signum: Signal number of the signal that was just caught.
                  14 for SIGALRM.
  @param _frame: Current stack frame.
  @raise TimeoutException: Automatically raises so that the time out is caught
                           by the try/except surrounding the Popen call.

  """
  raise TimeoutException('Process Timed Out')


def get_cmd_list(dir_entry, gs_path):
  """Return the command to offload a specified directory.

  @param dir_entry: Directory entry/path that which we need a cmd_list to
                    offload.
  @param gs_path: Location in google storage where we will
                  offload the directory.

  @return: A command list to be executed by Popen.

  """
  if USE_RSYNC_ENABLED:
    return ['gsutil', '-m', 'rsync', '-eR',
            dir_entry, os.path.join(gs_path, os.path.basename(dir_entry))]
  return ['gsutil', '-m', 'cp', '-eR', '-a', 'project-private',
          dir_entry, gs_path]


def get_directory_size_kibibytes_cmd_list(directory):
    """Returns command to get a directory's total size."""
    # Having this in its own method makes it easier to mock in unittests.
    return ['du', '-sk', directory]


def get_directory_size_kibibytes(directory):
    """Calculate the total size of a directory with all its contents.

    @param directory: Path to the directory

    @returns: Size of the directory in kibibytes.
    """
    cmd = get_directory_size_kibibytes_cmd_list(directory)
    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_data, stderr_data = process.communicate()

    if process.returncode != 0:
        # This function is used for statistics only, if it fails, nothing else
        # should crash.
        logging.warning('Getting size of %s failed. Stderr:', directory)
        logging.warning(stderr_data)
        return 0

    return int(stdout_data.split('\t', 1)[0])


def get_offload_dir_func(gs_uri):
  """Returns the offload directory function for the given gs_uri

  @param gs_uri: Google storage bucket uri to offload to.

  @returns offload_dir function to preform the offload.
  """
  @timer.decorate
  def offload_dir(dir_entry, dest_path):
    """Offload the specified directory entry to Google storage.

    @param dir_entry: Directory entry to offload.
    @param dest_path: Location in google storage where we will offload
                      the directory.

    """
    try:
      counter = stats.Counter(STATS_KEY)
      counter.increment('jobs_offload_started')

      error = False
      stdout_file = tempfile.TemporaryFile('w+')
      stderr_file = tempfile.TemporaryFile('w+')
      process = None
      signal.alarm(OFFLOAD_TIMEOUT_SECS)
      gs_path = '%s%s' % (gs_uri, dest_path)
      process = subprocess.Popen(get_cmd_list(dir_entry, gs_path),
                                 stdout=stdout_file, stderr=stderr_file)
      process.wait()
      signal.alarm(0)

      if process.returncode == 0:
        kibibytes_transferred = get_directory_size_kibibytes(dir_entry)

        counter.increment('kibibytes_transferred_total', kibibytes_transferred)
        stats.Gauge(STATS_KEY).send(
            'kibibytes_transferred', kibibytes_transferred)
        counter.increment('jobs_offloaded')
        shutil.rmtree(dir_entry)
      else:
        error = True
    except TimeoutException:
      # If we finished the call to Popen(), we may need to terminate
      # the child process.  We don't bother calling process.poll();
      # that inherently races because the child can die any time it
      # wants.
      if process:
          try:
              process.terminate()
          except OSError:
              # We don't expect any error other than "No such
              # process".
              pass
      logging.error('Offloading %s timed out after waiting %d seconds.',
                    dir_entry, OFFLOAD_TIMEOUT_SECS)
      error = True
    finally:
      signal.alarm(0)
      if error:
        # Rewind the log files for stdout and stderr and log their contents.
        stdout_file.seek(0)
        stderr_file.seek(0)
        logging.error('Error occurred when offloading %s:', dir_entry)
        logging.error('Stdout:\n%s \nStderr:\n%s',
                      stdout_file.read(), stderr_file.read())
      stdout_file.close()
      stderr_file.close()
  return offload_dir


def delete_files(dir_entry, dest_path):
  """Simply deletes the dir_entry from the filesystem.

  Uses same arguments as offload_dir so that it can be used in replace of it on
  systems that only want to delete files instead of offloading them.

  @param dir_entry: Directory entry to offload.
  @param dest_path: NOT USED.
  """
  shutil.rmtree(dir_entry)


def report_offload_failures(joblist):
  """Generate e-mail notification for failed offloads.

  The e-mail report will include data from all jobs in `joblist`.

  @param joblist List of jobs to be reported in the message.

  """
  def _format_job(job):
    d = datetime.datetime.fromtimestamp(job.get_failure_time())
    data = (d.strftime(ERROR_EMAIL_TIME_FORMAT),
            job.get_failure_count(),
            job.get_job_directory())
    return ERROR_EMAIL_DIRECTORY_FORMAT % data
  joblines = [_format_job(job) for job in joblist]
  joblines.sort()
  email_subject = ERROR_EMAIL_SUBJECT_FORMAT % socket.gethostname()
  email_message = ERROR_EMAIL_REPORT_FORMAT + ''.join(joblines)
  email_manager.manager.send_email(NOTIFY_ADDRESS, email_subject,
                                   email_message)


class Offloader(object):
  """State of the offload process.

  Contains the following member fields:
    * _offload_func:  Function to call for each attempt to offload
      a job directory.
    * _jobdir_classes:  List of classes of job directory to be
      offloaded.
    * _processes:  Maximum number of outstanding offload processes
      to allow during an offload cycle.
    * _age_limit:  Minimum age in days at which a job may be
      offloaded.
    * _open_jobs: a dictionary mapping directory paths to Job
      objects.
    * _next_report_time:  Earliest time that we should send e-mail
      if there are failures to be reported.

  """

  def __init__(self, options):
    if options.delete_only:
      self._offload_func = delete_files
    else:
      gs_uri = utils.get_offload_gsuri()
      logging.debug('Offloading to: %s', gs_uri)
      self._offload_func = get_offload_dir_func(gs_uri)
    classlist = []
    if options.process_hosts_only or options.process_all:
      classlist.append(job_directories.SpecialJobDirectory)
    if not options.process_hosts_only:
      classlist.append(job_directories.RegularJobDirectory)
    self._jobdir_classes = classlist
    assert self._jobdir_classes
    self._processes = options.parallelism
    self._age_limit = options.days_old
    self._open_jobs = {}
    self._next_report_time = time.time()

  def _add_new_jobs(self):
    """Find new job directories that need offloading.

    Go through the file system looking for valid job directories
    that are currently not in `self._open_jobs`, and add them in.

    """
    new_job_count = 0
    for cls in self._jobdir_classes:
      for resultsdir in cls.get_job_directories():
        if resultsdir in self._open_jobs:
          continue
        self._open_jobs[resultsdir] = cls(resultsdir)
        new_job_count += 1
    logging.debug("Start of offload cycle - found %d new jobs",
                  new_job_count)

  def _remove_offloaded_jobs(self):
    """Removed offloaded jobs from `self._open_jobs`."""
    removed_job_count = 0
    for jobkey, job in self._open_jobs.items():
      if job.is_offloaded():
        del self._open_jobs[jobkey]
        removed_job_count += 1
    logging.debug("End of offload cycle - cleared %d new jobs, "
                  "carrying %d open jobs",
                  removed_job_count, len(self._open_jobs))

  def _have_reportable_errors(self):
    """Return whether any jobs need reporting via e-mail.

    @returns True if there are reportable jobs in `self._open_jobs`,
             or False otherwise.
    """
    for job in self._open_jobs.values():
      if job.is_reportable():
        return True
    return False

  def _update_offload_results(self):
    """Check and report status after attempting offload.

    This function processes all jobs in `self._open_jobs`, assuming
    an attempt has just been made to offload all of them.

    Any jobs that have been successfully offloaded are removed.

    If any jobs have reportable errors, and we haven't generated
    an e-mail report in the last `REPORT_INTERVAL_SECS` seconds,
    send new e-mail describing the failures.

    """
    self._remove_offloaded_jobs()
    if self._have_reportable_errors():
      # N.B. We include all jobs that have failed at least once,
      # which may include jobs that aren't otherwise reportable.
      failed_jobs = [j for j in self._open_jobs.values()
                             if j.get_failure_time()]
      logging.debug("Currently there are %d jobs with offload failures",
                    len(failed_jobs))
      if time.time() >= self._next_report_time:
          logging.debug("Reporting failures by e-mail")
          report_offload_failures(failed_jobs)
          self._next_report_time = time.time() + REPORT_INTERVAL_SECS

  def offload_once(self):
    """Perform one offload cycle.

    Find all job directories for new jobs that we haven't seen
    before.  Then, attempt to offload the directories for any
    jobs that have finished running.  Offload of multiple jobs
    is done in parallel, up to `self._processes` at a time.

    After we've tried uploading all directories, go through the list
    checking the status of all uploaded directories.  If necessary,
    report failures via e-mail.

    """
    self._add_new_jobs()
    with parallel.BackgroundTaskRunner(
        self._offload_func, processes=self._processes) as queue:
      for job in self._open_jobs.values():
        job.enqueue_offload(queue, self._age_limit)
    self._update_offload_results()


def parse_options():
  """Parse the args passed into gs_offloader."""
  defaults = 'Defaults:\n  Destination: %s\n  Results Path: %s' % (
      utils.DEFAULT_OFFLOAD_GSURI, RESULTS_DIR)
  usage = 'usage: %prog [options]\n' + defaults
  parser = OptionParser(usage)
  parser.add_option('-a', '--all', dest='process_all', action='store_true',
                    help='Offload all files in the results directory.')
  parser.add_option('-s', '--hosts', dest='process_hosts_only',
                    action='store_true',
                    help='Offload only the special tasks result files located'
                         'in the results/hosts subdirectory')
  parser.add_option('-p', '--parallelism', dest='parallelism', type='int',
                    default=1, help='Number of parallel workers to use.')
  parser.add_option('-o', '--delete_only', dest='delete_only',
                    action='store_true',
                    help='GS Offloader will only the delete the directories '
                         'and will not offload them to google storage. '
                         'NOTE: If global_config variable '
                         'CROS.gs_offloading_enabled is False, --delete_only'
                         ' is automatically True.',
                    default=not GS_OFFLOADING_ENABLED)
  parser.add_option('-d', '--days_old', dest='days_old',
                    help='Minimum job age in days before a result can be '
                    'offloaded.', type='int', default=0)
  parser.add_option('-l', '--log_size', dest='log_size',
                    help='Limit the offloader logs to a specified number of '
                         'Mega Bytes.', type='int', default=0)
  options = parser.parse_args()[0]
  if options.process_all and options.process_hosts_only:
    parser.print_help()
    print ('Cannot process all files and only the hosts subdirectory. '
           'Please remove an argument.')
    sys.exit(1)
  return options


def main():
  """Main method of gs_offloader."""
  options = parse_options()

  if options.process_all:
    offloader_type = 'all'
  elif options.process_hosts_only:
    offloader_type = 'hosts'
  else:
    offloader_type = 'jobs'

  log_timestamp = time.strftime(LOG_TIMESTAMP_FORMAT)
  if options.log_size > 0:
    log_timestamp = ''
  log_filename = os.path.join(LOG_LOCATION,
          LOG_FILENAME_FORMAT % (offloader_type, log_timestamp))
  log_formatter = logging.Formatter(LOGGING_FORMAT)
  # Replace the default logging handler with a RotatingFileHandler. If
  # options.log_size is 0, the file size will not be limited. Keeps one backup
  # just in case.
  handler = logging.handlers.RotatingFileHandler(
      log_filename, maxBytes=1024*options.log_size, backupCount=1)
  handler.setFormatter(log_formatter)
  logger = logging.getLogger()
  logger.setLevel(logging.DEBUG)
  logger.addHandler(handler)

  # Nice our process (carried to subprocesses) so we don't overload
  # the system.
  logging.debug('Set process to nice value: %d', NICENESS)
  os.nice(NICENESS)
  if psutil:
      proc = psutil.Process()
      logging.debug('Set process to ionice IDLE')
      proc.ionice(psutil.IOPRIO_CLASS_IDLE)

  # os.listdir returns relative paths, so change to where we need to be to avoid
  # an os.path.join on each loop.
  logging.debug('Offloading Autotest results in %s', RESULTS_DIR)
  os.chdir(RESULTS_DIR)

  signal.signal(signal.SIGALRM, timeout_handler)

  offloader = Offloader(options)
  while True:
    offloader.offload_once()
    time.sleep(SLEEP_TIME_SECS)


if __name__ == '__main__':
  main()
