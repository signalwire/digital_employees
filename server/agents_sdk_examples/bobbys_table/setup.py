#!/usr/bin/env python3
"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

import os
import shutil

# Copy schema.json to the package directory if it's not already there
schema_src = os.path.join(os.path.dirname(__file__), 'schema.json')
schema_dst = os.path.join(os.path.dirname(__file__), 'signalwire_agents', 'schema.json')
if os.path.exists(schema_src) and not os.path.exists(schema_dst):
    os.makedirs(os.path.dirname(schema_dst), exist_ok=True)
    shutil.copy2(schema_src, schema_dst)
    print(f"Copied schema.json to {schema_dst}")

# Allow setuptools to handle the rest
from setuptools import setup
setup()
