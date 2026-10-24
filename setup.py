# SPDX-FileCopyrightText: Copyright (c) 2026 slopggobblercobbler81
# SPDX-License-Identifier: MIT

from setuptools import setup, find_packages

setup(
    name="license-doctor",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "license-doctor = license_doctor.cli:main",
        ],
    },
)
