# VertiSim
Despite operational similarities to commencial airlines, Urban Air Mobility (UAM) operations has unique characteristics. UAM differs from commercial airlines in terms of scheduling, planning, and ground handling. It also varies from urban mobility services due to its relatively complex and longer turnaround process. To address these new problems, VertiSim, a multi-agent discrete-event vertiport simulator, has developed to model passenger arrival/departure processes, eVTOL arrival and departure processes, vertiport surface operations including landing, taxi, passenger boarding/deboarding, charging, take-off and all the interactions between these processes. VertiSim simulates UAM operations and computes performance measures such as aircraft turnaround time, vertiport throughput, surface and terminal area congestion, vertiport resource utilization, passenger transfer time statistics, average aircraft load factor and more. 

## VertiSim Architecture
We adopted the building blocks approach to model the vertiport simulator. This approach allowed us to build comprehensive and flexible vertiport models that can be customized to meet different design and operational requirements. Our main building blocks are structural entities, flow entities, generator entities, and control entities. The structural entities in VertiSim encompass queues and servers that capture the static layout of the simulation environment. The queues comprise terminal airspace, aircraft departure queues, passenger departure queues, taxiway nodes, charger queues and passenger waiting rooms. The servers include TLOFs, taxiway links, parking pads, chargers, and batteries. Servers in VertiSim can have multiple queues, such as the TLOF server which features an aircraft arrival queue at the terminal airspace side and an aircraft departure queue at the vertiport surface side. The server-queue pair is defined as Resource in SimPy. Structural entities are connected to each other, and together they form a graph of the vertiport complex.

The flow entities in VertiSim are aircraft, passengers, passenger groups, and energy. These entities move within the vertiport complex, from one structural entity to another, and interact with the queues and servers. The flow entities ask for permission to use the structural entities, and their requests are granted or delayed based on the availability and used capacity of the structural entities. After the completion of the service, flow entities are required to request permission to use the subsequent structural entity. If the next structural entity is already occupied, the flow entity will wait in the respective queue. The shortest path algorithm, which can be selected by the user, determines the sequence of structural entities that must be traversed from the entry node of the simulation to the exit point of the simulation.

Lastly, the generator entities produce flow entities according to their scheduled arrivals, while the control entities handle tasks such as assigning TLOF for arrival and departure, allocating parking pads, determining arrival/departure priorities, flight creation, and routing.

In process-based simulations, every activity is modeled by a process that involves time. In VertiSim, the activities of flow entities are connected with structural entities via processes. To provide further clarity on the terminology used, it can be stated that the charging activity of an aircraft agent is associated with a charger structural entity through the charging process. The processing time of structural entities, such as the service time at a server, can be specified by the user through deterministic values or probability distributions, or it can emerge through the interaction of the processes.

VertiSim has 8 main modules to simulate processes at a vertiport: Passenger, Aircraft, Vertiport Manager, Scheduler, Vertiport Layout Creator, Configurator, Generator and Battery. In below Fig. we illustrate the VertiSim architecture. The modular design of VertiSim allows the effortless substitution of various models, including those for batteries, aircraft, and passengers.

![vertisim_arch](https://user-images.githubusercontent.com/55157858/209736749-40c8de9b-f0ab-402b-a11e-1f20c247fb7f.png)
 Vertisim Architecture
 
![aircraft_state](https://user-images.githubusercontent.com/55157858/209735096-e9860468-2bd7-4e27-92bb-d098fe1cb362.png)
Aircraft State Machine

![passenger_state](https://user-images.githubusercontent.com/55157858/209735125-18b65e96-a061-4004-a979-1de6bcafa02b.png)
Passenger State Machine

The units of the timed inputs are seconds. These seconds are converted into miliseconds internally. This is the design choice.

# Demo
Below we used 1 FATO (Final Approach and Take-off Area) and 4 parking pad vertiport configuration. FATO utilization is ~100%. Small circular shapes are parking pads and large circular shape is the FATO. The light red lines represent aircraft trajectories. Passenger trajectories are hidden. Aircraft are approaching from right to left and departing from FATO to left.

https://user-images.githubusercontent.com/55157858/205735871-aa410dec-6046-4c5e-9ab4-dc4c79fc3691.mov

# Installation
1. Download all of the files.
2. Open your terminal and cd to vertisim folder
3. Create a virtual environment: If you are using conda write `conda create -n vertisim python=3.8`
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


