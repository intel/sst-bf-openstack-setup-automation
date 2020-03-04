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

""" Test socket memory allocation for DPDK """
import os

import pytest
import testinfra.utils.ansible_runner

from common import ansible_vars, check_skip_dpdk_tests

TESTINFRA_HOSTS = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ["MOLECULE_INVENTORY_FILE"]
).get_hosts("all")


@pytest.fixture(scope="module")
def socket_mem_from_vars(ansible_vars):
    """ Return list of DPDK socket memory values defined in Ansible variables
    """

    numa_nodes = ansible_vars["numa_nodes"]
    socket_mem = []
    for node in sorted(numa_nodes.keys()):
        socket_mem.append(numa_nodes[node]["dpdk_socket_mem"])
    return socket_mem


@pytest.fixture(scope="module")
def socket_mem_from_ovs(host):
    """ Get DPDK socket memory from target and return values as list """

    all_socket_mem = None
    with host.sudo():
        if not host.exists("ovs-vsctl"):
            raise Exception("Failed to find ovs-vsctl in Path."
                            "Is OVS installed?")
        all_socket_mem = host.check_output("ovs-vsctl get Open_vSwitch . "
                                           "other_config:dpdk-socket-mem")
    if not all_socket_mem:
        raise Exception("Failed to get other_config output from OVS")
    dpdk_socket_mems = [mem.strip('"') for mem in all_socket_mem.split(",")]
    for socket_mem in dpdk_socket_mems:
        if not socket_mem.isdigit():
            raise ValueError("Failed to get dpdk socket memory from value "
                             "'{mem}' after parsing '{all_mem}'"
                             .format(mem=socket_mem, all_mem=all_socket_mem))
    return dpdk_socket_mems


# This test function uses the fixture "check_skip_dpdk_tests" to decide if the
# test should be executed. If the Ansible variable "skip_ovs_dpdk_config" is
# set to True, ovs-dpdk will not be configured on the target host, making
# execution of this test redundant. Hence, it will be skipped.
@pytest.mark.usefixtures("check_skip_dpdk_tests")
def test_dpdk_socket_mem(socket_mem_from_vars, socket_mem_from_ovs):
    """ Test to ensure we have set the correct socket memory """

    for i, _ in enumerate(socket_mem_from_vars):
        assert int(socket_mem_from_vars[i]) == int(socket_mem_from_ovs[i]),\
            "Socket memory defined in Ansible does not match info in OVS"
