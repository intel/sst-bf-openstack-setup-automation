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

""" Test hugepage allocation """
import os

import pytest
import testinfra.utils.ansible_runner

from common import ansible_vars, check_skip_dpdk_tests

TESTINFRA_HOSTS = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ["MOLECULE_INVENTORY_FILE"]
).get_hosts("all")


@pytest.fixture(scope="module")
def hugepage_allocation(host):
    """ Get number of 2M and 1G hugepages allocated from target and return as
        tuple """

    online_nodes_sysfs = "/sys/devices/system/node/online"
    hugepage_2m_sysfs = "/sys/devices/system/node/node{node_num}/hugepages/" \
                        "hugepages-2048kB/nr_hugepages"
    hugepage_1g_sysfs = "/sys/devices/system/node/node{node_num}/hugepages/" \
                        "hugepages-1048576kB/nr_hugepages"
    online_list = None
    with host.sudo():
        online_list = host.file(online_nodes_sysfs).content_string.strip()
    if not online_list:
        raise Exception("Failed to get online nodes from '{online_nodes}'"
                        .format(online_nodes=online_nodes_sysfs))
    # online_list represents a range of online NUMA nodes. It is a list of
    # comma delimited ranges. E.g 0-1,4-5 or more commonly just 0-1 in a two
    # socket system.
    nr_1g_hugepages = 0
    nr_2m_hugepages = 0
    for block_range in online_list.split(","):
        low, high = block_range.split("-")
        if not low.isdigit() or not high.isdigit():
            raise Exception("Failed to parse online nodes from '{online}'"
                            .format(online=online_list))
        for node_num in range(int(low), int(high) + 1):
            path_1g = hugepage_1g_sysfs.format(node_num=node_num)
            path_2m = hugepage_2m_sysfs.format(node_num=node_num)
            nr_1g_hugepages += get_sysfs_int(host, path_1g)
            nr_2m_hugepages += get_sysfs_int(host, path_2m)
    return (nr_2m_hugepages, nr_1g_hugepages)


def get_sysfs_int(host, path):
    """ Get integer from target at location retrieved from argument 'path' """

    value = None
    with host.sudo():
        host_dir = host.file(path)
        if not host_dir.is_file:
            raise Exception("Failed to detect file at path '{sysfs}'"
                            .format(sysfs=path))
        value = host.file(path).content_string.strip()
    if not value or not value.isdigit():
        raise Exception("Failed to get integer from sysfs path '{path}'"
                        .format(path=path))
    return int(value)


# This test function uses the fixture "check_skip_dpdk_tests" to decide if the
# test should be executed. If the Ansible variable "skip_ovs_dpdk_config" is
# set to True, ovs-dpdk will not be configured on the target host, making
# execution of this test redundant. Hence, it will be skipped.
@pytest.mark.usefixtures("check_skip_dpdk_tests")
def test_hugepage(ansible_vars, hugepage_allocation):
    """ Test to ensure the correct number of 1G/2M hugepages have been
        allocated """

    assert int(ansible_vars['ovs_dpdk_nr_2m_pages']) ==\
        hugepage_allocation[0], "2M hugepages defined in Ansible var "\
        "is different than amount seen on remote host"
    assert int(ansible_vars['ovs_dpdk_nr_1g_pages']) ==\
        hugepage_allocation[1], "1G hugepages defined in Ansible var "\
        "is different than amount seen on remote host"
