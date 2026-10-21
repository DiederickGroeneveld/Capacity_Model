from __future__ import annotations

import csv

from Calculations.Functions import combine_normal_distributions


def _parse_float_list(raw: str, field_name: str) -> list[float]:
	values = [value.strip() for value in raw.split(",") if value.strip()]
	if not values:
		raise ValueError(f"'{field_name}' cannot be empty.")
	return [float(value) for value in values]


def main() -> None:
	print("Combine multiple normal distributions into one probability curve")
	print("Enter values as comma-separated numbers (example: 10,12.5,15)")

	try:
		means = _parse_float_list(input("Piek moment(Digitaal uur van de dag): "), "means")
		std_devs = _parse_float_list(input("Curve vlakte 1(De standaardafwijking: de curve is  uur 'breed'. Ongeveer 68% van de massa ligt binnen ± input uur van de piek en ongeveer 95% binnen ±2 keer de ingevulde waarde uur.): "), "std_devs")

		weights_input = input("Weights (optional, press Enter for equal weights): ").strip()
		weights = _parse_float_list(weights_input, "weights") if weights_input else None

		minute_mode_input = input("One value per minute of the day (00:00-23:59)? [Y/n]: ").strip().lower()
		minute_mode = minute_mode_input in ("", "y", "yes")

		if minute_mode:
			x_values = [minute / 60.0 for minute in range(24 * 60)]
			x_values, y_values = combine_normal_distributions(
				means=means,
				std_devs=std_devs,
				weights=weights,
				x_values=x_values,
			)
		else:
			num_points_input = input("Number of points [500]: ").strip()
			std_range_input = input("Standard deviation range [4.0]: ").strip()

			num_points = int(num_points_input) if num_points_input else 500
			std_range = float(std_range_input) if std_range_input else 4.0

			x_values, y_values = combine_normal_distributions(
				means=means,
				std_devs=std_devs,
				weights=weights,
				num_points=num_points,
				std_range=std_range,
			)
	except ValueError as error:
		print(f"Input error: {error}")
		return

	print(f"\nCombined curve built with {len(x_values)} points.")
	print("First 10 points (x-hour, probability):")
	for x_value, y_value in list(zip(x_values, y_values))[:10]:
		print(f"{x_value:.6f}, {y_value:.12f}")

	export_path = input("\nOptional CSV output path (press Enter to skip): ").strip()
	if export_path:
		with open(export_path, "w", newline="", encoding="utf-8") as csv_file:
			writer = csv.writer(csv_file)
			writer.writerow(["minute_of_day", "hour_of_day", "probability"])
			for index, (x_value, y_value) in enumerate(zip(x_values, y_values)):
				minute_of_day = index if len(x_values) == 24 * 60 else ""
				writer.writerow([minute_of_day, x_value, y_value])
		print(f"Curve saved to: {export_path}")


if __name__ == "__main__":
	main()
