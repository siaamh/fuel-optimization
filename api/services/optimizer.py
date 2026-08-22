class OptimizationService:

    MAX_RANGE = 500       # miles
    MPG = 10              # miles per gallon
    TANK_CAPACITY = 50    # gallons  (MAX_RANGE / MPG)

    def optimize(
        self,
        stations,
        route_distance,
        initial_fuel=0,
    ):
        """
        Greedy cost-optimal fueling algorithm.

        stations        — list of dicts with keys:
                          id, name, price, distance_from_start
        route_distance  — total route length in miles
        initial_fuel    — gallons already in tank at departure

        Strategy:
          At each station, if a cheaper station is reachable from here
          on the current tank, buy only enough fuel to reach that cheaper
          station.  Otherwise (this is the cheapest we can get for now),
          fill up as much as possible.
        """
        current_position = 0.0
        current_fuel = float(initial_fuel)

        stops = []
        total_cost = 0.0

        for station in stations:

            distance_to_station = (
                station["distance_from_start"] - current_position
            )

            fuel_needed_to_arrive = distance_to_station / self.MPG

            # Can't reach this station on remaining fuel — skip
            # (shouldn't normally happen if buffer_miles is generous, but
            #  handle gracefully rather than break so we keep looking)
            if fuel_needed_to_arrive > current_fuel:
                continue

            # Consume fuel to drive here
            current_fuel -= fuel_needed_to_arrive
            current_position = station["distance_from_start"]

            # ------------------------------------------------------------------
            # Decide how much to buy
            # ------------------------------------------------------------------
            cheaper_station = self._find_cheaper_station(
                station,
                stations,
                current_position,
                current_fuel,
            )

            if cheaper_station:
                # Buy only enough to reach that cheaper station
                fuel_to_buy = self._fuel_needed_to_reach(
                    cheaper_station,
                    current_position,
                    current_fuel,
                )
            else:
                # Best price in reach — fill the tank
                fuel_to_buy = self._fuel_for_max_range(current_fuel)

            if fuel_to_buy > 0:
                cost = round(fuel_to_buy * station["price"], 4)
                current_fuel += fuel_to_buy
                total_cost += cost

                stops.append({
                    "station_id": station["id"],
                    "name": station["name"],
                    "price_per_gallon": round(station["price"], 4),
                    "gallons": round(fuel_to_buy, 4),
                    "cost": cost,
                    "distance_from_start_miles": station["distance_from_start"],
                    "latitude": station.get("latitude"),
                    "longitude": station.get("longitude"),
                })

        return {
            "stops": stops,
            "total_cost": round(total_cost, 2),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_cheaper_station(
        self,
        current_station,
        stations,
        current_position,
        current_fuel,
    ):
        """
        Look ahead for the nearest station that is:
          1. Further along the route than current_station
          2. Cheaper than current_station
          3. Reachable on the current tank
        Returns the first such station, or None.
        """
        max_reachable = current_position + current_fuel * self.MPG

        for s in stations:
            if s["distance_from_start"] <= current_station["distance_from_start"]:
                continue
            if s["distance_from_start"] > max_reachable:
                break  # stations are sorted; no point looking further
            if s["price"] < current_station["price"]:
                return s

        return None

    def _fuel_needed_to_reach(
        self,
        target_station,
        current_position,
        current_fuel,
    ):
        """
        Gallons to buy NOW so we arrive at target_station with exactly 0 fuel
        (we'll refuel there).  Returns 0 if we already have enough.
        """
        distance = target_station["distance_from_start"] - current_position
        fuel_required = distance / self.MPG
        shortfall = fuel_required - current_fuel
        return max(0.0, shortfall)

    def _fuel_for_max_range(self, current_fuel):
        """Gallons needed to top up to tank capacity."""
        return max(0.0, self.TANK_CAPACITY - current_fuel)