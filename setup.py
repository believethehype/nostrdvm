from setuptools import setup, find_packages

VERSION = '1.1.4'
DESCRIPTION = 'A framework to build and run Nostr NIP90 Data Vending Machines'
LONG_DESCRIPTION = ('A framework to build and run Nostr NIP90 Data Vending Machines. See the github repository for more information')

# Setting up
setup(
    name="nostr-dvm",
    version=VERSION,
    author="Believethehype",
    author_email="believethehypeonnostr@proton.me",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    packages=find_packages(include=['nostr_dvm', 'nostr_dvm.*']),

    install_requires=["nostr-sdk==0.44.6",
                      "bech32==1.2.0",
                      "pycryptodome==3.20.0",
                      "yt-dlp==2026.7.4",
                      "python-dotenv==1.2.2",
                      "emoji==2.12.1",
                      "ffmpegio==0.9.1",
                      "pillow==12.3.0",
                      "PyUpload==0.1.4",
                      "pandas==2.2.2",
                      "requests==2.33.0",
                      "moviepy==2.0.0",
                      "zipp==3.19.1",
                      "urllib3==2.7.0",
                      "networkx==3.3",
                      "scipy==1.13.1",
                      "typer==0.15.1",
                      "beautifulsoup4==4.12.3"
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