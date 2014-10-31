#!/usr/bin/python
#
# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for server/cros/dynamic_suite/dynamic_suite.py."""

import mox
import os
import signal

from autotest_lib.client.common_lib import base_job, error
from autotest_lib.client.common_lib.cros import dev_server
from autotest_lib.server.cros.dynamic_suite import dynamic_suite


class DynamicSuiteTest(mox.MoxTestBase):
    """Unit tests for dynamic_suite module methods.

    @var _DARGS: default args to vet.
    """

    _DEVSERVER_HOST = 'http://devserver1'
    _BUILD = 'build'

    def setUp(self):

        super(DynamicSuiteTest, self).setUp()
        self._DARGS = {'name': 'name',
                       'build': self._BUILD,
                       'board': 'board',
                       'job': self.mox.CreateMock(base_job.base_job),
                       'num': 1,
                       'pool': 'pool',
                       'check_hosts': False,
                       'add_experimental': False,
                       'suite_dependencies': ['test_dep'],
                       'devserver_url': self._DEVSERVER_HOST}



    def testVetRequiredReimageAndRunArgs(self):
        """Should verify only that required args are present and correct."""
        spec = dynamic_suite.SuiteSpec(**self._DARGS)
        self.assertEquals(spec.build, self._DARGS['build'])
        self.assertEquals(spec.board, 'board:' + self._DARGS['board'])
        self.assertEquals(spec.name, self._DARGS['name'])
        self.assertEquals(spec.job, self._DARGS['job'])


    def testVetReimageAndRunBuildArgFail(self):
        """Should fail verification because |build| arg is bad."""
        self._DARGS['build'] = None
        self.assertRaises(error.SuiteArgumentException,
                          dynamic_suite.SuiteSpec,
                          **self._DARGS)


    def testVetReimageAndRunBoardArgFail(self):
        """Should fail verification because |board| arg is bad."""
        self._DARGS['board'] = None
        self.assertRaises(error.SuiteArgumentException,
                          dynamic_suite.SuiteSpec,
                          **self._DARGS)


    def testVetReimageAndRunNameArgFail(self):
        """Should fail verification because |name| arg is bad."""
        self._DARGS['name'] = None
        self.assertRaises(error.SuiteArgumentException,
                          dynamic_suite.SuiteSpec,
                          **self._DARGS)


    def testVetReimageAndRunJobArgFail(self):
        """Should fail verification because |job| arg is bad."""
        self._DARGS['job'] = None
        self.assertRaises(error.SuiteArgumentException,
                          dynamic_suite.SuiteSpec,
                          **self._DARGS)


    def testOverrideOptionalReimageAndRunArgs(self):
        """Should verify that optional args can be overridden."""
        spec = dynamic_suite.SuiteSpec(**self._DARGS)
        self.assertEquals(spec.pool, 'pool:' + self._DARGS['pool'])
        self.assertEquals(spec.num, self._DARGS['num'])
        self.assertEquals(spec.check_hosts, self._DARGS['check_hosts'])
        self.assertEquals(spec.add_experimental,
                          self._DARGS['add_experimental'])
        self.assertEquals(spec.suite_dependencies,
                          self._DARGS['suite_dependencies'])


    def testDefaultOptionalReimageAndRunArgs(self):
        """Should verify that optional args get defaults."""
        del(self._DARGS['pool'])
        del(self._DARGS['check_hosts'])
        del(self._DARGS['add_experimental'])
        del(self._DARGS['num'])
        del(self._DARGS['suite_dependencies'])

        spec = dynamic_suite.SuiteSpec(**self._DARGS)
        self.assertEquals(spec.pool, None)
        self.assertEquals(spec.num, None)
        self.assertEquals(spec.check_hosts, True)
        self.assertEquals(spec.add_experimental, True)
        self.assertEquals(spec.suite_dependencies, [])


    def testReimageAndSIGTERM(self):
        """Should reimage_and_run that causes a SIGTERM and fails cleanly."""
        def suicide(*_):
            """Send SIGTERM to current process to exit.

            @param _: Ignored.
            """
            os.kill(os.getpid(), signal.SIGTERM)

        # Mox doesn't play well with SIGTERM, but it does play well with
        # with exceptions, so here we're using an exception to simulate
        # execution being interrupted by a signal.
        class UnhandledSIGTERM(Exception):
            """Exception to be raised when SIGTERM is received."""
            pass

        def handler(signal_number, frame):
            """Handler for receiving a signal.

            @param signal_number: signal number.
            @param frame: stack frame object.
            """
            raise UnhandledSIGTERM()

        signal.signal(signal.SIGTERM, handler)
        spec = self.mox.CreateMock(dynamic_suite.SuiteSpec)
        spec.build = ''
        spec.devserver = self.mox.CreateMock(dev_server.ImageServer)
        spec.devserver.stage_artifacts(
                spec.build, ['control_files', 'test_suites']).WithSideEffects(
                suicide)

        self.mox.ReplayAll()

        self.assertRaises(UnhandledSIGTERM,
                          dynamic_suite._perform_reimage_and_run,
                          spec, None, None, None)
