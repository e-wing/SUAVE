# test_solar_network.py
# 
# Created:  Aug 2014, Emilio Botero, 
#           Mar 2020, M. Clarke
#           Apr 2020, M. Clarke

#----------------------------------------------------------------------
#   Imports
# ----------------------------------------------------------------------

import SUAVE
from SUAVE.Core import Units
from SUAVE.Plots.Mission_Plots import *  
import matplotlib.pyplot as plt  
from SUAVE.Core import (
Data, Container,
)

import numpy as np
import copy, time

from SUAVE.Components.Energy.Networks.Solar import Solar
from SUAVE.Methods.Propulsion import propeller_design
from SUAVE.Methods.Power.Battery.Sizing import initialize_from_energy_and_power, initialize_from_mass

import sys

sys.path.append('../Vehicles')
# the analysis functions

from Solar_UAV import vehicle_setup, configs_setup

def main():
    
 
    # vehicle data
    vehicle  = vehicle_setup()
    configs  = configs_setup(vehicle)
    
    # vehicle analyses
    configs_analyses = analyses_setup(configs)
    
    # mission analyses
    mission  = mission_setup(configs_analyses,vehicle)
    missions_analyses = missions_setup(mission)

    analyses = SUAVE.Analyses.Analysis.Container()
    analyses.configs  = configs_analyses
    analyses.missions = missions_analyses
    
    configs.finalize()
    analyses.finalize()    
    
    # weight analysis
    weights = analyses.configs.base.weights    
    
    # mission analysis
    mission = analyses.missions.base
    results = mission.evaluate()

    # load older results
    #save_results(results)
    old_results = load_results()   

    # plt the old results
    plot_mission(results)
    plot_mission(old_results,'k-') 
    
    # Check Results 
    F       = results.segments.cruise1.conditions.frames.body.thrust_force_vector[1,0]
    rpm     = results.segments.cruise1.conditions.propulsion.rpm[1,0] 
    current = results.segments.cruise1.conditions.propulsion.current[1,0] 
    energy  = results.segments.cruise1.conditions.propulsion.battery_energy[8,0]  
    
    # Truth results
    truth_F   = 110.95088296453225
    truth_rpm = 163.49393123862325
    truth_i   = 137.91886268177407
    truth_bat = 88509256.18474567
    
    print('battery energy')
    print(energy)
    print('\n')
    
    error = Data()
    error.Thrust   = np.max(np.abs(F-truth_F))
    error.RPM      = np.max(np.abs(rpm-truth_rpm))
    error.Current  = np.max(np.abs(current-truth_i))
    error.Battery  = np.max(np.abs(energy-truth_bat))
    
    print(error)
    
    for k,v in list(error.items()):
        assert(np.abs(v)<1e-6)
 
    
    return


# ----------------------------------------------------------------------        
#   Setup Analyses
# ----------------------------------------------------------------------  

def analyses_setup(configs):
    
    analyses = SUAVE.Analyses.Analysis.Container()
    
    # build a base analysis for each config
    for tag,config in configs.items():
        analysis = base_analysis(config)
        analyses[tag] = analysis
    
    return analyses

# ----------------------------------------------------------------------        
#   Define Base Analysis
# ----------------------------------------------------------------------  

def base_analysis(vehicle): # ------------------------------------------------------------------
    #   Initialize the Analyses
    # ------------------------------------------------------------------     
    analyses = SUAVE.Analyses.Vehicle()
    
    # ------------------------------------------------------------------
    #  Basic Geometry Relations
    sizing = SUAVE.Analyses.Sizing.Sizing()
    sizing.features.vehicle = vehicle
    analyses.append(sizing)
    
    # ------------------------------------------------------------------
    #  Weights
    weights = SUAVE.Analyses.Weights.Weights_UAV()
    weights.settings.empty_weight_method = \
        SUAVE.Methods.Weights.Correlations.Human_Powered.empty
    weights.vehicle = vehicle
    analyses.append(weights)
    
    # ------------------------------------------------------------------
    #  Aerodynamics Analysis
    aerodynamics = SUAVE.Analyses.Aerodynamics.Fidelity_Zero()
    aerodynamics.settings.plot_vortex_distribution   = True 
    aerodynamics.geometry                            = vehicle
    aerodynamics.settings.drag_coefficient_increment = 0.0000
    analyses.append(aerodynamics)
    
    # ------------------------------------------------------------------
    #  Energy
    energy = SUAVE.Analyses.Energy.Energy()
    energy.network = vehicle.propulsors #what is called throughout the mission (at every time step))
    analyses.append(energy)
    
    # ------------------------------------------------------------------
    #  Planet Analysis
    planet = SUAVE.Analyses.Planets.Planet()
    analyses.append(planet)
    
    # ------------------------------------------------------------------
    #  Atmosphere Analysis
    atmosphere = SUAVE.Analyses.Atmospheric.US_Standard_1976()
    atmosphere.features.planet = planet.features
    analyses.append(atmosphere)   
 
    return analyses    


