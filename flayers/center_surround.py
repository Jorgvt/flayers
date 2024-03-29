# AUTOGENERATED! DO NOT EDIT! File to edit: ../Notebooks/01_center_surround.ipynb.

# %% auto 0
__all__ = ['gaussian_2d_tf', 'create_gaussian_rot_tf', 'create_multiple_different_rot_gaussian_tf', 'GaussianLayer',
           'RandomGaussian']

# %% ../Notebooks/01_center_surround.ipynb 4
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras.constraints import NonNeg
from .constraints import Positive

from einops import rearrange, repeat, reduce

from fastcore.basics import patch

from .layers import cast_all

# %% ../Notebooks/01_center_surround.ipynb 8
@tf.function
def gaussian_2d_tf(i, # Horizontal domain
                   j, # Vertical domain
                   imean, # Horizontal mean
                   jmean, # Vertical mean
                   sigma_i, # Horizontal width
                   sigma_j, # Vertical width
                   freq, # Frecuency of the filter
                   sigma_theta # Width of the angle?? Rotation of the domain??
                   ):
    i, j, imean, jmean, sigma_i, sigma_j, freq, sigma_theta, PI = cast_all(i, j, imean, jmean, sigma_i, sigma_j, freq, sigma_theta, np.pi)
    sigma_vector = tf.convert_to_tensor([sigma_i, sigma_j])
    # sigma_vector = tf.clip_by_value(sigma_vector, clip_value_min=1e-5, clip_value_max=200)
    cov_matrix = tf.linalg.diag(sigma_vector)**2
    det_cov_matrix = tf.linalg.det(cov_matrix)
    constant = tf.convert_to_tensor((1/(2*PI*tf.sqrt(det_cov_matrix))))
    rotation_matrix = tf.convert_to_tensor([[tf.cos(sigma_theta), -tf.sin(sigma_theta)],
                                            [tf.sin(sigma_theta), tf.cos(sigma_theta)]])
    rotated_covariance = tf.cast(rotation_matrix @ tf.linalg.inv(cov_matrix) @ tf.transpose(rotation_matrix), tf.float32)

    x_r_1 = rotated_covariance[0,0] * i + rotated_covariance[0,1] * j
    y_r_1 = rotated_covariance[1,0] * i + rotated_covariance[1,1] * j

    distance = i * x_r_1 + j * y_r_1

    gabor = constant * tf.exp(-distance/2)

    return gabor

# %% ../Notebooks/01_center_surround.ipynb 9
@tf.function
def create_gaussian_rot_tf(Nrows, # Number of horizontal pixels
                           Ncols, # Number of vertical pixels
                           imean, # Horizontal mean *(in degrees)*
                           jmean, # Vertical mean *(in degrees)*
                           sigma_i, # Horizontal width *(in degrees)*
                           sigma_j, # Vertical width *(in degrees)*
                           freq, # Frequency
                           rot_theta, # Rotation of the domain??
                           sigma_theta, # Width of the angle?? Rotation of the domain??
                           fs, # Sampling frequency
                           ):
    """
    Creates a rotated Gabor filter with the input parameters.
    """
    Nrows, Ncols, imean, jmean, sigma_i, sigma_j, freq, rot_theta, sigma_theta, fs = cast_all(Nrows, Ncols, imean, jmean, sigma_i, sigma_j, freq, rot_theta, sigma_theta, fs)
    
    x_max = Nrows/fs
    int_x = Ncols/fs
    int_y = Nrows/fs

    Nrows, Ncols = cast_all(Nrows, Ncols, dtype=tf.int32)
    fot_x = tf.linspace(0.0, int_x, Nrows+1)[:-1]
    fot_y = tf.linspace(0.0, int_y, Ncols+1)[:-1]
    x, y = tf.meshgrid(fot_x, fot_y, indexing='xy')

    x_r = tf.cos(rot_theta) * (x - imean) - tf.sin(rot_theta) * (y - jmean)
    y_r = tf.sin(rot_theta) * (x - imean) + tf.cos(rot_theta) * (y - jmean)

    return gaussian_2d_tf(x_r, y_r, imean = imean, jmean = jmean, sigma_i = sigma_i, sigma_j = sigma_j, freq = freq, sigma_theta = sigma_theta)

