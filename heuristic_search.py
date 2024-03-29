#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import os
import time
import heapq
import math
from collections import defaultdict

class State(object):
    """
    Encapsulates per-state information for the grid world coin collection
    planning task.

    Variables:
        grid: stores reference to the grid
        x: current x position on the grid
        y: current y position on the grid
        coins_collected: stores the set of coin ids that have been collected
                         already

    Functions:
        has_collected_coin(coin_id): returns True if the coin with the given
                                     id has been collected
        has_collected_at_location(x, y): returns True if the coin at the given
                                         location has been collected
    """
    def __init__(self, grid, x, y, coins_collected):
        self.grid = grid
        self.x = x
        self.y = y
        self.coins_collected = coins_collected

    def has_collected_coin(self, coin_id):
        """
        Returns True if the coin with the given id has been collected.
        """
        return coin_id in self.coins_collected

    def has_collected_coin_at_location(self, x, y):
        """
        Returns True if the coin at the given location has been collected.
        """
        assert(grid.is_coin(x,y))
        return self.has_collected_coin(grid.get_coin_id(x, y))

    def __hash__(self):
        return hash(self.__tuple__())

    def __tuple__(self):
        return (self.x, self.y, self.coins_collected)

    def __lt__(self, other):
        return type(self) == type(other) and self.__tuple__() < other.__tuple__()

    def __gt__(self, other):
        return type(self) == type(other) and self.__tuple__() > other.__tuple__()

    def __le__(self, other):
        return type(self) == type(other) and self.__tuple__() <= other.__tuple__()

    def __ge__(self, other):
        return type(self) == type(other) and self.__tuple__() >= other.__tuple__()

    def __eq__(self, other):
        return type(self) == type(other) and self.__tuple__() == other.__tuple__()


