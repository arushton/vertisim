class PhaseParameters:
    
    def __init__(self, take_off_mass, altitude, horizontal_distance, vertical_distance, cost_type):
        """Note: the initial guess of V is not included because it is assumed to have no impact on the final optimal velocities."""
        self.signature = (take_off_mass, altitude, horizontal_distance, vertical_distance, cost_type)
        
    def __eq__(self, other):
        if isinstance(other, PhaseParameters):
            return self.signature == other.signature
        return False
    
    def __hash__(self) -> int:
        return hash(self.signature)
    
    