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

""" Test if DPDK's PMD is configured correctly """
import os

import pytest
import testinfra.utils.ansible_runner

from common import ansible_vars, check_skip_dpdk_tests

TESTINFRA_HOSTS = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ["MOLECULE_INVENTORY_FILE"]
).get_hosts("all")


@pytest.fixture(scope="module")
def pinned_cores_from_vars(ansible_vars):
    """ Get requested number of pinned CPU cores for PMD from Ansible Role run
        and return integer """

    numa_nodes = ansible_vars["numa_nodes"]
    total_num_cores = 0

    for node in sorted(numa_nodes.keys()):
        num_cores = numa_nodes[node]["no_physical_cores_pinned"]
        total_num_cores += num_cores

    return total_num_cores


@pytest.fixture(scope="module")
def pmd_mask_host(host):
    """ Get DPDK's PMD CPU hex mask and return as string with the leading '0x'
        stripped """

    pmd_mask_cmd = "ovs-vsctl get Open_vSwitch . other_config:pmd-cpu-mask"
    with host.sudo():
        if not host.exists("ovs-vsctl"):
            raise Exception("Unable to find ovs-vsctl in PATH")
        mask_cmd = host.run(pmd_mask_cmd)
    if mask_cmd.failed or not mask_cmd.stdout or "0x" not in mask_cmd.stdout:
        raise Exception("Failed to get PMD mask from command '{cmd}'"
                        .format(cmd=pmd_mask_cmd))
    return mask_cmd.stdout.strip('\n"')[2:]


# The test functions below use the fixture "check_skip_dpdk_tests" to decide if
# the tests should be executed. If the Ansible variable "skip_ovs_dpdk_config"
# is set to True, ovs-dpdk will not be configured on the target host, making
# execution of these tests redundant. Hence, they will be skipped.
@pytest.mark.usefixtures("check_skip_dpdk_tests")
def test_pmd_mask(pmd_mask_host, ansible_vars):
    """ Test to ensure PMD mask generated by Ansible process equals
        PMD mask set in OVS """

    pmd_mask_ansible = ansible_vars["pmd_mask"]
    if not pmd_mask_ansible.startswith("0x"):
        raise Exception("Invalid PMD hex '{mask}' generated from Ansible"
                        .format(mask=pmd_mask_ansible))
    assert pmd_mask_host == pmd_mask_ansible[2:]


@pytest.mark.usefixtures("check_skip_dpdk_tests")
def test_pmd_num_threads(host, pinned_cores_from_vars):
    """ Test to check if the number of PMD threads matches the defined number
        of physical cores pinned (2 threads per physical core) """

    num_threads = 0
    threads_per_core = 2
    res = None
    with host.sudo():
        if not host.exists("ovs-appctl"):
            raise Exception("Failed to find ovs-appctl in Path."
                            "Is OVS installed?")

        res = host.run("ovs-appctl dpif-netdev/pmd-stats-show")

    if not res or res.failed:
        raise Exception("No PMD threads found")

    for line in res.stdout.splitlines():
        if "pmd thread" in line:
            num_threads += 1

    assert int(pinned_cores_from_vars) * threads_per_core == int(num_threads)
