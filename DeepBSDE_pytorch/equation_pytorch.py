# -*- coding: utf-8 -*-
"""equation_pytorch.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/github/wqiu96/summer_project/blob/master/DeepBSDE_pytorch/equation_pytorch.ipynb
"""

import numpy as np
import torch
import torch.nn.functional as F
from scipy.stats import multivariate_normal as normal


class Equation(object):
    """Base class for defining PDE related function."""

    def __init__(self, dim, total_time, num_time_interval):
        self._dim = dim
        self._total_time = total_time
        self._num_time_interval = num_time_interval
        self._delta_t = (self._total_time + 0.0) / self._num_time_interval
        self._sqrt_delta_t = np.sqrt(self._delta_t)
        self._y_init = None

    def sample(self, num_sample):
        """Sample forward SDE."""
        raise NotImplementedError

    def f_tf(self, t, x, y, z):
        """Generator function in the PDE."""
        raise NotImplementedError

    def g_tf(self, t, x):
        """Terminal condition of the PDE."""
        raise NotImplementedError

    @property
    def y_init(self):
        return self._y_init

    @property
    def dim(self):
        return self._dim

    @property
    def num_time_interval(self):
        return self._num_time_interval

    @property
    def total_time(self):
        return self._total_time

    @property
    def delta_t(self):
        return self._delta_t


def get_equation(name, dim, total_time, num_time_interval):
    try:
        return globals()[name](dim, total_time, num_time_interval)
    except KeyError:
        raise KeyError("Equation for the required problem not found.")


class AllenCahn(Equation):
    def __init__(self, dim, total_time, num_time_interval):
        super(AllenCahn, self).__init__(dim, total_time, num_time_interval)
        self._x_init = np.zeros(self._dim)
        self._sigma = np.sqrt(2.0)

    def sample(self):
        dw_sample = normal.rvs(size=[self._dim,
                                     self._num_time_interval]) * self._sqrt_delta_t
        x_sample = np.zeros([self._dim, self._num_time_interval + 1])
        x_sample[:, 0] = np.ones(self._dim) * self._x_init
        for i in range(self._num_time_interval):
            x_sample[:, i + 1] = x_sample[:, i] + self._sigma * dw_sample[:, i]
        return dw_sample, x_sample

    def f_tf(self, t, x, y, z):
        return y - torch.pow(y, 3)

    def g_tf(self, t, x):
        return 0.5 / (1 + 0.2 * torch.sum(torch.pow(x, 2)))


class HJB(Equation):
    def __init__(self, dim, total_time, num_time_interval):
        super(HJB, self).__init__(dim, total_time, num_time_interval)
        self._x_init = np.zeros(self._dim)
        self._sigma = np.sqrt(2.0)
        self._lambda = 1.0

    def sample(self):
        dw_sample = normal.rvs(size=[self._dim,
                                     self._num_time_interval]) * self._sqrt_delta_t
        x_sample = np.zeros([self._dim, self._num_time_interval + 1])
        x_sample[:, 0] = np.ones(self._dim) * self._x_init
        for i in range(self._num_time_interval):
            x_sample[:, i + 1] = x_sample[:, i] + self._sigma * dw_sample[:, i]
        return dw_sample, x_sample

    def f_tf(self, t, x, y, z):
        return -self._lambda * torch.sum(torch.pow(z,2))

    def g_tf(self, t, x):
        return torch.log((1 + torch.sum(torch.pow(x,2))) / 2)


class PricingOption(Equation):
    def __init__(self, dim, total_time, num_time_interval):
        super(PricingOption, self).__init__(dim, total_time, num_time_interval)
        self._x_init = np.ones(self._dim) * 100
        self._sigma = 0.2
        self._mu_bar = 0.06
        self._rl = 0.04
        self._rb = 0.06
        self._alpha = 1.0 / self._dim

    def sample(self):
        dw_sample = normal.rvs(size=[self._dim,
                                     self._num_time_interval]) * self._sqrt_delta_t
        x_sample = np.zeros([self._dim, self._num_time_interval + 1])
        x_sample[:, 0] = np.ones([self._dim]) * self._x_init
        # for i in xrange(self._n_time):
        # 	x_sample[:, :, i + 1] = (1 + self._mu_bar * self._delta_t) * x_sample[:, :, i] + (
        # 		self._sigma * x_sample[:, :, i] * dw_sample[:, :, i])
        factor = np.exp((self._mu_bar-(self._sigma**2)/2)*self._delta_t)
        for i in range(self._num_time_interval):
            x_sample[:, i + 1] = (factor * np.exp(self._sigma * dw_sample[:, i])) * x_sample[:, i]
        return dw_sample, x_sample

    def f_tf(self, t, x, y, z):
        temp = torch.sum(z) / self._sigma
        return -self._rl * y - (self._mu_bar - self._rl) * temp + (
            (self._rb - self._rl) * F.relu(temp - y))

    def g_tf(self, t, x):
        temp = torch.max(x)
        return F.relu(temp - 120) - 2 * F.relu(temp - 150)


