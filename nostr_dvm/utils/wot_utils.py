import asyncio
import os
from itertools import islice

import nostr_sdk


import networkx as nx

# General
import json
import datetime
import time
import numpy as np
import random
from scipy.sparse import lil_matrix, csr_matrix, isspmatrix_csr


from nostr_sdk import Options, Keys, NostrSigner, NostrDatabase, ClientBuilder, SecretKey, Kind, PublicKey, Filter

from nostr_dvm.utils.definitions import relay_timeout
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nostr_utils import check_and_set_private_key


async def get_following(pks, max_time_request=10, newer_than_time=None):
    '''
        OUTPUT: following; a networkx graph
        > each node has associated the timestamp of the latest retrivable kind3 event

        > it's possible to limit the search to events newer_than_time

        NOTE: do not get_following of more than 1000 pks;
        instead, divide the request into batches of smaller size (500 recommended)
    '''

    # handling the case of a single key passed
    if type(pks) == str:
        pks = [pks]

    # transforming into PubKey object type
    list_pk = [nostr_sdk.PublicKey.parse(pk) for pk in pks]

    # newer_than_time provided? If so, it only fetch events that are newer
    if newer_than_time is None:
        filter = nostr_sdk.Filter().authors(list_pk).kind(Kind(3))

    else:
        newer_than_time = round(newer_than_time)
        ts = nostr_sdk.Timestamp().from_secs(newer_than_time)
        filter = nostr_sdk.Filter().authors(list_pk).kind(3).since(ts)

    # fetching events
    opts = (Options().wait_for_send(False).send_timeout(datetime.timedelta(seconds=5)))
    keys = Keys.parse(check_and_set_private_key("test_client"))
    signer = NostrSigner.keys(keys)
    cli = ClientBuilder().signer(signer).opts(opts).build()

    for relay in DVMConfig.RECONCILE_DB_RELAY_LIST:
        await cli.add_relay(relay)

    await cli.connect()

    events = await cli.get_events_of([filter], relay_timeout)

    # initializing the graph structure
    following = nx.DiGraph()
    following.add_nodes_from(pks)

    if events == []:
        return following

    for event in events:

        author = event.author().to_hex()

        # events are returned based on the timestamp,
        # the first event for each pubkey is the most recent = the one we should use

        if event.verify() and author in following.nodes() and 'timestamp' not in following.nodes[author]:
            # updating the nodes and edges
            nodes = event.public_keys()

            # converting to hex and removing self-following
            nodes = [pk.to_hex() for pk in nodes if pk.to_hex() != author]

            following.update(edges=[(author, pk) for pk in nodes], nodes=nodes)

            # updating the timestamp
            tp = event.created_at().as_secs()
            following.nodes[author]['timestamp'] = tp

    return following


async def build_network_from(seed_pks, depth=2, max_batch=500, max_time_request=10):
    if not seed_pks:
        print('Error: seed_pks cannot be empty')
        return

    if depth < 1:
        print('Error: depth cannot be lower than 1')
        return

        # handling the case of a single key being passed
    if type(seed_pks) == str:
        seed_pks = [seed_pks]

    print('Step 1: fetching kind 3 events from relays & pre-processing')

    tic = time.time()

    # initialize the index_map
    index_map = {pk: i for i, pk in enumerate(seed_pks)}

    # initialize the graph
    seed_graph = nx.DiGraph()
    seed_graph.add_nodes_from(index_map.values())

    # build the network internal function
    index_map, network_graph = await _build_network_from(index_map, seed_graph, set(), depth, max_batch,
                                                         max_time_request)

    toc = time.time()

    print('\nFinished in ' + str(toc - tic))

    return index_map, network_graph


