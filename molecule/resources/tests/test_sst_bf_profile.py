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

""" Test if SST-BF profile has been applied correctly """
from os import environ

import pytest
import testinfra.utils.ansible_runner

from common import ansible_vars, get_cores, high_cores, normal_cores
from common import sst_bf_repo_path

TESTINFRA_HOSTS = testinfra.utils.ansible_runner.AnsibleRunner(
    environ["MOLECULE_INVENTORY_FILE"]
).get_hosts("all")


# NOTE:
# The high and normal core frequency values for the SST-BF profiles defined
# below (FREQUENCY_VAR_HIGH_DEDICATED and FREQUENCY_VAR_HIGH_SHARED) currently
# have only been tested on Xeon 6230N.
def get_min_max_freq(sst_bf_profile):
    """ CPU profile frequency map """

    profile_freq_map = {
        "FREQUENCY_VAR_HIGH_DEDICATED": {"high": {"min": 2700000,
                                                  "max": 3900000},
                                         "normal": {"min": 800000,
                                                    "max": 2100000}},
        "FREQUENCY_VAR_HIGH_SHARED": {"high": {"min": 2700000,
                                               "max": 3900000},
                                      "normal": {"min": 800000,
                                                 "max": 2100000}}}
    return profile_freq_map.get(sst_bf_profile, None)


def get_core_freq(host, cpu_no):
    """ Get min/max and base frequencies for a single CPU on the target and
        return a dict """

    root_path = "/sys/devices/system/cpu/cpu{}/cpufreq/".format(str(cpu_no))
    min_path = root_path + "scaling_min_freq"
    max_path = root_path + "scaling_max_freq"
    base_path = root_path + "base_frequency"
    min_freq, max_freq, base_freq = None, None, None

    with host.sudo():
        if not host.file(root_path).is_directory:
            raise ValueError("Core numbered '{}' not found".format(cpu_no))
        min_freq = host.check_output("cat {}".format(min_path)).rstrip()
        max_freq = host.check_output("cat {}".format(max_path)).rstrip()
        base_freq = host.check_output("cat {}".format(base_path)).rstrip()
    if not(min_freq and max_freq and base_freq) or \
       not (min_freq.isdigit() and max_freq.isdigit() and base_freq.isdigit()):
        raise Exception("Failed to get cpu freq for core {}"
                        .format(str(cpu_no)))
    return {"min": int(min_freq), "max": int(max_freq), "base": int(base_freq)}


@pytest.fixture(scope="module")
def no_cpus(normal_cores, high_cores):
    """ Return total number of high and normal priority CPUs """

    return len(normal_cores + high_cores)


@pytest.fixture(scope="module")
def core_freqs(host, no_cpus):
    """ Return dictionary with CPU IDs as the keys and a value of a dict which
        contains keys that denote min/max and base frequency """

    core_data = {}
    for cpu_no in range(0, no_cpus):
        core_data[cpu_no] = get_core_freq(host, cpu_no)
    return core_data


def test_sst_bf_applied(normal_cores, high_cores, ansible_vars,
                        core_freqs, sst_bf_repo_path):
    """ Test min and max freq for each core and ensure it is set to the freq
        expected for the associated SST-BF profile applied to the system """

    msg_low = "Mix core frequency does not equal base core frequency"
    msg_hi = "Max core frequency does not equal base core frequency"
    sst_bf_profile = ansible_vars["sst_bf_profile"]
    if sst_bf_profile in ("FREQUENCY_FIXED_HIGH_DEDICATED",
                          "FREQUENCY_FIXED_HIGH_SHARED"):
        for core in normal_cores + high_cores:
            assert core_freqs[core]["base"] == core_freqs[core]["min"], msg_low
            assert core_freqs[core]["base"] == core_freqs[core]["max"], msg_hi
    elif sst_bf_profile in ("FREQUENCY_VAR_HIGH_DEDICATED",
                            "FREQUENCY_VAR_HIGH_SHARED"):
        min_max_freq = get_min_max_freq(sst_bf_profile)
        for core in normal_cores:
            for lvl in ["min", "max"]:
                assert core_freqs[core][lvl] == min_max_freq["normal"][lvl], \
                    "{lvl} level normal core freq is not set correctly"\
                    .format(lvl=lvl)
        for core in high_cores:
            for lvl in ["min", "max"]:
                assert core_freqs[core][lvl] == min_max_freq["high"][lvl],\
                    "{lvl} level high core frequency is not set correctly"\
                    .format(lvl=lvl)
    else:
        raise Exception("Invalid sst_bf_profile")
