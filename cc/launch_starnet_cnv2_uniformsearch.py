import os
import itertools
import numpy as np

# Starting number for jobs
start_model_num = 55
num_models = 30

# [Min, max, num_decimals]
'''uniform_params = {'lr': [0.0001, 0.01, 4],
               'lrf': [100, 10000, -2],
              'ti': [10000, 60000, -3],
              'mr': [0.2, 0.8, 2],
              'wd': [0.001, 0.05, 3],
              'lplr': [0.0001, 0.01, 4],
              'lplrf': [100, 10000, -2],
              'lpti': [10000, 40000, -3],
              'lpdo': [0, 0.3, 2]}'''

uniform_params = {'lr': [0.001, 0.005, 3],
               'lrf': [500, 1500, -2],
              'ti': [20000, 40000, -3],
              'mr': [0.4, 0.7, 2],
              'wd': [0.001, 0.01, 3],
              'lplr': [0.00001, 0.001, 4],
              'lplrf': [100, 2000, -2],
              'lpti': [20000, 40000, -3],
              'lpdo': [0, 0.1, 2],
                 'tlw': [0.1, 10, 1],
                 'mnf': [0.01,0.2,2]}

# Create a list of all possible parameter combinations
#keys, values = zip(*grid_params.items())
#param_combos = [dict(zip(keys, v)) for v in itertools.product(*values)]
print('Launching %i models' % (num_models))

# Each model will draw all of the parameters from a uniform distribution
for model_num in range(start_model_num, start_model_num+num_models):
    param_cmd = ''
    for k, vals in uniform_params.items():
        # Sample from uniform distbn
        val = np.random.uniform(vals[0], vals[1])
        # Round to correct decimals
        val = np.round(val, vals[2])
        if vals[2]<=0:
            val=int(val)
        param_cmd += '-%s %s '% (k, val)
    
    launch_cmd = ('python launch_starnet_cnv2.py starnet_cnv2_%i' % (model_num) +
                  ' %s -co " %s"' % (param_cmd, param_cmd))
    print(launch_cmd)
    
    
    # Execute jobs
    os.system(launch_cmd)
