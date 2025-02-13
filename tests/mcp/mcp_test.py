import asyncio
import json
from pathlib import Path

import dotenv

from nostr_dvm.framework import DVMFramework
from nostr_dvm.tasks.mcpbridge import MCPBridge
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_sdk import  Tag


async def get_tools(config_path, server_names):
    tools = await MCPBridge.list_tools(config_path, server_names)
    return tools




def playground(announce=False):

    framework = DVMFramework()

    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce
    admin_config.UPDATE_PROFILE = announce

    name = "MCP Test DVM"
    identifier = "mcp_test"  # Chose a unique identifier in order to get a lnaddress
    dvm_config = build_default_config(identifier)
    dvm_config.DELETE_ANNOUNCEMENT_ON_SHUTDOWN = True

    # MCP CONFIG
    config_path = str(Path.absolute(Path(__file__).parent / "mcp_server_config.json"))
    server_names = ["Echo", "mcp-crypto-price"]


    tools = asyncio.run(get_tools(config_path, server_names))
    # for now get the first connected server only
    #print(tools)
    if len (tools) == 0:
        print("Couldnt load tools, shutting down.")
        exit()

    final_tools =[]
    for tool in tools:
        j = json.loads(json.dumps(tool[1]))["tools"]
        for tool in j:
            final_tools.append(tool)
    print(final_tools)



    # Add NIP89
    nip89info = {
        "name": name,
        "picture": "https://i.nostr.build/er2Vu8DccjfanFLo.png",
        "about": "I'm a MCP Test DVM'",
        "supportsEncryption": True,
        "acceptsNutZaps": dvm_config.ENABLE_NUTZAP,
        "nip90Params": {
        },
        "tools": final_tools

    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)

    capabilities_tag = Tag.parse(["capabilities", "mcp-1.0"])
    t1_tag = Tag.parse(["t","mcp"])
    t2_tag = Tag.parse(["t", "bitcoin price"])
    nip89config.EXTRA_TAGS =[capabilities_tag, t1_tag, t2_tag]


    options = {
        "config_path": config_path,
        "server_names": server_names
    }



    dvm = MCPBridge(name=name, dvm_config=dvm_config, nip89config=nip89config,
                     admin_config=admin_config, options=options)


    framework.add(dvm)

    framework.run()


if __name__ == '__main__':
    env_path = Path('../.env')
    if not env_path.is_file():
        with open('../.env', 'w') as f:
            print("Writing new .env file")
            f.write('')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    playground(announce=True)
