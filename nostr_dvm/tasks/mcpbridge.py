import asyncio
import json
import os
from datetime import timedelta
from pathlib import Path

from nostr_sdk import Client, Timestamp, PublicKey, Tag, Keys, Options, SecretKey, NostrSigner, Kind

from nostr_dvm.backends.mcp import config
from nostr_dvm.backends.mcp.config import load_config
from nostr_dvm.backends.mcp.messages.send_call_tool import send_call_tool
from nostr_dvm.backends.mcp.messages.send_initialize_message import send_initialize
from nostr_dvm.backends.mcp.messages.send_ping import send_ping
from nostr_dvm.backends.mcp.messages.send_tools_list import send_tools_list
from nostr_dvm.backends.mcp.transport.stdio.stdio_client import stdio_client
from nostr_dvm.framework import DVMFramework
from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions, relay_timeout
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.output_utils import post_process_list_to_events


"""
This File contains a Module to search for notes
Accepted Inputs: a search query
Outputs: A list of events 
Params:  None
"""


class MCPBridge(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_MCP
    TASK: str = "mcp-bridge"
    FIX_COST: float = 0
    dependencies = [("nostr-dvm", "nostr-dvm"),
                    ("mcp", "mcp")]
    dvm_config: DVMConfig


    async def init_dvm(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                       admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)




    async def is_input_supported(self, tags, client=None, dvm_config=None):
        for tag in tags:
            if tag.as_vec()[0] == 'i':
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type != "text":
                    return False
        return True

    async def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        self.dvm_config = dvm_config

        request_form = {"jobID": event.id().to_hex()}

        self.config_path = Path.absolute(Path(__file__).parent / "server_config.json")
        self.server_names = ["mcp-crypto-price"]


        if self.options.get("config_path"):
            self.config_path = self.options.get("config_path")
        if self.options.get("server_names"):
            self.server_names = (self.options.get("server_names"))

        c = "list-tools"
        for tag in event.tags().to_vec():
            if tag.as_vec()[0] == 'c':
                c = tag.as_vec()[1]

        content = event.content()


        options = {
            "command" : c,
            "config_path" : self.config_path,
            "server_names" : self.server_names,
            "payload": content
        }
        request_form['options'] = json.dumps(options)
        return request_form

    async def process(self, request_form):
        options = self.set_options(request_form)

        config_path = options["config_path"]
        server_names = options["server_names"]

        if options["command"] == "list-tools":
            tools = await self.list_tools(config_path, server_names)
            # Just return the first for now.
            for tool in tools:
                print(tool[1])
                return json.dumps(tool[1])


        elif options["command"] == "execute-tool":

            print(options["payload"])
            ob = json.loads(options["payload"])

            tool_name = ob["name"]
            tool_args = ob["parameters"]
            tool_response = await self.call_tool(config_path, server_names, tool_name, tool_args)

            return json.dumps(tool_response)



    async def post_process(self, result, event):
        """Overwrite the interface function to return a social client readable format, if requested"""
        for tag in event.tags().to_vec():
            if tag.as_vec()[0] == 'output':
                format = tag.as_vec()[1]
                if format == "text/plain":  # check for output type
                    result = post_process_list_to_events(result)

        # if not text/plain, don't post-process
        return result

    @classmethod
    async def list_tools(cls, config_path, server_names):

        alltools = []
        for server_name in server_names:
            server_params = await config.load_config(config_path, server_name)
            try:
                async with stdio_client(server_params) as (read_stream, write_stream):
                    # Initialize the server

                    tools = await send_tools_list(read_stream, write_stream)
                    if tools is not None:
                        alltools.append((server_name, tools))
                        raise Exception("I'm gonna leave you.")

                    else:
                        print("nada")
            except:
                pass

        print("Ignore the error. We're good.")
        return alltools


    @classmethod
    async def call_tool(cls, config_path, server_names, tool_name, tool_args):
        print("starting to call the tool")

        tool_response = None
        try:
            for server_name in server_names:
                server_params = await config.load_config(config_path, server_name)
                try:
                    async with stdio_client(server_params) as (read_stream, write_stream):
                        #Check if our current config has a tool.


                        tools = await send_tools_list(read_stream, write_stream)
                        stuff = json.dumps(tools)
                        toolsobject = json.loads(stuff)["tools"]
                        print(toolsobject)

                        server_has_tool = False
                        for tool in toolsobject:
                            if tool["name"] == tool_name:
                                print(f"Found tool {tool_name}.")
                                server_has_tool = True
                        if server_has_tool is False:
                            continue

                        tool_response = await send_call_tool(
                            tool_name, tool_args, read_stream, write_stream)
                        raise Exception("I'm gonna leave you.") # Until we find a better way to leave the async with

                except:
                    pass

                return tool_response

            raise Exception("I'm gonna leave you.")
        except:
            pass

        return "not_found"


        alltools = []
        for server_name in server_names:
            server_params = await config.load_config(config_path, server_name)
            try:
                async with stdio_client(server_params) as (read_stream, write_stream):
                    # Initialize the server

                    tools = await send_tools_list(read_stream, write_stream)
                    if tools is not None:
                        alltools.append((server_name, tools))
                        raise Exception("I'm gonna leave you.")

                    else:
                        print("nada")
            except:
                pass

        print("All clear. We made it out of thread hell. never mind the error.")
        return alltools



# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(announce):
    framework = DVMFramework()

    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce
    admin_config.UPDATE_PROFILE = announce

    name = "MCP Test DVM"
    identifier = "mcp_test"  # Chose a unique identifier in order to get a lnaddress
    dvm_config = build_default_config(identifier)

    # MCP CONFIG
    config_path = str(Path.absolute(Path(__file__).parent / "mcp_server_config.json"))
    server_names = ["mcp-crypto-price"]

    tools = asyncio.run(get_tools(config_path, server_names))
    # for now get the first connected server only
    # print(tools)
    j = json.loads(json.dumps(tools[0][1]))

    # Add NIP89
    nip89info = {
        "name": name,
        "picture": "https://i.nostr.build/er2Vu8DccjfanFLo.png",
        "about": "I'm a MCP Test DVM'",
        "supportsEncryption": True,
        "acceptsNutZaps": dvm_config.ENABLE_NUTZAP,
        "nip90Params": {
        },
        "tools": j["tools"]

    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)

    capabilities_tag = Tag.parse(["capabilities", "mcp-1.0"])
    t1_tag = Tag.parse(["t", "mcp"])
    t2_tag = Tag.parse(["t", "bitcoin price"])
    nip89config.EXTRA_TAGS = [capabilities_tag, t1_tag, t2_tag]

    options = {
        "config_path": config_path,
        "server_names": server_names
    }

    dvm = MCPBridge(name=name, dvm_config=dvm_config, nip89config=nip89config,
                    admin_config=admin_config, options=options)

    framework.add(dvm)

    framework.run()


async def get_tools(config_path, server_names):
    tools = await MCPBridge.list_tools(config_path, server_names)
    return tools

if __name__ == '__main__':
    process_venv(MCPBridge)
