#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Check SID value in detail."""

import os
from dotenv import load_dotenv

load_dotenv()

service_key = os.getenv("JVLINK_SERVICE_KEY")

print(f"Service Key value: '{service_key}'")
print(f"Length: {len(service_key) if service_key else 0}")
print(f"Type: {type(service_key)}")

if service_key:
    print(f"First character: '{service_key[0]}' (ord={ord(service_key[0])})")
    print(f"Repr: {repr(service_key)}")
    print(f"Bytes: {service_key.encode('utf-8')}")

    # Check for spaces
    if service_key[0] == ' ':
        print("WARNING: First character is a space!")
    else:
        print("OK: First character is not a space")
