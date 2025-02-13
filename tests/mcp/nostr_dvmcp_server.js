import {McpServer} from "@modelcontextprotocol/sdk/server/mcp.js";
import {StdioServerTransport} from "@modelcontextprotocol/sdk/server/stdio.js";
import {z} from "zod";
import {
    Alphabet,
    Client,
    ClientBuilder,
    Duration,
    EventBuilder,
    Filter,
    Keys,
    Kind,
    loadWasmAsync,
    loadWasmSync,
    NostrSigner,
    SingleLetterTag,
    Tag

} from "@rust-nostr/nostr-sdk";

// To use in a config, such as in Claude Desktop
//
//   "mcpServers": {
//     "nostrdvmcp": {
//       "command": "node",
//       "args": [
//         "<Path to this file>/nostr_dvmcp_server.js"
//       ]
//     }
//   }
// }



//Basic config
const name = "nostr-mcp-server"
const version = "0.0.1"

const config = {
    name: name,
    version: version,
    capabilities: {
        logging: {},
    },
    timeout: 1000
}
 const relays =

        [   "wss://relay.nostrdvm.com",
            "wss://nostr.mom",
            "wss://nostr.oxtr.dev",
            "wss://relay.damus.io",
        ];

// replace publickey with a unique one (it doesn't matter as much, we just do the requests)
let pkey = "e318cb3e6ac163814dd297c2c7d745faacfbc2a826eb4f6d6c81430426a83c2b"

// Create an MCP server for Stdio
const server = new McpServer(config);

//fetch nip89s of mcp servers TODO: allow to filter
await getnip89s()


//define getNip89s. Fetch from Nostr and add as tools to server.
async function getnip89s() {
    await loadWasmAsync();



    let keys = Keys.parse(pkey)
    let signer = NostrSigner.keys(keys)
    let client = new ClientBuilder().signer(signer).build()

    for (const relay of relays) {
        await client.addRelay(relay);
    }
    await client.connect();


    const filter = new Filter().kind(new Kind(31990)).customTags(SingleLetterTag.lowercase(Alphabet.K), ["5910"])
    let evts = await client.fetchEvents(filter, Duration.fromSecs(5))

    for (let evt of evts.toVec()) {

        let pubkey = evt.author.toHex()
        let content_json = JSON.parse(evt.content)
        let tools = content_json.tools
        for (let tool of tools) {
            if (tool.inputSchema === undefined || tool.inputSchema.properties === undefined) {
                continue
            }

            //TODO convert inputSchema.properties? to zod schema or to any other way so it works.
            let inputSchema = {symbol: z.string()}

            server.tool(tool.name, tool.description, inputSchema,
                async (args) => {
                    return await handle_dvm_request(args, tool.name, pubkey)
                });
        }
    }

}

async function handle_dvm_request(args, name, pubkey) {
    await loadWasmSync();


    // Generate new random keys
    let keys = Keys.parse(pkey)

    let request_kind = new Kind(5910);
    let response_kind = new Kind(6910);

    let payload = {
        "name": name,
        "parameters": args
    }
    let signer = NostrSigner.keys(keys);
    let client = new Client(signer);
      for (const relay of relays) {
        await client.addRelay(relay);
    }
    await client.connect();
      var relays_list = merge(["relays"], relays)

    let tags = [
        Tag.parse(["c", "execute-tool"]),
        Tag.parse(["p", pubkey]),
        Tag.parse(["output", "application/json"]),
        Tag.parse(relays_list)
    ]

    let event =  new EventBuilder(request_kind, JSON.stringify(payload)).tags(tags)
    //send our request to the DVM
    await client.sendEventBuilder(event);


    let abortable
    const filter = new Filter().pubkey(keys.publicKey).kind(response_kind).limit(0); // Limit set to 0 to get only new events! Timestamp.now() CAN'T be used for gift wrap since the timestamps are tweaked!
    //listen for a response
    await client.subscribe(filter);


    var result = ""
    const handle = {
        handleEvent: async (relayUrl, subscriptionId, event) => {
            //TODO More logic / safety checks
            result = JSON.parse(event.content).content[0].text
            abortable.abort()
            return true
        },

        handleMsg: async (relayUrl, message) => {
            //console.log("Received message from", relayUrl, message.asJson());
        }

    };

         abortable = client.handleNotifications(handle)

        //Wait till we have our response
        await new Promise((resolve) => {
            const checkAbort = setInterval(() => {
                if (abortable.is_aborted()) {
                    clearInterval(checkAbort);
                    resolve();
                }
            }, 100);
        });
        // Then return the final result.
        return {
            content: [{ type: "text", text: `${result}` }]
        };
}

//Connection
// Connect stdio
const transport = new StdioServerTransport();
await server.connect(transport);
