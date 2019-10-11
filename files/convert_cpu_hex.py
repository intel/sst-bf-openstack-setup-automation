#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

from __future__ import print_function
import sys

# Ansible does not support binary representation which is necessary
# to get the cpu mask. We leverage python to accomplish this using std libs.
# Input: String representing core numbers. Ex. '4,7,9,19,25'
# Output: CPU mask in hex form via std out Ex. '0x4a'
if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise ValueError("Incorrect arguments specified")
    core_list_s = sys.argv[1].split(',')
    for cpu in core_list_s:
        if not cpu.isdigit():
            sys.exit(2)
    bit_mask = 0
#   Generate bit mask
    for cpu in core_list_s:
      bit_mask = bit_mask | (1 << int(cpu))
#   Convert to hex
    print(hex(bit_mask))
