import numpy as np
import os
import sys
import argparse
import configparser

def parseArguments():
    # Create argument parser
    parser = argparse.ArgumentParser()

    # Positional mandatory arguments
    parser.add_argument("model_name", help="Name of model.", type=str)

    ## Optional arguments
    
    # Job params
    parser.add_argument("-v", "--verbose_iters", 
                        help="Number of batch iters after which to evaluate val set and display output.", 
                        type=int, default=1000)
    parser.add_argument("-ct", "--cp_time", 
                        help="Number of minutes after which to save a checkpoint.", 
                        type=float, default=5)
    parser.add_argument("-n", "--num_runs", 
                        help="Number of jobs to run for this simulation.", 
                        type=int, default=1)
    parser.add_argument("-acc", "--account", 
                        help="Compute Canada account to run jobs under.", 
                        type=str, default='def-sfabbro')
    parser.add_argument("-mem", "--memory", 
                        help="Memory per job in GB.", 
                        type=int, default=16)
    parser.add_argument("-ncp", "--num_cpu", 
                        help="Number of CPU cores per job.", 
                        type=int, default=10)
    
    # Config params
    parser.add_argument("-sfn", "--source_data_file", 
                        help="Source data file for training.", 
                        type=str, default='gaia_grid_crossref.h5') 
    parser.add_argument("-tfn", "--target_data_file", 
                        help="Target data file for training.", 
                        type=str, default='gaia_observed_crossref.h5') 
    parser.add_argument("-lk", "--label_keys",  type=str, nargs='+',
                        help="Dataset keys for labels in data file.", 
                        default="['teff', 'feh', 'logg', 'alpha']") 
    parser.add_argument("-tvs", "--target_val_survey", 
                        help="Survey for target domain validation label data.", 
                        type=str, default='APOGEE') 
    parser.add_argument("-mnf", "--max_noise_factor", 
                        help="Maximum fraction of continuum to set random noise to.", 
                        type=float, default=0.0)
    
    parser.add_argument("-bs", "--batch_size", 
                        help="Training batchsize.", 
                        type=int, default=256)
    parser.add_argument("-lr", "--lr", 
                        help="Initial learning rate.", 
                        type=float, default=0.003)
    parser.add_argument("-lrf", "--final_lr_factor", 
                        help="Final lr will be lr/lrf.", 
                        type=float, default=1000.0)
    parser.add_argument("-wd", "--weight_decay", 
                        help="Weight decay for AdamW optimizer.", 
                        type=float, default=0.0001)
    parser.add_argument("-ti", "--total_batch_iters", 
                        help="Total number of batch iterations for training.", 
                        type=int, default=60000)

    parser.add_argument("-ssz", "--spectrum_size", 
                        help="Number of flux values in spectrum.", 
                        type=int, default=800)
    parser.add_argument("-nf", "--num_filters", 
                        help="Number of filters in each conv layer.", 
                        type=int, nargs='+', default=[4, 16])
    parser.add_argument("-fl", "--filter_length", 
                        help="Length of the conv filters.", 
                        type=int, default=8)
    parser.add_argument("-pl", "--pool_length", 
                        help="Length of the pooling filter.", 
                        default=4)
    parser.add_argument("-nh", "--num_hidden", 
                        help="Number of nodes in each fully connected layer.", 
                        type=int, nargs='+', default=[256, 128])
    
    parser.add_argument("-co", "--comment", 
                        help="Comment for config file.", 
                        default='Original.')
    
    # Parse arguments
    args = parser.parse_args()

    return args

# Directories
cur_dir = os.path.dirname(os.path.realpath(__file__))
data_dir = os.path.join(cur_dir, '../data')
model_dir = os.path.join(cur_dir, '../models/')
training_script1 = os.path.join(cur_dir, '../train_starnet.py')
testing_script1 = os.path.join(cur_dir, '../test_starnet.py')

# Read command line arguments
args = parseArguments()

