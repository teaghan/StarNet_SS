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
                        type=int, default=5000)
    parser.add_argument("-ct", "--cp_time", 
                        help="Number of minutes after which to save a checkpoint.", 
                        type=float, default=10)
    parser.add_argument("-n", "--num_runs", 
                        help="Number of jobs to run for this simulation.", 
                        type=int, default=6)
    parser.add_argument("-acc", "--account", 
                        help="Compute Canada account to run jobs under.", 
                        type=str, default='def-sfabbro')
    parser.add_argument("-mem", "--memory", 
                        help="Memory per job in GB.", 
                        type=int, default=16)
    parser.add_argument("-ncp", "--num_cpu", 
                        help="Number of CPU cores per job.", 
                        type=int, default=11)
    
    # Config params
    parser.add_argument("-sfn", "--source_data_file", 
                        help="Source data file for training.", 
                        type=str, default='ambre.h5') 
    parser.add_argument("-tfn", "--target_data_file", 
                        help="Target data file for training.", 
                        type=str, default='golden_sample.h5') 
    parser.add_argument("-wfn", "--wave_grid_file", 
                        help="Wave grid file.", 
                        type=str, default='weave_hr_wavegrid_arms.npy')
    parser.add_argument("-mmk", "--multimodal_keys",  type=str, nargs='+',
                        help="Dataset keys for labels in data file.", 
                        default="['teff', 'feh', 'logg', 'alpha']") 
    parser.add_argument("-umk", "--unimodal_keys",  type=str, nargs='+',
                        help="Dataset keys for labels in data file.", 
                        default="['vrad']") 
    parser.add_argument("-cn", "--continuum_normalize", 
                        help="Whether or not to continuum normalize each spectrum.", 
                        type=str, default='True')
    parser.add_argument("-dbm", "--divide_by_median", 
                        help="Whether or not to divide each spectrum by its median value.", 
                        type=str, default='False')
    parser.add_argument("-an", "--add_noise_to_source", 
                        help="Whether or not to add noise to source spectra during training.", 
                        type=str, default='True')
    parser.add_argument("-rc", "--random_chunk", 
                        help="Whether or not to choose random parts of each spectrum.", 
                        type=str, default='True')
    parser.add_argument("-ov", "--overlap", 
                        help="The overlap between neighbouring chunks.", 
                        type=float, default=0.5)
    
    parser.add_argument("-bs", "--batchsize", 
                        help="Training batchsize.", 
                        type=int, default=8)
    parser.add_argument("-lr", "--lr", 
                        help="Initial learning rate.", 
                        type=float, default=0.001)
    parser.add_argument("-wd", "--weight_decay", 
                        help="Weight decay for AdamW optimizer.", 
                        type=float, default=0.01)
    parser.add_argument("-ti", "--total_batch_iters", 
                        help="Total number of batch iterations for training.", 
                        type=int, default=500000)
    parser.add_argument("-smw", "--source_mm_weights", 
                        help="Loss weights for the multimodal NLL in the source domain.", 
                        default=[5.0, 5.0, 5.0, 5.0])
    parser.add_argument("-suw", "--source_um_weights", 
                        help="Loss weights for the unimodal MSE in the source domain.", 
                        default=[0.1])
    parser.add_argument("-tfw", "--target_feature_weight", 
                        help="Loss weight for the feature comparison in the target domain.", 
                        type=float, default=1.)
    parser.add_argument("-sfw", "--source_feature_weight", 
                        help="Loss weight for the feature comparison in the source domain.", 
                        type=float, default=1.)
    parser.add_argument("-ttw", "--target_task_weights", 
                        help="Loss weights for each task in the target domain.", 
                        default=[0.1, 0.05, 0.05, 0.1])
    parser.add_argument("-stw", "--source_task_weights", 
                        help="Loss weights for each task in the target domain.", 
                        default=[0.1, 0.05, 0.05, 0.1])
    
    parser.add_argument("-nf", "--num_fluxes", 
                        help="Number of flux values used as input to model.", 
                        type=int, default=6000)
    parser.add_argument("-ssz", "--spectrum_size", 
                        help="Number of flux values in spectrum.", 
                        type=int, default=43480)
    parser.add_argument("-ed", "--encoder_dim", 
                        help="Dimension of positional encoder (use 0 to not use positional encoder).", 
                        type=int, default=18)
    parser.add_argument("-cwsh", "--conv_widths_sh", 
                        help="Number of to use in each stage of the ConvNext model.", 
                        default=[32, 64, 128, 128])
    parser.add_argument("-cdsh", "--conv_depths_sh", 
                        help="Depth of each stage of the ConvNext model.", 
                        default=[3, 4, 6, 4])
    parser.add_argument("-sfsh", "--stem_features_sh", 
                        help="Number of features to use in initial stem layer of the ConvNext model.", 
                        type=int, default=32)
    parser.add_argument("-cf", "--conv_filts_sp", 
                        help="Number of filters in conv layers.", 
                        default=[32])
    parser.add_argument("-fl", "--filter_lengths_sp", 
                        help="Length of filters in conv layers.", 
                        default=[7])
    parser.add_argument("-cs", "--conv_strides_sp", 
                        help="Stride length of filters in conv layers.", 
                        default=[2])
    parser.add_argument("-pl", "--pool_length", 
                        help="Output size of pooling layer (use 0 for no pooling).", 
                        default=1)
    parser.add_argument("-umm", "--unimodal_means", 
                        help="Mean value of each label used for normalization.", 
                        default=[0])
    parser.add_argument("-ums", "--unimodal_stds", 
                        help="Standard deviation of each label used for normalization.", 
                        default=[50])
    parser.add_argument("-sm", "--spectra_mean", 
                        help="Number of flux values in spectrum.", 
                        type=float, default=0.883)
    parser.add_argument("-ss", "--spectra_std", 
                        help="Number of flux values in spectrum.", 
                        type=float, default=0.192)
    parser.add_argument("-ta", "--tasks", type=str, nargs='+',
                        help="Names of the tasks to use during training.", 
                        default=['wavelength', 'slope', 'bias', 'snr'])
    parser.add_argument("-tm", "--task_means", 
                        help="Mean value of each task label used for normalization.", 
                        default=[5416,0,0.0,30])
    parser.add_argument("-ts", "--task_stds", 
                        help="Standard deviation of each task label used for normalization.", 
                        default=[900,5e-05,0.1,60])
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
training_script = os.path.join(cur_dir, '../train_starnet_ss.py')
testing_script = os.path.join(cur_dir, '../test_starnet_ss.py')

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
                      'wave_grid_file': args.wave_grid_file, 
                      'multimodal_keys': args.multimodal_keys,
                      'unimodal_keys': args.unimodal_keys,
                      'continuum_normalize': args.continuum_normalize,
                      'divide_by_median': args.divide_by_median,
                      'add_noise_to_source': args.add_noise_to_source,
                      'random_chunk': args.random_chunk,
                      'overlap': args.overlap}

    config['TRAINING'] = {'batchsize': args.batchsize,
                          'lr': args.lr,
                          'weight_decay': args.weight_decay,
                          'total_batch_iters': args.total_batch_iters,
                          'source_mm_weights': args.source_mm_weights,
                          'source_um_weights': args.source_um_weights,
                          'target_feature_weight': args.target_feature_weight,
                          'source_feature_weight': args.source_feature_weight,
                          'source_task_weights': args.source_task_weights,
                          'target_task_weights': args.target_task_weights}
    
    config['ARCHITECTURE'] = {'spectrum_size': args.spectrum_size,
                              'num_fluxes': args.num_fluxes,
                              'encoder_dim': args.encoder_dim,
                              'conv_widths_sh': args.conv_widths_sh,
                              'conv_depths_sh': args.conv_depths_sh,
                              'stem_features_sh': args.stem_features_sh,
                              'conv_filts_sp': args.conv_filts_sp,
                              'conv_strides_sp': args.conv_strides_sp,
                              'filter_lengths_sp': args.filter_lengths_sp,
                              'pool_length': args.pool_length,
                              'unimodal_means': args.unimodal_means,
                              'unimodal_stds': args.unimodal_stds,
                              'spectra_mean': args.spectra_mean,
                              'spectra_std': args.spectra_std,
                              'tasks': args.tasks,
                              'task_means': args.task_means,
                              'task_stds': args.task_stds}
        
    config['Notes'] = {'comment': args.comment}

    with open(config_fn, 'w') as configfile:
        config.write(configfile)
        
    source_data_file = args.source_data_file
    target_data_file = args.target_data_file
    wave_grid_file = args.wave_grid_file
    
    # Delete existing model file
    model_filename =  os.path.join(model_dir, args.model_name+'.pth.tar')
    if os.path.exists(model_filename):
        os.remove(model_filename)
        
