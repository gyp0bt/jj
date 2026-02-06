import numpy as np


def is_empty_array(arr: np.ndarray) -> bool:
    return not any([i for i in tuple(arr.shape)])
