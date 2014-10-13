# Copyright 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import dbus
import dbus.mainloop.glib
import logging
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import utils
from autotest_lib.client.cros import dbus_util

Service = collections.namedtuple('Service', ['service_id', 'service_info'])
Peer = collections.namedtuple('Peer', ['uuid', 'name', 'note',
                                       'last_seen', 'services'])

# DBus constants for use with peerd.
SERVICE_NAME = 'org.chromium.peerd'
DBUS_INTERFACE_MANAGER = 'org.chromium.peerd.Manager'
DBUS_INTERFACE_PEER = 'org.chromium.peerd.Peer'
DBUS_INTERFACE_SERVICE = 'org.chromium.peerd.Service'
DBUS_INTERFACE_OBJECT_MANAGER = 'org.freedesktop.DBus.ObjectManager'
DBUS_PATH_MANAGER = '/org/chromium/peerd/Manager'
DBUS_PATH_OBJECT_MANAGER = '/org/chromium/peerd'
PEER_PATH_PREFIX = '/org/chromium/peerd/peers/'
PEER_PROPERTY_ID = 'UUID'
PEER_PROPERTY_NAME = 'FriendlyName'
PEER_PROPERTY_NOTE = 'Note'
PEER_PROPERTY_LAST_SEEN = 'LastSeen'
SERVICE_PROPERTY_ID = 'ServiceId'
SERVICE_PROPERTY_INFO = 'ServiceInfo'

# Possible technologies for use with PeerdHelper.start_monitoring().
TECHNOLOGY_ALL = dbus.UInt32(1 << 0)
TECHNOLOGY_MDNS = dbus.UInt32(1 << 1)


def make_helper(bus=None, start_instance=False, timeout_seconds=10,
                verbosity_level=0):
    """Wait for peerd to come up, then return a PeerdHelper for it.

    @param bus: DBus bus to use, or specify None to create one internally.
    @param start_instance: bool True if we should start a peerd instance.
    @param timeout_seconds: number of seconds to wait for peerd to come up.
    @param verbosity_level: int level of log verbosity from peerd (e.g. 0
                            will log INFO level, 3 is verbosity level 3).
    @return PeerdHelper instance if peerd comes up, None otherwise.

    """
    pid_to_kill = None
    if start_instance:
        result = utils.run('peerd --v=%d & echo $!' % verbosity_level)
        pid_to_kill = int(result.stdout)
    else:
        # TODO(wiley) Add a verbosity switch to peerd, call it here.
        pass
    if bus is None:
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
    end_time = time.time() + timeout_seconds
    connection = None
    while time.time() < end_time:
        if not bus.name_has_owner(SERVICE_NAME):
            time.sleep(0.2)
        return PeerdHelper(bus, pid_to_kill)
    raise error.TestFail('peerd did not start in a timely manner.')


class PeerdHelper(object):
    """Container for convenience methods related to peerd."""

    def __init__(self, bus, peerd_pid_to_kill):
        """Construct a PeerdHelper.

        @param bus: DBus bus to use, or specify None and this object will
                    create a mainloop and bus.
        @param peerd_pid_to_kill: pid to kill on close() or None.

        """
        self._bus = bus
        self._pid = peerd_pid_to_kill
        self._manager = dbus.Interface(
                self._bus.get_object(SERVICE_NAME, DBUS_PATH_MANAGER),
                DBUS_INTERFACE_MANAGER)


    def _get_peers(self):
        object_manager = dbus.Interface(
                self._bus.get_object(SERVICE_NAME, DBUS_PATH_OBJECT_MANAGER),
                DBUS_INTERFACE_OBJECT_MANAGER)
        # |dbus_objects| is a map<object path,
        #                         map<interface name,
        #                             map<property name, value>>>
        dbus_objects = object_manager.GetManagedObjects()
        objects = dbus_util.dbus2primitive(dbus_objects)
        peer_objects = [(path, interfaces)
                        for path, interfaces in objects.iteritems()
                        if (path.startswith(PEER_PATH_PREFIX) and
                            DBUS_INTERFACE_PEER in interfaces)]
        peers = []
        for peer_path, interfaces in peer_objects:
            service_property_sets = [
                    interfaces[DBUS_INTERFACE_SERVICE]
                    for path, interfaces in objects.iteritems()
                    if (path.startswith(peer_path + '/services/') and
                        DBUS_INTERFACE_SERVICE in interfaces)]
            services = []
            for service_properties in service_property_sets:
                services.append(Service(
                        service_id=service_properties[SERVICE_PROPERTY_ID],
                        service_info=service_properties[SERVICE_PROPERTY_INFO]))
            peer_properties = interfaces[DBUS_INTERFACE_PEER]
            peer = Peer(uuid=peer_properties[PEER_PROPERTY_ID],
                        name=peer_properties[PEER_PROPERTY_NAME],
                        note=peer_properties[PEER_PROPERTY_NOTE],
                        last_seen=peer_properties[PEER_PROPERTY_LAST_SEEN],
                        services=services)
            peers.append(peer)
        return peers


    def close(self):
        """Clean up peerd state related to this helper.

        Removes related services and monitoring requests.
        Optionally kills the peerd instance if we created this instance.

        """
        if self._pid is not None:
            utils.run('kill %d' % self._pid, ignore_status=True)
            self._pid = None


    def start_monitoring(self, technologies):
        """Monitor the specified technologies.

        Note that peerd will watch bus connections and stop monitoring a
        technology if this bus connection goes away.A

        @param technologies: iterable container of TECHNOLOGY_* defined above.
        @return string monitoring_token for use with stop_monitoring().

        """
        return self._manager.StartMonitoring(technologies)


    def has_peer(self, uuid, name=None, note=None):
        """
        Return a Peer instance if peerd has found a matching peer.

        Optional parameters are also matched if not None.

        @param uuid: string unique identifier of peer.
        @param name: string optional friendly name of peer.
        @param note: string optional note of peer.
        @return Peer tuple if a matching peer exists, None otherwise.

        """
        peers = self._get_peers()
        logging.debug('Found peers: %r.', peers)
        for peer in peers:
            if peer.uuid != uuid:
                continue
            if name is not None and name != peer.name:
                logging.debug('Mismatched peer names; found %s, expected %s.',
                              peer.name, name)
                return None
            if note is not None and note != peer.note:
                logging.debug('Mismatched peer notes; found %s, expected %s.',
                              peer.note, note)
                return None
            return peer
        logging.debug('No peer had a matching ID.')
        return None


    def expose_service(self, service_id, service_info):
        """Expose a service via peerd.

        Note that peerd should watch DBus connections and remove this service
        if our bus connection ever goes down.

        @param service_id: string id of service.  See peerd documentation
                           for limitations on this string.
        @param service_info: dict of string, string entries.  See peerd
                             documentation for relevant restrictions.
        @return string service token for use with remove_service().

        """
        return self._manager.ExposeService(service_id, service_info)


    def remove_service(self, service_token):
        """Remove a service previously added via expose_service().

        @param service_token: string token returned by expose_service().

        """
        self._manager.RemoveExposedService(service_token)
