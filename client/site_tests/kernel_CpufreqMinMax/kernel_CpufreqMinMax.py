#!/usr/bin/python
#
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.bin import test
from autotest_lib.client.common_lib import error

class kernel_CpufreqMinMax(test.test):
    """
    Test to ensure cpufreq user min/max limits can be set and reset.

    Test the kernel's ability to change the min and max cpufreq values
    in both directions.  I.e. we must be able to lower the max
    frequency and then raise it back up again, and raise the minimum
    frequency and lower it back again.  The test on the max is to make
    sure that thermal throttling will work correctly, and the test on
    the min is just for symmetry.
    """
    version = 1

    sys_cpufreq_path = '/sys/devices/system/cpu/cpu0/cpufreq/'

    def _test_freq_set(self, freqs, filename):
        """
        Iteratively write frequencies into a file and check the file.

        This is a helper function for testing the min and max
        given an ordered list, it sets each frequency in the list and
        then checks to make sure it really got set, and raises an
        error if it doesn't match.

        @param freqs: a list of frequencies to set
        @param filename: the filename in the cpufreq directory to use
        """
        for freq in freqs:
            logging.info('setting %s to %d' % (filename, freq))
            f = open(self.sys_cpufreq_path + filename, 'w')
            f.write(str(freq))
            f.close()

            f = open(self.sys_cpufreq_path + filename, 'r')
            cur_freq = int(f.readline())
            f.close()

            if (cur_freq != freq):
                logging.info('%s was set to %d instead of %d' %
                             (filename, cur_freq, freq))
                raise error.TestFail('unable to set %s to %d' %
                                     (filename, freq))


    def run_once(self):
        f = open(self.sys_cpufreq_path + 'scaling_available_frequencies', 'r')
        available_freqs = sorted(map(int, f.readline().split()))
        f.close()

        # exit if there are not at least two frequencies
        if (len(available_freqs) < 2):
            return

        # set max to 2nd to highest frequency, then the highest
        self._test_freq_set(available_freqs[-2:], 'scaling_max_freq')

        # set to min 2nd to lowest frequency, then the lowest
        self._test_freq_set(reversed(available_freqs[:2]),
                           'scaling_min_freq')