# %% ../Notebooks/01_center_surround.ipynb 11
@tf.function
def create_multiple_different_rot_gaussian_tf(filters, # Number of Gaussian filters we want to create.
                                              Nrows, # Number of horizontal pixels.
                                              Ncols, # Number of vertical pixels.
                                              imean, # Horizontal mean *(in degrees)*.
                                              jmean, # Vertical mean *(in degrees)*.
                                              sigma_i: list, # Horizontal width *(in degrees)*.
                                              sigma_j: list, # Vertical width *(in degrees)*.
                                              freq: list, # Frequency.
                                              rot_theta: list, # Rotation of the domain??
                                              sigma_theta: list, # Width of the angle?? Rotation of the domain??
                                              fs, # Sampling frequency.
                                              normalize:bool = True, # Wether to normalize (and divide by filters) or not the filters.
                                              ):
    """
    Creates a set of Gaussian filters.
    """
    Nrows, Ncols, imean, jmean, sigma_i, sigma_j, freq, rot_theta, sigma_theta, fs = cast_all(Nrows, Ncols, imean, jmean, sigma_i, sigma_j, freq, rot_theta, sigma_theta, fs)
    gaussians = tf.TensorArray(dtype = tf.float32, size = filters)

    for n in tf.range(start = 0, limit = filters, dtype = tf.int32):
        gaussians = gaussians.write(n, create_gaussian_rot_tf(Nrows, Ncols, imean, jmean, tf.gather(sigma_i, n), tf.gather(sigma_j, n), tf.gather(freq, n), 
                                                              tf.gather(rot_theta, n), tf.gather(sigma_theta, n), fs))

    gaussians = gaussians.stack()
    ## Normalize the filters
    if normalize: 
        max_per_filter = reduce(gaussians, "filters Ncols Nrows -> filters () ()", "max")
        gaussians = gaussians/(max_per_filter*tf.cast(filters, tf.float32))
    return gaussians

# %% ../Notebooks/01_center_surround.ipynb 15
class GaussianLayer(tf.keras.layers.Layer):
    """
    Pre-initialized Gaussian layer that is trainable through backpropagation.
    """
    def __init__(self,
                 filters, # Number of Gaussian filters.
                 size, # Size of the filters (they will be square).
                 imean, # Horizontal mean *(in degrees)*.
                 jmean, # Vertical mean *(in degrees)*.
                 sigma_i: list, # Horizontal width *(in degrees)*.
                 sigma_j: list, # Vertical width *(in degrees)*.
                 freq: list, # Frequency.
                 rot_theta: list, # Rotation of the domain **(rad)**.
                 sigma_theta: list, # Rotation of the envelope  **(rad)**.
                 fs, # Sampling frequency.,
                 normalize: bool = True, # Wether to normalize the Gabor filters or not.
                 **kwargs, # Arguments to be passed to the base `Layer`.
                 ):
        super(GaussianLayer, self).__init__(**kwargs)

        # if len(sigma_i) != filters: raise ValueError(f"sigma_i has {len(sigma_i)} values but should have {filters} (filters = {filters}).")

        self.filters = filters
        self.size = size
        self.Nrows, self.Ncols = size, size
        self.fs = fs
        self.normalize = normalize

        self._check_parameter_length(sigma_i, sigma_j, freq, rot_theta, sigma_theta)
        self.imean, self.jmean, self.sigma_i, self.sigma_j, self.freq, self.rot_theta, self.sigma_theta = cast_all(imean, jmean, sigma_i, sigma_j, freq, rot_theta, sigma_theta)
        self.logsigma_i, self.logsigma_j = tf.math.log(self.sigma_i), tf.math.log(self.sigma_j)
        
    def build(self, input_shape):

        self.imean = tf.Variable(self.imean, trainable=True, name="imean", constraint=Positive())
        self.jmean = tf.Variable(self.jmean, trainable=True, name="jmean", constraint=Positive())

        # self.sigma_i = tf.Variable(np.random.uniform(0, self.Nrows/self.fs, filters), trainable=True, name="sigma_i")
        self.logsigma_i = tf.Variable(self.logsigma_i, trainable=True, name="logsigma_i")#, constraint=Positive())

        # self.sigma_j = tf.Variable(np.random.uniform(0, self.Ncols/self.fs, filters), trainable=True, name="sigma_j")
        self.logsigma_j = tf.Variable(self.logsigma_j, trainable=True, name="logsigma_j")#, constraint=Positive())

        # self.freq = tf.Variable(np.random.uniform(0, self.fs, filters), trainable=True, name="freq")
        self.freq = tf.Variable(self.freq, trainable=True, name="freq", constraint=Positive())

        # self.rot_theta = tf.Variable(np.random.uniform(0,6, filters), trainable=True, name="rot_theta")
        self.rot_theta = tf.Variable(self.rot_theta, trainable=True, name="rot_theta")

        # self.sigma_theta = tf.Variable(np.random.uniform(0,6, filters), trainable=True, name="sigma_theta")
        self.sigma_theta = tf.Variable(self.sigma_theta, trainable=True, name="sigma_theta")

        self.precalc_filters = tf.Variable(create_multiple_different_rot_gaussian_tf(filters=self.filters, Nrows=self.Nrows, Ncols=self.Ncols, imean=self.imean, jmean=self.jmean, sigma_i=self.sigma_i, sigma_j=self.sigma_j,
                                                                                     freq=self.freq, rot_theta=self.rot_theta, sigma_theta=self.sigma_theta, fs=self.fs, normalize=self.normalize),
                                           trainable=False, name="precalc_filters")

    def _check_parameter_length(self, *args):
        for arg in args:
            if len(arg) != self.filters: raise ValueError(f"Listed parameters should have the same length as filters ({self.filters}).")


