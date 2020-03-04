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

""" Test if OpenStack flavors for SST-BF are configured correctly """
from os import environ

import openstack
import pytest
import testinfra.utils.ansible_runner

from common import ansible_vars, os_secrets

TESTINFRA_HOSTS = testinfra.utils.ansible_runner.AnsibleRunner(
    environ["MOLECULE_INVENTORY_FILE"]
).get_hosts("all")


PROFILE_FLAVOR_MAP = {"FREQUENCY_FIXED_HIGH_DEDICATED":
                      ["SST_BF.micro.freq-fixed.high-tier-dedicated",
                       "SST_BF.micro.freq-fixed.normal-tier-shared",
                       "SST_BF.tiny.freq-fixed.high-tier-dedicated",
                       "SST_BF.tiny.freq-fixed.normal-tier-shared",
                       "SST_BF.small.freq-fixed.high-tier-dedicated",
                       "SST_BF.small.freq-fixed.normal-tier-shared",
                       "SST_BF.medium.freq-fixed.high-tier-dedicated",
                       "SST_BF.medium.freq-fixed.normal-tier-shared",
                       "SST_BF.large.freq-fixed.high-tier-dedicated",
                       "SST_BF.large.freq-fixed.normal-tier-shared",
                       "SST_BF.xlarge.freq-fixed.high-tier-dedicated",
                       "SST_BF.xlarge.freq-fixed.normal-tier-shared"],
                      "FREQUENCY_FIXED_HIGH_SHARED":
                      ["SST_BF.micro.freq-fixed.normal-tier-dedicated",
                       "SST_BF.micro.freq-fixed.high-tier-shared",
                       "SST_BF.tiny.freq-fixed.normal-tier-dedicated",
                       "SST_BF.tiny.freq-fixed.high-tier-shared",
                       "SST_BF.small.freq-fixed.normal-tier-dedicated",
                       "SST_BF.small.freq-fixed.high-tier-shared",
                       "SST_BF.medium.freq-fixed.normal-tier-dedicated",
                       "SST_BF.medium.freq-fixed.high-tier-shared",
                       "SST_BF.large.freq-fixed.normal-tier-dedicated",
                       "SST_BF.large.freq-fixed.high-tier-shared",
                       "SST_BF.xlarge.freq-fixed.normal-tier-dedicated",
                       "SST_BF.xlarge.freq-fixed.high-tier-shared"],
                      "FREQUENCY_VAR_HIGH_DEDICATED":
                      ["SST_BF.micro.freq-var.high-tier-dedicated",
                       "SST_BF.micro.freq-var.normal-tier-shared",
                       "SST_BF.tiny.freq-var.high-tier-dedicated",
                       "SST_BF.tiny.freq-var.normal-tier-shared",
                       "SST_BF.small.freq-var.high-tier-dedicated",
                       "SST_BF.small.freq-var.normal-tier-shared",
                       "SST_BF.medium.freq-var.high-tier-dedicated",
                       "SST_BF.medium.freq-var.normal-tier-shared",
                       "SST_BF.large.freq-var.high-tier-dedicated",
                       "SST_BF.large.freq-var.normal-tier-shared",
                       "SST_BF.xlarge.freq-var.high-tier-dedicated",
                       "SST_BF.xlarge.freq-var.normal-tier-shared"],
                      "FREQUENCY_VAR_HIGH_SHARED":
                      ["SST_BF.micro.freq-var.normal-tier-dedicated",
                       "SST_BF.micro.freq-var.high-tier-shared",
                       "SST_BF.tiny.freq-var.normal-tier-dedicated",
                       "SST_BF.tiny.freq-var.high-tier-shared",
                       "SST_BF.small.freq-var.normal-tier-dedicated",
                       "SST_BF.small.freq-var.high-tier-shared",
                       "SST_BF.medium.freq-var.normal-tier-dedicated",
                       "SST_BF.medium.freq-var.high-tier-shared",
                       "SST_BF.large.freq-var.normal-tier-dedicated",
                       "SST_BF.large.freq-var.high-tier-shared",
                       "SST_BF.xlarge.freq-var.normal-tier-dedicated",
                       "SST_BF.xlarge.freq-var.high-tier-shared"]}


