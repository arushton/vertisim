# VertiSim
Despite operational similarities to commencial airlines, Urban Air Mobility (UAM) operations has unique characteristics. UAM differs from commercial airlines in terms of scheduling, planning, and ground handling. It also varies from urban mobility services due to its relatively complex and longer turnaround process. To address these new problems, VertiSim, a multi-agent discrete-event vertiport simulator, has developed to model passenger arrival/departure processes, eVTOL arrival and departure processes, vertiport surface operations including landing, taxi, passenger boarding/deboarding, charging, take-off and all the interactions between these processes. VertiSim simulates UAM operations and computes performance measures such as aircraft turnaround time, vertiport throughput, surface and terminal area congestion, vertiport resource utilization, passenger transfer time statistics, average aircraft load factor and more. 

## VertiSim Architecture
VertiSim is driven by an event queue for which events are processed in chronological sequence. In process-based simulations every activity is modeled by a process. In other words, processes requires an activity that involves in time. VertiSim has five main modules to simulate processes at a vertiport: Passenger, Aircraft, Vertiport Manager, Scheduler, and Vertiport Layout Creator. Below VertiSim architecture presented.

![vertisim_arch](https://user-images.githubusercontent.com/55157858/209736749-40c8de9b-f0ab-402b-a11e-1f20c247fb7f.png)
 Vertisim Architecture
 
![aircraft_state](https://user-images.githubusercontent.com/55157858/209735096-e9860468-2bd7-4e27-92bb-d098fe1cb362.png)
Aircraft State Machine

![passenger_state](https://user-images.githubusercontent.com/55157858/209735125-18b65e96-a061-4004-a979-1de6bcafa02b.png)
Passenger State Machine


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


# TODO
1. Charging process interruption.
2. Battery charging model for multi-aircraft type scenario.
3. Passenger - aircraft assignment problem in the case of more than one type of aircraft.
4. Documentation

