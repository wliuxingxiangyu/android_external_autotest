#!/usr/bin/python
#
# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tool to validate code in prod branch before pushing to lab.

The script runs push_to_prod suite to verify code in prod branch is ready to be
pushed. Link to design document:
https://docs.google.com/a/google.com/document/d/1JMz0xS3fZRSHMpFkkKAL_rxsdbNZomhHbC3B8L71uuI/edit

To verify if prod branch can be pushed to lab, run following command in
chromeos-autotest.cbf server:
/usr/local/autotest/site_utils/test_push.py -e someone@company.com

The script uses latest gandof canary build as test build by default.

"""

import argparse
import ast
import getpass
import multiprocessing
import os
import re
import subprocess
import sys
import time
import traceback
import urllib2

import common
try:
    from autotest_lib.frontend import setup_django_environment
    from autotest_lib.frontend.afe import models
except ImportError:
    # Unittest may not have Django database configured and will fail to import.
    pass
from autotest_lib.client.common_lib import global_config
from autotest_lib.server import site_utils
from autotest_lib.server.cros import provision
from autotest_lib.server.cros.dynamic_suite import frontend_wrappers
from autotest_lib.server.hosts import factory
from autotest_lib.site_utils import gmail_lib
from autotest_lib.site_utils.suite_scheduler import constants

AUTOTEST_DIR='/usr/local/autotest'
CONFIG = global_config.global_config

AFE = frontend_wrappers.RetryingAFE(timeout_min=0.5, delay_sec=2)

MAIL_FROM = 'chromeos-test@google.com'
BUILD_REGEX = 'R[\d]+-[\d]+\.[\d]+\.[\d]+'
RUN_SUITE_COMMAND = 'run_suite.py'
PUSH_TO_PROD_SUITE = 'push_to_prod'
DUMMY_SUITE = 'dummy'
AU_SUITE = 'paygen_au_canary'
DEFAULT_TIMEOUT_MIN_FOR_SUITE_JOB = 30
IMAGE_BUCKET = CONFIG.get_config_value('CROS', 'image_storage_server')
DEFAULT_NUM_DUTS = "{'board:gandof': 4, 'board:quawks': 2}"

SUITE_JOB_START_INFO_REGEX = ('^.*Created suite job:.*'
                              'tab_id=view_job&object_id=(\d+)$')

# Dictionary of test results keyed by test name regular expression.
EXPECTED_TEST_RESULTS = {'^SERVER_JOB$':                 'GOOD',
                         # This is related to dummy_Fail/control.dependency.
                         'dummy_Fail.dependency$':       'TEST_NA',
                         'login_LoginSuccess.*':         'GOOD',
                         'provision_AutoUpdate.double':  'GOOD',
                         'dummy_Pass.*':                 'GOOD',
                         'dummy_Fail.Fail$':             'FAIL',
                         'dummy_Fail.RetryFail$':        'FAIL',
                         'dummy_Fail.RetrySuccess':      'GOOD',
                         'dummy_Fail.Error$':            'ERROR',
                         'dummy_Fail.Warn$':             'WARN',
                         'dummy_Fail.NAError$':          'TEST_NA',
                         'dummy_Fail.Crash$':            'GOOD',
                         }

EXPECTED_TEST_RESULTS_DUMMY = {'^SERVER_JOB$':       'GOOD',
                               'dummy_Pass.*':       'GOOD',
                               'dummy_Fail.Fail':    'FAIL',
                               'dummy_Fail.Warn':    'WARN',
                               'dummy_Fail.Crash':   'GOOD',
                               'dummy_Fail.Error':   'ERROR',
                               'dummy_Fail.NAError': 'TEST_NA',}

EXPECTED_TEST_RESULTS_AU = {'SERVER_JOB$':                        'GOOD',
         'autoupdate_EndToEndTest.paygen_au_canary_delta.*': 'GOOD',
         'autoupdate_EndToEndTest.paygen_au_canary_full.*':  'GOOD',
         }

URL_HOST = CONFIG.get_config_value('SERVER', 'hostname', type=str)
URL_PATTERN = CONFIG.get_config_value('CROS', 'log_url_pattern', type=str)

# Some test could be missing from the test results for various reasons. Add
# such test in this list and explain the reason.
IGNORE_MISSING_TESTS = [
    # For latest build, npo_test_delta does not exist.
    'autoupdate_EndToEndTest.npo_test_delta.*',
    # For trybot build, nmo_test_delta does not exist.
    'autoupdate_EndToEndTest.nmo_test_delta.*',
    # Older build does not have login_LoginSuccess test in push_to_prod suite.
    # TODO(dshi): Remove following lines after R41 is stable.
    'login_LoginSuccess']

# Save all run_suite command output.
run_suite_output = []

class TestPushException(Exception):
    """Exception to be raised when the test to push to prod failed."""
    pass


def check_dut_inventory(required_num_duts):
    """Check DUT inventory for each board.

    @param required_num_duts: a dict specified the number of DUT each board
                              requires in order to finish push tests.
    @raise TestPushException: if number of DUTs are less than the requirement.
    """
    hosts = AFE.run('get_hosts', status='Ready', locked=False)
    boards = [[l for l in host['labels'] if l.startswith('board:')][0]
              for host in hosts]
    current_inventory = {b:boards.count(b) for b in boards}
    error_msg = ''
    for board, req_num in required_num_duts.items():
        curr_num = current_inventory.get(board, 0)
        if curr_num < req_num:
            error_msg += ('\nRequire %d %s DUTs, only %d are Ready now' %
                          (req_num, board, curr_num))
    if error_msg:
        raise TestPushException('Not enough DUTs to run push tests. %s' %
                                error_msg)


def powerwash_dut(hostname):
    """Powerwash the dut with the given hostname.

    @param hostname: hostname of the dut.
    """
    host = factory.create_host(hostname)
    host.run('echo "fast safe" > '
             '/mnt/stateful_partition/factory_install_reset')
    host.run('reboot')
    host.close()


def get_default_build(board='gandof'):
    """Get the default build to be used for test.

    @param board: Name of board to be tested, default is gandof.
    @return: Build to be tested, e.g., gandof-release/R36-5881.0.0
    """
    build = None
    cmd = ('%s/cli/atest stable_version list --board=%s -w cautotest' %
           (AUTOTEST_DIR, board))
    result = subprocess.check_output(cmd, shell=True).strip()
    build = re.search(BUILD_REGEX, result)
    if build:
        return '%s-release/%s' % (board, build.group(0))

    # If fail to get stable version from cautotest, use that defined in config
    build = CONFIG.get_config_value('CROS', 'stable_cros_version')
    return '%s-release/%s' % (board, build)

def parse_arguments():
    """Parse arguments for test_push tool.

    @return: Parsed arguments.

    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--board', dest='board', default='gandof',
                        help='Default is gandof.')
    parser.add_argument('-sb', '--shard_board', dest='shard_board',
                        default='quawks',
                        help='Default is quawks.')
    parser.add_argument('-i', '--build', dest='build', default=None,
                        help='Default is the latest canary build of given '
                             'board. Must be a canary build, otherwise AU test '
                             'will fail. (ex: gandolf-release/R53-8397.0.0)')
    parser.add_argument('-si', '--shard_build', dest='shard_build', default=None,
                        help='Default is the latest canary build of given '
                             'board. Must be a canary build, otherwise AU test '
                             'will fail.')
    parser.add_argument('-p', '--pool', dest='pool', default='bvt')
    parser.add_argument('-u', '--num', dest='num', type=int, default=3,
                        help='Run on at most NUM machines.')
    parser.add_argument('-e', '--email', dest='email', default=None,
                        help='Email address for the notification to be sent to '
                             'after the script finished running.')
    parser.add_argument('-t', '--timeout_min', dest='timeout_min', type=int,
                        default=DEFAULT_TIMEOUT_MIN_FOR_SUITE_JOB,
                        help='Time in mins to wait before abort the jobs we '
                             'are waiting on. Only for the asynchronous suites '
                             'triggered by create_and_return flag.')
    parser.add_argument('-ud', '--num_duts', dest='num_duts',
                        default=DEFAULT_NUM_DUTS,
                        help="String of dict that indicates the required number"
                             " of DUTs for each board. E.g {'gandof':4}")

    arguments = parser.parse_args(sys.argv[1:])

    # Get latest canary build as default build.
    if not arguments.build:
        arguments.build = get_default_build(arguments.board)
    if not arguments.shard_build:
        arguments.shard_build = get_default_build(arguments.shard_board)

    arguments.num_duts = ast.literal_eval(arguments.num_duts)

    return arguments