# ----------------------------------------------------------------------
#   Define the Mission
# ----------------------------------------------------------------------
def mission_setup(analyses,vehicle):
    
    # ------------------------------------------------------------------
    #   Initialize the Mission
    # ------------------------------------------------------------------

    mission = SUAVE.Analyses.Mission.Sequential_Segments()
    mission.tag = 'The Test Mission'

    mission.atmosphere  = SUAVE.Attributes.Atmospheres.Earth.US_Standard_1976()
    mission.planet      = SUAVE.Attributes.Planets.Earth()
    
    # unpack Segments module
    Segments = SUAVE.Analyses.Mission.Segments
    
    # base segment
    base_segment = Segments.Segment()   
    ones_row     = base_segment.state.ones_row
    base_segment.process.iterate.unknowns.network            = vehicle.propulsors.solar.unpack_unknowns
    base_segment.process.iterate.residuals.network           = vehicle.propulsors.solar.residuals    
    base_segment.process.iterate.initials.initialize_battery = SUAVE.Methods.Missions.Segments.Common.Energy.initialize_battery
    base_segment.state.unknowns.propeller_power_coefficient  = vehicle.propulsors.solar.propeller.power_coefficient  * ones_row(1)/15.
    base_segment.state.residuals.network                     = 0. * ones_row(1)      
    
    # ------------------------------------------------------------------    
    #   Cruise Segment: constant speed, constant altitude
    # ------------------------------------------------------------------    
    
    segment = SUAVE.Analyses.Mission.Segments.Cruise.Constant_Mach_Constant_Altitude(base_segment)
    segment.tag = "cruise1"
    
    # connect vehicle configuration
    segment.analyses.extend( analyses.cruise)
    
    # segment attributes     
    segment.state.numerics.number_control_points = 16
    segment.start_time     = time.strptime("Tue, Jun 21 11:30:00  2020", "%a, %b %d %H:%M:%S %Y",)
    segment.altitude       = 15.0  * Units.km 
    segment.mach           = 0.12
    segment.distance       = 3050.0 * Units.km
    segment.battery_energy = vehicle.propulsors.solar.battery.max_energy*0.3 #Charge the battery to start
    segment.latitude       = 37.4300   # this defaults to degrees (do not use Units.degrees)
    segment.longitude      = -122.1700 # this defaults to degrees
    
    mission.append_segment(segment)    

    # ------------------------------------------------------------------    
    #   Mission definition complete    
    # ------------------------------------------------------------------
    
    return mission


def missions_setup(base_mission):

    # the mission container
    missions = SUAVE.Analyses.Mission.Mission.Container()

    # ------------------------------------------------------------------
    #   Base Mission
    # ------------------------------------------------------------------
    missions.base = base_mission 
    
    # done!
    return missions  

# ----------------------------------------------------------------------
#   Plot Mission
# ----------------------------------------------------------------------

def plot_mission(results,line_style='bo-'):     
    
    # Plot Propeller Performance 
    plot_propeller_conditions(results,line_style)
    
    # Plot Power and Disc Loading
    plot_disc_power_loading(results,line_style)
    
    # Plot Solar Radiation Flux
    plot_solar_flux(results,line_style) 
    
    return



def load_results():
    return SUAVE.Input_Output.SUAVE.load('solar_uav_mission.res')

def save_results(results):
    SUAVE.Input_Output.SUAVE.archive(results,'solar_uav_mission.res')
    return


# ----------------------------------------------------------------------        
#   Call Main
# ----------------------------------------------------------------------    

if __name__ == '__main__':
    main()
    plt.show()
