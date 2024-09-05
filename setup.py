from setuptools import setup, find_packages

VERSION = '0.8.18'
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

    install_requires=["nostr-sdk==0.34.0",
                      "bech32==1.2.0",
                      "pycryptodome==3.20.0",
                      "yt-dlp==2024.5.27",
                      "python-dotenv==1.0.0",
                      "emoji==2.12.1",
                      "ffmpegio==0.9.1",
                      "Pillow==10.1.0",
                      "PyUpload==0.1.4",
                      "pandas==2.2.2",
                      "requests==2.32.3",
                      "moviepy==2.0.0.dev2",
                      "zipp==3.17.0",
                      "urllib3==2.2.1",
                      "networkx==3.3",
                      "scipy==1.13.1",
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