def do_run_suite(suite_name, arguments, use_shard=False,
                 create_and_return=False):
    """Call run_suite to run a suite job, and return the suite job id.

    The script waits the suite job to finish before returning the suite job id.
    Also it will echo the run_suite output to stdout.

    @param suite_name: Name of a suite, e.g., dummy.
    @param arguments: Arguments for run_suite command.
    @param use_shard: If true, suite is scheduled for shard board.
    @param create_and_return: If True, run_suite just creates the suite, print
                              the job id, then finish immediately.

    @return: Suite job ID.

    """
    if not use_shard:
        board = arguments.board
        build = arguments.build
    else:
        board = arguments.shard_board
        build = arguments.shard_build

    # Remove cros-version label to force provision.
    hosts = AFE.get_hosts(label=constants.Labels.BOARD_PREFIX+board)
    for host in hosts:
        for label in [l for l in host.labels
                      if l.startswith(provision.CROS_VERSION_PREFIX)]:
            AFE.run('host_remove_labels', id=host.id, labels=[label])

        if use_shard and not create_and_return:
            # Let's verify the repair flow and powerwash the duts.  We can
            # assume they're all cros hosts (valid assumption?) so powerwash
            # will work.
            try:
                powerwash_dut(host.hostname)
            except Exception as e:
                raise TestPushException('Failed to powerwash dut %s. Make '
                                        'sure the dut is working first. '
                                        'Error: %s' % (host.hostname, e))
            AFE.reverify_hosts(hostnames=[host.hostname])

    current_dir = os.path.dirname(os.path.realpath(__file__))
    cmd = [os.path.join(current_dir, RUN_SUITE_COMMAND),
           '-s', suite_name,
           '-b', board,
           '-i', build,
           '-p', arguments.pool,
           '-u', str(arguments.num)]
    if create_and_return:
        cmd += ['-c']

    suite_job_id = None

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)

    while True:
        line = proc.stdout.readline()

        # Break when run_suite process completed.
        if not line and proc.poll() != None:
            break
        print line.rstrip()
        run_suite_output.append(line.rstrip())

        if not suite_job_id:
            m = re.match(SUITE_JOB_START_INFO_REGEX, line)
            if m and m.group(1):
                suite_job_id = int(m.group(1))

    if not suite_job_id:
        raise TestPushException('Failed to retrieve suite job ID.')

    # If create_and_return specified, wait for the suite to finish.
    if create_and_return:
        end = time.time() + arguments.timeout_min * 60
        while not AFE.get_jobs(id=suite_job_id, finished=True):
            if time.time() < end:
                time.sleep(10)
            else:
                AFE.run('abort_host_queue_entries', job=suite_job_id)
                raise TestPushException(
                        'Asynchronous suite triggered by create_and_return '
                        'flag has timed out after %d mins. Aborting it.' %
                        arguments.timeout_min)

    print 'Suite job %s is completed.' % suite_job_id
    return suite_job_id


