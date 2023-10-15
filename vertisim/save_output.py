import mysql.connector

def save_output():
    """Saves output to mySQL database.
    Simulation: ID | Timestamp | Config
    Performance Metrics: ID | SimulationID | Metric_1 | Metric_2 | ... | Metric_N """
    
    # TODO: Pick save_output parameters
    """ save_output(
            trajectories={
                'aircraft_agent_trajectory': self.event_saver.aircraft_agent_trajectory,
                'passenger_agent_trajectory': self.event_saver.passenger_agent_trajectory
            },
            time_tables={
                'flight_schedule': self.event_saver.flight_schedule,
                'ground_aircraft_counter': self.event_saver.ground_aircraft_counter,
                'flying_aircraft_counter': self.event_saver.flying_aircraft_counter
            },
            trackers={
                'aircraft_idle_time_tracker': self.event_saver.aircraft_idle_time_tracker,
                'flight_and_time_tracker': self.event_saver.flight_and_time_tracker,
                'aircraft_holding_time': self.event_saver.aircraft_holding_time,
                'passenger_trip_time_tracker': self.event_saver.passenger_trip_time_tracker,
                'aircraft_process_time_tracker': self.event_saver.aircraft_process_time_tracker,
                'flight_phase_energy_consumption_tracker': self.event_saver.flight_phase_energy_consumption_tracker
            },
            simulation_params={
                'sim_params': self.sim_params,
                'network_and_demand': self.network_and_demand_params,
                'passenger_params': self.passenger_params,
                'aircraft_params': self.aircraft_params,
                'output_params': self.output_params
            },
            output_dir=self.output_folder_path,
            config_output_file_name=self.output_params['config_output_file_name'],
            performance_metrics_output_file_name=self.output_params['performance_metrics_output_file_name'],
            performance_metrics=performance_metrics,
            sim_id=self.sim_id
        ) """

    db = mysql.connector.connect(
        host="localhost",
        user="root",
        passwd="*()&*!@&*382",
        database="vertisimdatabase"
    )

    cursor = db.cursor()
    
    # TODO: initialize Simulation and Performance Metrics Tables
