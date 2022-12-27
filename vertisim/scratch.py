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



# Merge the "performance_metrics" tables from performance_metrics_3.db and performance_metrics_2.db. Keep the column names the same.
import sqlite3
import pandas as pd

# Connect to the database
conn = sqlite3.connect('performance_metrics_3.db')

# Read the "performance_metrics" table into a pandas dataframe
df = pd.read_sql_query("SELECT * FROM performance_metrics", conn)

# Close the connection
conn.close()

# Connect to the database
conn = sqlite3.connect('performance_metrics_2.db')

# Read the "performance_metrics" table into a pandas dataframe
df_2 = pd.read_sql_query("SELECT * FROM performance_metrics", conn)

# Close the connection
conn.close()

# Merge the two dataframes
df = pd.concat([df, df_2])

# Create a new database and save the merged dataframe to the new database
conn = sqlite3.connect('performance_metrics_merged.db')
df.to_sql('performance_metrics', conn, index=False)
conn.close()






# Remove the rows in performance_metrics table in performance_metrics_3.db where passenger_arrival_process_param is 90
import sqlite3
import pandas as pd

# Connect to the database
conn = sqlite3.connect('performance_metrics_3.db')

# Create a cursor
c = conn.cursor()

# Query the database
c.execute("DELETE FROM performance_metrics WHERE passenger_arrival_process_param = 90")

# Commit the changes
conn.commit()

# Close the connection
conn.close()



def find_first_int(string):
    """
    Find the first integer in a string.
    """
    return int(re.findall(r'\d+', string)[0])


def find_second_int(string):
    """
    Find the second integer in a string.
    """
    return int(re.findall(r'\d+', string)[1])


# Using the find_first_int function get the first integer from the "vertiport_layout" column and save the result to a new column called "num_parking_pads"
df['num_parking_pads'] = df['vertiport_layout'].apply(find_first_int)

# function that takes dataframe name and column names to apply filter on the dataframe. Column names and filter values will inputted as dictionary. User should be able to filter the values by using operators like ">", "<", ">=", "<=", "==", "!=" for each of the items in the dictionary. The filter dictionary should be like {"column_name_1": ["operator_1", value1], "column_name_2": ["operator_2", "string"], ...}. Then sort values by the first two columns in the filter dictionary. The function should return the filtered dataframe.
def filter_dataframe(df, filter_dict, sorting_columns=None):
    """
    Filter a pandas dataframe using a dictionary of column names and filter values.
    """
    # Create a list to store the filter expressions
    filter_expressions = []

    # Loop over the filter dictionary
    for column_name, filter_value in filter_dict.items():
        # Get the operator and the value
        operator, value = filter_value

        if type(value) == str:
            # Create the filter expression
            filter_expression = f"{column_name} {operator} '{value}'"
        else:
            # Create the filter expression
            filter_expression = f"{column_name} {operator} {value}"

        # Append the filter expression to the list
        filter_expressions.append(filter_expression)

    # Join the filter expressions with the "and" keyword
    filter_expression = " and ".join(filter_expressions)

    # Filter the dataframe
    df = df.query(filter_expression)

    # Sort the dataframe
    if sorting_columns != None:
        df = df.sort_values(sorting_columns)

    # Return the dataframe
    return df.reset_index(drop=True)


# Set the plot size of a seaborn plot
def set_plot_size(width, height):
    """
    Set the size of a seaborn plot.
    """
    # Set the size of the plots
    plt.rcParams['figure.figsize'] = (width, height)

# Set the font size of a seaborn plot
def set_font_size(size):
    """
    Set the font size of a seaborn plot.
    """
    # Set the font size of the plots
    plt.rcParams['font.size'] = size


# Filter a dataframe column using a list of values
def filter_column(df, column_name, values):

    # Create a list to store the filter expressions
    filter_expressions = []

    # Loop over the values
    for value in values:
        # Create the filter expression
        filter_expression = f"{column_name} == {value}"

        # Append the filter expression to the list
        filter_expressions.append(filter_expression)

    # Join the filter expressions with the "or" keyword
    filter_expression = " or ".join(filter_expressions)

    # Filter the dataframe
    df = df.query(filter_expression)

    # Return the dataframe
    return df


# Terminal code to extract a zip file
import zipfile

# Extract the zip file
with zipfile.ZipFile('performance_metrics.zip', 'r') as zip_ref:
    zip_ref.extractall()

# Import the os module
import os

# Get the current working directory
cwd = os.getcwd()

# Print the current working directory
print(cwd)

# Import the os module
import os

