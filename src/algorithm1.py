# algorithm1.py - cultural algorithm solver

import random
import time
from copy import deepcopy



# check if cage is satisfied by certain given values
def cage_valid(values, target, op):
    if op == '+':
        return sum(values) == target
    if op == '-':
        return len(values) == 2 and abs(values[0] - values[1]) == target
    if op == '*':
        p = 1
        for v in values:
            p *= v
        return p == target
    if op == '/':
        if len(values) != 2 or 0 in values:
            return False
        a, b = values
        return max(a, b) / min(a, b) == target
    if op == '=':
        return values[0] == target
    return False


# it is to generate all possible sequences of numbers in certain length (repeat) 
def product(values, repeat):
    if repeat == 1:
        for v in values:
            yield (v,)
        return
    for v in values:
        for rest in product(values, repeat - 1):
            yield (v,) + rest


# to identify all valid number combinations that appear inside cage
def generate_cage_combinations(cells, target, op, n):
    k = len(cells)
    values = range(1, n+1)
    combos = []

    if op == '=':
        return [[target]]

    if op == '-':
        for a in values:
            for b in values:
                if abs(a - b) == target:
                    combos.append([a, b])
        return combos

    if op == '/':
        for a in values:
            for b in values:
                if a != 0 and b != 0 and max(a,b)/min(a,b) == target:
                    combos.append([a, b])
        return combos

    if op == '+':
        if k == 2:
            for a in values:
                for b in values:
                    if a + b == target:
                        combos.append([a, b])
        else:
            for cand in product(values, repeat=k):
                if sum(cand) == target:
                    combos.append(list(cand))
        return combos

    if op == '*':
        if k == 2:
            for a in values:
                for b in values:
                    if a * b == target:
                        combos.append([a, b])
        else:
            for cand in product(values, repeat=k):
                p = 1
                for v in cand:
                    p *= v
                if p == target:
                    combos.append(list(cand))
        return combos

    return combos


# evaluating fitness function
def evaluate_fitness(grid, cages, n):
    row_pen = 0
    col_pen = 0
    cage_pen = 0

    for r in range(n):
        row_pen += n - len(set(grid[r]))

    for c in range(n):
        col = [grid[r][c] for r in range(n)]
        col_pen += n - len(set(col))

    for cells, target, op in cages:
        vals = [grid[r][c] for (r, c) in cells]
        if not cage_valid(vals, target, op):
            cage_pen += 1

    return row_pen + col_pen + cage_pen * 7  #added weight to cage penalty ~ youssef241784


# build the full grid from assignments
def build_grid(assignments, cages, n):
    grid = [[0]*n for _ in range(n)]
    for (cells, _, _), combo in zip(cages, assignments):
        combo = list(combo)
        for i, (r,c) in enumerate(cells):
            grid[r][c] = combo[i]
    return grid


# structure repair to fix latin square violations ( duplicated numbers in row andd column)
def repair_latin(grid, n):
    g = deepcopy(grid)

    # to fix rows
    for r in range(n):
        row = g[r]
        if len(set(row)) != n:
            missing = [v for v in range(1,n+1) if v not in row]
            dups = []
            seen = set()
            for c,v in enumerate(row):
                if v in seen:
                    dups.append(c)
                seen.add(v)
            random.shuffle(missing)
            for cc,val in zip(dups,missing):
                g[r][cc] = val

    # to fix columns
    for c in range(n):
        col = [g[r][c] for r in range(n)]
        if len(set(col)) != n:
            missing = [v for v in range(1,n+1) if v not in col]
            dups = []
            seen = set()
            for r,v in enumerate(col):
                if v in seen:
                    dups.append(r)
                seen.add(v)
            random.shuffle(missing)
            for rr,val in zip(dups,missing):
                g[rr][c] = val

    return g


# function to swap two cages positions in a trial to escape a trap
def structural_swap(assignments, cages, n):

    new = deepcopy(assignments)

    idx1 = random.randrange(len(cages))
    idx2 = random.randrange(len(cages))

    if idx1 == idx2:
        return new

    cells1 = cages[idx1][0]
    cells2 = cages[idx2][0]

    # only swap if they have same number of cells
    if len(cells1) != len(cells2):
        return new

    # also same shape arrangement
    if set(cells1) & set(cells2):
        return new

    # allowed swap combos
    new[idx1], new[idx2] = new[idx2], new[idx1]
    return new