def check_dut_image(build, suite_job_id):
    """Confirm all DUTs used for the suite are imaged to expected build.

    @param build: Expected build to be imaged.
    @param suite_job_id: job ID of the suite job.
    @raise TestPushException: If a DUT does not have expected build imaged.
    """
    print 'Checking image installed in DUTs...'
    job_ids = [job.id for job in
               models.Job.objects.filter(parent_job_id=suite_job_id)]
    hqes = [models.HostQueueEntry.objects.filter(job_id=job_id)[0]
            for job_id in job_ids]
    hostnames = set([hqe.host.hostname for hqe in hqes])
    for hostname in hostnames:
        found_build = site_utils.get_build_from_afe(hostname, AFE)
        if found_build != build:
            raise TestPushException('DUT is not imaged properly. Host %s has '
                                    'build %s, while build %s is expected.' %
                                    (hostname, found_build, build))


def test_suite(suite_name, expected_results, arguments, use_shard=False,
               create_and_return=False):
    """Call run_suite to start a suite job and verify results.

    @param suite_name: Name of a suite, e.g., dummy
    @param expected_results: A dictionary of test name to test result.
    @param arguments: Arguments for run_suite command.
    @param use_shard: If true, suite is scheduled for shard board.
    @param create_and_return: If True, run_suite just creates the suite, print
                              the job id, then finish immediately.
    """
    suite_job_id = do_run_suite(suite_name, arguments, use_shard,
                                create_and_return)

    # Confirm all DUTs used for the suite are imaged to expected build.
    # hqe.host_id for jobs running in shard is not synced back to master db,
    # therefore, skip verifying dut build for jobs running in shard.
    if suite_name != AU_SUITE and not use_shard:
        check_dut_image(arguments.build, suite_job_id)

    # Find all tests and their status
    print 'Comparing test results...'
    TKO = frontend_wrappers.RetryingTKO(timeout_min=0.1, delay_sec=10)
    test_views = site_utils.get_test_views_from_tko(suite_job_id, TKO)

    mismatch_errors = []
    extra_test_errors = []

    found_keys = set()
    for test_name,test_status in test_views.items():
        print "%s%s" % (test_name.ljust(30), test_status)
        # platform_InstallTestImage test may exist in old builds.
        if re.search('platform_InstallTestImage_SERVER_JOB$', test_name):
            continue
        test_found = False
        for key,val in expected_results.items():
            if re.search(key, test_name):
                test_found = True
                found_keys.add(key)
                if val != test_status:
                    error = ('%s Expected: [%s], Actual: [%s]' %
                             (test_name, val, test_status))
                    mismatch_errors.append(error)
        if not test_found:
            extra_test_errors.append(test_name)

    missing_test_errors = set(expected_results.keys()) - found_keys
    for exception in IGNORE_MISSING_TESTS:
        try:
            missing_test_errors.remove(exception)
        except KeyError:
            pass

    summary = []
    if mismatch_errors:
        summary.append(('Results of %d test(s) do not match expected '
                        'values:') % len(mismatch_errors))
        summary.extend(mismatch_errors)
        summary.append('\n')

    if extra_test_errors:
        summary.append('%d test(s) are not expected to be run:' %
                       len(extra_test_errors))
        summary.extend(extra_test_errors)
        summary.append('\n')

    if missing_test_errors:
        summary.append('%d test(s) are missing from the results:' %
                       len(missing_test_errors))
        summary.extend(missing_test_errors)
        summary.append('\n')

    # Test link to log can be loaded.
    job_name = '%s-%s' % (suite_job_id, getpass.getuser())
    log_link = URL_PATTERN % (URL_HOST, job_name)
    try:
        urllib2.urlopen(log_link).read()
    except urllib2.URLError:
        summary.append('Failed to load page for link to log: %s.' % log_link)

    if summary:
        raise TestPushException('\n'.join(summary))


