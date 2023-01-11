import torch
import argparse
from torch.optim.lr_scheduler import LambdaLR

def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")

def parseArguments():
    # Create argument parser
    parser = argparse.ArgumentParser()

    # Positional mandatory arguments
    parser.add_argument("model_name", help="Name of model.", type=str)

    # Optional arguments
    
    # How often to display the losses
    parser.add_argument("-v", "--verbose_iters", 
                        help="Number of batch  iters after which to evaluate val set and display output.", 
                        type=int, default=10000)
    
    # How often to display save the model
    parser.add_argument("-ct", "--cp_time", 
                        help="Number of minutes after which to save a checkpoint.", 
                        type=float, default=15)
    # Alternate data directory than cycgan/data/
    parser.add_argument("-dd", "--data_dir", 
                        help="Different data directory from ml/data.", 
                        type=str, default=None)
    
    # Parse arguments
    args = parser.parse_args()
    
    return args

# Learning rate scheduler
class WarmupLinearSchedule(LambdaLR):
    """ Linear warmup and then linear decay.
        Linearly increases learning rate from 0 to 1 over `warmup_steps` training steps.
        Linearly decreases learning rate from 1. to min_lr over remaining `t_total - warmup_steps` steps.
    """
    def __init__(self, optimizer, warmup_steps, min_lr, t_total, last_epoch=-1):
        self.warmup_steps = warmup_steps
        self.min_lr = min_lr
        self.t_total = t_total
        super(WarmupLinearSchedule, self).__init__(optimizer, self.lr_lambda, last_epoch=last_epoch)

    def lr_lambda(self, step):
        if step < self.warmup_steps:
            return float(step) / float(max(1, self.warmup_steps))
        return max(self.min_lr, float(self.t_total - step) / float(max(1.0, self.t_total - self.warmup_steps)))
    
def loss_fn(y_true, y_pred, y_sigma):
    return torch.mean(torch.log(y_sigma)/2+ (y_true - y_pred)**2/(2*y_sigma)) + 5

def task_loss_fn(y_true, y_pred):
    '''Take average of each task loss separately.'''
    return torch.mean((y_true - y_pred)**2, axis=0)

def run_iter(model, src_batch, tgt_batch, optimizer, lr_scheduler, 
             tgt_task_weights, src_task_weights, losses_cp, mode='train'):
    
    if mode=='train':
        model.module.train_mode()
    else:
        model.module.eval_mode()
        
    total_loss = 0.
    # Compute prediction on source batch
    model_outputs_src = model(src_batch['spectrum'],
                              src_batch['pixel_indx'],
                              norm_in=True, denorm_out=False)
    # Compute prediction on target batch
    model_outputs_tgt = model(tgt_batch['spectrum'],
                              tgt_batch['pixel_indx'],
                              norm_in=True, denorm_out=False)
        
    if model.module.num_labels>0:
        src_label_loss = torch.nn.MSELoss()(model_outputs_src['stellar labels'], 
                                            model.module.normalize_labels(src_batch['stellar labels']))
        
        # Add to total loss
        total_loss = total_loss + src_label_loss
    else:
        src_label_loss = 0.
        
    if len(model.module.tasks)>0:
        # Compute loss on task labels
        src_task_losses = task_loss_fn(model.module.normalize_tasks(src_batch['task labels']), 
                                       model_outputs_src['task_labels'])
        tgt_task_losses = task_loss_fn(model.module.normalize_tasks(tgt_batch['task labels']), 
                                       model_outputs_tgt['task_labels'])
        # Add to total loss
        total_loss = total_loss + torch.mean(src_task_losses*src_task_weights)
        total_loss = total_loss + torch.mean(tgt_task_losses*tgt_task_weights)
        
    if mode=='train':        
        # Update the gradients
        total_loss.backward()

        # Save loss and metrics
        losses_cp['train_loss'].append(float(total_loss))
        if model.module.num_labels>0:
            losses_cp['train_src_labels'].append(float(src_label_loss))
        if len(model.module.tasks)>0:
            losses_cp['train_src_tasks'].append(src_task_losses.cpu().data.numpy().tolist())
            losses_cp['train_tgt_tasks'].append(tgt_task_losses.cpu().data.numpy().tolist())

        # Adjust network weights
        optimizer.step()
        # Reset gradients
        optimizer.zero_grad(set_to_none=True)
        # Adjust learning rate
        lr_scheduler.step()

    else:
        # Save loss and metrics
        losses_cp['val_loss'].append(float(total_loss))
        if model.module.num_labels>0:
            losses_cp['val_src_labels'].append(float(src_label_loss))
        if len(model.module.tasks)>0:
            losses_cp['val_src_tasks'].append(src_task_losses.cpu().data.numpy().tolist())
            losses_cp['val_tgt_tasks'].append(tgt_task_losses.cpu().data.numpy().tolist())
                
    return model, optimizer, lr_scheduler, losses_cp