class Grid(object):
    """
    Stores grid related information (i.e., the location of the coins, walls,
    etc.). Also implements the coin collection planning task semantics.

    Variables:
        width:  the width of the grid
        height: the height of the grid
        grid:   width * height array, storing per-cell information
                (it should not be necessary to access grid from outside the
                Grid class itself)

    Functions:
        is_within_boundaries(x, y): checks if the given coordinate is within
                                    the grid
        is_wall(x, y): checks if there is a wall at the given coordinate
        is_coin(x, y): checks if there is a coin at the given coordinate
        get_coin_id(x, y): If there is a coin at the given coordinate,
                           returns the id of the coin. Otherwise returns None.

        get_initial_state(): Returns the initial state.
        get_coin_locations(): Returns a list of the coordinates of all coins.
        get_successor_states(state): Computes and returns the list of successor
                                     states.
    """
    AGENT_SYMBOL = 'A'
    COIN_SYMBOL = 'C'
    WALL_SYMBOL = '#'
    EMPTY_SYMBOL = ' '

    def __init__(self, inv = None):
        if inv != None:
            self.width = len(inv[0])
            self.height = len(inv)
            self.grid = [[inv[y][x] for y in range(self.height)] for x in range(self.width)]
        else:
            self.width = 0
            self.height = 0
            self.grid = []

    @staticmethod
    def load_from_file(path, start, coins, diag = False):
        grid = Grid()
        with open(path) as f:
            l0 = f.readline().strip()
            l1 = f.readline().strip()
            l2 = f.readline().strip()
            l3 = f.readline().strip()
            if l0 != "type octile" \
                    or not l1.startswith("height ") \
                    or not l2.startswith("width ") \
                    or l3 != "map":
                raise ValueError("Unexpected file format")
            try:
                grid.width = int(l2[6:])
                grid.height = int(l1[7:])
            except ValueError:
                raise ValueError("Unexpected file format")
            grid.grid = [ [None for y in range(grid.height)] for x in range(grid.width) ]
            for y in range(grid.height):
                l = f.readline()
                if l == "":
                    raise ValueError("Unexpected end of file")
                l = l.strip()
                if len(l) != grid.width:
                    raise ValueError("Invalid line length")
                for x in range(grid.width):
                    if l[x] in [ ".", " ", "G", "S" ]:
                        grid.grid[x][y] = Grid.EMPTY_SYMBOL
                    elif l[x] in [ "@", "O", "T", "W", "#" ]:
                        grid.grid[x][y] = Grid.WALL_SYMBOL
                    else:
                        raise ValueError("Unknown cell symbol '%s'" % l[x])
        try:
            s = start.split(",")
            grid.grid[int(s[0])][int(s[1])] = Grid.AGENT_SYMBOL
        except Exception:
            raise ValueError("Invalid start position '%s'" % start)
        num = 0
        for g in coins:
            try:
                s = g.split(",")
                grid.grid[int(s[0])][int(s[1])] = num
                num += 1
            except Exception:
                raise ValueError("Invalid coin position '%s'" % g)
        return grid

    def is_within_boundaries(self, x, y):
        """
        Checks if the given coordinate is within the grid.
        """
        return x >= 0 and x < self.width and y >= 0 and y < self.height

    def lookup(self, x, y):
        assert(self.is_within_boundaries(x, y))
        return self.grid[x][y]

    def is_wall(self, x, y):
        """
        Checks if there is a wall at the given coordinate
        """
        return self.lookup(x, y) == Grid.WALL_SYMBOL

    def is_coin(self, x, y):
        """
        Checks if there is a coin at the given coordinate
        """
        return isinstance(self.lookup(x, y), int)

    def get_coin_id(self, x, y):
        """
        If there is a coin at the given coordinate, returns the id of the coin.
        Otherwise returns None.
        """
        assert(self.is_within_boundaries(x, y))
        return self.grid[x][y] if self.is_coin(x, y) else None

    def get_initial_state(self):
        """
        Returns the initial state.
        """
        for x in range(self.width):
            for y in range(self.height):
                if self.grid[x][y] == Grid.AGENT_SYMBOL:
                    return State(self, x, y, frozenset())
        return None

    def get_coin_locations(self):
        """
        Returns a list of the coordinates of all coins.
        """
        coins = []
        for x in range(self.width):
            for y in range(self.height):
                if self.is_coin(x, y):
                    coins.append((x, y))
        return coins

    def get_successor_states(self, state):
        """
        Computes and returns the list of successor states.
        """
        result = []
        for i in range(-1, 2):
            for j in range(-1, 2):
                if (i == 0 and j == 0) or i * j != 0:
                    continue
                succ = State(self, state.x+i, state.y+j, set(state.coins_collected))
                if self.is_within_boundaries(succ.x, succ.y) \
                        and not self.is_wall(succ.x, succ.y):
                    if self.is_coin(succ.x, succ.y):
                        succ.coins_collected.add(self.grid[succ.x][succ.y])
                    succ.coins_collected = frozenset(succ.coins_collected)
                    result.append(succ)
        return result


class SearchNode(object):
    """
    Stores information of a search node in A*.

    Variables:
        state: referenced state
        parent: reference to SearchNode that was used by A* to generate this
                search node
        h: heuristic estimate
        g: A*'s g-value

    """
    def __init__(self, state, h, parent = None):
        assert(isinstance(state, State))
        assert(isinstance(h, int))
        assert(parent is None or isinstance(parent, SearchNode))
        self.state = state
        self.parent = parent
        self.h = h
        self.g = 0 if parent is None else parent.g + 1

    def extract_plan(self):
        plan = []
        p = self
        while p != None:
            plan.append(p.state)
            p = p.parent
        return list(reversed(plan))

    def set_flag(self, flags, val = True):
        flags[self.state.coins_collected][self.state.x][self.state.y] = True

    def check_if_flagged(self, flags):
        return flags[self.state.coins_collected][self.state.x][self.state.y]

    def get_f_value(self):
        return self.h + self.g

    def __lt__(self, other):
        return (self.get_f_value(), self.g, self.state) < (other.get_f_value(), other.g, other.state)


class SearchResult(object):
    """
    Stores A* related statistics and the final plan.
    """
    def __init__(self, expansions = 0, visited = 0, plan = None):
        self.expansions = expansions
        self.visited = visited
        self.plan = plan