elif user_input=='r':
    config = configparser.ConfigParser()
    config.read(config_fn)
    source_data_file = os.path.join(data_dir, config['DATA']['source_data_file'])
    target_data_file = os.path.join(data_dir, config['DATA']['target_data_file'])
    wave_grid_file = os.path.join(data_dir, config['DATA']['wave_grid_file'])

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
    f.write('cp %s $SLURM_TMPDIR\n\n' % (os.path.join(data_dir, wave_grid_file)))
    f.write('# Run training\n')
    f.write('python %s %s -v %i -ct %0.2f -dd $SLURM_TMPDIR/\n' % (training_script, 
                                                                   args.model_name,
                                                                   args.verbose_iters, 
                                                                   args.cp_time))
    f.write('\n# Run testing\n')
    f.write('python %s %s -dd $SLURM_TMPDIR/\n' % (testing_script,
                                                   args.model_name))

# Compute-canada goodies command
cmd = 'python %s ' % (os.path.join(cur_dir, 'queue_cc.py'))
cmd += '--account "%s" --todo_dir "%s" ' % (args.account, todo_dir)
cmd += '--done_dir "%s" --output_dir "%s" ' % (done_dir, stdout_dir)
cmd += '--num_jobs 1 --num_runs %i --num_gpu 1 ' % (args.num_runs)
cmd += '--num_cpu %i --mem %sG --time_limit "00-03:00"' % (args.num_cpu, args.memory)

# Execute jobs
os.system(cmd)