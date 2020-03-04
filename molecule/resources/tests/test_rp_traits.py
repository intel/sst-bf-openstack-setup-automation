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

""" Test if OpenStack Resource Provider is configured correctly """
from os import environ
from shlex import split
import re
import subprocess

import pytest
import testinfra.utils.ansible_runner

from common import ansible_vars, os_secrets

TESTINFRA_HOSTS = testinfra.utils.ansible_runner.AnsibleRunner(
    environ["MOLECULE_INVENTORY_FILE"]
).get_hosts("all")


@pytest.fixture(scope="module")
def os_cli(os_secrets):
    """ Return full OpenStack CLI command """

    cmd = (
        "openstack "
        "--os-auth-type password "
        "--os-placement-api-version {api_ver} "
        "--os-username {username} "
        "--os-password {password} "
        "--os-project-domain-id {proj_id} "
        "--os-user-domain-id {user_id} "
        "--os-project-name {proj_name} "
        "--os-region-name {reg_name} "
        "--os-auth-url {auth_url}").format(
            api_ver=os_secrets["OS_PLACEMENT_API_VERSION"],
            username=os_secrets["OS_USERNAME"],
            password=os_secrets["OS_PASSWORD"],
            proj_id=os_secrets["OS_PROJECT_DOMAIN_ID"],
            user_id=os_secrets["OS_USER_DOMAIN_ID"],
            proj_name=os_secrets["OS_PROJECT_NAME"],
            reg_name=os_secrets["OS_REGION_NAME"],
            auth_url=os_secrets["OS_AUTH_URL"])

    return cmd


def subprocess_run(cmd, subp_input=None):
    """ Execute process on target as defined by argument 'cmd' """

    cmd = split(cmd)
    return subprocess.run(cmd,
                          input=subp_input,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          universal_newlines=True,
                          check=True)


@pytest.fixture(scope="module")
def resource_provider_list(os_cli):
    """ Get OpenStack Resource Provider list """

    rp_list_cmd = "resource provider list -f value"
    cmd = "{os_cli} {rp_list_cmd}".format(os_cli=os_cli,
                                          rp_list_cmd=rp_list_cmd)
    run_cmd = subprocess_run(cmd)

    if run_cmd.returncode != 0:
        raise Exception("Failed to list resource providers")

    return run_cmd.stdout


@pytest.fixture(scope="module")
def resource_provider(host, resource_provider_list):
    """ Get OpenStack Resource Provider list only for target """

    hostname = host.check_output("hostname -s")
    cmd = "{grep} {hostname}".format(grep="grep", hostname=hostname)
    run_cmd = subprocess_run(cmd, subp_input=resource_provider_list)

    if run_cmd.returncode != 0:
        raise Exception("Resource provider matching hostname '{hostname}' "
                        "not found".format(hostname=hostname.strip()))
    return run_cmd.stdout


@pytest.fixture(scope="module")
def resource_provider_uuid(resource_provider):
    """ Return OpenStack Resource Provider UUID """

    cmd = "{awk} {column}".format(awk="awk", column="'{ print $1 }'")
    run_cmd = subprocess_run(cmd, subp_input=resource_provider)

    # Regex to match uuid version 4 denoted by first character of the third
    # grouping delimited by hyphens
    uuid_regex = ("[0-9a-f]{8}-[0-9a-f]{4}-[4][0-9a-f]{3}-[89ab]"
                  "[0-9a-f]{3}-[0-9a-f]{12}")
    if not re.match(uuid_regex, run_cmd.stdout):
        raise Exception("Failed to obtain resource provider UUID")

    return run_cmd.stdout


@pytest.fixture(scope="module")
def resource_provider_traits(os_cli, resource_provider_uuid):
    """ Return a list of OpenStack Traits associated with Resource Provider
        UUID provided by argument 'resource_provider_uuid' """

    rp_trait_list_cmd = "resource provider trait list -c name -f value"
    cmd = ("{os_cli} "
           "{rp_trait_list_cmd} "
           "{uuid}".format(os_cli=os_cli, rp_trait_list_cmd=rp_trait_list_cmd,
                           uuid=resource_provider_uuid))
    run_cmd = subprocess_run(cmd)

    if run_cmd.returncode != 0:
        raise Exception(run_cmd.stderr)

    if len(run_cmd.stdout) == 0:
        raise Exception("No traits found for resource provider: "
                        "{uuid}".format(uuid=resource_provider_uuid.strip()))

    return run_cmd.stdout.splitlines()


def test_sst_bf_capable_trait(resource_provider_traits):
    """ Test to check if SST-BF capable trait is set to resource provider """

    assert "CUSTOM_CPU_X86_INTEL_SST_BF" in resource_provider_traits, \
           "CUSTOM_CPU_X86_INTEL_SST_BF not set to resource provider"


def test_sst_bf_profile_trait(ansible_vars, resource_provider_traits):
    """ Test to check if correct trait based on profile applied to resource
        provider """

    sst_bf_profile = ansible_vars["sst_bf_profile"]
    sst_bf_profile_trait = "{prefix}{profile}".format(prefix="CUSTOM_CPU_",
                                                      profile=sst_bf_profile)
    false_msg = "{profile} not set to resource provider".format(
        profile=sst_bf_profile_trait)

    assert sst_bf_profile_trait in resource_provider_traits, false_msg
