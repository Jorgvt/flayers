# AUTOGENERATED! DO NOT EDIT! File to edit: ../Notebooks/00_layers.ipynb.

# %% auto 0
__all__ = ['gabor_2d_tf', 'create_gabor_rot_tf', 'create_multiple_different_rot_gabor_tf', 'GaborLayer',
           'create_simple_random_set', 'RandomGabor']

# %% ../Notebooks/00_layers.ipynb 5
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras.constraints import NonNeg
from .constraints import Positive

from einops import rearrange, repeat, reduce

from fastcore.basics import patch

# %% ../Notebooks/00_layers.ipynb 9
def cast_all(*args, dtype=tf.float32):
    return [tf.cast(arg, dtype=dtype) for arg in args]

# %% ../Notebooks/00_layers.ipynb 13
@tf.function
def gabor_2d_tf(i, # Horizontal domain
                j, # Vertical domain
                imean, # Horizontal mean
                jmean, # Vertical mean
                sigma_i, # Horizontal width
                sigma_j, # Vertical width
                freq, # Frecuency of the filter
                theta, # Angle of the filter
                sigma_theta # Width of the angle?? Rotation of the domain??
                ):
    i, j, imean, jmean, sigma_i, sigma_j, freq, theta, sigma_theta, PI = cast_all(i, j, imean, jmean, sigma_i, sigma_j, freq, theta, sigma_theta, np.pi)
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

    gabor = constant * tf.exp(-distance/2) * tf.cos(2*3.14*freq*(i*tf.cos(theta)+j*tf.sin(theta)))

    return gabor

# %% ../Notebooks/00_layers.ipynb 25
@tf.function
def create_gabor_rot_tf(Nrows, # Number of horizontal pixels
                        Ncols, # Number of vertical pixels
                        imean, # Horizontal mean *(in degrees)*
                        jmean, # Vertical mean *(in degrees)*
                        sigma_i, # Horizontal width *(in degrees)*
                        sigma_j, # Vertical width *(in degrees)*
                        freq, # Frequency
                        theta, # Angle
                        rot_theta, # Rotation of the domain??
                        sigma_theta, # Width of the angle?? Rotation of the domain??
                        fs, # Sampling frequency
                        ):
    """
    Creates a rotated Gabor filter with the input parameters.
    """
    Nrows, Ncols, imean, jmean, sigma_i, sigma_j, freq, theta, rot_theta, sigma_theta, fs = cast_all(Nrows, Ncols, imean, jmean, sigma_i, sigma_j, freq, theta, rot_theta, sigma_theta, fs)
    
    x_max = Nrows/fs
    int_x = Ncols/fs
    int_y = Nrows/fs

    Nrows, Ncols = cast_all(Nrows, Ncols, dtype=tf.int32)
    fot_x = tf.linspace(0.0, int_x, Nrows+1)[:-1]
    fot_y = tf.linspace(0.0, int_y, Ncols+1)[:-1]
    x, y = tf.meshgrid(fot_x, fot_y, indexing='xy')

    x_r = tf.cos(rot_theta) * (x - imean) - tf.sin(rot_theta) * (y - jmean)
    y_r = tf.sin(rot_theta) * (x - imean) + tf.cos(rot_theta) * (y - jmean)

    return gabor_2d_tf(x_r, y_r, imean = imean, jmean = jmean, sigma_i = sigma_i, sigma_j = sigma_j, freq = freq, theta = theta, sigma_theta = sigma_theta)

