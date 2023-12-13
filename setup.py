from setuptools import setup, find_packages

VERSION = '0.0.1'
DESCRIPTION = 'A framework to build and run NIP90 Data Vending Machines'
LONG_DESCRIPTION = '-'

# Setting up
setup(
    # the name must match the folder name 'verysimplemodule'
    name="nostr-dvm",
    version=VERSION,
    author="Believethehype",
    author_email="-",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    packages=find_packages(),
    install_requires=[],  # add any additional packages that
    # needs to be installed along with your package. Eg: 'caer'

    keywords=['nostr', 'nip90', 'dvm', 'data vending machine'],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "Programming Language :: Python :: 3",
    ]
)