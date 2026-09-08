from setuptools import setup, find_packages

VERSION = '1.1.5'
DESCRIPTION = 'A framework to build and run Nostr NIP90 Data Vending Machines. Unrecommended by fiatjaf.'
LONG_DESCRIPTION = ('A framework to build and run Nostr NIP90 Data Vending Machines. See the github repository for more information.')

# Setting up
setup(
    name="nostr-dvm",
    version=VERSION,
    author="Believethehype",
    author_email="believethehypeonnostr@proton.me",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    packages=find_packages(include=['nostr_dvm', 'nostr_dvm.*']),

    install_requires=["nostr-sdk==0.45.1",
                      "bech32==1.2.0",
                      "pycryptodome==3.20.0",
                      "yt-dlp==2026.8.19",
                      "python-dotenv==1.2.3",
                      "emoji==2.12.1",
                      "ffmpegio==0.9.1",
                      "ffmpegio-core==0.10.0",
                      "pillow==12.3.0",
                      "PyUpload==0.1.4",
                      "pandas==2.2.2",
                      "requests==2.34.2",
                      "zipp==3.19.1",
                      "urllib3==2.7.0",
                      "networkx==3.3",
                      "scipy==1.13.1",
                      "typer==0.15.1",
                      "beautifulsoup4==4.12.3",
                      "tqdm==4.66.6"
                      ],
    extras_require={"openai": ["openai>=1.55.3,<2"]},
    keywords=['nostr', 'nip90', 'dvm', 'data vending machine'],
    url="https://github.com/believethehype/nostrdvm",
    license="MIT",
    python_requires='>=3.10',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "Programming Language :: Python :: 3",
    ]
)