async def _build_network_from(index_map, network_graph, visited_pk=None, depth=2, max_batch=500, max_time_request=10):
    '''
        OUTPUTS:

        1. index_map = {pk0 : 0, pk1 : 1, ... }
        > an index that translates pub keys in hex format into nodes in the graph

        2. network_graph; a networkx directed graph about who follows who
        > each node has associated the timestamp of the latest retrivable kind3 event
        > if the node is a leaf or doesn't follow anyone, it has no attribute 'timestamp'

    '''

    # pks to be visited next, splitted in batches
    if visited_pk is None:
        visited_pk = set()
    to_visit_pk = split_set(index_map.keys() - visited_pk, max_batch)

    for pks in to_visit_pk:
        # getting the followings as a graph
        following = await get_following(pks, max_time_request)

        # update the visited_pk
        visited_pk.update(pks)

        # add the new pub_keys to the index_map
        index_map = _extend_index_map(index_map, following)

        # re-lable nodes using the index_map to use storage more efficiently
        nx.relabel_nodes(following, index_map, copy=False)

        # extend the network graph
        network_graph.update(following)

        print('current network: ' + str(len(index_map)) + ' npubs', end='\r')

    if depth == 1:
        return index_map, network_graph

    else:

        # recursive call
        index_map, network_graph = await _build_network_from(index_map, network_graph, visited_pk, depth - 1, max_batch,
                                                             max_time_request)

    print('current network: ' + str(len(network_graph.nodes())) + ' npubs', end='\r')

    return index_map, network_graph


def _extend_index_map(index_map, following):
    '''
        index_map = { pk0: 0, pk1:1, ...}
    '''

    # getting all new pubkeys
    new_pk = following.nodes() - index_map.keys()

    # start assigning new indices from the next available index
    start_index = len(index_map)

    # Update the index_map with new keys and their assigned indices
    for i, pk in enumerate(new_pk, start=start_index):
        index_map[pk] = i

    return index_map


def split_set(my_set, max_batch):
    my_list = list(my_set)
    return [set(my_list[x: x + max_batch]) for x in range(0, len(my_set), max_batch)]


def save_network(index_map, network_graph, name=None):
    if name == None:
        # adding unix time to file name to avoid replacing an existing file
        name = str(round(time.time()))
    #filename = os.path.join('/cache/', 'index_map_' + name + '.json')
    filename = 'index_map_' + name + '.json'
    # saving the index_map as a json file
    with open(filename, 'w') as f:
        json.dump(index_map, f, indent=4)

    # Convert to node-link format suitable for JSON
    data = nx.node_link_data(network_graph)

    # saving the network_graph as a json file
    #filename = os.path.join('/cache/', 'network_graph_' + name + '.json')
    filename = 'network_graph_' + name + '.json'
    with open(filename, 'w') as f:
        json.dump(data, f)

    print(' > index_map_' + name + '.json')
    print(' > network_graph_' + name + '.json')

    return


def load_network(name):
    if type(name) != str:
        name = str(name)

    # loading the index_map
    with open('index_map_' + name + '.json', 'r') as f:
        index_map = json.load(f)

    # loading the JSON for the graph
    with open('network_graph_' + name + '.json', 'r') as f:
        data = json.load(f)

    # Convert JSON back to graph
    network_graph = nx.node_link_graph(data)

    return index_map, network_graph


