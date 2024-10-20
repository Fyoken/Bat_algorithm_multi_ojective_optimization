# -*- coding: utf-8 -*-
"""Bat_Algorithm_Task_Scheduling.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1jT2FUPPwXxoiaAudcmAwFtXH__6Dy8bZ
"""

!pip install ortools

import numpy as np
import random
import pandas as pd
from google.colab import drive
from scipy.spatial import distance
from math import exp
from ortools.linear_solver import pywraplp
import matplotlib.pyplot as plt

drive.mount('/content/gdrive')

# Read data with 40 tasks
task_details = pd.read_excel("./task40.xlsx", sheet_name="TaskDetails")
node_details = pd.read_excel("./task40.xlsx", sheet_name="NodeDetails")
execution_table = pd.read_excel("./task40.xlsx", sheet_name="ExecutionTable")
cost_table = pd.read_excel("./task40.xlsx", sheet_name="CostTable")

# Define problem parameters
num_tasks = len(task_details)  # Number of tasks
num_vms = len(node_details)  # Number of virtual machines

# Capacity of the VM in 10s
vm_capacity = node_details['CPU rate (MIPS)'].values/10

# Use the number of instructions from TaskDetails as workload
workload = task_details['Number of instructions (109 instructions)'].values.reshape(-1, 1)  # Reshape to 2D array
workload = np.array(workload).flatten()

# Convert times and costs to floats excluding the first row and column
times = np.array(execution_table.iloc[1:, 1:], dtype=float)
costs = np.array(cost_table.iloc[1:, 1:], dtype=float)

# Function that returns a solution (2D matrix containing the X_ij) respecting the constraints
def bat_task_assignment(position, workload, capacities):
    # Initialization
    num_tasks = len(workload)
    num_vms = len(capacities)
    solution = np.zeros((num_vms, num_tasks), dtype=int)
    assigned_workloads = np.zeros(num_vms)

    # Sort the tasks in ascending order based on the position of the bat
    sorted_task_indices = np.argsort(position)
    for task_index in sorted_task_indices:
        task_workload = workload[task_index]
        vm_candidates = np.where(np.array(capacities) >= task_workload)[0]
        for vm in vm_candidates:
            # Capacity constraint
            if assigned_workloads[vm] + task_workload <= capacities[vm]:
                solution[vm, task_index] = 1
                assigned_workloads[vm] += task_workload
                break  # Assign task to the first available VM to make sure only one VM has this task
    return solution

class Bat:
    def __init__(self, pos):
        # Position: a number between 0 and 1 for each task
        # Velocity: a vector representing the speed of moving for bats
        self.pos, self.vel = pos, [0.00 for _ in range(len(pos))]

        # Pulse rate of the bats
        self.max_pulse_rate = random.uniform(0, 1)
        self.pulse_rate = 0

        # Fitness values of makespan and total cost
        self.fitness = None

        # Solution: 2D matrix with X_ij values
        self.sol = None

    def set_fitness(self, fitness):
        self.fitness = fitness

    def set_sol(self, sol):
        self.sol = sol

    def get_fitness(self):
        return self.fitness


def multi_objective_bat_algorithm(dim, epochs, pop_size, gam, qmin, qmax, workload, capacity):
    # Initialization with random positions
    population = [Bat(np.random.uniform(0, 1, dim)) for _ in range(pop_size)]
    archive = []

    # Values for the plot
    makespan_costs = []

    best_bat = None

    for e in range(1, epochs+1):
        makespan_cost_epoch = []

        # Archive part
        for bat in population:
            # Get and evaluate a solution depending on position of the bat
            solution = bat_task_assignment(bat.pos, workload, capacity)
            bat_fitness = [makespan(solution), total_cost(solution)]
            bat.set_fitness(bat_fitness)
            bat.set_sol(solution)
            if bat not in archive:
                is_dominated = False
                for archived_bat in archive:
                    if bat_fitness[0] < archived_bat.fitness[0] and bat_fitness[1] < archived_bat.fitness[1]:
                        # If the new bat dominates an archived bat, remove the archived bat
                        archive.remove(archived_bat)
                    elif bat_fitness[0] >= archived_bat.fitness[0] and bat_fitness[1] >= archived_bat.fitness[1]:
                        # If an archived bat dominates the new bat, it is dominated
                        is_dominated = True

                if not is_dominated:
                    # If the new bat is not dominated, add it to the archive
                    archive.append(bat)
                    # Selecting the last best bat as a reference
                    best_bat = bat
            else:
              # Checking the dominance in the archive
              for archived_bat in archive:
                if bat.fitness[0]>=archived_bat.fitness[0] and bat.fitness[1]>=archived_bat.fitness[1] and bat.fitness!=archived_bat.fitness:
                  archive.remove(bat)
            makespan_cost_epoch.append(bat_fitness)

        makespan_costs.append(makespan_cost_epoch)

        # Moving part
        for bat in population:
          if bat not in archive:
            new_pos = [0.00 for _ in range(dim)]
            new_vel = [0.00 for _ in range(dim)]

            # Frequence of the bat
            freq = random.uniform(qmin, qmax)

            # Random pulsation
            pulse_chance = random.uniform(0, 1)
            for d in range(dim):
                # Updating velocity
                new_vel[d] = bat.vel[d] + (bat.pos[d] - best_bat.pos[d]) * freq

                # If pulsation rate not loud enough
                if pulse_chance > bat.pulse_rate:
                    # Stays close to the best bat
                    new_pos[d] = best_bat.pos[d] + (random.uniform(-1, 1) * 0.1)
                else:
                    # Moving toward the best bat and keeps exploring
                    new_pos[d] = bat.pos[d] + new_vel[d]

            # Update
            bat.vel = new_vel
            bat.pos = new_pos
            bat.pulse_rate = bat.max_pulse_rate * (1 - exp(-gam * e))
    return archive, makespan_costs


