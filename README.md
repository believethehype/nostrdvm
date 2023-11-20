# NostrAI Data Vending Machine

This example DVM implementation in Python currently supports simple translations using Google translate, as well as extraction of text from links with pdf files.

At a later stage, additional example tasks will be added, as well as the integration into a larger Machine Learning backend 


Place .env file (based on .env_example) in main folder, install requirements.txt (python 3.10) run main.py. Optionally supports LNbits to create invoices instead of lnaddresses.

Use vendata.io to create a nip89 announcement of your dvm and save the dtag in your .env config.

A tutorial on how to add additional tasks, as well as the larger server backend will be added soon. 

Known Issues:
- After refactoring DVMs work independent from each other for the most part.
  - They currently still share a joblist and might act weird together (TODO rework joblist) 
  - Some functions might work easier than they did before (need some refactoring)
- Bot currently not implemented
- Some basic functionality is still missing, e.g. handling various mediasources
- Interface might still change a lot and brick things.
