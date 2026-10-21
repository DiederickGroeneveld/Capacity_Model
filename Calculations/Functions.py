from __future__ import annotations

from math import exp, pi, sqrt
from typing import Sequence

"""
Combine multiple normal distributions into one probability curve.

This builds a *mixture distribution*:
    f(x) = sum(w_i * N(x | mu_i, sigma_i))

Args:
    means: Mean for each normal distribution.
    std_devs: Standard deviation for each normal distribution.
    weights: Optional weight per distribution. If omitted, all are equal.
    x_values: Optional x-axis values for evaluating the curve.
    num_points: Number of points to generate when x_values is omitted.
    std_range: Auto-generated x-axis covers [mu - std_range*sigma, mu + std_range*sigma].

Returns:
    A tuple of (x, y) where x is the curve x-axis and y is the combined PDF.
"""
def combine_normal_distributions(
	means: Sequence[float],
	std_devs: Sequence[float],
	weights: Sequence[float] | None = None,
	x_values: Sequence[float] | None = None,
	num_points: int = 3600,
	std_range: float = 4.0,
) -> tuple[list[float], list[float]]:

	if not means or not std_devs:
		raise ValueError("'means' and 'std_devs' must be non-empty.")

	if len(means) != len(std_devs):
		raise ValueError("'means' and 'std_devs' must have the same length.")

	if any(std <= 0 for std in std_devs):
		raise ValueError("All standard deviations must be > 0.")

	if weights is None:
		normalized_weights = [1.0 / len(means)] * len(means)
	else:
		if len(weights) != len(means):
			raise ValueError("'weights' must match the number of distributions.")

		if any(weight < 0 for weight in weights):
			raise ValueError("All weights must be >= 0.")

		weight_sum = float(sum(weights))
		if weight_sum == 0:
			raise ValueError("At least one weight must be > 0.")

		normalized_weights = [float(weight) / weight_sum for weight in weights]

	if x_values is None:
		if num_points < 2:
			raise ValueError("'num_points' must be at least 2.")
		if std_range <= 0:
			raise ValueError("'std_range' must be > 0.")

		x_min = min(mean - std_range * std for mean, std in zip(means, std_devs))
		x_max = max(mean + std_range * std for mean, std in zip(means, std_devs))
		step = (x_max - x_min) / (num_points - 1)
		x = [x_min + i * step for i in range(num_points)]
	else:
		if len(x_values) < 2:
			raise ValueError("'x_values' must contain at least 2 points.")
		x = [float(value) for value in x_values]

	def _normal_pdf(value: float, mean: float, std: float) -> float:
		z = (value - mean) / std
		return exp(-0.5 * z * z) / (std * sqrt(2 * pi))

	y = [
		sum(
			weight * _normal_pdf(value, mean, std)
			for mean, std, weight in zip(means, std_devs, normalized_weights)
		)
		for value in x
	]

	# Normalize numerically so area under the discrete curve is ~1.
	area = 0.0
	for i in range(len(x) - 1):
		width = x[i + 1] - x[i]
		area += 0.5 * (y[i] + y[i + 1]) * width

	if area > 0:
		y = [value / area for value in y]

	return x, y