def print_search_node(grid, node):
    """
    Prints a search node to the console.
    """
    if max([grid.width, grid.height]) > 100:
        return

    os.system('cls' if os.name == 'nt' else 'clear')  

    visited = set()
    p = node
    while p != None:
        visited.add((p.state.x, p.state.y))
        p = p.parent

    for y in range(grid.height):
        s1 = ""
        for x in range(grid.width):
            symbol = Grid.EMPTY_SYMBOL
            color = "1;30"
            if grid.is_wall(x, y):
                symbol = u"\u25A8"
            elif node.state.x == x and node.state.y == y:
                symbol = Grid.AGENT_SYMBOL
            elif grid.is_coin(x, y):
                symbol = str(grid.get_coin_id(x, y))
                color = "1;28"
            elif (x, y) in visited:
                symbol = u"\u25CF"

            if (x, y) in visited:
                color = "1;34"

            s1 += (u'\x1b[%sm %s\x1b[0m' % (color, symbol))

        print(s1)

    if len(node.state.coins_collected) == 0:
        print(" Collected coin ids: --")
    else:
        print(" Collected coin ids: %s" % ", ".join([str(i) for i in sorted(node.state.coins_collected)]))


def print_search_progress(grid, state, expanded, visited):
    """
    Prints the search progress to the console. Highlights visited and expanded
    states.
    """
    if max([grid.width, grid.height]) > 100:
        return

    os.system('cls' if os.name == 'nt' else 'clear')  

    for y in range(grid.height):
        s1 = ""
        for x in range(grid.width):
            symbol = Grid.EMPTY_SYMBOL
            color = "1;30"
            if grid.is_wall(x, y):
                symbol = u"\u25A8"
            elif state.x == x and state.y == y:
                symbol = Grid.AGENT_SYMBOL
            elif grid.is_coin(x, y) and not grid.get_coin_id(x, y) in state.coins_collected:
                symbol = str(grid.get_coin_id(x, y))
                color = "1;28"
            elif visited[state.coins_collected][x][y] != None or expanded[state.coins_collected][x][y]:
                symbol = u"\u25CF"

            if expanded[state.coins_collected][x][y]:
                color = "1;31"
            elif visited[state.coins_collected][x][y] != None:
                color = "1;33"

            s1 += (u'\x1b[%sm %s\x1b[0m' % (color, symbol))

        print(s1)

    if len(state.coins_collected) == 0:
        print(" Collected coin ids: --")
    else:
        print(" Collected coin ids: %s" % ", ".join([str(i) for i in sorted(state.coins_collected)]))


def astar_search(grid, heuristic, print_rate_per_sec = None):
    """
    Implementation of the A* algorithm.
    """
    assert(isinstance(grid, Grid))
    assert(isinstance(heuristic, Heuristic))
    initial_state = grid.get_initial_state()
    num_coins = len(grid.get_coin_locations())
    open_list = [ SearchNode(initial_state, heuristic(initial_state)) ]
    expanded = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: False)))
    visited = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: None)))
    visited[initial_state.coins_collected][initial_state.x][initial_state.y] = open_list[0].h
    print_search_progress(grid, open_list[0].state, expanded, visited)
    
    result = SearchResult()
            
    while len(open_list) > 0:
        node = heapq.heappop(open_list)
        if node.check_if_flagged(expanded):
            continue
        result.expansions += 1
        if len(node.state.coins_collected) == num_coins:
            result.plan = node.extract_plan()
            print_search_node(grid, node)
            break
        successors = grid.get_successor_states(node.state)
        for succ in successors:
            if expanded[succ.coins_collected][succ.x][succ.y]:
                continue
            if visited[succ.coins_collected][succ.x][succ.y] is None:
                result.visited += 1
                visited[succ.coins_collected][succ.x][succ.y] = heuristic(succ)
            heapq.heappush(open_list, SearchNode(succ, visited[succ.coins_collected][succ.x][succ.y], node))
        if print_rate_per_sec != None:
            print_search_progress(grid, node.state, expanded, visited)
            time.sleep(print_rate_per_sec)
        node.set_flag(expanded)

    return result


