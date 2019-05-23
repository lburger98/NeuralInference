#! /usr/bin/python2.7
from Bishop import *
from nltk import Tree
import numpy as np
import random
import string

HUMAN_READABLE = False
DEBUG = False

rules = ['OR', 'AND', 'THEN', "OBJ"]
total_objects = 15
objects = list(string.ascii_uppercase)[:total_objects] # first total_objects uppercase letters 
grid_size = 100

# FULL SIZE DATA SET
# map_count = 1000
# bias_count = 50
# desire_count = 100
# starting_point_count = 100
# agent_count = 100
# grid_size = 100

# SMALLER SIZE DATA SET
map_count = 1
bias_count = 1
desire_count = 10
starting_point_count = 3
agent_count = 20

cost_matrix = np.zeros((grid_size, grid_size))

# NOTES/IDEAS:

# idea - new CFG rules could be related to positional arangement (whichever is above)
	# inclusive or

# read machine tom paper
	# copy their method for object/starting representations
	# then show one layer w/ trajectory

# figure out how many epochs to run w/o over fitting - use some sort of visualization
# getting a sense of the error that its making
	# research which error function to use (cross entropy)

def generate_map():
	# CONFIRM: is this the right way to sample? (poisson?)
	number_of_objects = bounded_poisson(round(len(objects)/2), 1, len(objects))
	selected_objects = random.sample(objects, number_of_objects)
	obj_locs = {}

	for obj in objects:
		if obj not in selected_objects:
			obj_locs[obj] = None
		else:
			obj_locs[obj] = np.random.randint(0, grid_size)

	return obj_locs

def bounded_poisson(mean, start, end):
	rand = np.random.poisson(mean, 1)[0]
	if rand <= start: rand = start
	if rand >= end: rand = end
	return rand

def zero_bias(bias):
	zero_count = bounded_poisson(round(len(bias)/4), 0, len(bias)-1)
	to_be_zeroed = random.sample(range(len(bias)), zero_count)
	for i in to_be_zeroed:
		bias[i] = 0
	return bias

def generate_biases(obj_locs):
	# CONFIRM: is this right? - this can lead to probs all zero
	obj_bias = np.zeros((len(objects))) + 1
	obj_bias = zero_bias(obj_bias)
	for i in range(len(objects)):
		obj = objects[i]
		if obj_locs[obj] == None:
			obj_bias[i] = 0
		elif obj_bias[i] != 0:
			obj_bias[i] = np.random.uniform(0,1)


	rule_bias = np.zeros((len(rules))) + 1
	rule_bias = zero_bias(rule_bias)
	for j in range(len(rules)):
		if rule_bias[j] != 0:
			rule_bias[j] = np.random.uniform(0,1)

	if sum(rule_bias) > 0: rule_bias /= float(sum(rule_bias))
	if sum(obj_bias) > 0: obj_bias /= float(sum(obj_bias))

	return rule_bias, obj_bias

def sample_distribution(probs):
	assert sum(probs) > 0
	# return an index given a probability distribution
	random = np.random.uniform(0,sum(probs))
	total = 0
	i = 0
	for p in probs:
		total += p
		if random <= total:
			return i
		i += 1
	return i

def generate_desire(rule_bias, obj_bias, d=0):
	# CONFIRM: if object on left can't be on right
	# given a rule and object bias construct a desire CFG
	rule = rules[sample_distribution(rule_bias)]
	obj_bias_copy = [x for x in obj_bias]

	if rule != 'OBJ' and np.count_nonzero(obj_bias) > 2 ** d: 
		lh_desire, lh_objs = generate_desire(rule_bias, obj_bias_copy, d+1)

		for obj in lh_objs:
			obj_bias_copy[objects.index(obj)] = 0

		rh_desire, rh_objs = generate_desire(rule_bias, obj_bias_copy, d+1)
		used_objects = lh_objs + rh_objs

		return Tree(rule, [lh_desire, rh_desire]), used_objects
	else:
		obj = objects[sample_distribution(obj_bias)]
		return obj, [obj]

def generate_intentions(expression):
	# enumerate all possible intentions from a desire CFG
	if type(expression) == str: # if expression is object return (base case)
		return [ expression ]

	results = []
	rule = expression.label()
	lhs = generate_intentions(expression[0])
	rhs = generate_intentions(expression[1])
	
	if rule == 'OR':
		for i in lhs:
			results.append(i)
		for j in rhs:
			results.append(j)
	elif rule == 'AND':
		for i in lhs:
			for j in rhs:
				results.append(i+j)
				results.append(j+i)
	elif rule == 'THEN':
		for i in lhs:
			for j in rhs:
				results.append(i+j)

	results = list(set(results)) # dedup intentions
	return results

