# VertiSim
VertiSim distinguishes itself from legacy aviation simulators by simultaneously modeling three critical flows: passenger, aircraft, and energy. This integrated approach reflects the unique operational characteristics of e-VTOL networks where flight durations, passenger waiting times, and aircraft charging times at vertiports are closely interrelated, necessitating a comprehensive understanding and detailed study of each flow for a holistic evaluation of system performance. VertiSim processes these interdependent flow into key metrics instrumental for effective network operation, such as aircraft utilization, average load factor, vertiport throughput, terminal area congestion, utilization of resources, energy consumption for each flight phase, repositioning flights, and passenger waiting times.

## VertiSim Architecture
We adopted the building blocks approach to model the vertiport simulator. This approach allowed us to build comprehensive and flexible vertiport models that can be customized to meet different design and operational requirements. Our main building blocks are structural entities, flow entities, generator entities, and control entities. Structural entities form the static layout of the simulation environment with elements like queues and servers. Flow entities such as aircraft, passengers, passenger groups, and energy interact with and move within these structural entities. Generator entities produce flow entities based on their schedule, while control entities handle tasks such as assigning TLOF (Touch-down and Lift-Off area) for arrival and departure, allocating parking pads, determining service priorities, dispatching flights, initiating charging and routing.

VertiSim employs a graph-theoretic methodology to build structural entities based on the input vertiport layout. The simulation environment is conceptualized as a network of nodes and links, $G(V, E)$ in which $V = \{v_i\}$ is its vertex set and $E = \{(v_i, v_j)\}$ its edge set. Node positions are sourced from the input data. In VertiSim, every node and link is treated as a resource with a user-specified capacity. The software architecture of VertiSim comprises nine main modules: Passenger, Aircraft, Airspace, Vertiport Manager, Scheduler, Vertiport Layout Creator, Configurator, Generator and Battery. In below Fig. we illustrate the VertiSim architecture. The modular design of VertiSim allows the effortless substitution of various models, including those for batteries, aircraft, and passengers.

![vertisim_arch](https://user-images.githubusercontent.com/55157858/209736749-40c8de9b-f0ab-402b-a11e-1f20c247fb7f.png)
 Vertisim Architecture
 
![aircraft_state](https://user-images.githubusercontent.com/55157858/209735096-e9860468-2bd7-4e27-92bb-d098fe1cb362.png)
Aircraft State Machine

![passenger_state](https://user-images.githubusercontent.com/55157858/209735125-18b65e96-a061-4004-a979-1de6bcafa02b.png)
Passenger State Machine

The units of the timed inputs are seconds. These seconds are converted into miliseconds internally. This is the design choice.

# Demo
Small circular shapes are parking pads and large circular shapes are FATO. The light red lines represent aircraft trajectories. Passenger trajectories are hidden.

https://user-images.githubusercontent.com/55157858/205735871-aa410dec-6046-4c5e-9ab4-dc4c79fc3691.mov

# VertiSim v2.0
## Key Features:
1. Triad Flow Modeling: A unique capability to simultaneously model passenger, aircraft, and energy flows, which is pivotal for understanding e-VTOL operations.

2. Holistic Infrastructure Modeling: Comprehensive infrastructure representation, encompassing vertiports, air routes, and flight profiles.

3. Advanced Charging & Discharging: Capture the nuances of energy dynamics through non-linear charging models, moving beyond the constraints of traditional linear models.

4. Dynamic Optimization Engine: An offline optimization model that harmonizes flight and charging schedules, adapting to variable demand scenarios.

5. Multi-Vertiport System: Specialized numerical analysis focusing on a two-vertiport system to optimize fleet utilization, resource management, and passenger experience.

## Metrics Offered:
- Aircraft Utilization
- Average Load Factor
- Vertiport Throughput
- Terminal Area Congestion
- Vertiport Resource Utilization
- Aircraft Energy Consumption
- Repositioning Flights
- Passenger Trip Times
- and more...

# Installation
1. Download all of the files.
2. Open your terminal and cd to vertisim folder
3. Create a virtual environment: If you are using conda write `conda create -n vertisim python=3.11`
4. After you create your environment activate your environment by writing `conda activate vertisim` to your terminal.
5. Install the requirements with `pip install -r requirements.txt`
6. Done!

For questions and collaborations, please email eminburak_onat@berkeley.edu. Thanks!

# How To Run
1. Activate the vertisim environment (for conda users `conda activate vertisim`)
2. There are three ways of running vertisim. <br>
a) Run a single configuration: `python3 inputs.py` <br>
b) Run many configuration serially: `python3 loop_runner.py` <br>
c) Run many configuration in parallel (CPU parallelization by multiprocessing): `python3 loop_runner_multiprocess.py`


