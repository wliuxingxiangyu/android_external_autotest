# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
DES_01 Descriptors Validation for NCM/MBIM Functions

Reference:
    [1] Universal Serial Bus Communication Class MBIM Compliance Testing: 23
        http://www.usb.org/developers/docs/devclass_docs/MBIM-Compliance-1.0.pdf

"""

import common
from autotest_lib.client.cros.cellular.mbim_compliance import mbim_errors
from autotest_lib.client.cros.cellular.mbim_compliance import test_context
from autotest_lib.client.cros.cellular.mbim_compliance import usb_descriptors
from autotest_lib.client.cros.cellular.mbim_compliance.sequences \
        import get_descriptors_sequence
from autotest_lib.client.cros.cellular.mbim_compliance.tests import des_test


class DES_01_Test(des_test.DesTest):
    """ Implement the DES_01 Descriptors Validation for NCM/MBIM Functions """

    def run_internal(self):
        """ Run the DES_01 test. """
        # Precondition.
        descriptors = get_descriptors_sequence.GetDescriptorsSequence(
                self.test_context).run()
        device = self.test_context.device
        if not device:
            mbim_errors.log_and_raise(mbim_errors.MBIMComplianceFrameworkError,
                                      'Device not found')
        interfaces = usb_descriptors.filter_descriptors(
                usb_descriptors.InterfaceDescriptor, descriptors)

        # Test step 1
        # Get ncm communication interface and mbim communication interface.
        ncm_communication_interfaces = self.filter_interface_descriptors(
                interfaces, self.NCM_MBIM_COMMUNICATION_INTERFACE_NCM)

        if len(ncm_communication_interfaces) != 1:
            mbim_errors.log_and_raise(mbim_errors.MBIMComplianceAssertionError,
                                      'mbim1.0:3.2.1#2')

        ncm_communication_interface = ncm_communication_interfaces[0]

        mbim_communication_interfaces = self.filter_interface_descriptors(
                interfaces, self.NCM_MBIM_COMMUNICATION_INTERFACE_MBIM)

        if len(mbim_communication_interfaces) != 1:
            mbim_errors.log_and_raise(mbim_errors.MBIMComplianceAssertionError,
                                      'mbim1.0:3.2.1#3')

        mbim_communication_interface = mbim_communication_interfaces[0]

        if (ncm_communication_interface.bInterfaceNumber !=
            mbim_communication_interface.bInterfaceNumber):
            mbim_errors.log_and_raise(mbim_errors.MBIMComplianceAssertionError,
                                      'mbim1.0:3.2.1#1')

        # Test step 2
        if (ncm_communication_interface.index >
            mbim_communication_interface.index):
            mbim_errors.log_and_raise(
                    mbim_errors.MBIMComplianceGenericAssertionError,
                    'Alternate setting 1 of the interface must appear after'
                    'alternate setting 0 of the interface.')

        # Test step 3
        # Get header functional descriptor, union functinoal descriptor,
        # MBIM functinoal descriptor and MBIM extended functional
        # descriptor from |ncm_communication_interface|[0].
        ncm_communication_interface_bundle = (
                usb_descriptors.get_descriptor_bundle(
                        descriptors, ncm_communication_interface))

        header_descriptors = usb_descriptors.filter_descriptors(
                usb_descriptors.HeaderFunctionalDescriptor,
                ncm_communication_interface_bundle)
        union_descriptors = usb_descriptors.filter_descriptors(
                usb_descriptors.UnionFunctionalDescriptor,
                ncm_communication_interface_bundle)
        mbim_descriptors = usb_descriptors.filter_descriptors(
                usb_descriptors.MBIMFunctionalDescriptor,
                ncm_communication_interface_bundle)
        mbim_extended_descriptors = usb_descriptors.filter_descriptors(
                usb_descriptors.MBIMExtendedFunctionalDescriptor,
                ncm_communication_interface_bundle)
        if not(header_descriptors and union_descriptors and mbim_descriptors):
            mbim_errors.log_and_raise(mbim_errors.MBIMComplianceAssertionError,
                                      'mbim1.0:6.3#2')

        # Test step 4
        # Check header funcional descriptor.
        if usb_descriptors.has_distinct_descriptors(header_descriptors):
            mbim_errors.log_and_raise(
                    mbim_errors.MBIMComplianceGenericAssertionError,
                    'Expected 1 unique header functional descriptor.')
        header_descriptor = header_descriptors[0]
        if not(header_descriptor.bDescriptorType == 0x24 and
               header_descriptor.bDescriptorSubtype == 0x00 and
               header_descriptor.bLength == 5 and
               header_descriptor.bcdCDC >= 0x0120):
            mbim_errors.log_and_raise(
                    mbim_errors.MBIMComplianceGenericAssertionError,
                    'Header functional descriptor: wrong value(s)')

        # Test step 5
        # Check union functional descriptor.
        if usb_descriptors.has_distinct_descriptors(union_descriptors):
            mbim_errors.log_and_raise(
                    mbim_errors.MBIMComplianceGenericAssertionError,
                    'Expected 1 unique union functional descriptor.')

        union_descriptor = union_descriptors[0]
        if union_descriptor.index < header_descriptor.index:
            mbim_errors.log_and_raise(mbim_errors.MBIMComplianceAssertionError,
                                      'mbim1.0:6.3#3')
        # Get no data data interface.
        no_data_data_interfaces = self.filter_interface_descriptors(
                interfaces, self.NCM_MBIM_DATA_INTERFACE_NO_DATA)

        if len(no_data_data_interfaces) != 1:
            mbim_errors.log_and_raise(
                    mbim_errors.MBIMComplianceAssertionError,
                    'mbim1.0:3.2.2.4#2')

        no_data_data_interface = no_data_data_interfaces[0]
        no_data_data_interface_bundle = usb_descriptors.get_descriptor_bundle(
                descriptors, no_data_data_interface)
        endpoint_descriptors = (
                usb_descriptors.filter_descriptors(
                        usb_descriptors.EndpointDescriptor,
                        no_data_data_interface_bundle))

        if endpoint_descriptors:
            mbim_errors.log_and_raise(mbim_errors.MBIMComplianceAssertionError,
                                      'mbim1.0:3.2.2.4#4')

        # Get NCM data interface.
        ncm_data_interfaces = (
                self.filter_interface_descriptors(
                        interfaces,
                        self.NCM_MBIM_DATA_INTERFACE_NCM))

        if len(ncm_data_interfaces) != 1:
            mbim_errors.log_and_raise(mbim_errors.MBIMComplianceAssertionError,
                                      'mbim1.0:3.2.2.4#2')
        ncm_data_interface = ncm_data_interfaces[0]
        if ncm_data_interface.bNumEndpoints != 2:
            mbim_errors.log_and_raise(mbim_errors.MBIMComplianceAssertionError,
                                      'mbim1.0:3.2.2.4#4')
        ncm_data_interface_bundle = (
                usb_descriptors.get_descriptor_bundle(descriptors,
                                                      ncm_data_interface))
        endpoint_descriptors = (
                usb_descriptors.filter_descriptors(
                        usb_descriptors.EndpointDescriptor,
                        ncm_data_interface_bundle))
        # Check endpoint descriptors in |ncm_data_interface_bundle|
        # There should be one bulk OUT and one bulk IN.
        if not self.has_bulk_in_and_bulk_out(endpoint_descriptors):
            mbim_errors.log_and_raise(mbim_errors.MBIMComplianceAssertionError,
                                      'mbim1.0:3.2.2.4#4')

        # Get MBIM data interface.
        mbim_data_interfaces = self.filter_interface_descriptors(
                interfaces, self.NCM_MBIM_DATA_INTERFACE_MBIM)

        if len(mbim_data_interfaces) != 1:
           mbim_errors.log_and_raise(mbim_errors.MBIMComplianceAssertionError,
                                     'mbim1.0:3.2.2.4#3')
        mbim_data_interface = mbim_data_interfaces[0]
        if mbim_data_interface.bNumEndpoints != 2:
            mbim_errors.log_and_raise(mbim_errors.MBIMComplianceAssertionError,
                                      'mbim1.0:3.2.2.4#4')

        mbim_data_interface_bundle = (
                usb_descriptors.get_descriptor_bundle(descriptors,
                                                      mbim_data_interface))
        endpoint_descriptors = (
                usb_descriptors.filter_descriptors(
                        usb_descriptors.EndpointDescriptor,
                        mbim_data_interface_bundle))
        # Check endpoint descriptors in |mbim_data_interface_bundle|
        # alternate setting 2. There should be one bulk OUT and one bulk IN.
        if not self.has_bulk_in_and_bulk_out(endpoint_descriptors):
            mbim_errors.log_and_raise(mbim_errors.MBIMComplianceAssertionError,
                                      'mbim1.0:3.2.2.4#4')

        if not(no_data_data_interface.bInterfaceNumber ==
               ncm_data_interface.bInterfaceNumber ==
               mbim_data_interface.bInterfaceNumber):
            mbim_errors.log_and_raise(mbim_errors.MBIMComplianceAssertionError,
                                      'mbim1.0:3.2.2.4#1')

        if not(union_descriptor.bLength == 5 and
               union_descriptor.bControlInterface == (
                       ncm_communication_interface.bInterfaceNumber) and
               union_descriptors.bSubordinateInterface0 == (
                       no_data_data_interface.bInterfaceNumber)):
            mbim_errors.log_and_raise(mbim_errors.MBIMComplianceAssertionError,
                                      'mbim1.0:6.3#4')
        # TODO(mcchou): Continue the remaining test steps.

        # Update |test_context| with NCM/MBIM function settings.
        if self.test_context.device_type == test_context.DEVICE_TYPE_MBIM:
            mbim_errors.log_and_raise(mbim_errors.MBIMComplianceFrameworkError,
                                      'A device can only be either a MBIM'
                                      'device ro a NCM/MBIM device.')
        self.test_context.device_type = test_context.DEVICE_TYPE_NCM_MBIM
        self.test_context.ncm_communication_interface = (
                ncm_communication_interface)
        self.test_context.mbim_communication_interface = (
                mbim_communication_interface)
        self.test_context.no_data_data_interface = no_data_data_interface
        self.test_context.ncm_data_interface = ncm_data_interface
        self.test_context.mbim_data_interface = mbim_data_interface
    # End of run_internal()
