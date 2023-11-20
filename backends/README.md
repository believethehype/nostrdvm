# NostrAI Data Vending Machine Backends

Each DVM task might either run locally or use a specific backend.
Especially for GPU tasks it might make sense to outsource some tasks on other machines.
Backends can also be API calls to (paid) services. This directory contains basic calling functions to such backends.
Modules in the folder "tasks" might use these functions to call a specific backend.

Using backends might require some extra work like running/hosting a server or acquiring an API key.


