import sys
from setuptools import setup, find_packages

# PyAudio must be installed separately on Windows (via pipwin or .whl).
# All other deps are installed here.
REQUIRES = [
    line.strip()
    for line in open("requirements.txt")
    if line.strip() and not line.startswith("#") and "pyaudio" not in line.lower()
]

setup(
    name="booster",
    version="0.1.0",
    packages=find_packages(),
    install_requires=REQUIRES,
    entry_points={
        "console_scripts": [
            "booster=booster.main:main",
        ],
    },
    python_requires=">=3.11",
)