def get_mc_pagerank(G, R, nodelist=None, alpha=0.85):
    '''
        Monte-Carlo complete path stopping at dandling nodes

        INPUTS
        ------
        G: graph
            A directed Networkx graph. This function cannot work on directed graphs.

        R: int
            The number of random walks to be performed per node

        nodelist: list, optional
            the list of nodes in G networkx graph.
            It is used to order the nodes in a specified way

        alpha: float, optional
            It is the dampening factor of Pagerank. default value is 0.85

        OUTPUTS
        -------
        walk_visited_count: CSR matrix
            a Compressed Sparse Row (CSR) matrix; element (i,j) is equal to
            the number of times v_j has been visited by a random walk started from v_i

        mc_pagerank: dict
            The dictionary {node: pg} of the pagerank value for each node in G

        References
        ----------
        [1] K.Avrachenkov, N. Litvak, D. Nemirovsky, N. Osipova
        "Monte Carlo methods in PageRank computation: When one iteration is sufficient"
        https://www-sop.inria.fr/members/Konstantin.Avratchenkov/pubs/mc.pdf
    '''

    # validate all the inputs and initialize variables
    N, nodelist, inverse_nodelist = _validate_inputs_and_init_mc(G, R, nodelist, alpha)

    # initialize walk_visited_count as a sparse LIL matrix
    walk_visited_count = lil_matrix((N, N), dtype='int')

    progress_count = 0

    # perform R random walks for each node
    for node in nodelist:

        # print progress every 200 nodes
        progress_count += 1
        if progress_count % 200 == 0:
            print('progress = {:.2f}%'.format(100 * progress_count / N), end='\r')

        for _ in range(R):

            node_pos = inverse_nodelist[node]
            walk_visited_count[node_pos, node_pos] += 1

            current_node = node

            while random.uniform(0, 1) < alpha:

                successors = list(G.successors(current_node))
                if not successors:
                    break

                current_node = random.choice(successors)
                current_node_pos = inverse_nodelist[current_node]

                # add current node to the walk_visited_count
                walk_visited_count[node_pos, current_node_pos] += 1

    # convert lil_matrix to csr_matrix for efficient storage and access
    walk_visited_count = walk_visited_count.tocsr()

    # sum all visits for each node into a numpy array
    total_visited_count = np.array(walk_visited_count.sum(axis=0)).flatten()

    # reciprocal of the number of total visits
    one_over_s = 1 / sum(total_visited_count)

    mc_pagerank = {nodelist[j]: total_visited_count[j] * one_over_s for j in range(N)}

    print('progress = 100%       ', end='\r')
    print('\nTotal walks performed: ', N * R)

    return walk_visited_count, mc_pagerank


def _validate_inputs_and_init_mc(G, R, nodelist, alpha):
    '''
    This function validate the inputs and initialize the following variables:

    N: int
        the number of nodes in G Networkx graph

    nodelist : list
        the list of nodes in G Networkx graph

    inverse_nodelist : dict
       a dictionary that maps each node in G to its position in nodelist
    '''

    N = len(G)
    if N == 0:
        raise ValueError("Graph G is empty")

    if not isinstance(R, int) or R <= 0:
        raise ValueError("R must be a positive integer")

    if not isinstance(alpha, float) or not (0 < alpha < 1):
        raise ValueError("alpha must be a float between 0 and 1")

    if nodelist is not None and set(nodelist) != set(G.nodes()):
        raise ValueError("nodelist does not match the nodes in G")

    elif nodelist is None:
        nodelist = list(G.nodes())

    # compute the inverse map of nodelist
    inverse_nodelist = {nodelist[j]: j for j in range(N)}

    return N, nodelist, inverse_nodelist


