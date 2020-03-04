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

""" This file contains functions to support test files """
from os import stat
from tempfile import mkstemp
import pytest


@pytest.fixture(scope="module")
def os_secrets(host, ansible_vars):
    """ Open file defined by Ansible var 'secrets_path' and check if
        appropriate keys are available which will allow OS authentication
        Return a dict which contain the OpenStack credentials """

    required_os_cred_keys = ["OS_USERNAME", "OS_PASSWORD", "OS_AUTH_URL",
                             "OS_REGION_NAME", "OS_PROJECT_NAME",
                             "OS_USER_DOMAIN_ID", "OS_PROJECT_DOMAIN_ID",
                             "OS_PLACEMENT_API_VERSION"]
    secure_file_permission = "0640"
    secrets_path_key = "secrets_path"
    stat_f = None
    os_key_not_found = []

    # Check if 'converge' sequence has outputted 'secrets_path'
    if secrets_path_key not in ansible_vars:
        hostname = host.check_output("hostname -s")
        raise KeyError("Unable to find key 'secrets_path' in file "
                       "/tmp/sst_bf_role_vars_{host}.yaml"
                       .format(host=hostname))

    file_path = ansible_vars[secrets_path_key]

    # Get information about local OpenStack secrets file
    try:
        stat_f = stat(file_path)
    except FileNotFoundError as fnf:
        fnf.message = "Could not find OpenStack secrets file at path "\
                      + "'{path}'\n".format(path=file_path)
        raise

    # Get ACL and throw exception if it is not set correctly
    if oct(stat_f.st_mode)[-4:] != secure_file_permission:
        raise Exception("OpenStack secrets file at path '{path}' does not have"
                        " a secure ACL of '{perm}'."
                        .format(path=file_path, perm=secure_file_permission))

    # Load OpenStack secrets file
    i_var = "file={path} name=sec".format(path=file_path)
    os_sec = host.ansible("include_vars", i_var)["ansible_facts"]["sec"]

    if not os_sec:
        raise Exception("Failed to load OpenStack secrets. Please define a "
                        "yaml file containing the secrets defined in README")

    # Check for any missing OpenStack credential information
    for os_cred_key in required_os_cred_keys:
        if os_cred_key not in os_sec or not os_sec[os_cred_key]:
            os_key_not_found.append(os_cred_key)

    if os_key_not_found:
        keys_missing = ", ".join(os_key_not_found)
        raise Exception("Please ensure the following keys are defined and "
                        " contain a string value in a yaml file at path "
                        "'{path}' to ensure we can connect "
                        " to OpenStack: '{keys}'".format(path=file_path,
                                                         keys=keys_missing))
    return os_sec


@pytest.fixture(scope="module")
def sst_bf_repo_path(host, ansible_vars):
    """ Get supporting script and return file path as string """

    remote_location = "https://github.com/intel/CommsPowerManagement"
    commit = "05509e90fc082538609198c05179a52971bb5897"

    # Attempt to get repository from GitHub
    _, file_location = mkstemp()
    cmd = host.run("git clone {repo_url} {file_loc}"
                   .format(repo_url=remote_location, file_loc=file_location))
    if cmd.rc != 0:
        raise IOError("Failed to download git repo needed to test SST-BF")

    # Checkout specific commit
    cmd = host.run("git -C {file_loc} checkout {commit_id}"
                   .format(file_loc=file_location, commit_id=commit))
    if cmd.rc != 0:
        raise Exception("Faied to checkout commit")

    if not host.file(file_location + "/sst_bf.py").exists:
        raise FileNotFoundError("Could not find sst_bf.py in dir '{file_loc}'"
                                .format(file_loc=file_location))

    yield file_location

    # clean up repository
    host.run("rm -rf {file_loc}".format(file_loc=file_location))


@pytest.fixture(scope="module")
def high_cores(host, sst_bf_repo_path):
    """ Get list of high priority cores. Return list of CPU IDs """

    return get_cores(host, sst_bf_repo_path, " -l")


@pytest.fixture(scope="module")
def normal_cores(host, sst_bf_repo_path):
    """ Get list of normal priority cores. Return list of CPU IDs """

    return get_cores(host, sst_bf_repo_path, " -n")


@pytest.fixture(scope="module")
def check_skip_dpdk_tests(ansible_vars):
    """ Check if DPDK test should be skipped """

    skip_ovs_dpdk_config = ansible_vars["skip_ovs_dpdk_config"]
    if skip_ovs_dpdk_config:
        pytest.skip("Skipping test due to skip ovs-dpdk config set to true")


@pytest.fixture(scope="module")
def ansible_vars(host):
    """ Put variables from Ansible Role run which are in a file
        into a dictionary """

    hostname = host.check_output("hostname -s")
    return host.ansible("include_vars",
                        "file=/tmp/sst_bf_role_vars_{host}.yaml "
                        "name=test_run"
                        .format(host=hostname))["ansible_facts"]["test_run"]


def get_cores(host, sst_bf_repo_path, arg):
    """ Get targets high or normal priority cores in a list. Argument 'arg'
        is either '-n' (normal priority cores) or '-l' (high priority cores).
        Return list of CPU IDs """

    with host.sudo():
        out = host.check_output("python3 " + sst_bf_repo_path + "/sst_bf.py" +
                                arg)
    out_split = out.split("\n")
    if len(out_split) != 2:
        raise Exception("Stdout from sst_bf.py is not what is expected '{out}'"
                        .format(out=out))
    comma_delim = out_split[0]
    if ',' not in comma_delim:
        raise Exception("Expected comma delimited string from sst_bf.py but \
                        received '{out}'".format(out=out))
    cores = []
    for core in comma_delim.split(","):
        if core.isdigit():
            cores.append(int(core))
        else:
            raise ValueError("Expected integer. Something went wrong")
    if not cores:
        raise Exception("Failed to get cores from sst_bf.py output '{out}'"
                        .format(out=out))
    return cores
