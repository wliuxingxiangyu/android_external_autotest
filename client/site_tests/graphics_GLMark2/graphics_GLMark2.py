# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Run the test with validation_mode=True to invoke glmark2 to do quick
# validation that runs in a second. When glmark2 is run in normal mode, it
# outputs a final performance score, and the test checks the performance score
# against minimum requirement if min_score is set.

import logging
import os
import re

from autotest_lib.client.bin import test, utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.cros import service_stopper

GLMARK2_SCORE_RE = 'glmark2 Score: (\d+)'

class graphics_GLMark2(test.test):
    version = 1
    preserve_srcdir = True
    _services = None

    def setup(self):
        self.job.setup_dep(['glmark2'])

    def initialize(self):
        self._services = service_stopper.ServiceStopper(['ui'])

    def cleanup(self):
        if self._services:
           self._services.restore_services()

    def run_once(self, size='800x600', validation_mode=False, min_score=None):
        dep = 'glmark2'
        dep_dir = os.path.join(self.autodir, 'deps', dep)
        self.job.install_pkg(dep, 'dep', dep_dir)
        glmark2 = os.path.join(dep_dir, 'bin/glmark2')

        if not os.path.isfile(glmark2):
            glmark2 = os.path.join(dep_dir, 'bin/glmark2-es2')
        if not os.path.isfile(glmark2):
            error.TestFail('Could not find test binary. Test setup error.')

        options = []
        options.append('--size %s' % size)
        if validation_mode:
           options.append('--validate')
        else:
           options.append('--annotate')
        cmd = '%s %s' % (glmark2, ' '.join(options))

        # If UI is running, we must stop it and restore later.
        self._services.stop_services()

        # Just sending SIGTERM to X is not enough; we must wait for it to
        # really die before we start a new X server (ie start ui).
        # The term_process function of /sbin/killers makes sure that all X
        # process are really dead before returning; this is what stop ui uses.
        kill_cmd = '. /sbin/killers; term_process "^X$"'
        cmd = 'X :1 vt1 & sleep 1; chvt 1 && DISPLAY=:1 %s; %s' % (cmd, kill_cmd)

        if os.environ.get('CROS_FACTORY'):
            from autotest_lib.client.cros import factory_setup_modules
            from cros.factory.test import ui
            ui.start_reposition_thread('^glmark')
        result = utils.run(cmd)
        for line in result.stderr.splitlines():
            if line.startswith('Error:'):
                raise error.TestFail(line)

        if not validation_mode:
            score = None
            for line in result.stdout.splitlines():
                # glmark2 output the final performance score as:
                #   glmark2 Score: 530
                match = re.findall(GLMARK2_SCORE_RE, line)
                if match:
                    score = int(match[0])
            if score is None:
                raise error.TestFail('Unable to read benchmark score')
            # Output numbers for plotting by harness.
            logging.info('GLMark2 score: %d', score)
            if os.environ.get('CROS_FACTORY'):
                from autotest_lib.client.cros import factory_setup_modules
                from cros.factory.event_log import EventLog
                EventLog('graphics_GLMark2').Log('glmark2_score', score=score)
            keyvals = {}
            keyvals['glmark2_score'] = score
            self.write_perf_keyval(keyvals)
            self.output_perf_value(description='Score', value=score,
                                   units='score', higher_is_better=True)

            if min_score is not None and score < min_score:
                raise error.TestFail('Benchmark score %d < %d (minimum score '
                                     'requirement)' % (score, min_score))