def get_subrank(S, G, walk_visited_count, nodelist, alpha=0.85):
    '''
        Subrank algorithm (stopping at dandling nodes);
        it aims to approximate the Pagerank over S subgraph of G

        INPUTS
        ------
        S: graph
            A directed Networkx graph, induced subgraph of G

        G: graph
            A directed Networkx graph. This function cannot work on directed graphs.

        walk_visited_count: CSR matrix
            a Compressed Sparse Row (CSR) matrix; element (i,j) is equal to
            the number of times v_j has been visited by a random walk started from v_i

        nodelist: list, optional
            the list of nodes in G Networkx graph. It is used to decode walk_visited_count

       alpha: float, optional
            It is the dampening factor of Pagerank. default value is 0.85

        OUTPUTS
        -------
        subrank: dict
            The dictionary {node: pg} of the pagerank value for each node in S

        References
        ----------
        [1] Pippellia,
        "Pagerank on subgraphs—efficient Monte-Carlo estimation"
        https://pippellia.com/pippellia/Social+Graph/Pagerank+on+subgraphs%E2%80%94efficient+Monte-Carlo+estimation
    '''

    # validate inputs and initialize variables
    N, S_nodes, G_nodes, inverse_nodelist = _validate_inputs_and_init(S, G, walk_visited_count, nodelist, alpha)

    # compute visited count from walks that started from S
    visited_count_from_S = _get_visited_count_from_S(N, S_nodes, walk_visited_count, nodelist, inverse_nodelist)

    # compute positive and negative walks to do
    positive_walks, negative_walks = _get_walks_to_do(S_nodes, G_nodes, S, G, visited_count_from_S, alpha)

    print(f'walks performed = {sum(positive_walks.values()) + sum(negative_walks.values())}')

    # perform the walks and get the visited counts
    positive_count = _perform_walks(S_nodes, S, positive_walks, alpha)
    negative_count = _perform_walks(S_nodes, S, negative_walks, alpha)

    # add the effects of the random walk to the count of G
    new_visited_count = {node: visited_count_from_S[node] + positive_count[node] - negative_count[node]
                         for node in S_nodes}

    # compute the number of total visits
    total_visits = sum(new_visited_count.values())

    # compute the subrank
    subrank = {node: visits / total_visits
               for node, visits in new_visited_count.items()}

    return subrank


def _validate_inputs_and_init(S, G, walk_visited_count, nodelist, alpha):
    '''
    This function validate the inputs and initialize the following variables:

    N: int
        the number of nodes in G Networkx graph

    S_nodes: set
        the set of nodes that belongs to S

    G_nodes: set
        the set of nodes that belongs to G

    inverse_nodelist : dict
        a dictionary that maps each node in G to its position in nodelist

    Note: S being a subgraph of G is NOT checked because it's computationally expensive.
    '''

    if len(S) == 0:
        raise ValueError("graph S is empty")

    N = len(G)
    if N == 0:
        raise ValueError("graph G is empty")

    if not isinstance(alpha, float) or not (0 < alpha < 1):
        raise ValueError("alpha must be a float between 0 and 1")

    if not isspmatrix_csr(walk_visited_count) or walk_visited_count.shape != (N, N):
        raise ValueError(f"walk_visited_count must be a {(N, N)} CSR matrix")

    S_nodes = set(S.nodes())
    G_nodes = set(G.nodes())

    if not nodelist or set(nodelist) != set(G_nodes):
        raise ValueError("nodelist does not match the nodes in G")

    # compute the inverse map of nodelist
    inverse_nodelist = {nodelist[j]: j for j in range(N)}

    return N, S_nodes, G_nodes, inverse_nodelist


def _get_visited_count_from_S(N, S_nodes, walk_visited_count, nodelist, inverse_nodelist):
    '''
    This function extracts the number of visits that come from walks that started from S
    '''

    # getting the indices of nodes in S
    S_indices = [inverse_nodelist[node] for node in S_nodes]

    # Extract the rows
    S_matrix = walk_visited_count[S_indices, :]

    # Sum the rows
    visited_count_from_S = np.array(S_matrix.sum(axis=0)).flatten()

    # convert to a dictionary
    visited_count_from_S = {nodelist[j]: visited_count_from_S[j] for j in range(N)}

    return visited_count_from_S