# Plot function
def plot_makespan_cost(makespan_costs, pareto_solutions):
    plt.figure(figsize=(10, 5))
    all_points = []
    for i in range(len(makespan_costs)):
        makespan_cost_epoch = makespan_costs[i]
        makespan = [x[0] for x in makespan_cost_epoch]
        cost = [x[1] for x in makespan_cost_epoch]

        # Plot in blue if not in pareto_solutions
        for j, (mk, cst) in enumerate(zip(makespan, cost)):
            if (mk, cst) not in pareto_solutions:
                plt.plot(mk, cst, marker='o', color='blue')

        # Collect red points
        red_points = [(makespan[i], cost[i]) for i in range(len(makespan)) if (makespan[i], cost[i]) in pareto_solutions]
        all_points.extend(red_points)

    # Sort the red points by makespan
    all_points.sort(key=lambda x: x[0])

    # Extract sorted makespan and cost
    sorted_makespan = [point[0] for point in all_points]
    sorted_cost = [point[1] for point in all_points]

    # Plot a line connecting all red points
    plt.plot(sorted_makespan, sorted_cost, 'o-', color='red')

    plt.xlabel('Makespan')
    plt.ylabel('Cost')
    plt.title('Makespan vs Cost for {} Tasks'.format(dim))
    plt.grid(True)
    plt.tight_layout()
    plt.show()


# Makespan function
def makespan(solution):
    completion_times = np.zeros(num_vms)
    max_completion_time = 0
    for i in range(num_vms):
        for j in range(num_tasks):
            completion_times[i] += times[i, j] * solution[i, j]
    return sum(completion_times)

# Energy consumption function
"""
def energy_consumption(solution):
    total_energy = 0
    ej = ?
    for j in range(num_tasks):
        for i in range(num_vms):
            total_energy += times[i, j] * solution[i, j] * ej
    return total_energy
"""

# Total cost function
def total_cost(solution):
    cost = 0
    for i in range(num_vms):
        for j in range(num_tasks):
            cost += costs[i, j] * solution[i, j]
    return cost

# Parameters
dim = num_tasks  # Dimensionality of the tasks
epochs = 100 # Number of generations
pop_size = 100  # Population size
gam = 0.1  # Pulse rate increasing rate
qmin = 0  # Minimum frequency
qmax = 1  # Maximum frequency

# Run multi-objective bat algorithm
archive, makespan_costs = multi_objective_bat_algorithm(dim, epochs, pop_size, gam, qmin, qmax, workload, vm_capacity)
# Print non-dominated solutions in the archive
print("Non-dominated solutions in the archive:")
for bat in archive:
    # "Energy Consumption:", energy_consumption(bat.sol)
    print("Makespan:", makespan(bat.sol), "Total Cost:", total_cost(bat.sol))

pareto_solutions = []
for bat in archive:
  pareto_solutions.append((bat.fitness[0], bat.fitness[1]))
plot_makespan_cost(makespan_costs, pareto_solutions)

# Read data with 120 tasks
task_details = pd.read_excel("./task120.xlsx", sheet_name="TaskDetails")
node_details = pd.read_excel("./task120.xlsx", sheet_name="NodeDetails")
execution_table = pd.read_excel("./task120.xlsx", sheet_name="ExecutionTable")
cost_table = pd.read_excel("./task120.xlsx", sheet_name="CostTable")

# Define problem parameters
num_tasks = len(task_details)  # Number of tasks
num_vms = len(node_details)  # Number of virtual machines

# Capacity in 100ms
vm_capacity = node_details['CPU rate (MIPS)'].values/10

# Use the number of instructions from TaskDetails as workload
workload = task_details['Number of instructions (109 instructions)'].values.reshape(-1, 1)  # Reshape to 2D array
workload = np.array(workload).flatten()

# Convert times and costs to floats excluding the first row and column
times = np.array(execution_table.iloc[1:, 1:], dtype=float)
costs = np.array(cost_table.iloc[1:, 1:], dtype=float)

# Parameters
dim = num_tasks  # Dimensionality of the tasks
epochs = 100  # Number of generations
pop_size = 30  # Population size
gam = 0.1  # Pulse rate increasing rate
qmin = 0  # Minimum frequency
qmax = 1  # Maximum frequency

# Run multi-objective bat algorithm
archive, makespan_costs = multi_objective_bat_algorithm(dim, epochs, pop_size, gam, qmin, qmax, workload, vm_capacity)
# Print non-dominated solutions in the archive
print("Non-dominated solutions in the archive:")
for bat in archive:
    # "Energy Consumption:", energy_consumption(bat.sol)
    print("Makespan:", makespan(bat.sol), "Total Cost:", total_cost(bat.sol))

pareto_solutions = []
for bat in archive:
  pareto_solutions.append((makespan(bat.sol), total_cost(bat.sol)))
plot_makespan_cost(makespan_costs, pareto_solutions)
