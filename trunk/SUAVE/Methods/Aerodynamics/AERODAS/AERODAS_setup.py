## @ingroup Methods-Aerodynamics-AERODAS
# AERODAS_setup.py
# 
# Created:  Feb 2016, E. Botero
# Modified: Jun 2017, E. Botero

# ----------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------

import jax.numpy as np
from SUAVE.Core import Data, Units

# ----------------------------------------------------------------------
#  Setup Daa
# ----------------------------------------------------------------------

## @ingroup Methods-Aerodynamics-AERODAS
def setup_data(state,settings,geometry):
    """ This sets up the data structure for pre and post stall coefficients
    that will be generated by the AERODAS model.

    Assumptions:
    None

    Source:
    NASA TR: "Models of Lift and Drag Coefficients of Stalled and Unstalled Airfoils in
      Wind Turbines and Wind Tunnels" by D. A. Spera

    Inputs:
    state.conditions.aerodynamics (to be modified)

    Outputs:
    None

    Properties Used:
    N/A
    """      
    
    state.conditions.aerodynamics.pre_stall_coefficients  = Data()
    state.conditions.aerodynamics.post_stall_coefficients = Data()
    
    
    return 

# ----------------------------------------------------------------------
#  Lift and Drag Total
# ----------------------------------------------------------------------

## @ingroup Methods-Aerodynamics-AERODAS
def lift_drag_total(state,settings,geometry):
    """ This sums lift and drag contributions from all of the wings.

    Assumptions:
    None

    Source:
    NASA TR: "Models of Lift and Drag Coefficients of Stalled and Unstalled Airfoils in
      Wind Turbines and Wind Tunnels" by D. A. Spera

    Inputs:
    geometry.
      reference_area                                                      [m^2]
      wings
    state.conditions.aerodynamics.
      angle_of_attack                                                     [radians]
      pre_stall_coefficients[wing.tag].lift_coefficient (for each wing)   [Unitless]
      pre_stall_coefficients[wing.tag].drag_coefficient (for each wing)   [Unitless]
      post_stall_coefficients[wing.tag].lift_coefficient (for each wing)  [Unitless]
      post_stall_coefficients[wing.tag].drag_coefficient (for each wing)  [Unitless]
    settings.section_zero_lift_angle_of_attack                            [radians]

    Outputs:
    state.conditions.aerodynamics.
      lift_coefficient                                                    [Unitless]
      drag_coefficient                                                    [Unitless]

    Properties Used:
    N/A
    """      
    
    # prime the totals
    CL_total = 0.
    CD_total = 0.
    
    # Unpack general things
    ref       = geometry.reference_area
    wing_aero = state.conditions.aerodynamics
    alpha     = state.conditions.aerodynamics.angle_of_attack
    A0        = settings.section_zero_lift_angle_of_attack
    
    #  loop through each wing 
    for wing in geometry.wings:
        
        # unpack inputs
        area = wing.areas.reference
        CL1  = wing_aero.pre_stall_coefficients[wing.tag].lift_coefficient
        CD1  = wing_aero.pre_stall_coefficients[wing.tag].drag_coefficient
        CL2  = wing_aero.post_stall_coefficients[wing.tag].lift_coefficient
        CD2  = wing_aero.post_stall_coefficients[wing.tag].drag_coefficient
        
        # Equation 3a
        CL = np.fmax(CL1,CL2)
        
        # Equation 3b
        CL[alpha<=A0] = np.fmin(CL1[alpha<=A0],CL2[alpha<=A0])
        
        # Equation 3c
        CD            = np.fmax(CD1,CD2)
        
        # Add to the total
        CD_total      = CD_total + CD*area/ref

        if wing.vertical == False:
            CL_total      = CL_total + CL*area/ref
        else:
            pass

        
    CD_total = CD_total + settings.drag_coefficient_increment
        
    # Pack outputs
    state.conditions.aerodynamics.lift_coefficient = CL_total
    state.conditions.aerodynamics.drag_coefficient = CD_total
    
    return CL_total, CD_total


# ----------------------------------------------------------------------
#  Drag Total
# ----------------------------------------------------------------------

## @ingroup Methods-Aerodynamics-AERODAS
def drag_total(state,settings,geometry):
    """Extract the drag coefficient

    Assumptions:
    None

    Source:
    N/A

    Inputs:
    state.conditions.aerodynamics.drag_coefficient [Unitless]

    Outputs:
    CD (coefficient of drag)                       [Unitless]

    Properties Used:
    N/A
    """  
    
    CD = state.conditions.aerodynamics.drag_coefficient     
    
    return CD