def _get_walks_to_do(S_nodes, G_nodes, S, G, visited_count_from_S, alpha):
    '''
    This function calculates the positive and negative walks to be done for each node.
    It is a necessary step to take into account the different structure of S
    with respect to that of G.
    '''

    # compute nodes in G-S
    external_nodes = G_nodes - S_nodes

    # compute nodes in S that point to G-S
    nodes_that_point_externally = {u for u, v in nx.edge_boundary(G, S_nodes, external_nodes)}

    walks_to_do = {node: 0 for node in S_nodes}

    # add positive random walks to walks_to_do
    for node in nodes_that_point_externally:

        successors = set(G.successors(node)) & S_nodes

        if successors:

            # compute estimate visits
            visited_count = visited_count_from_S[node]
            degree_S = S.out_degree(node)
            degree_G = G.out_degree(node)
            estimate_visits = alpha * visited_count * (1 / degree_S - 1 / degree_G)

            for succ in successors:
                walks_to_do[succ] += estimate_visits

    # subtract number of negative random walks
    for node in external_nodes:

        successors = set(G.successors(node)) & S_nodes

        if successors:

            # compute estimate visits
            visited_count = visited_count_from_S[node]
            degree = G.out_degree(node)
            estimate_visits = alpha * visited_count / degree

            for succ in successors:
                walks_to_do[succ] -= estimate_visits

    # split the walks to do into positive and negative
    positive_walks_to_do = {node: round(value) for node, value in walks_to_do.items() if value > 0}
    negative_walks_to_do = {node: round(-value) for node, value in walks_to_do.items() if value < 0}

    return positive_walks_to_do, negative_walks_to_do


def _perform_walks(S_nodes, S, walks_to_do, alpha):
    '''
    This function performs a certain number of random walks on S for each node;
    It then returns the visited count for each node in S.
    '''

    # initializing the visited count
    visited_count = {node: 0 for node in S_nodes}

    for starting_node in walks_to_do.keys():

        num = walks_to_do[starting_node]

        # performing num random walks
        for _ in range(num):

            current_node = starting_node
            visited_count[current_node] += 1

            # performing one random walk
            while random.uniform(0, 1) < alpha:

                successors = list(S.successors(current_node))

                if not successors:
                    break

                current_node = random.choice(successors)

                # updating the visited count
                visited_count[current_node] += 1

    return visited_count
async def get_metadata(npub):
    name = ""
    nip05 = ""
    lud16 = ""
    try:
        pk = PublicKey.parse(npub)
    except:
        return "", "", ""
    opts = (Options().wait_for_send(False).send_timeout(datetime.timedelta(seconds=5)))
    keys = Keys.parse(check_and_set_private_key("test_client"))
    signer = NostrSigner.keys(keys)
    client = ClientBuilder().signer(signer).opts(opts).build()
    await client.add_relay("wss://relay.damus.io")
    await client.add_relay("wss://relay.primal.net")
    await client.add_relay("wss://purplepag.es")
    await client.connect()

    profile_filter = Filter().kind(Kind(0)).author(pk).limit(1)

    events = await client.get_events_of([profile_filter], relay_timeout)
    if len(events) > 0:
        try:
            profile = json.loads(events[0].content())
            if profile.get("name"):
                name = profile['name']
            if profile.get("nip05"):
                nip05 = profile['nip05']
            if profile.get("lud16"):
                lud16 = profile['lud16']
        except Exception as e:
            print(e)
    await client.shutdown()
    return name, nip05, lud16


async def print_results(graph, index_map, show_results_num, getmetadata=True):
    for item in islice(graph, show_results_num):
        key = next((PublicKey.parse(pubkey).to_bech32() for pubkey, id in index_map.items() if id == item), None)
        name= ""
        if getmetadata:
            name, nip05, lud16 = await get_metadata(key)
        print(name + "(" + key + ") " + str(graph[item]))

async def convert_index_to_hex(graph, index_map, show_results_num):
    result = {}
    for item in islice(graph, show_results_num):
        key = next((pubkey for pubkey, id in index_map.items() if id == item), None)
        result[key] = graph[item]

    return result


def test():
    # WARNING, DEPENDING ON DEPTH THIS TAKES LONG
    user = '3bf0c63fcb93463407af97a5e5ee64fa883d107ef9e558472c4eb9aaaefa459d'
    index_map, network_graph = asyncio.run(build_network_from(user, depth=2, max_batch=500, max_time_request=10))
    save_network(index_map, network_graph, user)
