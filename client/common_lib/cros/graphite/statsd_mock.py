#pylint: disable-msg=C0111

# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import stats_es_mock


class Connection:
    """Mock class for statsd.Connection"""
    def __init__(self, host, port):
        pass


    @classmethod
    def set_defaults(cls, host, port):
        pass


class Average(stats_es_mock.mock_class_base):
    """Mock class for statsd.Average."""


class Counter(stats_es_mock.mock_class_base):
    """Mock class for statsd.Counter."""


class Gauge(stats_es_mock.mock_class_base):
    """Mock class for statsd.Gauge."""


class Timer(stats_es_mock.mock_class_base):
    """Mock class for statsd.Timer."""


    def __enter__(self):
        pass


    def __exit__(self):
        pass


class Raw(stats_es_mock.mock_class_base):
    """Mock class for statsd.Raw."""
