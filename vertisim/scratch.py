import pandas as pd

df[['vertiport_layout',
    'max_passenger_waiting_time_threshold',
    'passenger_arrival_process_param'
   'aircraft_arrival_process_param',
   'charging_time_param_mu',
   'mean_passenger_consolidation_time',
    'max_passenger_consolidation_time',
    'min_passenger_consolidation_time',
   'mean_passenger_waiting_time',
   'max_passenger_waiting_time',
   'min_passenger_waiting_time',
   'mean_aircraft_arrival_queue_count',
   'mean_load_factor',
   'max_load_factor',
   'min_load_factor',
   'mean_aircraft_throughput',
   'mean_passenger_throughput',
   'fato_utilization']]

# Visualize the above data in a meaningful way
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Set the style of the plots
sns.set_style("whitegrid")
sns.set_context("paper")

# Set the size of the plots
plt.rcParams['figure.figsize'] = (10, 6)

# Set the font size of the plots
plt.rcParams['font.size'] = 12

# Set the font family of the plots
plt.rcParams['font.family'] = 'serif'

# Set the font style of the plots
plt.rcParams['font.style'] = 'normal'

# Set the font variant of the plots
plt.rcParams['font.variant'] = 'normal'

# Set the font weight of the plots
plt.rcParams['font.weight'] = 'normal'

# Set the font stretch of the plots
plt.rcParams['font.stretch'] = 'normal'

# Set the font size of the axes
plt.rcParams['axes.labelsize'] = 12

# Set the font size of the legend
plt.rcParams['legend.fontsize'] = 12

# Set the font size of the ticks
plt.rcParams['xtick.labelsize'] = 12
plt.rcParams['ytick.labelsize'] = 12

# Set the font size of the title
plt.rcParams['axes.titlesize'] = 12

# Set the font size of the figure
plt.rcParams['figure.titlesize'] = 12

# Visualize the mean_aircraft_throughput vs passenger_arrival_process_param
sns.lineplot(x='passenger_arrival_process_param', y='mean_aircraft_throughput', hue='vertiport_layout', data=df)
plt.show()



# Merge the "performance_metrics" tables from performance_metrics.db and performance_metrics_2.db
import sqlite3
import pandas as pd

# Connect to the database
conn = sqlite3.connect('performance_metrics.db')
conn_2 = sqlite3.connect('performance_metrics_2.db')

# Create a cursor
c = conn.cursor()
c_2 = conn_2.cursor()

# Query the database
c.execute("SELECT * FROM performance_metrics")
c_2.execute("SELECT * FROM performance_metrics")

# Fetch the results
results = c.fetchall()
results_2 = c_2.fetchall()

# Create a dataframe
df = pd.DataFrame(results)
df_2 = pd.DataFrame(results_2)

# Close the connection
conn.close()
conn_2.close()

# Merge the two dataframes
df = pd.concat([df, df_2], ignore_index=True)



# Remove the rows in performance_metrics table in performance_metrics.db where passenger_arrival_process_param is 90
import sqlite3
import pandas as pd

# Connect to the database
conn = sqlite3.connect('performance_metrics.db')

# Create a cursor
c = conn.cursor()

# Query the database
c.execute("DELETE FROM performance_metrics WHERE passenger_arrival_process_param = 90")

# Commit the changes
conn.commit()

# Close the connection
conn.close()