# %% ../Notebooks/00_layers.ipynb 29
@tf.function
def create_multiple_different_rot_gabor_tf(n_gabors, # Number of Gabor filters we want to create.
                                           Nrows, # Number of horizontal pixels.
                                           Ncols, # Number of vertical pixels.
                                           imean, # Horizontal mean *(in degrees)*.
                                           jmean, # Vertical mean *(in degrees)*.
                                           sigma_i: list, # Horizontal width *(in degrees)*.
                                           sigma_j: list, # Vertical width *(in degrees)*.
                                           freq: list, # Frequency.
                                           theta: list, # Angle.
                                           rot_theta: list, # Rotation of the domain??
                                           sigma_theta: list, # Width of the angle?? Rotation of the domain??
                                           fs, # Sampling frequency.
                                           normalize:bool = True, # Wether to normalize (and divide by n_gabors) or not the Gabors.
                                           ):
    """
    Creates a set of Gabor filters.
    """
    Nrows, Ncols, imean, jmean, sigma_i, sigma_j, freq, theta, rot_theta, sigma_theta, fs = cast_all(Nrows, Ncols, imean, jmean, sigma_i, sigma_j, freq, theta, rot_theta, sigma_theta, fs)
    gabors = tf.TensorArray(dtype = tf.float32, size = n_gabors)

    for n in tf.range(start = 0, limit = n_gabors, dtype = tf.int32):
        gabors = gabors.write(n, create_gabor_rot_tf(Nrows, Ncols, imean, jmean, tf.gather(sigma_i, n), tf.gather(sigma_j, n), tf.gather(freq, n), tf.gather(theta, n), 
                                                     tf.gather(rot_theta, n), tf.gather(sigma_theta, n), fs))

    gabors = gabors.stack()
    # gabors = tf.expand_dims(gabors, axis = -1)
    # gabors = tf.transpose(gabors, perm = [1,2,3,0])
    ## Normalize the gabors
    if normalize: 
        max_per_gabor = reduce(gabors, "n_gabors Ncols Nrows -> n_gabors () ()", "max")
        gabors = gabors/(max_per_gabor*tf.cast(n_gabors, tf.float32))
    return gabors

# %% ../Notebooks/00_layers.ipynb 37
class GaborLayer(tf.keras.layers.Layer):
    """
    Pre-initialized Gabor layer that is trainable through backpropagation.
    """
    def __init__(self,
                 n_gabors, # Number of Gabor filters
                 size, # Size of the filters (they will be square),
                 imean, # Horizontal mean *(in degrees)*.
                 jmean, # Vertical mean *(in degrees)*.
                 sigma_i: list, # Horizontal width *(in degrees)*.
                 sigma_j: list, # Vertical width *(in degrees)*.
                 freq: list, # Frequency.
                 theta: list, # Rotation of the sinusoid **(rad)**.
                 rot_theta: list, # Rotation of the domain **(rad)**.
                 sigma_theta: list, # Rotation of the envelope  **(rad)**.
                 fs, # Sampling frequency.,
                 normalize: bool = True, # Wether to normalize the Gabor filters or not.
                 **kwargs, # Arguments to be passed to the base `Layer`.
                 ):
        super(GaborLayer, self).__init__(**kwargs)

        # if len(sigma_i) != n_gabors: raise ValueError(f"sigma_i has {len(sigma_i)} values but should have {n_gabors} (n_gabors = {n_gabors}).")

        self.n_gabors = n_gabors
        self.size = size
        self.Nrows, self.Ncols = size, size
        self.fs = fs
        self.normalize = normalize

        self._check_parameter_length(sigma_i, sigma_j, freq, theta, rot_theta, sigma_theta)
        self.imean, self.jmean, self.sigma_i, self.sigma_j, self.freq, self.theta, self.rot_theta, self.sigma_theta = cast_all(imean, jmean, sigma_i, sigma_j, freq, theta, rot_theta, sigma_theta)
        self.logsigma_i, self.logsigma_j = tf.math.log(self.sigma_i), tf.math.log(self.sigma_j)
        
    def build(self, input_shape):

        self.imean = tf.Variable(self.imean, trainable=True, name="imean", constraint=Positive())
        self.jmean = tf.Variable(self.jmean, trainable=True, name="jmean", constraint=Positive())

        # self.sigma_i = tf.Variable(np.random.uniform(0, self.Nrows/self.fs, n_gabors), trainable=True, name="sigma_i")
        self.logsigma_i = tf.Variable(self.logsigma_i, trainable=True, name="logsigma_i")#, constraint=Positive())

        # self.sigma_j = tf.Variable(np.random.uniform(0, self.Ncols/self.fs, n_gabors), trainable=True, name="sigma_j")
        self.logsigma_j = tf.Variable(self.logsigma_j, trainable=True, name="logsigma_j")#, constraint=Positive())

        # self.freq = tf.Variable(np.random.uniform(0, self.fs, n_gabors), trainable=True, name="freq")
        self.freq = tf.Variable(self.freq, trainable=True, name="freq", constraint=Positive())

        # self.theta = tf.Variable(np.random.uniform(0,6, n_gabors), trainable=True, name="theta")
        self.theta = tf.Variable(self.theta, trainable=True, name="theta")

        # self.rot_theta = tf.Variable(np.random.uniform(0,6, n_gabors), trainable=True, name="rot_theta")
        self.rot_theta = tf.Variable(self.rot_theta, trainable=True, name="rot_theta")

        # self.sigma_theta = tf.Variable(np.random.uniform(0,6, n_gabors), trainable=True, name="sigma_theta")
        self.sigma_theta = tf.Variable(self.sigma_theta, trainable=True, name="sigma_theta")

        self.precalc_filters = tf.Variable(create_multiple_different_rot_gabor_tf(n_gabors=self.n_gabors, Nrows=self.Nrows, Ncols=self.Ncols, imean=self.imean, jmean=self.jmean, sigma_i=self.sigma_i, sigma_j=self.sigma_j,
                                                                                  freq=self.freq, theta=self.theta, rot_theta=self.rot_theta, sigma_theta=self.sigma_theta, fs=self.fs, normalize=self.normalize),
                                           trainable=False, name="precalc_filters")

    def _check_parameter_length(self, *args):
        for arg in args:
            if len(arg) != self.n_gabors: raise ValueError(f"Listed parameters should have the same length as n_gabors ({self.n_gabors}).")


