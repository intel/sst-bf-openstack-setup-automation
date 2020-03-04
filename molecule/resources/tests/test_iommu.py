# Copyright (c) 2019 Intel Corporation. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" Test if IOMMU is enabled """
import os
import pytest

import testinfra.utils.ansible_runner

from common import ansible_vars, check_skip_dpdk_tests

TESTINFRA_HOSTS = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
).get_hosts('all')


# This test function uses the fixture "check_skip_dpdk_tests" to decide if the
# test should be executed. If the Ansible variable "skip_ovs_dpdk_config" is
# set to True, ovs-dpdk will not be configured on the target host, making
# execution of this test redundant. Hence, it will be skipped.
@pytest.mark.usefixtures("check_skip_dpdk_tests")
def test_iommu(host):
    """ Test if IOMMU enabled """

    iommu_path = "/sys/class/iommu/*/devices/*"
    cmd = None
    with host.sudo():
        cmd = host.run("find {path} -maxdepth 1 -quit 2> /dev/null"
                       .format(path=iommu_path))
    # If IOMMU is enabled, there will be one or more folders in
    # /sys/class/iommu which contain devices
    assert cmd and cmd.succeeded, "IOMMU is not configured correctly"
