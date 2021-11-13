from routingalgos.base import Routing
from secrets import randbelow, choice
import math
from queue import PriorityQueue
import nested_dict as nd
from math import inf


class RandomHopsRouting(Routing):

    # Initialize routing algorithm
    def __init__(self, baseRouting, filterSources) -> None:
        super().__init__()
        self.__baseRouting = baseRouting
        self.__filterSources = filterSources

    # human readable name for this routing algorithm
    def name(self):
        return "Random Hops + " + self.__baseRouting.name()

    # Returns tech used by base routing
    def tech(self):
        return self.__baseRouting.tech()

    # cost function, uses same cost function as base routing algorithm
    def cost_function(self, G, amount, u, v):
        return self.__baseRouting.cost_function(G, amount, u, v)

    # cost function for first hop, uses same cost function as base routing algorithm
    def cost_function_no_fees(self, G, amount, u, v):
        return self.__baseRouting.cost_function_no_fees(G, amount, u, v)

    # construct route
    def routePath(self, G, u, v, amt, payment_source=True, target_delay=0):

        # first construct original route
        route = self.__baseRouting.routePath(G, u, v, amt)
        path = route["path"]
        amount = route["amount"]

        # add random hops
        # TODO old amount? check correctness
        modified, delay, amount = self.add_random_hops(G,path, amt)

        return {"path": modified, "delay": delay, "amount": amount, "dist": 0}


    # The function takes a path and adds a minimum of 2 random hops to it.
    def add_random_hops(self, G, path, amount):
        if len(path) == 2:
            # If there is a direct channel do not add random hops
            return path, G.edges[path[0], path[1]]["Delay"], amount
        elif len(path) < 2:
            # The path is either not found or incorrect
            return [], -1, -1

        # The delay is calculated after having determined the path
        delay = 0
        # Reversing the path to start at the last node for simplicity
        path.reverse()
        modified = []
        # Adds a minimum of 2 hops
        hops_to_add = randbelow(len(path) - 3) + 2 if len(path) > 3 else 2
        hops_added = 0

        # The length of the path is capped at 20
        if hops_to_add + len(path) > 20:
            hops_to_add = 20 - len(path)

        for i in range(len(path) - 1):
            possible_hops = []
            for [hop, _] in G.in_edges(path[i]):
                if (hop != path[i + 1]  # Exclude current edge
                        and G.has_edge(hop, path[i + 1])
                        and len(set(modified + [hop])) == len(modified + [hop])
                        # Check for valid hop with no loops
                        and len(set(path + [hop])) == len(path + [hop])
                        and G.edges[hop, path[i]]["Balance"] + G.edges[path[i], hop]["Balance"] >= amount
                        # Check for enough capacity
                            and G.edges[hop, path[i + 1]]["Balance"] + G.edges[path[i + 1], hop]["Balance"] >= amount
                        ):
                    possible_hops.append(hop)

            modified.append(path[i])
            if len(modified) > 1:
                a = len(modified) - 1
                b = len(modified) - 2
                amount = amount + G.edges[modified[a], modified[b]]["BaseFee"] + (
                    amount * G.edges[modified[a], modified[b]]["FeeRate"])

            if len(possible_hops) > 0 and hops_added < hops_to_add:
                modified.append(choice(possible_hops))
                hops_added += 1
                a = len(modified) - 1
                b = len(modified) - 2
                amount = amount + G.edges[modified[a], modified[b]]["BaseFee"] + (
                    amount * G.edges[modified[a], modified[b]]["FeeRate"])
        modified.append(path[len(path) - 1])

        for i in range(len(modified) - 1):
            delay = delay + G.edges[modified[i + 1], modified[i]]["Delay"]

        # The path was reversed so the return value has to be reversed again
        return modified[::-1], delay, amount


    # Check whether suboptimal could have been generated by the function add_random_hops and passing optimal to it
    def is_not_possible_mod(self, suboptimal, optimal):
        sub = set(suboptimal)
        opti = set(optimal)
        if len(opti - sub) > 0:
            # Optimal set contains more nodes than the suboptimal
            return True

        i = 1
        j = 1
        while i < len(optimal) and j < len(suboptimal):
            # Check if there's a possible added hop
            if suboptimal[j] == optimal[i]:
                i += 1
                j += 1
            else:
                if j + 1 >= len(suboptimal):
                    # There are no more hops left so the paths don't match
                    return True
                elif suboptimal[j + 1] != optimal[i]:
                    # sub[j] is not a hop because sub[j + 1] does not go back to the optimal path at opti[i]
                    return True
                else:
                    i += 1
                    j += 2

        # If there are no more hops to consider in suboptimal then it could be a possible modification
        return j < len(suboptimal)

    def adversarial_attack(self, G, adversary, delay, amount, pre, next, attack_position = -1):
        T = nd.nested_dict()
        flag1 = True
        level = 0
        T[0]["nodes"] = [next]
        T[0]["delays"] = [delay]
        T[0]["previous"] = [-1]
        T[0]["visited"] = [[pre, adversary, next]]
        T[0]["amounts"] = [amount]
        flag = True

        while(flag):
            level += 1
            if(level == 4):
                flag1 = False
                break
            t1 = T[level - 1]["nodes"]
            d1 = T[level - 1]["delays"]
            v1 = T[level - 1]["visited"]
            a1 = T[level - 1]["amounts"]
            t2 = []
            d2 = []
            p2 = []
            v2 = [[]]
            a2 = []
            for i in range(0, len(t1)):
                u = t1[i]
                for [u, v] in G.out_edges(u):
                    if(v != pre and v != adversary and v != next and v not in v1[i] and (d1[i] - G.edges[u, v]["Delay"]) >= 0 and (G.edges[u, v]["Balance"]+G.edges[v, u]["Balance"]) >= ((a1[i] - G.edges[u, v]["BaseFee"]) / (1 + G.edges[u, v]["FeeRate"]))):
                        t2.append(v)
                        d2.append(d1[i] - G.edges[u, v]["Delay"])
                        p2.append(i)
                        v2.append(v1[i]+[v])
                        a2.append(((a1[i] - G.edges[u, v]["BaseFee"]
                                    ) / (1 + G.edges[u, v]["FeeRate"])))
            T[level]["nodes"] = t2
            T[level]["delays"] = d2
            T[level]["previous"] = p2
            T[level]["visited"] = v2
            T[level]["amounts"] = a2
            if(len(t2) == 0):
                flag = False
        level = level - 1

        if (self.__filterSources):
            return self.phase2_filtered_sources(G, T, pre, adversary, level), flag1
        else:
            return self.phase2_all_sources(G, T, pre, adversary, next, level), flag1

    # Second phase all nodes are checked to be a possible source for each destination
    # (second attack strategy)
    def phase2_all_sources(self,G, T, pre, adversary, next, level):
        anon_sets = {}
        while(level >= 0):
            t = T[level]["nodes"]
            d = T[level]["delays"]
            p = T[level]["previous"]
            a = T[level]["amounts"]
            v = T[level]["visited"]
            for i in range(0, len(t)):
                if(d[i] == 0):
                    possible_destination = T[level]["nodes"][i]
                    amount = T[level]["amounts"][i]
                    sources = set()
                    # For all possible sources
                    for source in G.nodes():
                        if source == possible_destination or source == adversary:
                            continue
                        c_route = self.__baseRouting.routePath(G, source, possible_destination, amount)
                        c_path = c_route["path"]
                        # If adversary, pre and next are on the path add to anon_set
                        if adversary in c_path and pre in c_path and next in c_path:
                            sources.add(source)
                        else:
                            # check if adversary is connected to two subsequent nodes on the path
                            for j in range(len(c_path) - 1):
                                for [_, v] in G.out_edges(c_path[j]):
                                    if v == adversary and c_path[j] == pre and c_path[j + 1] == next and G.has_edge(c_path[j], v) and G.has_edge(v, c_path[j + 1]):
                                        sources.add(source)
                    if len(sources) > 0:
                        anon_sets[possible_destination] = list(sources)
            level = level - 1
        return anon_sets
    
    # Second phase a second search discards optimal paths if they can't be generated by the modification
    # (first attack strategy)
    def phase2_filtered_sources(self,G, T, pre, adversary, level):
        anon_sets = {}
        while(level>=0):
            t = T[level]["nodes"]
            d = T[level]["delays"]
            p = T[level]["previous"]
            a = T[level]["amounts"]
            v = T[level]["visited"]
            for i in range(0, len(t)):
                if(d[i] == 0):
                    path = []
                    level1 = level
                    path.append(T[level1]["nodes"][i])
                    loc = T[level1]["previous"][i]
                    while (level1 > 0):
                        level1 = level1 - 1
                        path.append(T[level1]["nodes"][loc])
                        loc = T[level1]["previous"][loc]
                    path.reverse()
                    path = [pre,adversary]+path
                    if (len(path) == len(set(path))):
                        amt = a[i]
                        dl = d[i]
                        pot = path[len(path) - 1]
                        sources = self.deanonymize(G,pot,path,amt, dl)
                        if sources != None and len(sources) > 0:
                            anon_sets[pot] = list(sources)
            level = level - 1
        return anon_sets

    def deanonymize(self, G, target, path, amt, dl):
        pq = PriorityQueue()
        delays = {}
        costs = {}
        paths = nd.nested_dict()
        paths1 = nd.nested_dict()
        dists = {}
        visited = set()
        previous = {}
        done = {}
        prob = {}
        sources = []
        pre = path[0]
        adv = path[1]
        nxt = path[2]
        for node in G.nodes():
            previous[node] = -1
            delays[node] = -1
            costs[node] = inf
            paths[node] = []
            dists[node] = inf
            done[node] = 0
            paths1[node] = []
            prob[node] = 1
        dists[target] = 0
        paths[target] = [target]
        costs[target] = amt
        delays[target] = dl
        pq.put((dists[target], target))
        flag1 = 0
        flag2 = 0
        while(0 != pq.qsize()):
            curr_cost, curr = pq.get()
            if curr_cost > dists[curr]:
                continue
            visited.add(curr)
            for [v, curr] in G.in_edges(curr):
                if (G.edges[v, curr]["Balance"] + G.edges[curr, v]["Balance"] >= costs[curr]) and v not in visited:
                    if done[v] == 0:
                        paths1[v] = [v]+paths[curr]
                        done[v] = 1
                    cost = dists[curr] + self.cost_function(G, costs[curr], curr, v)
                    if cost < dists[v]:
                        paths[v] = [v]+paths[curr]
                        dists[v] = cost
                        delays[v] = delays[curr] + G.edges[v, curr]["Delay"]
                        costs[v] = costs[curr] + G.edges[v, curr]["BaseFee"] + \
                            costs[curr] * G.edges[v, curr]["FeeRate"]
                        pq.put((dists[v], v))
            if(curr in path[1:]):
                ind = path.index(curr)
                """
                if(paths[curr]!=path[ind:]):
                    return None
                """
                # Check if the current optimal path could be trasformed into the suboptimal path considered if random hops were added.
                if self.is_not_possible_mod(path[ind:], paths[curr]):
                    return None
                # """
                if curr == adv:
                    flag1 = 1
            """
            if(curr == pre):
                if paths[pre] != path:
                    return [pre]
                else:
                    sources.append(pre)
                flag2 = 1
            """
            # Due to the fact that suboptimal path are now being used this assumption has been removed to avoid large amounts of false positives.
            # Also bugs where the sender chooses a suboptimal path because of low forward balance while having a faster path with a large capacity channel are avoided.
            if (curr == pre):
                sources.append(pre)
                flag2 = 1
            # """
            if flag1 == 1 and flag2 == 1:
                if pre in paths[curr]:
                    for [v, curr] in G.in_edges(curr):
                        if v not in paths[curr]:
                            sources.append(v)
        sources = set(sources)
        return sources