# %% ../Notebooks/00_layers.ipynb 39
@patch
def call(self: GaborLayer, 
         inputs, # Inputs to the layer.
         training=False, # Flag indicating if we are training the layer or using it for inference.
         ):
    """
    Build a set of filters from the stored values and convolve them with the input.
    """
    if training:
         gabors = create_multiple_different_rot_gabor_tf(n_gabors=self.n_gabors, Nrows=self.Nrows, Ncols=self.Ncols, imean=self.imean, jmean=self.jmean, sigma_i=tf.math.exp(self.logsigma_i), sigma_j=tf.math.exp(self.logsigma_j),
                                                           freq=self.freq, theta=self.theta, rot_theta=self.rot_theta, sigma_theta=self.sigma_theta, fs=self.fs, normalize=self.normalize)
         self.precalc_filters.assign(gabors)
    else:
         gabors = self.precalc_filters


    ## Keras expects the convolutional filters in shape (size_x, size_y, C_in, C_out)
    gabors = repeat(gabors, "n_gabors Ncols Nrows -> Ncols Nrows C_in n_gabors", C_in=inputs.shape[-1])
    
    return tf.nn.conv2d(inputs, gabors, strides=1, padding="SAME")

# %% ../Notebooks/00_layers.ipynb 45
def find_grid_size(filters):
    ncols = int(np.round(np.sqrt(filters)))
    nrows = ncols
    if ncols*nrows < filters: nrows += 1
    return nrows, ncols

