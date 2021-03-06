import numpy as np
import random
import sys
rnd = np.random


class RCCRA:

    def __init__(self, net_obj, req_obj, srv_obj, REQUESTED_SERVICES, REQUESTS_ENTRY_NODES):
        self.net_obj = net_obj
        self.req_obj = req_obj
        self.srv_obj = srv_obj
        self.REQUESTED_SERVICES = REQUESTED_SERVICES
        self.REQUESTS_ENTRY_NODES = REQUESTS_ENTRY_NODES
        self.EPSILON = 0.001

    def solve(self):
        z = np.zeros((self.srv_obj.NUM_SERVICES, self.net_obj.NUM_NODES))
        g = np.zeros((self.req_obj.NUM_REQUESTS, self.net_obj.NUM_NODES))
        rho = np.zeros((self.req_obj.NUM_REQUESTS, len(self.net_obj.PRIORITIES)))
        req_path = np.zeros((self.req_obj.NUM_REQUESTS, len(self.net_obj.PATHS), len(self.net_obj.PRIORITIES)))
        rpl_path = np.zeros((self.req_obj.NUM_REQUESTS, len(self.net_obj.PATHS), len(self.net_obj.PRIORITIES)))

        DC_CAPACITIES = self.net_obj.DC_CAPACITIES
        LINK_BWS = self.net_obj.LINK_BWS
        LINK_BURSTS = np.array([self.net_obj.BURST_SIZE_LIMIT_PER_PRIORITY for l in self.net_obj.LINKS])
        # sorted_requests = self.sort_requests()
        # sorted_requests = np.argsort(self.req_obj.DELAY_REQUIREMENTS)
        resources = {}
        costs = {}
        cost_details = {}

        for r in self.req_obj.REQUESTS:
            resources_per_req = []
            costs_per_req = []
            cost_details_per_req = []

            ACTION_SEED = int(random.randrange(sys.maxsize) / (10 ** 15))  # 4
            rnd.seed(ACTION_SEED)
            v = rnd.choice(self.net_obj.NODES)
            z[self.REQUESTED_SERVICES[r]][v] = 1
            g[r][v] = 1

            ACTION_SEED = int(random.randrange(sys.maxsize) / (10 ** 15))  # 4
            rnd.seed(ACTION_SEED)
            k = rnd.choice(self.net_obj.PRIORITIES)
            rho[r][k] = 1

            p1 = -1
            ACTION_SEED = int(random.randrange(sys.maxsize) / (10 ** 15))  # 4
            rnd.seed(ACTION_SEED)
            potentialReqPaths = np.intersect1d(self.net_obj.PATHS_PER_HEAD[self.REQUESTS_ENTRY_NODES[r]], self.net_obj.PATHS_PER_TAIL[v])
            if len(potentialReqPaths) > 0:
                p1 = rnd.choice(potentialReqPaths)
                req_path[r][p1][k] = 1

            p2 = -1
            ACTION_SEED = int(random.randrange(sys.maxsize) / (10 ** 15))  # 4\
            rnd.seed(ACTION_SEED)
            potentialRplPaths = np.intersect1d(self.net_obj.PATHS_PER_HEAD[v], self.net_obj.PATHS_PER_TAIL[self.REQUESTS_ENTRY_NODES[r]])
            if len(potentialRplPaths) > 0:
                p2 = rnd.choice(potentialRplPaths)
                rpl_path[r][p2][k] = 1

            flag = True
            for l1 in np.where(self.net_obj.LINKS_PATHS_MATRIX[:, p1] == 1)[0]:
                if self.req_obj.BW_REQUIREMENTS[r] > LINK_BWS[l1] or self.req_obj.BURST_SIZES[r] > LINK_BURSTS[l1, k]:
                    flag = False
            for l2 in np.where(self.net_obj.LINKS_PATHS_MATRIX[:, p2] == 1)[0]:
                if self.req_obj.BW_REQUIREMENTS[r] > LINK_BWS[l2] or self.req_obj.BURST_SIZES[r] > LINK_BURSTS[l2][k]:
                    flag = False

            if flag:
                d = 0
                c = 0
                for l1 in np.where(self.net_obj.LINKS_PATHS_MATRIX[:, p1] == 1)[0]:
                    d += self.net_obj.LINK_DELAYS[l1][k]
                for l2 in np.where(self.net_obj.LINKS_PATHS_MATRIX[:, p2] == 1)[0]:
                    d += self.net_obj.LINK_DELAYS[l2][k]
                d += self.net_obj.PACKET_SIZE / (self.net_obj.DC_CAPACITIES[v] + self.EPSILON)
                if d <= self.req_obj.DELAY_REQUIREMENTS[r]:
                    c += self.net_obj.DC_COSTS[v]  # * self.req_obj.CAPACITY_REQUIREMENTS[r]
                    for l1 in np.where(self.net_obj.LINKS_PATHS_MATRIX[:, p1] == 1)[0]:
                        c += self.net_obj.LINK_COSTS[l1]  # * self.req_obj.BW_REQUIREMENTS[r]
                        # req_paths_cost += self.net_obj.LINK_COSTS[l1]
                    for l2 in np.where(self.net_obj.LINKS_PATHS_MATRIX[:, p2] == 1)[0]:
                        c += self.net_obj.LINK_COSTS[l2]  # * self.req_obj.BW_REQUIREMENTS[r]
                        # rpl_paths_cost += self.net_obj.LINK_COSTS[l1]
                    resources_per_req.append([v, k, p1, p2])
                    costs_per_req.append(c)
                    # cost_details_per_req.append([req_paths_cost, rpl_paths_cost])

            if len(costs_per_req) > 0:
                min_index = np.array(costs_per_req).argmin()
                resources[r] = resources_per_req[min_index]
                costs[r] = costs_per_req[min_index]

                DC_CAPACITIES[resources[r][0]] = DC_CAPACITIES[resources[r][0]] - self.req_obj.CAPACITY_REQUIREMENTS[r]
                for l1 in np.where(self.net_obj.LINKS_PATHS_MATRIX[:, resources[r][2]] == 1)[0]:
                    LINK_BWS[l1] = LINK_BWS[l1] - self.req_obj.BW_REQUIREMENTS[r]
                    LINK_BURSTS[l1, resources[r][1]] = LINK_BURSTS[l1, resources[r][1]] - self.req_obj.BURST_SIZES[r]
                for l2 in np.where(self.net_obj.LINKS_PATHS_MATRIX[:, resources[r][3]] == 1)[0]:
                    LINK_BWS[l2] = LINK_BWS[l2] - self.req_obj.BW_REQUIREMENTS[r]
                    LINK_BURSTS[l2, resources[r][1]] = LINK_BURSTS[l2, resources[r][1]] - self.req_obj.BURST_SIZES[r]
                # cost_details[r] = cost_details_per_req[min_index]
            else:
                resources[r] = [-1, -1, -1, -1]
                costs[r] = -1

        solution = {"pairs": {}, "priorities": {}, "req_paths": {}, "rpl_paths": {}, "info": "None", "OF": 0, "done": None, "opt_game_num_act_reqs": 0}
        pairs = {}
        priorities = {}
        req_paths = {}
        rpl_paths = {}
        num_act_reqs = 0

        OF = sum(costs.values())
        for r in self.req_obj.REQUESTS:
            if costs[r] != -1:
                pairs[r] = (self.REQUESTS_ENTRY_NODES[r], resources[r][0])
                priorities[r] = resources[r][1]
                req_paths[r] = self.net_obj.PATHS_DETAILS[resources[r][2]]
                rpl_paths[r] = self.net_obj.PATHS_DETAILS[resources[r][3]]
            else:
                pairs[r] = -1
                priorities[r] = -1
                req_paths[r] = -1
                rpl_paths[r] = -1

        for key in costs:
            if costs[key] != -1:
                num_act_reqs += 1

        solution["pairs"] = pairs
        solution["priorities"] = priorities
        solution["req_paths"] = req_paths
        solution["rpl_paths"] = rpl_paths
        solution["avg_of"] = OF/num_act_reqs
        solution["num_act_reqs"] = num_act_reqs

        return solution
