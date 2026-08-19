class OptimizationService:

    MAX_RANGE = 500
    MPG = 10
    TANK_CAPACITY = 50

    def optimize(
        self,
        stations,
        route_distance,
        initial_fuel,
    ):
        current_position = 0
        current_fuel = initial_fuel

        stops = []
        total_cost = 0

        for station in stations:

            distance = (
                station["distance_from_start"]
                - current_position
            )

            fuel_needed = distance / self.MPG

            # Can't reach this station
            if fuel_needed > current_fuel:
                break

            # Consume fuel to reach station
            current_fuel -= fuel_needed
            current_position = station[
                "distance_from_start"
            ]

            # Find cheaper reachable station
            cheaper_station = self._find_cheaper_station(
                station,
                stations,
                current_position,
                current_fuel,
            )

            if cheaper_station:
                # Buy only enough to reach it
                fuel_to_buy = self._fuel_needed_to_reach(
                    cheaper_station,
                    current_position,
                    current_fuel,
                )
            else:
                # No cheaper station reachable.
                # This is the best price available.
                fuel_to_buy = self._fuel_for_max_range(
                    current_fuel
                )

            if fuel_to_buy > 0:
                cost = (
                    fuel_to_buy
                    * station["price"]
                )

                current_fuel += fuel_to_buy
                total_cost += cost

                stops.append({
                    "station_id": station["id"],
                    "name": station["name"],
                    "price": station["price"],
                    "gallons": fuel_to_buy,
                    "cost": cost,
                })

        return {
            "stops": stops,
            "total_cost": total_cost,
        }