# cultural algorithm solve loop
def cultural_algorithm(
    cages, #puzzle that is required to be solved
    n, # size of puzzle example: 3(3x3), 7,(7x7)
    pop_size=100, #population size of the generation   also: #100 best for 7x7
    generations=5000, #number of maximum generations allowed (cycles)
    mutation_rate=0.12, #rate of randomizing combinations
    acceptance_ratio=0.19, # [elitism] percentage of top combinations that are going to affect the upcoming generation    also: #0.19 best for 7x7
    update_interval=10, # determines the gui update in terms of generations
    gui_callback=None,
    should_stop=lambda: False # used for force-stop button in gui
):

    # calculate valid number sets for each cage in the puzzle
    cage_domains = []
    for cells, target, op in cages:
        combos = generate_cage_combinations(cells, target, op, n)
        if not combos:
            combos = [[random.randint(1,n) for _ in cells]]
        cage_domains.append([tuple(c) for c in combos])

    C = len(cages)

    # creating or intializing the population & population consist of many candidate solutions
    population = [
        [random.choice(cage_domains[i]) for i in range(C)]
        for _ in range(pop_size)
    ]

    #intializing the belief space ( the main idea of cultural algorithm )
    situational = None #the best individual ever found
    normative = [set(domain) for domain in cage_domains] #the values that are learned from the best individuals

    prev_best = 99999 #high fitness to compare with the first candidate fitness to successfully initialize it
    stagnation = 0

    start = time.time()

    # main generation loop
    for gen in range(generations):

        if should_stop(): #to check if user pressed force stop in gui
            break

        # does the main functions & then scores it based on cage/row/column violations
        scored = []
        for indiv in population:
            grid = build_grid(indiv, cages, n)
            grid = repair_latin(grid, n)
            fit = evaluate_fitness(grid, cages, n)
            scored.append((fit, indiv, grid))

        scored.sort(key=lambda x: x[0]) #sorting of population in terms of fitness score
        best_fit, best_indiv, best_grid = scored[0]

        # --- GUI update ---
        if gui_callback and gen % update_interval == 0:
            gui_callback(best_grid, best_fit, gen)


        # if solved then it'll end here
        if best_fit == 0:
            return best_grid, 0, time.time()-start, gen

        # update situational knowledge ( best solution ever )
        if situational is None:
            situational = list(best_indiv)
        else:
            old_fit = evaluate_fitness(
                repair_latin(build_grid(situational, cages, n), n),
                cages, n
            )
            if best_fit < old_fit:
                situational = list(best_indiv)

        # to count stagnation ( how many times the fitness is stuck in the same score)
        if best_fit == prev_best:
            stagnation += 1
        else:
            stagnation = 0
        prev_best = best_fit

        # add diversity to escape being stuck
        if stagnation > 60:
            for _ in range(pop_size//10):
                population[random.randrange(pop_size)] = [
                    random.choice(cage_domains[i]) for i in range(C)
                ]
            stagnation = 0

        # selecting the best performing (lowest fitness) individuals
        elite_count = max(2, int(pop_size * acceptance_ratio))
        elites = [ind for (fit, ind, _) in scored[:elite_count]]

        # updating normative values from elites
        for i in range(C):
            vals = {tuple(ind[i]) for ind in elites}
            if len(vals) >= 2:
                normative[i] = vals


        # creating a new population

        new_pop = []

        while len(new_pop) < pop_size:

            # choosing 3 parents
            p1 = situational
            p2 = random.choice(elites)
            p3 = random.choice(elites)

            child = []

            # recombination (crossover) 
            for i in range(C):
                choice = random.random()
                if choice < 0.33:
                    child.append(p1[i])
                elif choice < 0.66:
                    child.append(p2[i])
                else:
                    child.append(p3[i])

            # mutation 
            for i in range(C):
                if random.random() < mutation_rate:
                    child[i] = random.choice(cage_domains[i])

            # permutation mutation (to shuffle values inside a cage)
            for i in range(C):
                if len(child[i]) > 1 and random.random() < 0.18:
                    temp = list(child[i])
                    random.shuffle(temp)
                    child[i] = tuple(temp)

            # structural swap mutation [explained that function at it's definition]
            if random.random() < 0.10:
                child = structural_swap(child, cages, n)

            # mutation using the normative knowledge (as said above, values of best performing)
            for i in range(C):
                if random.random() < 0.10:
                    child[i] = random.choice(list(normative[i]))

            new_pop.append(child)

        population = new_pop

    # return the best solution (lowest fitness score) if no exact solution was found
    best_fit, best_indiv, best_grid = min(scored, key=lambda x: x[0])
    return best_grid, best_fit, time.time()-start, generations