def test_suite_wrapper(queue, suite_name, expected_results, arguments,
                       use_shard=False, create_and_return=False):
    """Wrapper to call test_suite. Handle exception and pipe it to parent
    process.

    @param queue: Queue to save exception to be accessed by parent process.
    @param suite_name: Name of a suite, e.g., dummy
    @param expected_results: A dictionary of test name to test result.
    @param arguments: Arguments for run_suite command.
    @param use_shard: If true, suite is scheduled for shard board.
    @param create_and_return: If True, run_suite just creates the suite, print
                              the job id, then finish immediately.
    """
    try:
        test_suite(suite_name, expected_results, arguments, use_shard,
                   create_and_return)
    except:
        # Store the whole exc_info leads to a PicklingError.
        except_type, except_value, tb = sys.exc_info()
        queue.put((except_type, except_value, traceback.extract_tb(tb)))


def check_queue(queue):
    """Check the queue for any exception being raised.

    @param queue: Queue used to store exception for parent process to access.
    @raise: Any exception found in the queue.
    """
    if queue.empty():
        return
    exc_info = queue.get()
    # Raise the exception with original backtrace.
    print 'Original stack trace of the exception:\n%s' % exc_info[2]
    raise exc_info[0](exc_info[1])


def main():
    """Entry point for test_push script."""
    arguments = parse_arguments()

    try:
        check_dut_inventory(arguments.num_duts)
        queue = multiprocessing.Queue()

        push_to_prod_suite = multiprocessing.Process(
                target=test_suite_wrapper,
                args=(queue, PUSH_TO_PROD_SUITE, EXPECTED_TEST_RESULTS,
                      arguments))
        push_to_prod_suite.start()

        # TODO(dshi): Remove following line after crbug.com/267644 is fixed.
        # Also, merge EXPECTED_TEST_RESULTS_AU to EXPECTED_TEST_RESULTS
        au_suite = multiprocessing.Process(
                target=test_suite_wrapper,
                args=(queue, AU_SUITE, EXPECTED_TEST_RESULTS_AU,
                      arguments))
        au_suite.start()

        shard_suite = multiprocessing.Process(
                target=test_suite_wrapper,
                args=(queue, DUMMY_SUITE, EXPECTED_TEST_RESULTS_DUMMY,
                      arguments, True))
        shard_suite.start()

        # suite test with --create_and_return flag
        asynchronous_suite = multiprocessing.Process(
                target=test_suite_wrapper,
                args=(queue, DUMMY_SUITE, EXPECTED_TEST_RESULTS_DUMMY,
                      arguments, True, True))
        asynchronous_suite.start()

        while (push_to_prod_suite.is_alive() or au_suite.is_alive() or
               shard_suite.is_alive() or asynchronous_suite.is_alive()):
            check_queue(queue)
            time.sleep(5)

        check_queue(queue)

        push_to_prod_suite.join()
        au_suite.join()
        shard_suite.join()
        asynchronous_suite.join()
    except Exception as e:
        print 'Test for pushing to prod failed:\n'
        print str(e)
        # Send out email about the test failure.
        if arguments.email:
            gmail_lib.send_email(
                    arguments.email,
                    'Test for pushing to prod failed. Do NOT push!',
                    ('Errors occurred during the test:\n\n%s\n\n' % str(e) +
                     '\n'.join(run_suite_output)))
        raise

    message = ('\nAll tests are completed successfully, prod branch is ready to'
               ' be pushed.')
    print message
    # Send out email about test completed successfully.
    if arguments.email:
        gmail_lib.send_email(
                arguments.email,
                'Test for pushing to prod completed successfully',
                message)


if __name__ == '__main__':
    sys.exit(main())
