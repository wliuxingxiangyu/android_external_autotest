# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A module providing the summary for multiple test results.

This firmware_summary module is used to collect the test results of
multiple rounds from the logs generated by different firmware versions.
The test results of the various validators of every gesture are displayed.
In addition, the test results of every validator across all gestures are
also summarized.

Usage:
$ python firmware_summary log_directory


A typical summary output looks like

Test Summary (by gesture)            :  fw_2.41   fw_2.42     count
---------------------------------------------------------------------
one_finger_tracking
  CountTrackingIDValidator           :     1.00      0.90        12
  LinearityBothEndsValidator         :     0.97      0.89        12
  LinearityMiddleValidator           :     1.00      1.00        12
  NoGapValidator                     :     0.74      0.24        12
  NoReversedMotionBothEndsValidator  :     0.68      0.34        12
  NoReversedMotionMiddleValidator    :     1.00      1.00        12
  ReportRateValidator                :     1.00      1.00        12
one_finger_to_edge
  CountTrackingIDValidator           :     1.00      1.00         4
  LinearityBothEndsValidator         :     0.88      0.89         4
  LinearityMiddleValidator           :     1.00      1.00         4
  NoGapValidator                     :     0.50      0.00         4
  NoReversedMotionMiddleValidator    :     1.00      1.00         4
  RangeValidator                     :     1.00      1.00         4

  ...


Test Summary (by validator)          :   fw_2.4  fw_2.4.a     count
---------------------------------------------------------------------
  CountPacketsValidator              :     1.00      0.82         6
  CountTrackingIDValidator           :     0.92      0.88        84

  ...

