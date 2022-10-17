# AUTOGENERATED! DO NOT EDIT! File to edit: ../Notebooks/03_callbacks.ipynb.

# %% auto 0
__all__ = ['GaborLayerLogger', 'GaborLayerSeqLogger', 'FunctionalFilterLogger', 'GaborFiltersLogger', 'GaborErrorPrinter',
           'BatchesSeenLogger']

# %% ../Notebooks/03_callbacks.ipynb 2
import matplotlib.pyplot as plt

import wandb

import tensorflow as tf
from tensorflow.keras.callbacks import Callback

from .layers import *

# %% ../Notebooks/03_callbacks.ipynb 6
class GaborLayerLogger(Callback):
    import wandb

    """Logs the gabor parameters into wandb during training."""
    def on_train_batch_end(self, 
                           batch, # Batch number.
                           logs=None, # Dictionary containing metrics and information of the training.
                           ):
        """Logs the gabor parameters after each batch (after each parameter update)."""
        for layer in self.model.layers:
            if isinstance(layer, GaborLayer):
                for weight in layer.weights:
                    wandb.log({f'{layer.name}.{weight.name}': wandb.Histogram(weight)})

# %% ../Notebooks/03_callbacks.ipynb 7
class GaborLayerSeqLogger(Callback):
    import wandb

    """Logs the gabor parameters into wandb during training."""
    def on_train_batch_end(self, 
                           batch, # Batch number.
                           logs=None, # Dictionary containing metrics and information of the training.
                           ):
        """Logs the gabor parameters after each batch (after each parameter update)."""
        for layer in self.model.feature_extractor.layers:
            if isinstance(layer, GaborLayer):
                for weight in layer.weights:
                    wandb.log({f'{layer.name}.{weight.name}': wandb.Histogram(weight)})

# %% ../Notebooks/03_callbacks.ipynb 9
class FunctionalFilterLogger(Callback):
    """Logs the parametrics filters of any layer implementing a `show_filters` method."""
    
    def on_train_batch_end(self, 
                           batch, # Batch number.
                           logs=None, # Dictionary containing metrics and information of the training.
                           ):
        """Logs the parametric filters after each batch (after each parameter update)."""
        for layer in self.model.layers:
            if hasattr(layer, "show_filters"):
                layer.show_filters(show=False)
                wandb.log({f'{layer.name}': wandb.Image(plt)})

# %% ../Notebooks/03_callbacks.ipynb 19
class GaborFiltersLogger(Callback):
    import wandb

    def __init__(self,
                 batch_interval: int, # Batch interval for logging Gabor images.
                 ):
        self.batch_interval = batch_interval

    """Logs the gabor parameters into wandb during training."""
    def on_train_batch_end(self, 
                           batch, # Batch number.
                           logs=None, # Dictionary containing metrics and information of the training.
                           ):
        """Logs the gabor parameters after each batch (after `batch_interval` parameter updates)."""
        if batch % self.batch_interval == 0:
            for layer in self.model.layers:
                if isinstance(layer, GaborLayer):
                    layer.show_filters(show=False)
                    wandb.log({"gabors": plt})
                    plt.close()

# %% ../Notebooks/03_callbacks.ipynb 27
class GaborErrorPrinter(Callback):
    import wandb

    """Prints the parameters of the Gabor layer when an error is going to happen."""
    def on_train_batch_end(self, 
                           batch, # Batch number.
                           logs=None, # Dictionary containing metrics and information of the training.
                           ):
        """Logs the gabor parameters after each batch (after each parameter update)."""
        for layer in self.model.layers:
            if isinstance(layer, GaborLayer):
                try:
                    filters = create_multiple_different_rot_gabor_tf(n_gabors=layer.n_gabors, Nrows=layer.Nrows, Ncols=layer.Ncols, imean=layer.imean, jmean=layer.jmean, sigma_i=layer.sigma_i, sigma_j=layer.sigma_j,
                                                                     freq=layer.freq, theta=layer.theta, rot_theta=layer.rot_theta, sigma_theta=layer.sigma_theta, fs=layer.fs, normalize=layer.normalize)
                except:
                    print("ERROR IN THE CALCULATION OF THE GABOR FILTERS!!")
                    print("STOPPING TRAINING")
                    self.model.stop_training = True
                    attrs = {k:v for k, v in layer.__dict__.items() if k[0]!="_"}
                    for name, value in attrs.items():
                        print(f"{name}: {value}")

# %% ../Notebooks/03_callbacks.ipynb 31
class BatchesSeenLogger(Callback):
    """Logs the number of batches seen by the model."""

    def __init__(self):
        super(BatchesSeenLogger, self).__init__()
        self.batches_seen = 0

    def on_train_batch_end(self, 
                           batch, # Batch number.
                           logs=None, # Dictionary containing metrics and information of the training.
                           ):
        """Stores the number of batches seen."""
        self.batches_seen += 1

    def on_epoch_end(self,
                     epoch, # Epoch number.
                     logs=None, # Dictionary containing metrics and information of the training.
                     ):
        """Logs the number of batches seen into wandb."""
        wandb.log({"Batches": self.batches_seen})