class Heuristic(object):
    """
    Heuristic base class.
    
    Variables:
        grid: stores a reference to the grid
        coin_locations: list of the coordinates of all coins in the grid

    """
    def __init__(self, grid):
        assert(isinstance(grid, Grid))
        self.grid = grid
        self.coin_locations = grid.get_coin_locations()

    def __call__(self, state):
        assert(isinstance(state, State))
        raise NotImplemented("call function has not been implemented yet")


class BlindHeuristic(Heuristic):
    """
    The blind heuristic. Returns 0 for every state. Using this heuristic will
    turn A* into simple Dijkstra search. In our unit-cost setting, A* with the
    blind heuristic boils down to a simple breadth-first search.
    """
    def __init__(self, grid):
        # Call the super constructor to initialize the grid and coin_location
        # variables:
        super(BlindHeuristic, self).__init__(grid)

    def __call__(self, state):
        # The actual heuristic computation. The blind heuristic will simply
        # always return 0.
        return 0


class ManhattanMaxHeuristic(Heuristic):
    """
    The maximal distance from the agent's current coordinate to the coordinates
    of every coin that has not been collected. Manhattan distance is used for
    the distance estimation.
    """
    def __init__(self, grid):
        # Call the super constructor to initialize the grid and coin_location
        # variables:
        super(ManhattanMaxHeuristic, self).__init__(grid)

    def __call__(self, state):
        assert(isinstance(state, State))
        # The actual heuristic computation.
        # Maximum Distance
        maximum = 0
        # Get the location of coins
        coins = grid.get_coin_locations()
        for coin_x,coin_y in coins:
            # Check if the coin is collected. If not collected then calculate 
            # the distance between the state and the coin
            if not state.has_collected_coin_at_location(coin_x,coin_y):
                # Calculate the distance
                Sum = (abs(state.x - coin_x) + abs(state.y - coin_y))
                # If the calculated distance is larger than the max distance
                # then set the calculated distacne as the maximum distance.
                maximum = max(maximum, Sum)

        return maximum

class ManhattanSumHeuristic(Heuristic):
    """
    The sum of all distances from the agent's current coordinate to the
    coordinate of every coin that has not been collected. Manhattan distance is
    used for the distance estimation.
    """
    def __init__(self, grid):
        # Call the super constructor to initialize the grid and coin_location
        # variables:
        super(ManhattanSumHeuristic, self).__init__(grid)

    def __call__(self, state):
        assert(isinstance(state, State))
        # The actual heuristic computation.
        # Sum of distance from the state to all the coins 
        sum_dist = 0

        # get the location of all coins
        coins = grid.get_coin_locations()
        for coin_x,coin_y in coins:
            # Check if the coin is already collected if not then calculate the distance 
            # between the state and the coin
            if not state.has_collected_coin_at_location(coin_x,coin_y):
                Sum = (abs(state.x - coin_x) + abs(state.y - coin_y))
                # Add the distance to the sum_dist
                sum_dist += Sum

        return sum_dist

class ManhattanOrderedSumHeuristic(Heuristic):
    """
    The sum of pairwise-distances in a sequence of coordinates as defined on the
    exercise sheet. Manhattan distance is used for the distance estimation.
    """
    def __init__(self, grid):
        # Call the super constructor to initialize the grid and coin_location
        # variables:
        super(ManhattanOrderedSumHeuristic, self).__init__(grid)

    def __call__(self, state):
        assert(isinstance(state, State))
        # The actual heuristic computation.
         
        # The coordinates of coin1
        c1_x = 0
        c1_y = 0

        # Minimum Distance between the state and the coin
        dist = 32**32
        # Get the location of the coins
        coins = grid.get_coin_locations()
        # Check if the coin is collected. If not then calculate the distance
        for coin_x,coin_y in coins:
            if not state.has_collected_coin_at_location(coin_x,coin_y):
                Sum = (abs(state.x - coin_x) + abs(state.y - coin_y))
                # If the calculated distance is smaller than the minimum distance 
                # update the minimum distance as the caclulated distance
                # set the x and y coordinates of the coin to coin1 x and coin1 y.
                if Sum < dist:
                    dist = Sum
                    c1_x = coin_x
                    c1_y = coin_y


        # list of coins that are not collected
        coins_not_collected= []
        for coin_x, coin_y in coins:
            if not state.has_collected_coin_at_location(coin_x, coin_y):
                coins_not_collected.append((coin_x, coin_y))

            
        # Sort the coins such that, distance between coin_i and coin_i+1 is 
        # less than the distance between coin_i and coin_j
        coins_not_collected.sort()
        # Calculate the sum of distance from coin i to coin i+1
        dist_sum = 0
        if coins_not_collected is not None:
            for i in range(len(coins_not_collected)-1):
                distance = (abs(coins_not_collected[i][0]-coins_not_collected[i+1][0]) + abs(coins_not_collected[i][1]-coins_not_collected[i+1][1]))
                # add the calculated distance to the sum of distance
                dist_sum += distance

        # return the distance between state and coin 1 + the sum of distance between the coins
        return (abs(state.x - c1_x) + abs(state.y -c1_y)) + dist_sum

