"""
Pure-pursuit expert (the DAgger label oracle). Uses CARLA HD-map waypoints to
compute the geometrically-correct steering command from the vehicle pose. This
is privileged (map-based), the neural policy must later reproduce it from
camera pixels alone.
"""

import carla



def nearest_waypoint(world_map, vehicle_location):
    """Driving-lane waypoint nearest the vehicle (projected to road center)."""
    return world_map.get_waypoint(
        vehicle_location, project_to_road=True, lane_type=carla.LaneType.Driving
    )