"""


import glob
import json
import numpy as n
import os
import sys

from common_util import Debug
from firmware_constants import VLOG
from test_conf import validator_score_weight, log_root_dir
from validators import get_short_name


def _setup_debug(debug_flag):
    """Set up the global debug_print function."""
    if 'debug_print' not in globals():
        global debug_print
        debug = Debug(debug_flag)
        debug_print = debug.print_msg


class FirmwareSummary:
    """Summary for touchpad firmware tests."""

    def __init__(self, log_dir=log_root_dir, debug_flag=False):
        if os.path.isdir(log_dir):
            self.log_dir = log_dir
        else:
            error_msg = 'Error: The test result directory does not exist: %s'
            print error_msg % log_dir
            sys.exit(-1)

        # Set up the global debug_print function.
        _setup_debug(debug_flag)

        self.logs = self._get_result_logs()
        if not self.logs:
            warn_msg = 'Warning: no log files in the test result directory: %s'
            print warn_msg % log_dir
            sys.exit(-1)

        self._parse_result_summary()
        self._combine_rounds()
        self._combine_gestures()
        self._combine_validators()

    def _load_result_log(self, log_filename):
        """Load the json log file into the log dictionary."""
        with open(log_filename) as log_fd:
            log_data = json.load(log_fd)
        return log_data

    def _get_firmware_version(self, filename):
        """Get the firmware version from the given filename."""
        return filename.split('-')[2]

    def _get_result_logs(self):
        """Load the json log files in the log dictionary."""
        patterns = ['*.log', '*/*.log']
        log_filenames = []
        for pattern in patterns:
            log_filenames += glob.glob(os.path.join(self.log_dir, pattern))

        # TODO(josephsih): it is desirable to add a command line option
        # so that the tester could choose to make the summary against different
        # versions or against different file names.
        logs_dict = {}
        for log_filename in log_filenames:
            version = self._get_firmware_version(log_filename)
            if version not in logs_dict:
                logs_dict[version] = []
            logs_dict[version].append(self._load_result_log(log_filename))

        return logs_dict

    def _parse_result_summary(self):
        """Generate a summary of all the loaded logs."""
        self.gestures = []
        self.fws = []
        self.validators = []
        self.g_scores = {}

        for fw in self.logs:
            debug_print('firmware: %s' % fw)
            # Build the firmware list
            if fw not in self.fws:
                self.fws.append(fw)

            # Iterate through every round
            for round_log in self.logs[fw]:
                debug_print('  A new log file:')
                # Iterate through every gesture_variation of the round
                for gv in round_log[VLOG.GV_LIST]:
                    debug_print('    gv: %s' % gv)
                    # Build the gesture list
                    gesture = eval(gv)[0]
                    if gesture not in self.gestures:
                        self.gestures.append(gesture)

                    # Build the g_scores
                    if gesture not in self.g_scores:
                        self.g_scores[gesture] = {}
                    if fw not in self.g_scores[gesture]:
                        self.g_scores[gesture][fw] = {}

                    # Iterate through each validator score pair
                    for validator_score_pair in round_log[VLOG.DICT][gv]:
                        validator = validator_score_pair.keys()[0]
                        if validator not in self.g_scores[gesture][fw]:
                            # Build the validator
                            self.g_scores[gesture][fw][validator] = []

                        # Build the score of the validator
                        score = validator_score_pair[validator]
                        self.g_scores[gesture][fw][validator].append(score)

                        debug_print('      %s: %6.4f' % (validator, score))

                        if validator not in self.validators:
                            self.validators.append(validator)

        self.validators.sort()

    def _calc_sample_standard_deviation(self, sample):
        """Calculate the sample standard deviation from a given sample.

        To compute a sample standard deviation, the following formula is used:
            sqrt(sum((x_i - x_average)^2) / N-1)

        Note that N-1 is used in the denominator for sample standard deviation,
        where N-1 is the degree of freedom. We need to set ddof=1 below;
        otherwise, N would be used in the denominator as ddof's default value
        is 0.

        Reference:
            http://en.wikipedia.org/wiki/Standard_deviation
        """
        return n.std(n.array(sample), ddof=1)

    def _combine_rounds(self):
        """Combine the test results of multiple rounds of the same
        firmware version.
        """
        self.validator_all_scores = {}
        self.validator_average = {}
        self.validator_ssd = {}
        self.validator_count = {}
        for gesture in self.g_scores:
            for fw in self.fws:
                if fw not in self.validator_all_scores:
                    self.validator_all_scores[fw] = {}
                    self.validator_average[fw] = {}
                    self.validator_ssd[fw] = {}
                    self.validator_count[fw] = {}
                for validator in self.g_scores[gesture][fw]:
                    if validator not in self.validator_all_scores[fw]:
                        self.validator_all_scores[fw][validator] = []
                        self.validator_average[fw][validator] = {}
                        self.validator_ssd[fw][validator] = {}
                        self.validator_count[fw][validator] = {}

                    scores = self.g_scores[gesture][fw][validator]
                    self.validator_all_scores[fw][validator] += scores
                    # Compute the sum, count, average, and
                    # sample standard deviation (ssd)
                    average = n.average(n.array(scores))
                    self.validator_average[fw][validator][gesture] = average
                    ssd = self._calc_sample_standard_deviation(scores)
                    self.validator_ssd[fw][validator][gesture] = ssd
                    self.validator_count[fw][validator][gesture] = len(scores)

    def _combine_gestures(self):
        """Combine the test results of the gestures of the same firmware version
        for every validator.
        """
        self.validator_summary_score = {}
        self.validator_summary_ssd = {}
        self.validator_summary_count= {}
        for validator in self.validators:
            self.validator_summary_score[validator] = {}
            self.validator_summary_ssd[validator] = {}
            self.validator_summary_count[validator] = {}
            for fw in self.fws:
                all_scores = self.validator_all_scores[fw][validator]
                ssd = self._calc_sample_standard_deviation(all_scores)
                count = sum(self.validator_count[fw][validator].values())
                # TODO(josephsih): a weighted average is desirable
                average = n.average(n.array(all_scores))
                self.validator_summary_score[validator][fw] = average
                self.validator_summary_ssd[validator][fw] = ssd
                self.validator_summary_count[validator][fw] = count

    def _combine_validators(self):
        """Combine the scores of all validators to get the final weighted score.

        validator_score_weight looks like:
            {'CountTrackingIDValidator': 3,
             'DrumrollValidator': 1,
             'LinearityValidator': 2,
             'NoGapValidator': 2,
             ...
            }

        self.validators looks like:
            ['CountTrackingIDValidator',
             'DrumrollValidator',
             'LinearityBothEndsValidator',
             'LinearityMiddleValidator',
             'NoGapValidator',
             ...
            ]

        Note that both names of the validators
             'LinearityBothEndsValidator' and
             'LinearityMiddleValidator'
        are created at run time based on LinearityValidator and use
        the same weight of
             'LinearityValidator': 2
        """
        name_weight_tuple = validator_score_weight.items()
        name_weight_list = list(name_weight_tuple)
        name_weight_list.sort()

        # Reconstruct validator_score_weight with the validator short name.
        short_name_weight_dict = dict([(get_short_name(validator_name), weight)
                for validator_name, weight in name_weight_list])

        validator_name_weight_list = []
        for validator in self.validators:
            for name, weight in short_name_weight_dict.items():
                if validator.startswith(name):
                    break
            else:
                print 'Error: cannot find the weight of %s' % validator
                sys.exit(-1)
            validator_name_weight_list.append((validator, weight))

        validators, weights = zip(*validator_name_weight_list)

        self.weighted_average = {}
        for fw in self.fws:
            scores = [self.validator_summary_score[validator][fw]
                      for validator in self.validators]
            self.weighted_average[fw] = n.average(scores, weights=weights)

    def _print_summary_title(self, summary_title_str):
        """Print the summary of the test results by gesture."""
        # Create a flexible column title format according to the number of
        # firmware versions which could be 1, 2, or more.
        #
        # A typical summary title looks like
        # Test Summary ()          :    fw_11.26             fw_11.23
        #                               mean  ssd  count     mean ssd count
        # ----------------------------------------------------------------------
        #
        # The 1st line above is called title_fw.
        # The 2nd line above is called title_statistics.
        #
        # As an example for 2 firmwares, title_fw_format looks like:
        #     '{0:<37}:  {1:>12}  {2:>21}'
        title_fw_format_list = ['{0:<37}:',]
        for i in range(len(self.fws)):
            format_space = 12 if i == 0 else (12 + 9)
            title_fw_format_list.append('{%d:>%d}' % (i + 1, format_space))
        title_fw_format = ' '.join(title_fw_format_list)

        # As an example for 2 firmwares, title_statistics_format looks like:
        #     '{0:>47} {1:>6} {2:>5} {3:>8} {4:>6} {5:>5}'
        title_statistics_format_list = []
        for i in range(len(self.fws)):
            format_space = (12 + 35) if i == 0 else 8
            title_statistics_format_list.append('{%d:>%d}' % (3 * i,
                                                              format_space))
            title_statistics_format_list.append('{%d:>%d}' % (3 * i + 1 , 6))
            title_statistics_format_list.append('{%d:>%d}' % (3 * i + 2 , 5))
        title_statistics_format = ' '.join(title_statistics_format_list)

        # Create title_fw_list
        # As an example for two firmware versions, it looks like
        #   ['Test Summary (by gesture)', 'fw_2.4', 'fw_2.5']
        title_fw_list = [summary_title_str,] + self.fws

        # Create title_statistics_list
        # As an example for two firmware versions, it looks like
        #   ['mean', 'ssd', 'count', 'mean', 'ssd', 'count', ]
        title_statistics_list = ['mean', 'ssd', 'count'] * len(self.fws)

        # Print the title.
        title_fw = title_fw_format.format(*title_fw_list)
        title_statistics = title_statistics_format.format(
                *title_statistics_list)
        print '\n\n', title_fw
        print title_statistics
        print '-' * len(title_statistics)

    def _print_statistics(self, statistics):
        """Print the statistics including average scores, ssd, and counts."""
        # Create a flexible format to print scores, ssd, and counts according to
        # the number of firmware versions which could be 1, 2, or more.
        # As an example with 2 firmware versions, the format looks like
        #   '  {0:<35}:  {1:>8.2f} {2:>6.2f} {3:>5} {4:>8.2f} {5:>6.2f} {6:>5}'
        statistics_format_list = ['  {0:<35}:',]
        score_ssd_count_format = '{%d:>8.2f} {%d:>6.2f} {%d:>5}'
        for i in range(len(self.fws)):
            statistics_format_list.append(
                    score_ssd_count_format % (i * 3 + 1, i * 3 + 2, i * 3 + 3))
        statistics_format = ' '.join(statistics_format_list)
        print statistics_format.format(*tuple(statistics))

    def _print_result_summary_by_gesture(self):
        """Print the summary of the test results by gesture."""
        fw = self.fws[0]
        self._print_summary_title('Test Summary (by gesture)')
        for gesture in self.gestures:
            print gesture
            validators = self.validator_all_scores[fw].keys()
            validators.sort()
            for validator in validators:
                statistics = [validator,]
                for fw in self.fws:
                    average = self.validator_average[fw][validator].get(gesture)
                    ssd = self.validator_ssd[fw][validator].get(gesture)
                    count = self.validator_count[fw][validator].get(gesture)
                    # Append this validator only if it is used in this gesture.
                    if average is not None:
                        statistics += [average, ssd, count]
                if average is not None:
                    self._print_statistics(statistics)

    def _print_result_summary_by_validator(self):
        """Print the summary of the test results by validator."""
        fw = self.fws[0]
        self._print_summary_title('Test Summary (by validator)')
        for validator in self.validators:
            statistics = [validator,]
            for fw in self.fws:
                average = self.validator_summary_score[validator][fw]
                ssd = self.validator_summary_ssd[validator][fw]
                count = self.validator_summary_count[validator][fw]
                statistics += [average, ssd, count]
            self._print_statistics(statistics)

    def _print_result_summary_final_weighted_average(self):
        """Print the final weighted average of all validators."""
        title_str = 'Test Summary (final weighted average)'
        print '\n\n' + title_str
        print '-' * len(title_str)
        for fw in self.fws:
            print '%s: %4.3f' % (fw, self.weighted_average[fw])

    def print_result_summary(self):
        """Print the summary of the test results."""
        self._print_result_summary_by_gesture()
        self._print_result_summary_by_validator()
        self._print_result_summary_final_weighted_average()


def _usage_and_exit():
    """Print the usage message and exit."""
    print 'Usage: python %s log_directory [-d]' % sys.argv[0]
    print '       -d: enable debug flag'
    sys.exit(-1)


if __name__ == '__main__':
    # Parse the command options.
    debug_flag = False
    argc = len(sys.argv)
    if argc < 2 or argc > 3:
        _usage_and_exit()
    elif argc == 3:
        if sys.argv[2] == '-d':
            debug_flag = True
        else:
            _usage_and_exit()
    log_dir = sys.argv[1]

    # Calculate and print the summary.
    summary = FirmwareSummary(log_dir=log_dir, debug_flag=debug_flag)
    summary.print_result_summary()
