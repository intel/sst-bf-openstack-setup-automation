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

""" Test if OpenStack Nova is correctly configured """
from os import environ

import pytest
import testinfra.utils.ansible_runner

from common import ansible_vars, get_cores, high_cores, normal_cores
from common import sst_bf_repo_path

TESTINFRA_HOSTS = testinfra.utils.ansible_runner.AnsibleRunner(
    environ["MOLECULE_INVENTORY_FILE"]
).get_hosts("all")


@pytest.fixture(scope="module")
def nova_conf(host, ansible_vars):
    """ Get OpenStack Nova conf file and return a list with each item in
        the list representing a line in the Nova conf file """

    nova_path = ansible_vars.get("nova_conf_path", None)
    if not nova_path:
        raise KeyError("Could not get nova_conf_path Ansible var")
    nova_conf = None
    with host.sudo():
        nova_conf = host.file(nova_path)
        if not (nova_conf.exists and nova_conf.is_file):
            raise FileNotFoundError("Failed to find Nova conf file at "
                                    "location '{path}'".format(path=nova_path))
    return nova_conf.content_string.split("\n")


def check_key_value(partial_match, full_match, line, was_found):
    """ Search argument 'line' and ensure it is a full match with argument
        'full_match', else report error. Return tuple """

    error = False
    if line.startswith(partial_match):
        if line == full_match and not was_found:
            was_found = True
        else:
            error = True
    return (was_found, error)


def core_numbers_from_mask(core_mask):
    """ Generate a list of CPU IDs from CPU mask argument 'core_mask' and
        return a list of CPU IDs """

    cores = []
    if not isinstance(core_mask, int):
        core_mask = int(core_mask, 16)
    binary_mask = bin(core_mask)[2:]
    for i, val in enumerate(binary_mask[::-1]):
        if val == "1":
            cores.append(i)
    return cores


@pytest.fixture(scope="module")
def pmd_core_numbers_from_mask(ansible_vars):
    """ Return CPU core IDs from DPDK PMD CPU mask from Ansible variable """

    if ansible_vars["skip_ovs_dpdk_config"]:
        return

    pmd_core_mask = ansible_vars["pmd_mask"]
    return core_numbers_from_mask(pmd_core_mask)


@pytest.fixture(scope="module")
def lcore_core_numbers_from_mask(ansible_vars):
    """ Return CPU core IDs from DPDK lcore CPU mask from Ansible variables """

    if ansible_vars["skip_ovs_dpdk_config"]:
        return

    lcore_core_mask = ansible_vars["lcore_mask"]
    return core_numbers_from_mask(lcore_core_mask)


def check_nova_conf(nova_conf, shared_set, dedicated_set, allocation_ratio):
    """ Test OpenStack Nova configuration file has been correctly configured
    """

    error = False
    dedicated_found, shared_found, allocation_found = False, False, False
    in_default_blk, in_compute_blk = False, False
    for line in nova_conf:
        ret = False
        line_lo = line.lower().strip()
        if line_lo == "":
            in_default_blk, in_compute_blk = False, False
            continue
        elif line_lo == "[compute]":
            in_compute_blk = True
            continue
        elif line_lo == "[default]":
            in_default_blk = True
            continue

        if in_default_blk:
            allocation_found, ret = check_key_value("cpu_allocation_ratio",
                                                    allocation_ratio, line_lo,
                                                    allocation_found)
        elif in_compute_blk:
            shared_found, ret = check_key_value("cpu_shared_set", shared_set,
                                                line_lo, shared_found)
            dedicated_found, ret = check_key_value("cpu_dedicated_set",
                                                   dedicated_set, line_lo,
                                                   dedicated_found)
        elif (line_lo.startswith("cpu_dedicated_set")
              or line_lo.startswith("cpu_shared_set")
              or line_lo.startswith("cpu_allocation_ratio")):
            ret = True
        error = error or ret

    assert allocation_found, "Failed to find correct cpu_allocation_ratio"
    assert dedicated_found, "Failed to find correct cpu_dedicated_set"
    assert shared_found, "Failed to find correct cpu_shared_set"
    assert not error, "Nova conf file seems to be corrupted"


def filter_cores(cores_to_remove, cores):
    """ Remove CPU IDs in list argument 'cores_to_remove' from CPU IDs list in
        argument 'cores' """

    for core_id in cores_to_remove:
        cores.remove(core_id)


def remove_dpdk_cores(normal_cores, high_cores, lcore_core_numbers_from_mask,
                      pmd_core_numbers_from_mask, ansible_vars):
    """ Filter CPU IDs utilised for DPDK from either high or normal priority
        CPU IDs lists """

    priority = ansible_vars["ovs_core_high_priority"]
    if priority:
        filter_cores(pmd_core_numbers_from_mask, high_cores)
    else:
        filter_cores(pmd_core_numbers_from_mask, normal_cores)
    filter_cores(lcore_core_numbers_from_mask, normal_cores)


def test_nova_conf(normal_cores, high_cores, ansible_vars, nova_conf,
                   pmd_core_numbers_from_mask, lcore_core_numbers_from_mask):
    """ Ensure cpu_allocation_ratio, cpu_dedicated_set & cpu_shared_set
        are set correctly and under the correct heading"""

    skip_dpdk = ansible_vars["skip_ovs_dpdk_config"]
    if not skip_dpdk:
        remove_dpdk_cores(normal_cores, high_cores,
                          lcore_core_numbers_from_mask,
                          pmd_core_numbers_from_mask, ansible_vars)

    high_cores_comma = ",".join([str(core) for core in high_cores])
    normal_cores_comma = ",".join([str(core) for core in normal_cores])
    allocation_ratio = "cpu_allocation_ratio = " + \
        str(ansible_vars["cpu_allocation_ratio"])
    sst_bf_profile = ansible_vars["sst_bf_profile"]

    if sst_bf_profile in ("FREQUENCY_FIXED_HIGH_DEDICATED",
                          "FREQUENCY_VAR_HIGH_DEDICATED"):
        check_nova_conf(nova_conf, "cpu_shared_set = " + normal_cores_comma,
                        "cpu_dedicated_set = " + high_cores_comma,
                        allocation_ratio)
    elif sst_bf_profile in ("FREQUENCY_FIXED_HIGH_SHARED",
                            "FREQUENCY_VAR_HIGH_SHARED"):
        check_nova_conf(nova_conf, "cpu_shared_set = " + high_cores_comma,
                        "cpu_dedicated_set = " + normal_cores_comma,
                        allocation_ratio)
    else:
        raise ValueError("sst_bf_profile does not have a valid value")
