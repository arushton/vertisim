from sympy import Piecewise, var
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd


class BatteryModel:
    def __init__(self, charger_max_charge_rate, charger_efficiency, min_reserve_soc):
        self.charger_max_charge_rate = charger_max_charge_rate
        self.charger_efficiency = charger_efficiency
        self.min_reserve_soc = min_reserve_soc

        self.piecewise_soc = self.calc_piecewise_soc_charge_rate_func()

        # self.visualize_piecewise_soc_function(self.piecewise_soc)
        # self.save_battery_model_visual = save_battery_model_visual
        # self.output_folder_path = output_folder_path

    @staticmethod
    def slope_at_soc_charge_rate(max_charge_rate):
        """
        Between 0-20% SoC charge rate is constant. After 20% SoC we observe a linear decrease in the charge rate.
        For more check paper TODO: add paper link
        """
        return max_charge_rate / 80

    def calc_piecewise_soc_charge_rate_func(self):
        """
        Calculates the piecewise function for the charge rate as a function of SoC.
        :return: piecewise linear function
        """
        elbow_soc = 20
        var('x')
        max_charge_rate = self.charger_max_charge_rate * self.charger_efficiency
        piecewise_soc = Piecewise((max_charge_rate, x <= elbow_soc), (
            max_charge_rate - self.slope_at_soc_charge_rate(max_charge_rate) * (x - elbow_soc), x > elbow_soc))
        return piecewise_soc

    @staticmethod
    def calc_charge_rate(piecewise_soc, soc):
        return piecewise_soc.subs(x, soc)

    def compute_charging_process_params(self, battery_size=120):
        """
        Computes the charging process for a given battery size and charge rate. Each aircraft model has its own process
        :param battery_size:
        :return:
        """
        increments_size_in_soc = 1  # in %
        charge_rate_kw = self.charger_max_charge_rate * self.charger_efficiency
        prev_time = 0
        soc_initial = 0
        soc_final = 100
        total_charge = 0
        time = [prev_time]
        charge_rates = [charge_rate_kw]
        socs = [soc_initial]
        cumulative_energy_kwh = [0]

        piecewise_soc = self.calc_piecewise_soc_charge_rate_func()

        for soc in range(soc_initial, soc_final + 1, increments_size_in_soc):
            new_charge_rate_kw = self.calc_charge_rate(piecewise_soc, soc)
            average_kw = (charge_rate_kw + new_charge_rate_kw) / 2

            charge_increment_kwh = increments_size_in_soc / 100 * battery_size  # Charge in the interval
            time_increment = charge_increment_kwh / average_kw
            current_time = prev_time + time_increment
            total_charge += charge_increment_kwh
            cumulative_energy_kwh.append(total_charge)
            time.append(current_time)
            charge_rates.append(average_kw)
            socs.append(soc)
            prev_time = current_time
            charge_rate_kw = average_kw

        return pd.DataFrame(data=list(zip(time, charge_rates, socs, cumulative_energy_kwh)),
                            columns=['time', 'charge_rate', 'soc', 'cumulative_energy_kwh'], dtype=float)




# battery_model = BatteryModel()
#
# print(battery_model.calc_charge_rate(battery_model.piecewise_soc, 30))



    # def visualize_piecewise_soc_function(self, piecewise_soc):
    #     """
    #     Visualizes the piecewise function for the charge rate as a function of SoC.
    #     :param piecewise_soc:
    #     :return:
    #     """
    #     if self.save_battery_model_visual:
    #         x_axis = np.linspace(0, 101, 101)
    #         y_axis = [piecewise_soc.subs(x, i) for i in x_axis]
    #         plt.plot(x_axis, y_axis)
    #         plt.xlabel('SoC %')
    #         plt.ylabel('Charge Power (kW)')
    #         plt.grid('on', alpha=0.5)
    #         plt.savefig(f'{self.output_folder_path}/battery_model.png')