def update_obs(start=None, end=None):
	assert start != None and end != None, "needs start and end"
	obs.SetStartingPoint(start, 0)
	obs.Plr.Map.AddExitState(end)
	obs.Plr.Prepare()
	return

def choose_intention(intentions, starting_point):
	best_cost = float('-Inf')
	best_intention = None

	for intention in intentions:
		cost = 0
		next_starting_point = starting_point # set intial starting point

		for i in intention:

			if cost_matrix[next_starting_point, obj_locs[i]] != 0:
				cost += cost_matrix[next_starting_point, obj_locs[i]]
			else:
				update_obs(next_starting_point, obj_locs[i])

				cost += obs.Plr.CostMatrix[ 0 , 2 ] # cost from start state to end state on one obj
				cost_matrix[next_starting_point, obj_locs[i]] = obs.Plr.CostMatrix[ 0 , 2 ]
			next_starting_point = obj_locs[i]

		if cost >= best_cost:
			best_cost = cost
			best_intention = intention

	return best_intention

def generate_actions_and_states(intention, starting_point):
	# create action list for a given intention (one simulation)
	actions = [[] for _ in range(agent_count)]
	states = [[] for _ in range(agent_count)]
	next_starting_point = starting_point # set intial starting point
	
	for i in intention:
		update_obs(next_starting_point, obj_locs[i])
		agent_sequence = obs.SimulateAgents(agent_count, HUMAN_READABLE, Verbose=False)

		actions = np.concatenate((actions, agent_sequence.Actions), axis=1)
		states = np.concatenate((states, agent_sequence.States), axis=1)

		next_starting_point = obs.Plr.Map.ExitState

	return actions, states


def save_to_csv(obj_locs, starting_points, rule_bias, obj_bias, actions, states, training_data_file_count):
	#Confirm
	row_size = 2*total_objects + len(rule_bias) + (2*grid_size) + 1
	actions_base_index = row_size - (2*grid_size)
	states_base_index = row_size - (grid_size)

	table = np.zeros((agent_count*starting_point_count, row_size))

	for i in range(total_objects):
		obj = objects[i]
		if obj_locs[obj] != None:
			table[:,i] = obj_locs[obj]
		else:
			table[:,i] = -1
	table[:, total_objects+1:len(rule_bias)+total_objects+1] = rule_bias
	table[:, len(rule_bias)+total_objects+1: len(rule_bias)+(2*total_objects)+1] = obj_bias

	row_index = 0
	for s in range(starting_point_count):

		for a in range(agent_count):
			table[row_index, total_objects] = starting_points[s]
			for g in range(grid_size):
				if g < len(actions[s][a]):
					table[row_index, actions_base_index+g] = actions[s][a][g]
				else:
					table[row_index, actions_base_index+g] = -1
				if g < len(states[s][a]):
					table[row_index, states_base_index+g] = states[s][a][g]
				else:
					table[row_index, states_base_index+g] = -1

			row_index += 1

	np.savetxt("training_data/%d.csv" % training_data_file_count, table, delimiter=",")

obs = LoadObserver("Map", 0, 0)
training_data_file_count = 0

for _ in range(map_count):

	obj_locs = generate_map()

	for _ in range(bias_count):

		rule_bias, obj_bias = generate_biases(obj_locs)

		for _ in range(desire_count):

			desire, _ = generate_desire(rule_bias, obj_bias)
			intentions = generate_intentions(desire)
			actions = []
			states = []
			starting_points = []

			for _ in range(starting_point_count):

				starting_point = np.random.randint(0, grid_size) # CONFIRM: right probs?
				intention = choose_intention(intentions, starting_point)
				a, s = generate_actions_and_states(intention, starting_point)
				actions.append(a)
				states.append(s)
				starting_points.append(starting_point)

			
				# Pretty print
				if DEBUG:
					print(obj_locs)
					print("Rule Bias:")
					print(rule_bias)
					print("Object Bias:")
					print(obj_bias)
					print("Desire:")
					print(desire)
					print(intention)
					print(actions)

			save_to_csv(obj_locs, starting_points, rule_bias, obj_bias, actions, states, training_data_file_count)
			training_data_file_count += 1

