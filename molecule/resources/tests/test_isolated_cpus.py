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

""" Test if correct CPUs are isolated """
import os
from re import findall

import pytest
import testinfra.utils.ansible_runner

from common import ansible_vars, check_skip_dpdk_tests

TESTINFRA_HOSTS = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ["MOLECULE_INVENTORY_FILE"]
).get_hosts("all")


@pytest.fixture(scope="module")
def isolated_cores_sysfs(host):
    """ Get CPU IDs from target which are isolated and return CPU IDs as
        integers in a list """

    ex_msg = "Failed to get isolated CPUs from sysfs with output {out}"
    isolated_cores = []
    isol_sysfs = get_file_output(host, "/sys/devices/system/cpu/isolated")
    if not isol_sysfs:
        return isolated_cores
    for block in isol_sysfs.split(","):
        if "-" in block:
            low, high = block.split("-")
            if not low.isdigit() or not high.isdigit():
                raise Exception(ex_msg.format(out=isol_sysfs))
            for i in range(int(low), int(high) + 1):
                isolated_cores.append(i)
        else:
            if not block.isdigit():
                raise Exception(ex_msg.format(out=isol_sysfs))
            isolated_cores.append(int(block))
    return isolated_cores


def get_file_output(host, path):
    """ Get contents of a file from target at location defined by argument
        'path' and return as string """

    file = None

    with host.sudo():
        file = host.file(path)
    if not file or not file.exists:
        raise Exception("Unable to find file at path '{path}'"
                        .format(path=path))
    return file.content_string.strip()


@pytest.fixture(scope="module")
def pmd_core_mask(host):
    """ Get PMD CPU hex mask from target and return as string with leading
        '0x' stripped """

    hex_value = None

    if not host.exists("ovs-vsctl"):
        raise Exception("Failed to find ovs-vsctl in system PATH")
    with host.sudo():
        stdout = host.check_output("ovs-vsctl get Open_vSwitch . "
                                   "'other_config'")
        if "pmd-cpu-mask" not in stdout:
            raise Exception("Failed to find 'pmd-cpu-mask' in Open_vSwitch "
                            "column other_config")
        hex_value = host.check_output("ovs-vsctl get Open_vSwitch . "
                                      "'other_config':pmd-cpu-mask").strip('"')
    if hex_value.startswith("0x"):
        hex_value = hex_value[2:]
    return hex_value


@pytest.fixture(scope="module")
def pmd_core_numbers_from_mask(pmd_core_mask):
    """ Convert CPU hex mask to a list of CPU core IDs in a list """

    pmd_cores = []
    binary_mask = bin(int(pmd_core_mask, 16))[2:]
    for i, val in enumerate(binary_mask[::-1]):
        if val == "1":
            pmd_cores.append(i)
    return pmd_cores


@pytest.fixture(scope="module")
def pmd_core_numbers_from_appctl(host):
    """ Get PMD CPU IDs from target and return a list of CPU IDs """

    stdout = None

    with host.sudo():
        if not host.exists("ovs-appctl"):
            raise Exception("Failed to find ovs-vsctl in system PATH")
        stdout = host.check_output("ovs-appctl dpif-netdev/pmd-rxq-show")
    matches = findall(r"core_id (\d+)", stdout)
    pmd_core_ids = []
    for match in matches:
        pmd_core_ids.append(int(match))
    return pmd_core_ids


# The test functions below use the fixture "check_skip_dpdk_tests" to decide if
# the tests should be executed. If the Ansible variable "skip_ovs_dpdk_config"
# is set to True, ovs-dpdk will not be configured on the target host, making
# execution of these tests redundant. Hence, they will be skipped.
@pytest.mark.usefixtures("check_skip_dpdk_tests")
def test_isolated_cpus(isolated_cores_sysfs, pmd_core_numbers_from_mask):
    """ Test if PMD cores are isolated """

    assert isolated_cores_sysfs == pmd_core_numbers_from_mask, "Kernel "
    "isolated CPU's does not match PMD core mask"


@pytest.mark.usefixtures("check_skip_dpdk_tests")
def test_pmd_cores_match_mask(pmd_core_numbers_from_mask,
                              pmd_core_numbers_from_appctl):
    """ Test if PMD CPU mask applied to OVS by Ansible Role has been applied
        to DPDK's PMD """

    assert pmd_core_numbers_from_mask == pmd_core_numbers_from_appctl, "PMD "
    "core mask from OVS does not match actual PMD pinned cores"
