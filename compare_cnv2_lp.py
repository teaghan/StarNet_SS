import torch
import os
import numpy as np
import configparser
import glob
# Directory of training script
cur_dir = os.path.dirname(__file__)
import sys
sys.path.append(os.path.join(cur_dir,'cnv2_utils'))
from training_utils import str2bool, parseArguments, LARS

# Directories
cur_dir = os.path.dirname(__file__)
model_dir = os.path.join(cur_dir, 'models/')
config_dir = os.path.join(cur_dir, 'configs/')
results_dir = os.path.join(cur_dir, 'results/')


models_compare = []
incomplete_models = []
for i in range(4,55):
    model_name = 'starnet_cnv2_%i'%i

    model_filename = os.path.join(model_dir,model_name+'_lp.pth.tar')
        
    try:
        # Try loading model
        checkpoint = torch.load(model_filename, map_location=lambda storage, loc: storage)
        losses = dict(checkpoint['losses'])
    except:
        print('Model %i couldn\'t be opened.' %i)
        incomplete_models.append(i)
        continue
        
    try:
        # Load predictions
        src_preds = np.load(os.path.join(results_dir, '%s_source_preds.npy'%model_name))
        src_tgts = np.load(os.path.join(results_dir, '%s_source_tgts.npy'%model_name))
        src_feats = np.load(os.path.join(results_dir, '%s_source_feature_maps.npy'%model_name))
        tgt_preds = np.load(os.path.join(results_dir, '%s_target_preds.npy'%model_name))
        tgt_tgts = np.load(os.path.join(results_dir, '%s_target_tgts.npy'%model_name))
        tgt_feats = np.load(os.path.join(results_dir, '%s_target_feature_maps.npy'%model_name))
        
    except:
        print('Model %i broken hasn\'t finished training (%i/%s)' % (i, losses['lp_batch_iters'][-1], config['LINEAR PROBE TRAINING']['total_batch_iters']))
        incomplete_models.append(i)
        continue
    
    # Calculate MAE
    src_mae = np.mean(np.abs(src_preds-src_tgts), axis=0)
    tgt_mae = np.mean(np.abs(tgt_preds-tgt_tgts), axis=0)
    feature_loss = np.mean(np.abs(src_feats-tgt_feats))
    
    # Normalize labels
    label_means = np.mean(src_tgts, axis=0)
    label_stds = np.std(src_tgts, axis=0)
    src_preds = (src_preds - label_means) / label_stds 
    src_tgts = (src_tgts - label_means) / label_stds 
    tgt_preds = (tgt_preds - label_means) / label_stds 
    tgt_tgts = (tgt_tgts - label_means) / label_stds 
    
    # Calculate normalized MAE
    src_mae_norm = np.mean(np.abs(src_preds-src_tgts))
    tgt_mae_norm = np.mean(np.abs(tgt_preds-tgt_tgts))
    
    models_compare.append([i, src_mae[0], tgt_mae[0], 
                               src_mae[1], tgt_mae[1], 
                               src_mae[2], tgt_mae[2], 
                               src_mae[3], tgt_mae[3],
                           src_mae_norm, tgt_mae_norm,
                               feature_loss])
    # Model configuration
    config = configparser.ConfigParser()
    config.read(config_dir+model_name+'.ini')
    print('Model %i: %s' % (i, config['Notes']['comment']))
    print('\tBatch iters: %i' % (losses['lp_batch_iters'][-1]))
    print('\tSrc Labels: %0.0f, %0.3f, %0.2f, %0.4f' % (src_mae[0], src_mae[1], 
                                       src_mae[2], src_mae[3]))
    print('\tTgt Labels: %0.0f, %0.3f, %0.2f, %0.4f' % (tgt_mae[0], tgt_mae[1], 
                                       tgt_mae[2], tgt_mae[3]))
    print('\tFeatures: %0.5f' % (feature_loss))
    print('\tSrc MAE: %0.5f' % (src_mae_norm))
    print('\tTgt MAE: %0.5f\n' % (tgt_mae_norm))

models_compare = np.array(models_compare)
print('Model %i performed the best at predicting source Teff labels with %0.5f' % (models_compare[np.nanargmin(models_compare[:,1]),0], models_compare[np.nanargmin(models_compare[:,1]),1]))
print('Model %i performed the best at predicting target Teff labels with %0.5f' % (models_compare[np.nanargmin(models_compare[:,2]),0],
models_compare[np.nanargmin(models_compare[:,2]),2]))
print('Model %i performed the best at predicting source Fe/H labels with %0.5f' % (models_compare[np.nanargmin(models_compare[:,3]),0], 
                            models_compare[np.nanargmin(models_compare[:,3]),3]))
print('Model %i performed the best at predicting target Fe/H labels with %0.5f' % (models_compare[np.nanargmin(models_compare[:,4]),0],
models_compare[np.nanargmin(models_compare[:,4]),4]))
print('Model %i performed the best at predicting source log(g) labels with %0.5f' % (models_compare[np.nanargmin(models_compare[:,5]),0], 
                            models_compare[np.nanargmin(models_compare[:,5]),5]))
print('Model %i performed the best at predicting target log(g) labels with %0.5f' % (models_compare[np.nanargmin(models_compare[:,6]),0],
models_compare[np.nanargmin(models_compare[:,6]),6]))

print('Model %i performed the best at predicting source alpha/H labels with %0.5f' % (models_compare[np.nanargmin(models_compare[:,7]),0], 
                            models_compare[np.nanargmin(models_compare[:,7]),7]))
print('Model %i performed the best at predicting target alpha/H labels with %0.5f' % (models_compare[np.nanargmin(models_compare[:,8]),0],
models_compare[np.nanargmin(models_compare[:,8]),8]))

print('Model %i performed the best at matching the features with %0.5f' % (models_compare[np.nanargmin(models_compare[:,11]),0],
models_compare[np.nanargmin(models_compare[:,11]),11]))

print('Model %i performed the best on source domain with an MAE of %0.5f' % (models_compare[np.nanargmin(models_compare[:,9]),0],
models_compare[np.nanargmin(models_compare[:,9]),9]))

print('Model %i performed the best on target domain with an MAE of %0.5f' % (models_compare[np.nanargmin(models_compare[:,10]),0],
models_compare[np.nanargmin(models_compare[:,10]),10]))

if len(incomplete_models)>0:
    print('Incomplete model(s):')
    for i in incomplete_models:
        print(i)