class CallMeFancyHeuristic(Heuristic):
    """
    The implementation of your admissible heuristic goes in here.
    """
    def __init__(self, grid):
        # Call the super constructor to initialize the grid and coin_location
        # variables:
        super(CallMeFancyHeuristic, self).__init__(grid)
        # You may do any additional initialization / precomputation steps at
        # this point.

    def __call__(self, state):
        assert(isinstance(state, State))
        # The actual heuristic computation.

        # The maximum euclidean distance 
        maximum = 0
        # Get the coins location
        coins = grid.get_coin_locations()
        for coin_x,coin_y in coins:
            # Check if the coin has been already collected, if not calculate the euclidean distance
            if not state.has_collected_coin_at_location(coin_x,coin_y):
                Sum = math.sqrt((state.x - coin_x)**2 + (state.y - coin_y)**2)

                maximum += Sum
        return int(maximum)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("grid", help="Path to grid file (https://www.movingai.com/benchmarks/formats.html).", nargs="?", default=None)
    p.add_argument("start", help="Agent's initial position", nargs="?", default=None)
    p.add_argument("coin",  help="Coin positions", nargs="*", default=[])
    p.add_argument("--rate", help="States printed per second", default=1.5, type=float)
    p.add_argument("--benchmarking", help="Do not print search progress", default=False, action="store_true")
    p.add_argument("--heuristic", help="Which heuristic to use. The blind heuristic will turn A* into simple Breadth-First Search.", choices=sorted([x[:-9] for x in globals() if x != "Heuristic" and x.endswith("Heuristic")]), default="Blind")
    args = p.parse_args()

    n = int(args.grid != None) + int(args.start != None) + len(args.coin)
    if n != 0 and n < 3:
        p.error("grid, start, and coin must be defined together")

    grid = Grid([
        ['#','#','#','#','#','#','#','#','#'],
        ['#',' ',' ','A',' ',' ',' ',' ','#'],
        ['#',' ','#',' ','#',' ','#','#','#'],
        ['#',' ','#','#','#',' ','#',' ','#'],
        ['#',' ','#',' ','#',' ',' ',0,'#'],
        ['#',' ',' ',' ','#',' ','#','#','#'],
        ['#',' ','#',' ','#',' ',' ',' ','#'],
        ['#',' ','#',' ','#','#','#',' ','#'],
        ['#','#','#','#','#','#','#','#','#']])
    if args.grid != None:
        grid = Grid.load_from_file(args.grid, args.start, args.coin)

    if not args.benchmarking and max([grid.width, grid.height]) > 100:
        print("The grid is too large to be drawn. Switching to benchmarking mode.")
        args.benchmarking = True

    t = time.time()
    h = globals()["%sHeuristic" % args.heuristic](grid)
    result = astar_search(grid, h, None if args.benchmarking else 0.001/args.rate)
    # result = astar_search(grid, h, None)
    print("")

    if result.plan is None:
        print("Search terminated without finding a solution!")
    else:
        print("Solution found!")
        print("Plan length:     %d" % (len(result.plan) - 1))
    print("States expanded: %d" % result.expansions)
    print("States visited:  %d" % result.visited)
    print("Total time:      %.3fs" % (time.time() - t))

