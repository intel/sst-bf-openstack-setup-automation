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

""" Test if DPDK is initialised """
import os
import pytest

import testinfra.utils.ansible_runner

from common import ansible_vars, check_skip_dpdk_tests

TESTINFRA_HOSTS = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ["MOLECULE_INVENTORY_FILE"]
).get_hosts("all")


@pytest.fixture(scope="module")
def ovs_version_str(host):
    """ Retrieve OVS version and return it as a string """

    mask_cmd = None
    ovs_ver_cmd = "ovs-vsctl get Open_vSwitch . ovs_version"
    with host.sudo():
        if not host.exists("ovs-vsctl"):
            raise Exception("Unable to find ovs-vsctl in PATH")
        mask_cmd = host.run(ovs_ver_cmd)
    if not mask_cmd or mask_cmd.failed or not mask_cmd.stdout:
        raise Exception("Failed to get OVS version with command '{cmd}'"
                        .format(cmd=ovs_ver_cmd))
    return mask_cmd.stdout.strip('"\n')


@pytest.fixture(scope="module")
def ovs_version_check_ok(ovs_version_str):
    """ Check if the version string supplied by arg 'ovs_version_str' is
        greater than 2.10. Return true if it is the case otherwise false """

    ver_ok = False
    if ovs_version_str.count(".") != 2:
        raise Exception("Something went wrong getting OVS version. "
                        "Expected major.minor.patch versioning format")
    major, minor, _ = [int(i) for i in ovs_version_str.split(".")]
    if (major == 2 and minor >= 10) or (major >= 3):
        ver_ok = True
    return ver_ok


@pytest.fixture(scope="module")
def check_skip_dpdk_init(ovs_version_check_ok):
    """ Determine if we should skip a test """

    if not ovs_version_check_ok:
        pytest.skip("Skipping test due to OVS version < 2.10")


# This test function uses the fixture "check_skip_dpdk_tests" to decide if the
# test should be executed. If the Ansible variable "skip_ovs_dpdk_config" is
# set to True, ovs-dpdk will not be configured on the target host, making
# execution of this test redundant. Hence, it will be skipped.
@pytest.mark.usefixtures("check_skip_dpdk_tests")
@pytest.mark.usefixtures("check_skip_dpdk_init")
def test_dpdk_initialised(host):
    """ Test if DPDK is initialised with OVS ver. 2.10 or greater """

    res = ""
    with host.sudo():
        if not host.exists("ovs-vsctl"):
            raise Exception("Failed to find ovs-vsctl in Path."
                            "Is OVS installed?")
        res = host.check_output("ovs-vsctl get Open_vSwitch . "
                                "dpdk_initialized")
    assert res.lower() == "true", "DPDK is not initialised in OVS"
