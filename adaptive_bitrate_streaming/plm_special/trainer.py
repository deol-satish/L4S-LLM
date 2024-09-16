import numpy as np
import torch
import time

from munch import Munch
from torch.utils.data import DataLoader

from plm_special.utils.utils import process_batch


class Trainer:
    def __init__(self, args, model, optimizer, exp_dataset, loss_fn, device, batch_size=1, grad_accum_steps=1, lr_scheduler=None):
        self.args = args
        self.model = model
        self.optimizer = optimizer
        self.exp_dataset = exp_dataset
        self.loss_fn = loss_fn
        self.device = device
        self.batch_size = batch_size
        self.grad_accum_steps = grad_accum_steps
        self.lr_scheduler = lr_scheduler
        
        self.exp_dataset_info = Munch(exp_dataset.exp_dataset_info)
        self.dataloader = DataLoader(exp_dataset, batch_size, shuffle=True, pin_memory=True)

    def train_epoch(self, report_loss_per_steps=100):
        train_losses = []
        logs = dict()
        custom_logs={}

        train_start = time.time()
        dataset_size = len(self.dataloader)

        self.model.train()
        for step, batch in enumerate(self.dataloader):
            train_loss = self.train_step(batch)
            train_losses.append(train_loss.item())

            # perform gradient accumulation update
            train_loss = train_loss / self.grad_accum_steps
            train_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), .25)
            if ((step + 1) % self.grad_accum_steps == 0) or (step + 1 == dataset_size):
                self.optimizer.step()
                self.optimizer.zero_grad(set_to_none=True)
                if self.lr_scheduler is not None:
                    self.lr_scheduler.step()
            print(f'Step {step} - train_loss.item() {train_loss.item()}')


            if step % report_loss_per_steps == 0:                
                mean_train_loss = np.mean(train_losses)
                print(f'Step {step} - mean train loss {mean_train_loss:>9f}')

        logs['time/training'] = time.time() - train_start
        logs['training/train_loss_mean'] = np.mean(train_losses)
        logs['training/train_loss_std'] = np.std(train_losses)


        custom_logs['time/training'] = time.time() - train_start
        custom_logs['training/train_loss_mean'] = np.mean(train_losses)
        custom_logs['training/train_loss_std'] = np.std(train_losses)
        custom_logs['train_losses']=train_losses

        return logs, train_losses, custom_logs

    def train_step(self, batch):
        states, actions, returns, timesteps, labels = process_batch(batch, device=self.device)
        actions_pred1 = self.model(states, actions, returns, timesteps)
        actions_pred = actions_pred1.permute(0, 2, 1)
        loss = self.loss_fn(actions_pred, labels)
        # Open the file in write mode. This will create the file if it doesn't exist or overwrite it if it does.
        with open('trainer_step.txt', 'w') as file:
            file.write(f"actions_pred1.shape: {actions_pred1.shape}\n")
            file.write(f"actions_pred.shape: {actions_pred.shape}\n")    
            file.write(f"states.shape: {states.shape}\n")
            file.write(f"actions.shape: {actions.shape}\n")
            file.write(f"returns.shape: {returns.shape}\n")
            file.write(f"timesteps.shape: {timesteps.shape}\n")
            file.write(f"labels.shape: {labels.shape}\n")
            file.write(f"actions_pred1: {actions_pred1}\n")
            file.write(f"actions_pred: {actions_pred}\n")    
            file.write(f"states: {states}\n")
            file.write(f"actions: {actions}\n")
            file.write(f"returns: {returns}\n")
            file.write(f"timesteps: {timesteps}\n")
            file.write(f"labels: {labels}\n")
 
        return loss
