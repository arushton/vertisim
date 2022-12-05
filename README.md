# VertiSim
Despite operational similarities to commencial airlines, Urban Air Mobility (UAM) operations has unique characteristics. UAM differs from commercial airlines in terms of scheduling, planning, and ground handling. It also varies from urban mobility services due to its relatively complex and longer turnaround process. To address these new problems, VertiSim, an agent-based discrete-event vertiport simulator, has developed to model eVTOL arrival and departure processes, vertiport surface operations including landing, taxi, passenger boarding/deboarding, charging, take-off, passenger arrival/departure processes and all the interactions between these processes. VertiSim simulates UAM operations and computes performance measures such as aircraft turnaround time, vertiport throughput, surface and terminal area congestion, vertiport resource utilization, passenger transfer time statistics, average aircraft load factor and more. 
 
# Installation
1. Download all of the files.
2. Open your terminal and cd to vertisim folder
3. Create a virtual environment: If you are using conda write `conda create -n vertisim python=3.8`
4. After you create your environment activate your environment by writing `conda activate vertisim` to your terminal.
5. Install the requirements with `pip install -r requirements.txt`
6. Done!


# Demo
Below we used 1 FATO (Final Approach and Take-off Area) and 4 parking pad vertiport configuration. FATO utilization is 100%.

https://user-images.githubusercontent.com/55157858/205735871-aa410dec-6046-4c5e-9ab4-dc4c79fc3691.mov