class PricingDefaultRisk(Equation):
    def __init__(self, dim, total_time, num_time_interval):
        super(PricingDefaultRisk, self).__init__(dim, total_time, num_time_interval)
        self._x_init = np.ones(self._dim) * 100.0
        self._sigma = 0.2
        self._rate = 0.02   # interest rate R
        self._delta = 2.0 / 3
        self._gammah = 0.2
        self._gammal = 0.02
        self._mu_bar = 0.02
        self._vh = 50.0
        self._vl = 70.0
        self._slope = (self._gammah - self._gammal) / (self._vh - self._vl)

    def sample(self):
        dw_sample = normal.rvs(size=[self._dim,
                                     self._num_time_interval]) * self._sqrt_delta_t
        x_sample = np.zeros([self._dim, self._num_time_interval + 1])
        x_sample[:, 0] = np.ones(self._dim) * self._x_init
        for i in range(self._num_time_interval):
            x_sample[:, i + 1] = (1 + self._mu_bar * self._delta_t) * x_sample[:, i] + (
                self._sigma * x_sample[:, i] * dw_sample[:, i])
        return dw_sample, x_sample

    def f_tf(self, t, x, y, z):
        piecewise_linear = F.relu(
            F.relu(y - self._vh) * self._slope + self._gammah - self._gammal) + self._gammal
        return (-(1 - self._delta) * piecewise_linear - self._rate) * y

    def g_tf(self, t, x):
        return torch.min(x)


class BurgesType(Equation):
    def __init__(self, dim, total_time, num_time_interval):
        super(BurgesType, self).__init__(dim, total_time, num_time_interval)
        self._x_init = np.zeros(self._dim)
        self._y_init = 1 - 1.0 / (1 + np.exp(0 + np.sum(self._x_init) / self._dim))
        self._sigma = self._dim + 0.0

    def sample(self):
        dw_sample = normal.rvs(size=[self._dim,
                                     self._num_time_interval]) * self._sqrt_delta_t
        x_sample = np.zeros([self._dim, self._num_time_interval + 1])
        x_sample[:, 0] = np.ones(self._dim) * self._x_init
        for i in range(self._num_time_interval):
            x_sample[:, i + 1] = x_sample[:, i] + self._sigma * dw_sample[:, i]
        return dw_sample, x_sample

    def f_tf(self, t, x, y, z):
        return (y - (2 + self._dim) / 2.0 / self._dim) * torch.sum(z)

    def g_tf(self, t, x):
        return 1 - 1.0 / (1 + torch.exp(t + torch.sum(x) / self._dim))


class QuadraticGradients(Equation):
    def __init__(self, dim, total_time, num_time_interval):
        super(QuadraticGradients, self).__init__(dim, total_time, num_time_interval)
        self._alpha = 0.4
        self._x_init = np.zeros(self._dim)
        base = self._total_time + np.sum(np.square(self._x_init) / self._dim)
        self._y_init = np.sin(np.power(base, self._alpha))

    def sample(self):
        dw_sample = normal.rvs(size=[self._dim,
                                     self._num_time_interval]) * self._sqrt_delta_t
        x_sample = np.zeros([self._dim, self._num_time_interval + 1])
        x_sample[:, 0] = np.ones(self._dim) * self._x_init
        for i in range(self._num_time_interval):
            x_sample[:, i + 1] = x_sample[:, i] + dw_sample[:, i]
        return dw_sample, x_sample

    def f_tf(self, t, x, y, z):
        x_square = torch.sum(torch.pow(x,2))
        base = self._total_time - t + x_square / self._dim
        base_alpha = torch.pow(base, self._alpha)
        derivative = self._alpha * torch.pow(base, self._alpha - 1) * torch.cos(base_alpha)
        term1 = torch.sum(torch.pow(z,2))
        term2 = -4.0 * (derivative ** 2) * x_square / (self._dim ** 2)
        term3 = derivative
        term4 = -0.5 * (
            2.0 * derivative + 4.0 / (self._dim ** 2) * x_square * self._alpha * (
                (self._alpha - 1) * torch.pow(base, self._alpha - 2) * torch.cos(base_alpha) - (
                    self._alpha * torch.pow(base, 2 * self._alpha - 2) * torch.sin(base_alpha)
                    )
                )
            )
        return term1 + term2 + term3 + term4

    def g_tf(self, t, x):
        return torch.sin(
            torch.pow(torch.sum(torch.pow(x,2)) / self._dim, self._alpha))


class ReactionDiffusion(Equation):
    def __init__(self, dim, total_time, num_time_interval):
        super(ReactionDiffusion, self).__init__(dim, total_time, num_time_interval)
        self._kappa = 0.6
        self._lambda = 1 / np.sqrt(self._dim)
        self._x_init = np.zeros(self._dim)
        self._y_init = 1 + self._kappa + np.sin(self._lambda * np.sum(self._x_init)) * np.exp(
            -self._lambda * self._lambda * self._dim * self._total_time / 2)

    def sample(self):
        dw_sample = normal.rvs(size=[self._dim,
                                     self._num_time_interval]) * self._sqrt_delta_t
        x_sample = np.zeros([self._dim, self._num_time_interval + 1])
        x_sample[:, 0] = np.ones(self._dim) * self._x_init
        for i in range(self._num_time_interval):
            x_sample[:, i + 1] = x_sample[:, i] + dw_sample[:, i]
        return dw_sample, x_sample

    def f_tf(self, t, x, y, z):
        exp_term = torch.exp((self._lambda ** 2) * self._dim * (t - self._total_time) / 2)
        sin_term = torch.sin(self._lambda * torch.sum(x))
        temp = y - self._kappa - 1 - sin_term * exp_term
        return torch.min(torch.ones(temp.shape), torch.pow(temp,2))

    def g_tf(self, t, x):
        return 1 + self._kappa + torch.sin(self._lambda * torch.sum(x))