# Configuration filename
config_fn = os.path.join(cur_dir, '../configs', args.model_name+'.ini')
if os.path.isfile(config_fn):
    good_to_go = False
    while not good_to_go: 
        user_input = input('This config file already exists, would you like to:\n'+
                           '-Overwrite the file (o)\n' + 
                           '-Run the existing file for another %i runs (r)\n' % (args.num_runs) + 
                           '-Or cancel (c)?\n')
        if (user_input=='o') or (user_input=='r') or (user_input=='c'):
            good_to_go = True
        else:
            print('Please choose "o" "r" or "c"')
else:
    user_input = 'o' 

if user_input=='c':
    sys.exit()  
elif user_input=='o':
    # Create new configuration file
    config = configparser.ConfigParser()
    
    config['DATA'] = {'source_data_file': args.source_data_file, 
                      'target_data_file': args.target_data_file, 
                      'label_keys': args.label_keys,
                      'target_val_survey': args.target_val_survey,
                      'max_noise_factor': args.max_noise_factor}
    
    config['TRAINING'] = {'batch_size': args.batch_size,
                          'lr': args.lr,
                          'final_lr_factor': args.final_lr_factor,
                          'weight_decay': args.weight_decay,
                          'total_batch_iters': args.total_batch_iters}
    
    config['ARCHITECTURE'] = {'spectrum_size': args.spectrum_size,
                              'num_filters': args.num_filters,
                              'filter_length': args.filter_length,
                              'pool_length': args.pool_length,
                              'num_hidden': args.num_hidden}
        
    config['Notes'] = {'comment': args.comment}

    with open(config_fn, 'w') as configfile:
        config.write(configfile)
        
    source_data_file = args.source_data_file
    target_data_file = args.target_data_file
    
    # Delete existing model file
    model_filename =  os.path.join(model_dir, args.model_name+'.pth.tar')
    if os.path.exists(model_filename):
        os.remove(model_filename)

elif user_input=='r':
    config = configparser.ConfigParser()
    config.read(config_fn)
    source_data_file = os.path.join(data_dir, config['DATA']['source_data_file'])
    target_data_file = os.path.join(data_dir, config['DATA']['target_data_file'])

todo_dir = os.path.join(cur_dir, '../scripts/todo')
done_dir = os.path.join(cur_dir, '../scripts/done')
stdout_dir = os.path.join(cur_dir, '../scripts/stdout')

# Create script directories
if not os.path.exists(os.path.join(cur_dir,'../scripts')):
    os.mkdir(os.path.join(cur_dir,'../scripts'))
if not os.path.exists(todo_dir):
    os.mkdir(todo_dir)
if not os.path.exists(done_dir):
    os.mkdir(done_dir)
if not os.path.exists(stdout_dir):
    os.mkdir(stdout_dir)

# Create script file
script_fn = os.path.join(todo_dir, args.model_name+'.sh')
with open(script_fn, 'w') as f:
    f.write('#!/bin/bash\n\n')
    f.write('# Module loads\n')
    for line in open(os.path.join(cur_dir,'module_loads.txt'), 'r').readlines():
        f.write(line)
    f.write('\n\n')
    f.write('# Copy files to slurm directory\n')
    f.write('cp %s $SLURM_TMPDIR\n' % (os.path.join(data_dir, source_data_file)))
    f.write('cp %s $SLURM_TMPDIR\n' % (os.path.join(data_dir, target_data_file)))
    f.write('# Run training\n')
    f.write('python %s %s -v %i -ct %0.2f -dd $SLURM_TMPDIR/\n' % (training_script1, 
                                                                   args.model_name,
                                                                   args.verbose_iters, 
                                                                   args.cp_time))
    f.write('\n# Run testing\n')
    f.write('python %s %s -dd $SLURM_TMPDIR/\n' % (testing_script1,
                                                   args.model_name))

# Compute-canada goodies command
cmd = 'python %s ' % (os.path.join(cur_dir, 'queue_cc.py'))
cmd += '--account "%s" --todo_dir "%s" ' % (args.account, todo_dir)
cmd += '--done_dir "%s" --output_dir "%s" ' % (done_dir, stdout_dir)
cmd += '--num_jobs 1 --num_runs %i --num_gpu 1 ' % (args.num_runs)
cmd += '--num_cpu %i --mem %sG --time_limit "00-01:00"' % (args.num_cpu, args.memory)

# Execute jobs
os.system(cmd)
