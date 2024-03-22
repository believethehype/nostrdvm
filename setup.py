from setuptools import setup, find_packages

VERSION = '0.3.0'
DESCRIPTION = 'A framework to build and run Nostr NIP90 Data Vending Machines'
LONG_DESCRIPTION = ('A framework to build and run Nostr NIP90 Data Vending Machines. '
                    'This is an early stage release. Interfaces might change/brick')

# Setting up
setup(
    name="nostr-dvm",
    version=VERSION,
    author="Believethehype",
    author_email="believethehypeonnostr@proton.me",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    packages=find_packages(include=['nostr_dvm', 'nostr_dvm.*']),

    install_requires=["nostr-sdk==0.10.0",
                      "bech32",
                      "pycryptodome==3.20.0",
                      "python-dotenv==1.0.0",
                      "emoji==2.8.0",
                      "eva-decord==0.6.1",
                      "ffmpegio==0.8.5",
                      "lnurl",
                      "pandas==2.1.3",
                      "Pillow==10.1.0",
                      "PyUpload==0.1.4",
                      "requests==2.31.0",
                      "instaloader==4.10.1",
                      "pytube==15.0.0",
                      "moviepy==2.0.0.dev2",
                      "zipp==3.17.0",
                      "urllib3==2.1.0",
                      "typing_extensions>=4.9.0"
                      ],
    keywords=['nostr', 'nip90', 'dvm', 'data vending machine'],
    url="https://github.com/believethehype/nostrdvm",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "Programming Language :: Python :: 3",
    ]
)