@pytest.fixture(scope="module")
def conn(os_secrets):
    """ Attempt to connect to an OpenStack cloud and return the connection
        object """

    return openstack.connect(
        auth_url="{auth_url}".format(auth_url=os_secrets["OS_AUTH_URL"]),
        project_name="{proj}".format(proj=os_secrets["OS_PROJECT_NAME"]),
        username="{user}".format(user=os_secrets["OS_USERNAME"]),
        password="{password}".format(password=os_secrets["OS_PASSWORD"]),
        project_domain_id="{proj_id}"
        .format(proj_id=os_secrets["OS_PROJECT_DOMAIN_ID"]),
        user_domain_id="{user_id}"
        .format(user_id=os_secrets["OS_USER_DOMAIN_ID"]),
        region_name="{region}".format(region=os_secrets["OS_REGION_NAME"]),
        placement_api_version="{placement}"
        .format(placement=os_secrets["OS_PLACEMENT_API_VERSION"]),
        app_name="sst_bf_verification",
        app_version="1.0",
    )


@pytest.fixture(scope="module")
def has_cloud_access(conn):
    """ Check connection to OpenStack cloud """

    has_access = True
    try:
        conn.get_server()
    except Exception:
        # Hiding error messages to guard against sensitive data leakage
        has_access = False
    return has_access


@pytest.fixture(scope="module")
def flavors(has_cloud_access, ansible_vars, conn):
    """ Attempt to get SST-BF flavors and create a list of SST-BF Flavor
        objects """

    # Test connection to OpenStack cloud
    if not has_cloud_access:
        raise Exception("Failed to get information from OpenStack cloud. "
                        "Have you provided the correct information via "
                        "environment variables? Consult readme for more info."
                        "Suppressed error messages to protect sensitive data")

    sst_bf_profile = ansible_vars["sst_bf_profile"]
    flavors_names = PROFILE_FLAVOR_MAP[sst_bf_profile]
    if not flavors_names:
        raise KeyError("Value for sst_bf_profile is not in the accepted list"
                       " of values")
    sst_flavors = []
    for flavor in flavors_names:
        sst_flavor = conn.get_flavor(flavor)
        if not sst_flavor:
            raise Exception("Flavor {flav} not found".format(flav=flavor))
        sst_flavors.append(sst_flavor)

    return sst_flavors


def test_sst_bf_capability_trait(flavors):
    """ Test to check if SST-BF capable CPUs trait is set to required for all
        SST-BF flavors """

    for flavor in flavors:
        assert "trait:CUSTOM_CPU_X86_INTEL_SST_BF" in flavor.extra_specs,\
            "Trait CUSTOM_CPU_X86_INTEL_SST_BF not found in SST-BF flavor"
        assert flavor.extra_specs["trait:CUSTOM_CPU_X86_INTEL_SST_BF"] == \
            "required", "Trait CUSTOM_CPU_X86_INTEL_SST_BF is not set to"\
                        "required"


def test_sst_profile_trait(flavors, ansible_vars):
    """ Test to check if SST-BF profile trait is set to required for all
        SST-BF flavors """

    sst_bf_profile = ansible_vars["sst_bf_profile"]
    trait_name = "trait:CUSTOM_CPU_" + sst_bf_profile
    for flavor in flavors:
        assert trait_name in flavor.extra_specs,\
            "Trait CUSTOM_CPU_{prof} was not found in flavor extra specs"\
            .format(prof=sst_bf_profile)
        assert flavor.extra_specs[trait_name] == "required",\
            "Trait CUSTOM_CPU_{prof} is not set to required in flavor"\
            .format(prof=sst_bf_profile)


def test_hw_policy(flavors):
    """ Test to check if hardware CPU policy is set correctly to either
        dedicated or shared depending on flavor """

    for flavor in flavors:
        assert "hw:cpu_policy" in flavor.extra_specs,\
               "hw:cpu_policy was not found in a flavors extra specs"
        if flavor.name.endswith("dedicated"):
            assert flavor.extra_specs["hw:cpu_policy"] == "dedicated",\
                "hw:cpu_policy was not set to dedicated for a dedicated "\
                "type flavor"
        elif flavor.name.endswith("shared"):
            assert flavor.extra_specs["hw:cpu_policy"] == "shared",\
                "hw:cpu_policy was not set to shared for a shared type "\
                "flavor"
        else:
            raise Exception("Unknown flavor with name '{flav_name}'"
                            .format(flav_name=flavor.name))
