# AUTOGENERATED! DO NOT EDIT! File to edit: ../00_layers.ipynb.

# %% auto 0
__all__ = ['gabor_2d_tf', 'create_gabor_rot_tf', 'create_multiple_different_rot_gabor_tf']

# %% ../00_layers.ipynb 3
import numpy as np
import tensorflow as tf

# %% ../00_layers.ipynb 7
def cast_all(*args, dtype=tf.float32):
    return [tf.cast(arg, dtype=dtype) for arg in args]

# %% ../00_layers.ipynb 11
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

# %% ../00_layers.ipynb 12
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

# %% ../00_layers.ipynb 16
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
    return gabors
