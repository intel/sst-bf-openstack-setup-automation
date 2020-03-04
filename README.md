# Intel® Speed Select - Base Frequency for OpenStack - Setup Automation
The code herein allows a data center administrator or high-level orchestration tool to use Ansible\* for provisioning OpenStack\* Nova compute servers with Intel® Speed Select - Base Frequency feature. Please read [Intel® Speed Select Technology – Base Frequency Configuration Automation on OpenStack* Compute Host](https://builders.intel.com/docs/networkbuilders/intel-speed-select-technology-base-frequency-configuration-automation-on-openstack-compute-host.pdf) Application note for more detailed information.

Intel® SST-BF is a CPU feature designed to unlock software bottlenecks. For the same Thermal Design Power (TDP), a subset of cores have different frequency profiles depending on the profile selected with this Ansible\* role. A subset of cores run at higher core frequencies and this configuration presents an opportunity to address many use cases, including:
* Network Function Virtualization (NFV) Data Plane, Control Plane and Open vSwitch\* (OVS) use cases
* Pipeline software architectures
* Frequency bound workloads such as software based crypto
* Priority threads for run to completion such as unbalanced downlink or uplink threads
* Packet distribution and workload distribution in software
* Scenarios where polling user space drivers can be consolidated

This Ansible* role covers the following aspects of Intel® SST-BF provisioning, configuration and usage on an OpenStack\* Nova compute node:
* Configuring platform nodes by setting the CPU to the right frequency boundaries via direct CPU interaction using the Kernel file system (sysfs).
* Configuring OpenStack\* to provide tenants with the option to request and provision workloads on cores configured with different frequency levels.
* Presenting an automation process usage example of a particular OVS-DPDK use case: Pinning OVS-DPDK to a set of cores on a node running OpenStack\* compute process and sharing the CPU with virtualized workloads.

This Ansible\* role is focused on OpenStack\* but can also be ultilised to provision nodes with SST-BF for other orchestrators such as Kubernetes\*.

## Provisioning Automation Flow
The following diagram describes how to take an existing Ansible\* Playbook for a resource orchestrator (e.g OpenStack\*) and insert this role into an Ansible\* Playbook to perform the required automation.
![Screenshot](./images/sst_bf_provisioning_flow.png)

|  Activity|Description  |
|--|--|
|  Enable Intel® SST-BF in BIOS| Initial step required from the System Administrator to change the BIOS configuration as specified in section 3.2 of document [Intel® Speed Select - Base frequency enhancing performance](https://builders.intel.com/docs/networkbuilders/intel-speed-select-technology-base-frequency-enhancing-performance.pdf) |
| Set up Intel® SST-BF Core frequencies | Initial automated step to set up core configuration to get high and normal priority frequencies as identified by the kernel driver in sysfs. Frequency configuration is achieved using [Python SST-BF configuration script](https://github.com/intel/CommsPowerManagement).
| Configure OVS-DPDK Core Reservation | Before proceeding to the OVS-DPDK installation and configuration, it is required to reserve either high or normal priority cores and pin them to an OVS-DPDK process. (Optional step)
| Install / Configure OVS-DPDK | This role supports either installing OVS-DPDK from distribution repositorys or use OVS-DPDK which was previously installed. OVS-DPDK is configured to leverage SST-BF. Note: OVS-DPDK is not installed by default during an OpenStack\* installation process. This step is provided to ease the OVS-DPDK installation and configuration process as part of this flow. (Optional step)
| Install OpenStack\* | OpenStack\* is installed by the System Administrator using either an automation set or manual steps.
| Configure OpenStack\* to support Intel® SST-BF | The Intel® SST-BF configuration with the identification of high and normal priority tiers will be appended to the OpenStack\* Nova configuration file provisioned by the OpenStack\* installation mechanism on the compute node. The OpenStack\* Custom-Traits configuration to the node and the creation of the flavors related to the specific cloud configuration is done as part of this activity.

## OpenStack*: Exposing and Using the Intel® SST-BF feature
This role configures OpenStack* by adding a custom trait “CUSTOM_CPU_X86_INTEL_SST_BF" to show a Nova compute node is SST-BF capable to the placement database. There are four SST-BF profiles from which to choose from which indicate which SST-BF profile has been applied to the targeted Nova compute node.

### Standardize CPU resource tracking
A mechanism to split the pool of cores in OpenStack\* is defined in blueprint ["Standardize CPU resource tracking"](https://blueprints.launchpad.net/nova/+spec/cpu-resources). The mechanism uses the following two resource classes defined for placement API:
- PCPU to represent dedicated CPU cores
- VCPU to represent CPU cores that can be shared by multiple workloads

This resource tracking mechanism introduced in OpenStack\* Train allows the Cloud Admin to define:
- which host cores should be used for dedicated workloads (exclusive core pinning for critical execution)
- which host cores should be used for shared workloads (time sharing core cycles between independent workloads)

On the CPU, the SST-BF functionality allows you to setup the frequencies of the CPU cores to operate on different tiers, optimize the overall power consumption, critical workload throughput, and also create deterministic frequency boundaries on the CPU cores. The two features (Intel® SST-BF and OpenStack\* CPU resource tracking) can be combined to allow the Cloud Admin to setup the OpenStack\* core classification, match the dedicated list of cores to either high or normal frequency tiers and match the shared list of cores to either high or normal frequency tiers optionally subtracting any cores allocated to OVS-DPDK.

The core distribution ratio for the shared cores is defined by `cpu_allocation_ratio` Ansible\* variable (float).
Nova configuration file variables configured:

| Nova Variable         | Description           |
|-----------------------|-----------------------|
| cpu_dedicated_set     | Dedicated CPU cores   |
| cpu_shared_set        | Shared CPU cores      |
| cpu_allocation_ratio  | VCPU allocation ratio |

The following demonstrates the SST-BF CPU capable trait and four SST-BF profile frequency configuration traits:
![Screenshot](./images/custom_traits_rep_os.png)

### Sample OpenStack\* Ansible\* Playbook
Setup OpenStack\* Nova compute with SST-BF and configure OpenStack\* sample playbook:
```ansible
- name: Configure SST-BF for OpenStack
  hosts: nova_compute
  gather_facts: yes
  user: root
  tasks:
      - name: Set and get SST-BF
        include_role:
          name: "intel.sst_bf_openstack_setup_automation"

      # [ Insert role to install OpenStack Nova Compute here ]
      # OpenStack Nova compute must be installed before running the next task

      - name: Configure OpenStack for SST-BF
        vars:
          # For demonstrative purposes - Encrypt credentials using Ansible Vault
          OS_USERNAME: admin
          OS_PASSWORD: admin
          OS_AUTH_URL: https://192.168.1.1
          OS_PROJECT_NAME: default
          OS_USER_DOMAIN_ID: default
          OS_PROJECT_DOMAIN_ID: demo
          OS_REGION_NAME: RegionOne
          OS_PLACEMENT_API_VERSION: 1.6
          configure_os_only: true
        include_role:
          name: "intel.sst_bf_openstack_setup_automation"
```

## SST-BF Profile
The Ansible\* variable `sst_bf_profile` defines which SST-BF configuration to apply to the OpenStack\* Nova compute node. It also denotes how each frequency priority level is mapped to OpenStack\* Nova's `cpu_dedicated_set` & `cpu_shared_set` variables. The SST-BF profile applied to the target Node does not persist following a reboot.
The following values are options for `sst_bf_profile`:

### FREQUENCY_FIXED_HIGH_DEDICATED
The `cpu_dedicated_set` holds the list of cores set to high priority frequency.
- Min and Max boundary are set to the high BF tier.

The `cpu_shared_set` holds the list of cores set to normal priority frequency.
- Min and Max boundary are set to the normal BF tier

### FREQUENCY_FIXED_HIGH_SHARED
The `cpu_dedicated_set` holds the list of cores set to normal priority frequency.
- Min and Max boundary are set to the normal BF tier.

The `cpu_shared_set` holds the list of cores set to high priority frequency.
- Min and Max boundary are set to the high BF tier

### FREQUENCY_VAR_HIGH_DEDICATED
> **_NOTE:_**  This option is experimental!

The `cpu_dedicated_set` holds the list of cores set to high priority frequency.
- Min boundary is set to a given minimum CPU frequency. (Depends on SKU reference and recommended configuration.)
- Max boundary is set to the high BF tier.

The `cpu_shared_set` holds the list of cores set to normal priority frequency.
- Min boundary is set to a given minimum CPU frequency. (Depends on SKU reference and recommended configuration.)
- Max boundary is set to the normal BF tier.

### FREQUENCY_VAR_HIGH_SHARED
> **_NOTE:_**  This option is experimental!

The `cpu_dedicated_set` holds the list of cores set to normal priority frequency.
- Min boundary is set to a given minimum CPU frequency. (Depends on SKU reference and recommended configuration.)
- Max boundary is set to the normal BF tier.

The `cpu_shared_set` holds the list of cores set to high priority frequency.
- Min boundary is to a given minimum CPU frequency. (Depends on SKU reference and recommended configuration.)
- Max boundary is set to the high BF tier.

## Role Variables
| Variable                | Default                         | Description                                                                          |
|-------------------------|---------------------------------|------------------------------------------------------------------------------------- |
| configure_os_only       | false                           | When true, OpenStack\* is already present on the target host. Ansible variables OS_USERNAME, OS_PASSWORD, OS_AUTH_URL, OS_PROJECT_NAME, OS_USER_DOMAIN_ID, OS_PROJECT_DOMAIN_ID and OS_PLACEMENT_API_VERSION need to be defined for logging into OpenStack\* when this option is set to true                           |
| nova_conf_path          | /etc/nova/nova-cpu.conf         | Nova Configuration file location                                                     |
| restart_nova            | true                            | Option to restart nova after configuration changes                                   |
| nova_service_name       | devstack@n-cpu.service          | Systemctl Nova service name for restarting after configuration file changes          |
| skip_ovs_dpdk_config    | true                            | Skip OpenvSwitch*-DPDK                                                               |
| ovs_dpdk_installed      | true                            | If an existing installation of OpenvSwitch*-DPDK exists or not before executing this role  |
| ovs_core_high_priority  | true                            | If true then pin high priority cores to PMD otherwise choose normal priority  cores  |
| ovs_dpdk_nr_1g_pages    | 16                              | Number of 1 GB hugepages to reserve for DPDK                                         |
| ovs_dpdk_nr_2m_pages    | 2048                            | Number of 2 MB hugepages to reserve for DPDK                                         |
| ovs_dpdk_driver         | vfio-pci                        | Driver to bind to NIC                                                                |
| ovs_service_name        | openvswitch-switch              | Systemctl service name for OpenvSwitch*                                              |
| ovs_datapath            | netdev                          | Userspace datapath type for OpenvSwitch* bridge creation                             |
| ovs_dpdk_interface_type | dpdk                            | Interface type for DPDK                                                              |
| offline                 | false                           | Air-gapped deployment. Clone/copy [CommsPowerManagement](https://github.com/intel/CommsPowerManagement) to /tmp of Nova compute target if true     |
| sst_bf_profile          | FREQUENCY_FIXED_HIGH_DEDICATED  | Contains a set of values that control which Intel® SST-BF profile we apply to the target host. The possible values are:<br> * FREQUENCY_FIXED_HIGH_DEDICATED<br> * FREQUENCY_FIXED_HIGH_SHARED<br> * FREQUENCY_VAR_HIGH_DEDICATED<br> * FREQUENCY_VAR_HIGH_SHARED<br>This will be translated to the corresponding traits:<br> * CUSTOM_CPU_FREQUENCY_FIXED_HIGH_DEDICATED<br> * CUSTOM_CPU_FREQUENCY_FIXED_HIGH_SHARED<br> * CUSTOM_CPU_FREQUENCY_VAR_HIGH_DEDICATED<br> * CUSTOM_CPU_FREQUENCY_VAR_HIGH_SHARED |
| cpu_allocation_ratio    | 1.0                            | Core distribution ratio for shared cores (vCPUs)                                     |
| no_ovs_dpdk_lcore_pinned| 1                               | No. of normal priority logical cores to pin to OVS-DPDK's lcore                      |

A description of the target node is needed if you are configuring or installing OpenvSwitch*-DPDK.

### Sample host description
```
host_description:
  numa_nodes:
    0:
      interfaces:
        eno1:
          pci_address: "0000:3d:00.0"
        eno2:
          pci_address: "0000:3d:00.1"
      dpdk_socket_mem: 1024
      no_physical_cores_pinned: 4
    1:
      dpdk_socket_mem: 1024
      no_physical_cores_pinned: 2
  bridge_mappings:
    ovs-brnew: ['eno1','eno2']
```
### Ansible\* variable `host_description` key's description
| Value                    | Required definition | Description                                                                                                                                                                                     |
|--------------------------|---------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| host_description         | yes                 | Description of target node's assets needed to configure OpenvSwitch*-DPDK                                                                                                                       |
| numa_nodes               | yes                 | Description of target NUMA nodes describing interfaces, socket memory and number of physical cores to pin to PMD. numa_nodes dictionary must contain one or more NUMA nodes                     |
| interfaces               | no                  | One or more interfaces need to be defined if interfaces are defined. This information will be leveraged to build a bridge which will bind to an interface. This dict will contain key value pairs. The key is the interface name |
| pci_address              | no                  | A PCI address for a given interface and it needs to be defined if an interface is defined in bridge_mappings                                                                                    |
| dpdk_socket_mem          | yes                 | DPDK allocated socket memory                                                                                                                                                                    |
| no_physical_cores_pinned | yes                 | Number of physical cores to pin to associated NUMA node                                                                                                                                         |
| Bridge_mappings          | yes                 | Bridge definition for DPDK including one key-value 'bridge name (key) - (value) list of interface name(s)' definition. Interfaces defined here must have an associated definition in numa_nodes |

Ansible\* variable `no_physical_cores_pinned` denotes the amount of physical cores you wish to pin to DPDK's PMD.

## Requirements
- Server with Speed Select - Base Frequency functionality (e.g Intel® Xeon® 5218N / 6230N / 6252N )
- Linux\* kernel >= 5.1
- Python >= 3.5
- Ansible\* >= 2.5
- Molecule\* = 2.22
- OpenStack\* Train or greater

## OpenvSwitch-DPDK\* Optimisation using SST-BF (Optional flow)
An optional task for this role is to configure OpenvSwitch* with DPDK either with an existing installation present or installation from the distributions repositories.
This role allows DPDK to utilize and isolate either high or normal priority cores for DPDK's poll mode driver (PMD). The user can specify the amount of physical cores to pin to PMD on each NUMA node. The physical cores pinned to PMD will be isolated from kernel processes and OpenStack's\* provisioning of virtual machines. A user defined number of threads of normal priority is pinned to DPDK's lcore. A host restart is required for this functionality and the SST-BF profile selected is re-applied to the system following this reboot.

Set `skip_ovs_dpdk_config` to true if you wish to skip configuring OVS-DPDK completely.
If you have previously installed OVS-DPDK prior to running this Ansible\* Role and wish to pin either high or normal priority cores to DPDK's poll mode driver, then set `ovs_dpdk_installed` to true. If compiling OVS-DPDK from source, create a systemd service to allow for configuration changes to be applied and set the service name to Ansible variable `ovs_service_name`. Also, ensure interfaces used to form the OVS bridge are binded to the correct driver prior to executing this role.
If you wish to install OVS-DPDK from your distribution supported repositories then set `ovs_dpdk_installed` to false. Please ensure your distribution supports this option.

| Distro       | OVS-DPDK repo support |
|--------------|-----------------------|
| Ubuntu 18.04 | y                     |
| RHEL 8.0     | n                     |
| Fedora       | n                     |
| Centos       | n                     |

A host restart is required irregardless of whether `ovs_dpdk_installed` is true or false to ensure isolation of pinned cores to DPDK's PMD.

### OVS-DPDK Sample Ansible\* Playbooks
Setup OpenStack\* Nova compute with SST-BF, configure existing OVS-DPDK installation, pinning and isolating physical cores to DPDK's PMD and giving remaining cores to OpenStack\*. Please define target `host_description` Ansible\* variable to suit your OpenStack\* compute node.
```ansible
- name: Configure SST-BF for OpenStack
  hosts: nova_compute
  user: root
  gather_facts: yes
  tasks:
      - name: Set and get SST-BF
        vars:
          skip_ovs_dpdk_config: false
        include_role:
          name: "intel.sst_bf_openstack_setup_automation"

      # [ Insert role to install OpenStack Nova Compute here ]
      # OpenStack Nova compute must be installed before running the next task

      - name: Configure OpenStack for SST-BF
        vars:
          # For demonstrative purposes - Encrypt credentials using Ansible Vault
          OS_USERNAME: admin
          OS_PASSWORD: admin
          OS_AUTH_URL: https://192.168.1.1
          OS_PROJECT_NAME: default
          OS_USER_DOMAIN_ID: default
          OS_PROJECT_DOMAIN_ID: demo
          OS_REGION_NAME: RegionOne
          OS_PLACEMENT_API_VERSION: 1.6
          configure_os_only: true
        include_role:
          name: "intel.sst_bf_openstack_setup_automation"
```

Setup OpenStack\* Nova compute with SST-BF, install OVS-DPDK from distribution repository, pinning and isolating physical cores to DPDK's PMD and giving remaining cores to OpenStack\*. Please define target `host_description` Ansible\* variable to suit your OpenStack\* compute node.
```ansible
- name: Configure SST-BF for OpenStack
  hosts: nova_compute
  user: root
  gather_facts: yes
  tasks:
      - name: Set and get SST-BF
        vars:
          skip_ovs_dpdk_config: false
          ovs_dpdk_installed: false
        include_role:
          name: "intel.sst_bf_openstack_setup_automation"

      # [ Insert role to install OpenStack Nova Compute here ]
      # OpenStack Nova compute must be installed before running the next task

      - name: Configure OpenStack for SST-BF
        vars:
          # For demonstrative purposes - Encrypt credentials using Ansible Vault
          OS_USERNAME: admin
          OS_PASSWORD: admin
          OS_AUTH_URL: https://192.168.1.1
          OS_PROJECT_NAME: default
          OS_USER_DOMAIN_ID: default
          OS_PROJECT_DOMAIN_ID: demo
          OS_REGION_NAME: RegionOne
          OS_PLACEMENT_API_VERSION: 1.6
          configure_os_only: true
        include_role:
          name: "intel.sst_bf_openstack_setup_automation"
```

## Ansible Strategy
This role supports linear Ansible* strategy only. This is the default Ansible* strategy. See [Ansible* strategy documentation](https://docs.ansible.com/ansible/latest/user_guide/playbooks_strategies.html) for more details

## Running Tests Using Ansible Molecule
[Ansible Molecule](https://molecule.readthedocs.io/en/stable/) is used to run Python tests that validate the functionality of this Role. For each Molecule test scenario defined for this role, there is a playbook to orchestrate the scenario. In this playbook, there are two Ansible* variables which need your consideration; `molecule_test` and `secrets_path`. Ansible* variable `molecule_test` informs this role that it is currently under test and to output variables which are consumed during testing. Ansible* variable `secrets_path` defines the location of a yaml file which contains key-value pairs which are required for OpenStack* authentication. Please checkout heading "Sample secrets file" below for a sample yaml file.

### Install Molecule

Assuming you have `pip` installed:

```
pip install molecule
```

Check if installation was successful:

```
$ molecule --version
molecule, version 2.22
```

### Define Target Host

The target host is where Molecule will execute the Ansible Role.

In the files `molecule/*/molecule.yml`, add the hostname of your target host.

```
...
platforms:
  - name: # target-hostname-here
...
```
**Note**: The driver type used is [`delegated`](https://molecule.readthedocs.io/en/latest/configuration.html#delegated) with connection over SSH to the target host. Ensure you have SSH keys setup.

### Sample secrets file
For testing this Ansible* role in isolation using Molecule, a yaml file containing OpenStack* crendentials with a tightly controled ACL of '0640' needs to be created before testing. For each Molecule scenario, its associated playbook needs to be edited. Ansible variable `secrets_path` must have a value which is a path to the OpenStack secrets file. Ansible variable `secrets_path` must also be defined in cleanup.yml. A sample secrets file is defined below. Re-encrypt with Ansible* vault or delete this file following testing.
```yaml
---
OS_USER_DOMAIN_ID: default
OS_AUTH_URL: http://192.168.122.39/identity
OS_PROJECT_DOMAIN_ID: default
OS_REGION_NAME: RegionOne
OS_PROJECT_NAME: demo
OS_IDENTITY_API_VERSION: 3
OS_TENANT_NAME: demo
OS_AUTH_TYPE: password
OS_PASSWORD: C0mpl3xPassw0rd
OS_USERNAME: zero_day_provision
OS_VOLUME_API_VERSION: 3
OS_PLACEMENT_API_VERSION: 1.6
```

### Run Full Test Sequence

```
molecule test
```
**Note:** Targets the default [Scenario](#scenarios). See [here](#running-full-test-sequence-with-different-scenarios) to target other Scenarios.

The test sequence is defined in `molecule/*/molecule.yml`.

```
...
scenario:
  name: # scenario-name
  test_sequence:
    - lint
    - cleanup
    - syntax
    - converge
    - verify
    - cleanup
```

* `lint` - Runs linters [Yamllint, Flake8, Ansible Lint]
* `cleanup` - Cleanup script is at `molecule/*/cleanup.yml`. Attempts to revert/remove any configuration, installations, etc. executed by the Role
* `syntax` - Runs Ansible Lint on Role. (Different from `lint` as this runs the Playbook using the native Ansible `--syntax-check` option)
* `converge` - Runs the Role
* `verify` - Runs tests

**Note:** Molecule is heavily geared towards containerisation of test environments, where a container is created, the Ansible Role is executed and the container is destroyed. In the Molecule [documentation](https://molecule.readthedocs.io/en/latest/configuration.html#id12), it is recommended that the `cleanup` step be executed directly before every `destroy` step, as it is used for cleaning up test infrastructure external to the container. As this Role runs on baremetal, the cleanup script included cleans up/reverts any changes after the test run and also does the same to external files or systems modified. There is no need for a `destroy` step.

More information about each step in the sequence can be found [here](https://molecule.readthedocs.io/en/latest/usage.html#usage).

### Test Cases

Tests are shared across all [Scenarios](#scenarios).

| Case                        | Description                       															|
|---                          |---                                															|
| test_dpdk_init.py           | Test if DPDK is initialised                      								|
| test_dpdk_socket_mem.py     | Test socket memory allocation for DPDK         									|
| test_hugepage.py            | Test hugepage allocation                        								|
| test_iommu.py               | Test if IOMMU is enabled                  						 					|
| test_isolated_cpus.py       | Test if correct CPUs are isolated                               |
| test_lcore.py               | Test if DPDK's lcore is setup correctly                       	|
| test_nova_conf.py           | Test if OpenStack Nova is configured correctly                  |
| test_pmd.py                 | Test if DPDK's PMD is configured correctly                      |
| test_rp_traits.py           | Test if OpenStack Resource Provider is configured correctly     |
| test_sst_bf_flavors.py      | Test if OpenStack flavors for SST-BF are configured correctly   |
| test_sst_bf_profile.py      | Test if SST-BF profile has been applied correctly               |

**Note:** OVS-DPDK related tests will be skipped when using default flow Scenarios.

### Scenarios

[Molecule Scenarios](https://molecule.readthedocs.io/en/latest/getting-started.html#molecule-scenarios) are used to set up the Role for testing by selectively altering the [default Ansible variables](#role-variables) to represent different _scenarios_ or intended outcomes. This is achieved by setting the default variables to desired values (within constraints) in the `playbook.yml` file of each Scenario. These values will take precedence over the default variables declared in `defaults/main.yml`.


Below is a description of alterations by Scenario:

| Scenario Name    | Description                                                          | [Variables](#role-variables) Altered  |
|---          |---                                                                   |---                                    |
| default     | Default flow                                               | N/A                                   |
| scenario-2  | Optional [OVS-DPDK flow](#openvswitch-dpdk-optimisation-using-sst-bf-optional-flow)<br>Assumes user has `ovs-dpdk` installed | skip_ovs_dpdk_config -> False |
| scenario-3  | Optional [OVS-DPDK flow](#openvswitch-dpdk-optimisation-using-sst-bf-optional-flow)<br>Installs `ovs-dpdk` from distro repositories | skip_ovs_dpdk_config -> False<br>ovs_dpdk_installed -> False |
| scenario-4  | Default flow<br>Air-gapped/offline mode                    | offline -> True                       |
| scenario-5  | Optional [OVS-DPDK flow](#openvswitch-dpdk-optimisation-using-sst-bf-optional-flow)<br>Air-gapped/offline mode<br>Assumes user has `ovs-dpdk` installed | offline -> True<br>skip_ovs_dpdk_config -> False      |
| scenario-6  | Optional [OVS-DPDK flow](#openvswitch-dpdk-optimisation-using-sst-bf-optional-flow)<br>Pin normal priority cores to PMD<br>Assumes user has `ovs-dpdk` installed        | ovs_core_high_priority -> False<br>skip_ovs_dpdk_config -> False       |
| scenario-7  | Optional [OVS-DPDK flow](#openvswitch-dpdk-optimisation-using-sst-bf-optional-flow)<br>More than 1 normal priority core pinned to OVS-DPDK's lcore<br>Assumes user has `ovs-dpdk` installed | no_ovs_dpdk_lcore_pinned -> 2<br>skip_ovs_dpdk_config -> False         |
| scenario-8  | Optional [OVS-DPDK flow](#openvswitch-dpdk-optimisation-using-sst-bf-optional-flow)<br>Sets the SST-BF profile to `FREQUENCY_FIXED_HIGH_SHARED`<br>Assumes user has `ovs-dpdk` installed | sst_bf_profile  -> FREQUENCY_FIXED_HIGH_SHARED<br>skip_ovs_dpdk_config -> False |
| scenario-9  | Optional [OVS-DPDK flow](#openvswitch-dpdk-optimisation-using-sst-bf-optional-flow)<br>Sets the SST-BF profile to `FREQUENCY_VAR_HIGH_DEDICATED`<br>Assumes user has `ovs-dpdk` installed | sst_bf_profile  -> FREQUENCY_VAR_HIGH_DEDICATED<br>skip_ovs_dpdk_config -> False |
| scenario-10  | Optional [OVS-DPDK flow](#openvswitch-dpdk-optimisation-using-sst-bf-optional-flow)<br>Sets the SST-BF profile to `FREQUENCY_VAR_HIGH_SHARED`<br>Assumes user has `ovs-dpdk` installed | sst_bf_profile  -> FREQUENCY_VAR_HIGH_SHARED<br>skip_ovs_dpdk_config -> False |


> **_IMPORTANT:_**
> * For Scenarios which test the optional OVS-DPDK flow, each `playbook.yml` file is pre-populated with [`host_description`](#sample-host-description) options which can be tweaked to suit your system
> * Make sure to define target host for ALL Scenarios as described [here](#define-target-host)


### Running Full Test Sequence with Different Scenarios
The Molecule test sequence remains the same, except `converge` will utilise the targetted Scenario's `playbook.yml` to run the Role.

```
molecule test -s <scenario-name>
```

## Software Testing
This role has been tested against the following software and distributions. The tests executed are located in the Molecule directory.

| Name(s)                                                                | Source   | Version(s)                | Distro(s) |
|------------------------------------------------------------------------|----------|---------------------------|-----------|
| Openvswitch, DPDK                                                      | apt      | 2.9.5, 17.11.9            | Ubuntu 18.04    |
| Openvswitch, DPDK                                                      | compiled | 2.11, 18.11               | Ubuntu 18.04    |

## Dependencies
[Intel® CommsPowerManangement Python SST-BF configuration script](https://github.com/intel/CommsPowerManagement)

## Security Considerations
External dependencies (e.g CommsPowerManagement repo) for this role have been given the following security considerations.

### Creating a Directory for SST-BF Dependencies
A directory is created by Ansible* [tempfile](https://docs.ansible.com/ansible/latest/modules/tempfile_module.html) module. This directory name is unique and read only. When utilizing this directory, a check is in place to ensure it is not a symbolic link, which prevents a symbolic link attack (hijacking). Any file utilized inside this directory is also checked for the same.

### OpenStack* Credentials
Credentials for OpenStack* are sourced by looking for Ansible* variables. Ensure in your playbook, when including yaml variable files which contain sensitive credentials, such as OpenStack* credentials, that the yaml file is encrypted using Ansible Vault. Set the files ACL to '0640'. An adequately limited OpenStack* keystone user is needed for this role, which should have access to create/update/delete flavors through OpenStack* Nova and create/delete/update traits and resource providers though OpenStack* Placement.

## Licence
The role is provided under the Apache 2.0 license.

## Author Information
* Sohaib Iqbal
* Martin Kennelly - martin.kennelly@intel.com
* Mathana Sreedaran - mathana.nair.sreedaran@intel.com

## Further information
1. [Intel® Speed Select Technology – Base Frequency Configuration Automation on OpenStack* Compute Host](https://builders.intel.com/docs/networkbuilders/intel-speed-select-technology-base-frequency-configuration-automation-on-openstack-compute-host.pdf)
2. [Intel® Speed Select - Base frequency](https://builders.intel.com/docs/networkbuilders/intel-speed-select-technology-base-frequency-enhancing-performance.pdf)
3. [Intel® SST-BF configuration Python script](https://github.com/intel/CommsPowerManagement)

“*Other names and brands may be claimed as the property of others”.