# %% ../Notebooks/00_layers.ipynb 46
@patch
def show_filters(self: GaborLayer,
                 show: bool = True, # Wether to run plt.plot() or not.
                 ):
    """
    Calculates and plots the filters corresponding to the stored parameters.
    """
    nrows, ncols = find_grid_size(self.n_gabors)
    # gabors = self.filters.numpy()
    
    try: gabors = self.precalc_filters.numpy()
    except: gabors = create_multiple_different_rot_gabor_tf(n_gabors=self.n_gabors, Nrows=self.Nrows, Ncols=self.Ncols, imean=self.imean, jmean=self.jmean, sigma_i=tf.math.exp(self.logsigma_i), sigma_j=tf.math.exp(self.logsigma_j),
                                                            freq=self.freq, theta=self.theta, rot_theta=self.rot_theta, sigma_theta=self.sigma_theta, fs=self.fs, normalize=self.normalize)
    fig, axes = plt.subplots(int(nrows), int(ncols))
    for gabor, ax in zip(gabors, axes.ravel()):
        ax.imshow(gabor)
    if show: plt.show()

# %% ../Notebooks/00_layers.ipynb 52
@tf.function
def create_simple_random_set(n_gabors, # Number of Gabor filters we want to create.
                             size, # Size of the Gabor (they will be square).
                             ):
    """
    Creates a simple set of randomly initialized squared Gabor filters.
    """
    Nrows, Ncols = size, size
    fs = Ncols
    imean, jmean = 0.5, 0.5
    sigma_i = np.random.uniform(0, Nrows/fs, n_gabors)
    sigma_j = np.random.uniform(0, Ncols/fs, n_gabors)
    freq = np.random.uniform(0, fs, n_gabors)
    theta = np.random.uniform(0,6, n_gabors)
    rot_theta = np.random.uniform(0,6, n_gabors)
    sigma_theta = np.random.uniform(0,6, n_gabors)

    Nrows, Ncols, imean, jmean, sigma_i, sigma_j, freq, theta, rot_theta, sigma_theta, fs = cast_all(Nrows, Ncols, imean, jmean, sigma_i, sigma_j, freq, theta, rot_theta, sigma_theta, fs)
    gabors = tf.TensorArray(dtype = tf.float32, size = n_gabors)

    for n in tf.range(start = 0, limit = n_gabors, dtype = tf.int32):
        gabors = gabors.write(n, create_gabor_rot_tf(Nrows, Ncols, imean, jmean, tf.gather(sigma_i, n), tf.gather(sigma_j, n), tf.gather(freq, n), tf.gather(theta, n), 
                                                     tf.gather(rot_theta, n), tf.gather(sigma_theta, n), fs))

    gabors = gabors.stack()
    # gabors = tf.expand_dims(gabors, axis = -1)
    # gabors = tf.transpose(gabors, perm = [1,2,3,0])
    return gabors

# %% ../Notebooks/00_layers.ipynb 56
class RandomGabor(GaborLayer):
    """
    Randomly initialized Gabor layer that is trainable through backpropagation.
    """
    def __init__(self,
                 n_gabors, # Number of Gabor filters.
                 size, # Size of the filters (they will be square).
                 normalize: bool = True, # Wether to normalize the Gabor filters.
                 **kwargs, # Arguments to be passed to the base `Layer`.
                 ):
        super(GaborLayer, self).__init__(**kwargs) # Hacky way of using tf.keras.layers.Layer __init__ but maintain GaborLayer's methods.
        self.n_gabors = n_gabors
        self.size = size
        self.Nrows, self.Ncols = size, size
        self.fs = self.Ncols
        self.normalize = normalize

        self.imean = 0.5
        self.jmean = 0.5
        self.sigma_i = np.random.uniform(0, self.Nrows/self.fs, self.n_gabors)
        self.sigma_j = np.random.uniform(0, self.Ncols/self.fs, self.n_gabors)
        self.freq = np.random.uniform(0, self.fs, self.n_gabors)
        self.theta = np.random.uniform(0,6, self.n_gabors)
        self.rot_theta = np.random.uniform(0,6, self.n_gabors)
        self.sigma_theta = np.random.uniform(0,6, self.n_gabors)

        super(RandomGabor, self).__init__(self.n_gabors, self.size, self.imean, self.jmean,
                                          self.sigma_i, self.sigma_j, self.freq, self.theta, self.rot_theta, self.sigma_theta, self.fs, self.normalize)
