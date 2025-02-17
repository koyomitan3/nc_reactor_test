import numpy as np
from utils.metrics import reactor_metrics
from visualization.plot_utils import plot_grid
from core.nuclear_reactor import validate_array, is_array_valid
import time
import random 
import concurrent.futures
import logging


def generate_random_size():
    # Generate random dimensions a, b, c
    a = random.randint(3, 4)
    b = random.randint(3, 4)
    c = random.randint(3, 4)

    # Return the tuple (a, b, c)
    return (a, b, c)

POPULATION_SIZE = 256
SIZE = (3, 3, 3)
GENERATIONS = 200
INITIAL_MUTATION_RATE = 0.1 # Start with a higher rate
MUTATION_DECAY_RATE = 0.99   # Decay factor for mutation
ELITE_SIZE = 10   # Number of elites to preserve
TOURNAMENT_SIZE_BASE = 100  # Base size for tournament selection
TOURNAMENT_SIZE_FACTOR = 0.99 # Factor to adjust tournament size
REACTOR_DIMENSIONS = SIZE
CURRENT_FUEL = "TBU"


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_array():
    return np.random.randint(0, 18, SIZE)


def initialize_population(size):
    population = np.zeros(SIZE, dtype=np.int32)
    return [population for _ in range(size)] 

# Caching dictionary
fitness_cache = {}

def fitness(individual, fuel):
    key = tuple(individual.flat)
    if key in fitness_cache:
        return fitness_cache[key]

    metrics = reactor_metrics(individual, fuel)

    if not is_array_valid(individual):
        fitness_cache[key] = 0
        return 0

    heat_penalty = calculate_heat_penalty(metrics['heat_diff'])
    fitness_score = (0.9 * metrics['energy_gen']) + (
        0.3 * metrics['heat_gen']) + heat_penalty + (1.5 * (metrics['efficiency'] / 100))

    # Calculate symmetry
    symmetry_reward = calculate_symmetry_reward(individual)
    fitness_score += symmetry_reward * 2

    # Calculate diversity penalty
    diversity_penalty = calculate_diversity_penalty(individual)
    fitness_score -= diversity_penalty * 5

    fitness_cache[key] = fitness_score
    return fitness_score

def calculate_symmetry_reward(array):
    # Measure symmetry along each axis (x, y, z)
    sym_score = 0
    for axis in range(3):
        reversed_array = np.flip(array, axis=axis)
        diff = np.abs(array - reversed_array).sum()  # Measure difference
        sym_score += np.exp(-diff)  # Symmetry reward based on difference
    return sym_score

def calculate_diversity_penalty(array):
    unique_elements = len(np.unique(array))
    max_possible_unique = np.prod(array.shape)  # Maximum unique elements possible
    return (max_possible_unique - unique_elements) / max_possible_unique 

def calculate_heat_penalty(heat_diff):
    if heat_diff > 0:
        return -100 * heat_diff
    else:
        return heat_diff * -1

def tournament_selection(population, fitnesses, tournament_size):
    """Selects an individual using tournament selection."""
    selected = np.random.choice(len(population), size=tournament_size, replace=False)
    best_index_in_selected = np.argmax(fitnesses[selected])  # Index within the selected subset
    best_index = selected[best_index_in_selected]          # Index in the original population
    return population[best_index]

def crossover(parent1, parent2):
    point = np.random.randint(1, np.prod(REACTOR_DIMENSIONS))
    child = np.concatenate((parent1.flat[:point], parent2.flat[point:])).reshape(REACTOR_DIMENSIONS)
    return child

def mutate(individual, mutation_rate):
    mask = np.random.rand(*individual.shape) < mutation_rate
    individual[mask] = np.random.randint(1, 17, size=np.count_nonzero(mask))
    return individual

def genetic_algorithm():
    population = initialize_population(POPULATION_SIZE)
    mutation_rate = INITIAL_MUTATION_RATE

    for generation in range(GENERATIONS):
        # Evaluate fitness
        with concurrent.futures.ThreadPoolExecutor() as executor:
            fitnesses = list(executor.map(lambda ind: fitness(ind, CURRENT_FUEL), population))

        fitnesses = np.array(fitnesses)
        # Elitism: Preserve the best individuals
        elite_indices = np.argsort(fitnesses)[-ELITE_SIZE:]
        elites = [population[i] for i in elite_indices]

        # Create new population
        new_population = elites[:]  # Start with elites
        tournament_size = max(int(TOURNAMENT_SIZE_BASE * (TOURNAMENT_SIZE_FACTOR ** generation)), 2) 
        for _ in range(POPULATION_SIZE - ELITE_SIZE):
            parent1 = tournament_selection(population, fitnesses, tournament_size)
            parent2 = tournament_selection(population, fitnesses, tournament_size)
            child = crossover(parent1, parent2)
            child = mutate(child, mutation_rate)
            
            # Validate and replace invalid children
            try:
                validate_array(child)
            except Exception as e:
                logger.warning(f"Validation error in generation {generation}, replacing invalid child: {e}")
                child = generate_array() 
            new_population.append(child)

        population = new_population
        
        # Dynamic Mutation Rate Adjustment
        if mutation_rate > 0.02:
            mutation_rate *= MUTATION_DECAY_RATE

        # Logging and monitoring
        best_fitness = max(fitnesses)
        logger.info(f"Generation {generation}: Best Fitness: {best_fitness}, Mutation Rate: {mutation_rate:.4f}, Tournament Size: {tournament_size}")

    # Return the best solution found
    best_index = np.argmax(fitnesses)
    if is_array_valid(population[best_index]):
        return population[best_index], fitnesses[best_index]
    else:
        return generate_array(), 0

# Run the genetic algorithm
t1 = time.perf_counter()
best_solution, best_fitness = genetic_algorithm()
new_matrix = validate_array(best_solution)
print("Best solution found:", new_matrix)
logger.info(f"Best fitness: {best_fitness}")
t2 = time.perf_counter()
logger.info(f"Time taken {t2 - t1} seconds")
logger.info(reactor_metrics(new_matrix, CURRENT_FUEL))
plot_grid(new_matrix, 'visualization/img')
logger.info(f"Saved to {plot_grid.__name__}")

best_cyb = np.array([[
        [12, 1, 12],
        [12, 1, 12],
        [12, 1, 12]],

        [[1, 2, 1],
        [1, 2, 1],
        [1, 2, 1]],

        [[12, 1, 12],
        [12, 1, 12],
        [12, 1, 12]]], dtype=int)




print("cyb1024 benchmark score for 3x3x3: ", fitness(best_cyb, CURRENT_FUEL))
print("Cyb Metrics: ", reactor_metrics(best_cyb, CURRENT_FUEL))

plot_grid(best_cyb, 'visualization/img/cyb')

print("Score of this array: {invalid_aray_zeroes}", fitness(best_solution, CURRENT_FUEL))
print("Metrics of this array: ", reactor_metrics(best_solution, CURRENT_FUEL))
