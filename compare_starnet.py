import torch
import os
import numpy as np
import configparser
import glob

# Directories
cur_dir = os.path.dirname(__file__)
model_dir = os.path.join(cur_dir, 'models/')
config_dir = os.path.join(cur_dir, 'configs/')

models_compare = []
incomplete_models = []
for i in range(2, 224):
    model_name = 'starnet_%i'%i

    model_filenames =  glob.glob(os.path.join(model_dir,model_name+'_*.pth.tar'))
    if len(model_filenames)==0:
        model_filenames =  [os.path.join(model_dir,model_name+'.pth.tar')]

    for model_filename in model_filenames:
        
        try:
            # Try loading model
            checkpoint = torch.load(model_filename, map_location=lambda storage, loc: storage)
            
            model_name = model_filename.split('/')[-1].split('.')[0]
            
            # Model configuration
            config = configparser.ConfigParser()
            config.read(config_dir+model_name+'.ini')

            losses = dict(checkpoint['losses'])
            src_loss = np.mean(losses['val_source_loss'][-3:])
            tgt_loss = np.mean(losses['val_target_loss'][-3:])

            models_compare.append([i, src_loss, tgt_loss])
            print('Model %i: %s' % (i, config['Notes']['comment']))
            
            batch_iters = losses['batch_iters'][-1]
            if batch_iters<int(config['TRAINING']['total_batch_iters']):
                print('Incomplete training.')
                incomplete_models.append(i)
            
            print('\tBatch iters: %i' % (batch_iters))
            print('\tSrc Loss: %0.6f' % (src_loss))
            print('\tTgt Loss: %0.6f' % (tgt_loss))
        except:
            print('Model %i broken. Rerunning' %i)    
            '''
            try:
                os.remove(model_filename)
            except:
                pass

            cmd = 'python launch_starnet_ss.py %s -n 1' % model_name
            print(cmd)
            os.system(cmd)
            '''
            continue

print('Incomplete models:')
for i in incomplete_models:
    print(i)

models_compare = np.array(models_compare)
print('Model %i performed the best at predicting source labels with %0.5f' % (models_compare[np.nanargmin(models_compare[:,1]),0], models_compare[np.nanargmin(models_compare[:,1]),1]))
print('Model %i performed the best at predicting target labels with %0.5f' % (models_compare[np.nanargmin(models_compare[:,2]),0],
models_compare[np.nanargmin(models_compare[:,2]),2]))