# %% ../Notebooks/01_center_surround.ipynb 16
@patch
def call(self: GaussianLayer, 
         inputs, # Inputs to the layer.
         training=False, # Flag indicating if we are training the layer or using it for inference.
         ):
    """
    Build a set of filters from the stored values and convolve them with the input.
    """
    if training:
         gaussians = create_multiple_different_rot_gaussian_tf(filters=self.filters, Nrows=self.Nrows, Ncols=self.Ncols, imean=self.imean, jmean=self.jmean, sigma_i=tf.math.exp(self.logsigma_i), sigma_j=tf.math.exp(self.logsigma_j),
                                                               freq=self.freq, rot_theta=self.rot_theta, sigma_theta=self.sigma_theta, fs=self.fs, normalize=self.normalize)
         self.precalc_filters.assign(gaussians)
    else:
         gaussians = self.precalc_filters


    ## Keras expects the convolutional filters in shape (size_x, size_y, C_in, C_out)
    gaussians = repeat(gaussians, "filters Ncols Nrows -> Ncols Nrows C_in filters", C_in=inputs.shape[-1])
    
    return tf.nn.conv2d(inputs, gaussians, strides=1, padding="SAME")

# %% ../Notebooks/01_center_surround.ipynb 22
def find_grid_size(filters):
    ncols = int(np.round(np.sqrt(filters)))
    nrows = ncols
    if ncols*nrows < filters: nrows += 1
    return nrows, ncols

# %% ../Notebooks/01_center_surround.ipynb 23
@patch
def show_filters(self: GaussianLayer,
                 show: bool = True, # Wether to run plt.plot() or not.
                 ):
    """
    Calculates and plots the filters corresponding to the stored parameters.
    """
    nrows, ncols = find_grid_size(self.filters)
    # gabors = self.filters.numpy()
    
    try: gabors = self.precalc_filters.numpy()
    except: gabors = create_multiple_different_rot_gaussian_tf(filters=self.filters, Nrows=self.Nrows, Ncols=self.Ncols, imean=self.imean, jmean=self.jmean, sigma_i=tf.math.exp(self.logsigma_i), sigma_j=tf.math.exp(self.logsigma_j),
                                                               freq=self.freq, rot_theta=self.rot_theta, sigma_theta=self.sigma_theta, fs=self.fs, normalize=self.normalize)
    fig, axes = plt.subplots(int(nrows), int(ncols), squeeze=False)
    for gabor, ax in zip(gabors, axes.ravel()):
        ax.imshow(gabor)
    if show: plt.show()

# %% ../Notebooks/01_center_surround.ipynb 28
class RandomGaussian(GaussianLayer):
    """
    Randomly initialized Gaussian layer that is trainable through backpropagation.
    """
    def __init__(self,
                 filters, # Number of Gaussian filters.
                 size, # Size of the filters (they will be square).
                 normalize: bool = True, # Wether to normalize the Gaussian filters.
                 **kwargs, # Arguments to be passed to the base `Layer`.
                 ):
        super(GaussianLayer, self).__init__(**kwargs) # Hacky way of using tf.keras.layers.Layer __init__ but maintain GaussianLayer's methods.
        self.filters = filters
        self.size = size
        self.Nrows, self.Ncols = size, size
        self.fs = self.Ncols
        self.normalize = normalize

        self.imean = 0.5
        self.jmean = 0.5
        self.sigma_i = np.random.uniform(0, self.Nrows/self.fs, self.filters)
        self.sigma_j = np.random.uniform(0, self.Ncols/self.fs, self.filters)
        self.freq = np.random.uniform(0, self.fs, self.filters)
        self.theta = np.random.uniform(0,6, self.filters)
        self.rot_theta = np.random.uniform(0,6, self.filters)
        self.sigma_theta = np.random.uniform(0,6, self.filters)

        super(RandomGaussian, self).__init__(self.filters, self.size, self.imean, self.jmean,
                                             self.sigma_i, self.sigma_j, self.freq, self.rot_theta, self.sigma_theta, self.fs, self.normalize)