def compare_val_sample(model, src_batch, tgt_batch, losses_cp, batch_size=16):
    
    model.module.eval_mode()
    
    # Produce feature map of source batch
    model_feats_src = []
    for i in range(0, src_batch['spectrum chunks'].size(1), batch_size):
        model_feats_src.append(model(src_batch['spectrum chunks'][:,i:i+batch_size].squeeze(0),
                                     src_batch['pixel_indx'][:,i:i+batch_size].squeeze(0),
                                     norm_in=True, return_feats=True))
    
    # Produce feature map of target batch
    model_feats_tgt = []
    for i in range(0, tgt_batch['spectrum chunks'].size(1), batch_size):
        model_feats_tgt.append(model(tgt_batch['spectrum chunks'][:,i:i+batch_size].squeeze(0),
                                     tgt_batch['pixel_indx'][:,i:i+batch_size].squeeze(0),
                                     norm_in=True, return_feats=True))
    model_feats_src = torch.cat(model_feats_src)
    model_feats_tgt = torch.cat(model_feats_tgt)
    
    # Predict labels
    label_preds_src = model.module.label_predictor(model_feats_src)
    label_preds_tgt = model.module.label_predictor(model_feats_tgt)
    
    # Compute average from all chunks
    label_preds_src = torch.mean(label_preds_src, axis=0)
    label_preds_tgt = torch.mean(label_preds_tgt, axis=0)
    
    # Compute mean squared error on label predictions
    src_label_loss = torch.nn.MSELoss()(label_preds_src, 
                                        model.module.normalize_labels(src_batch['stellar labels'][0]))
    tgt_label_loss = torch.nn.MSELoss()(label_preds_tgt, 
                                        model.module.normalize_labels(tgt_batch['stellar labels'][0]))
    
    # Compute max and min of each feature
    max_feat = torch.max(torch.cat((model_feats_src, model_feats_tgt), 0), 
                         dim=0).values
    min_feat = torch.min(torch.cat((model_feats_src, model_feats_tgt), 0), 
                         dim=0).values

    # Normalize each feature between 0 and 1 across the entire batch
    model_feats_src_norm = (model_feats_src-min_feat)/(max_feat-min_feat+1e-8)
    model_feats_tgt_norm = (model_feats_tgt-min_feat)/(max_feat-min_feat+1e-8)
    
    # Find aligned chunks between source and target
    src_indices = []
    for i in range(tgt_batch['pixel_indx'].size()[1]):
        src_indices.append(torch.where(src_batch['pixel_indx'][0,:,0]==tgt_batch['pixel_indx'][0,i,0])[0])
    src_indices = torch.cat(src_indices)
    
    # Compute mean absolute error
    feat_loss = torch.mean(torch.abs(model_feats_src_norm[src_indices]-model_feats_tgt_norm))
    
    losses_cp['val_src_labels'].append(float(src_label_loss))
    losses_cp['val_tgt_labels'].append(float(tgt_label_loss))
    losses_cp['val_feats'].append(float(feat_loss))
    
    return losses_cp