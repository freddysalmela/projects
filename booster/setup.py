from setuptools import setup, find_packages

setup(
    name="booster",
    version="0.1.0",
    packages=find_packages(),
    install_requires=open("requirements.txt").read().splitlines(),
    entry_points={
        "console_scripts": [
            "booster=booster.main:main",
        ],
    },
    python_requires=">=3.11",
)
