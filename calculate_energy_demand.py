import json
import psycopg2

inp_file = open('./out_data/store_input_data_marked.json', "r")
data = json.load(inp_file)
inp_file.close()
cityobjects = data["CityObjects"]

# ---------------------------------------------------------------------------------------------
### Read database connection details
db_param = []
# with open('../P3/database_connection.txt') as f:
with open("./database_connection.txt") as f:
    lines = f.readlines()
    x = lines[0].split(' ')
    for par in x:
        db_param.append(par)

### Connection parameters
host = db_param[0]
port = int(db_param[1])
db = db_param[2]
user = db_param[3]
passw = db_param[4]

# ---------------------------------------------------------------------------------------------
## Connect to database
conn = psycopg2.connect(host=host, port=port, database=db, user=user, password=passw)

# --------------------------------------------------------------------------------------
### Fixed surcharge for linear thermal bridges
def deltaUfor(nom, denom):
    deltaU_second_part = 0.1 - 0.25 * (nom / denom - 0.4)
    if deltaU_second_part > 0:
        delta_final = deltaU_second_part
    else:
        delta_final = 0

    return delta_final
# ---------------------------------------------------------------------------------------------
### Heat coefficient for vertical pipes
def heat_coeff_pipes(num_pipes, num_storeys):
    pipe_coeff = 1.8  # Taken from NTA8800 Table 7.1
    sum_value = 0
    for y in range(num_pipes):
        multiply = num_storeys * pipe_coeff
        sum_value += multiply

    return sum_value
# ---------------------------------------------------------------------------------------------
### Format inclination to retrieve visibility factor
def visibility_inclination(incl):
    if incl <= 5:
        new_incl = "(-5]"
    elif 5 < incl <= 75:
        new_incl = "(5-75]"
    else:
        new_incl = "(75- )"
    return new_incl
# --------------------------------------------------------------------------------------
### Round inclination value
def round_inc(inc_val):
    if 0 <= inc_val <= 30:
        if 0 <= inc_val < 15:
            inc_val = 0
        elif 15 <= inc_val <= 30:
            inc_val = 30
    elif 30 < inc_val <= 45:
        if 30 < inc_val < 37.5:
            inc_val = 30
        elif 37.5 <= inc_val <= 45:
            inc_val = 45
    elif 45 < inc_val <= 60:
        if 45 < inc_val < 52.5:
            inc_val = 45
        elif 52.5 <= inc_val <= 60:
            inc_val = 60
    elif 60 < inc_val <= 90:
        if 60 < inc_val < 75:
            inc_val = 60
        elif 75 <= inc_val <= 90:
            inc_val = 90
    elif 90 < inc_val <= 135:
        if 90 < inc_val < 112.5:
            inc_val = 90
        elif 112.5 <= inc_val <= 135:
            inc_val = 135
    elif 135 < inc_val <= 180:
        if 135 < inc_val < 157.5:
            inc_val = 135
        elif 157.5 <= inc_val <= 180:
            inc_val = 180

    return inc_val

# --------------------------------------------------------------------------------------
### Round slope value
def round_slope(slope_val):
    return 15 * round(slope_val / 15)

# --------------------------------------------------------------------------------------
length_of_month = [744, 672, 744, 720, 744, 720, 744, 744, 720, 744, 720, 744] # According to NTA 8800
time_num = 0

for each_cityobj in cityobjects.copy():
    if cityobjects[each_cityobj]["type"] == "Building" or cityobjects[each_cityobj]["type"] == "BuildingPart":
        if cityobjects[each_cityobj]["attributes"]["bdg_in_calculation"] == "yes":
            thermal_name = cityobjects[each_cityobj]["children"][0]
            deltaU_nom_wall_roof = 0
            deltaU_denom_wall_roof = 0
            deltaU_nom_shared = 0
            deltaU_denom_shared = 0
            coeff_inside_outside = 0
            coeff_shared_wall = 0
            total_coeff_through_transmission_ground = 0
            final_energy_demand_values = []
            for each_boundary in cityobjects[thermal_name]["energy-boundedBy"]:
                boundary_attributes = cityobjects[each_boundary]["attributes"]
                if boundary_attributes["energy-thermalBoundaryType"] == "roof" or boundary_attributes["energy-thermalBoundaryType"] == "outerWall":
                    thermal_bound_area = boundary_attributes["energy-area"]
                    const_name = cityobjects[each_boundary]["energy-opaqueConstruction"]
                    thermal_bound_uValue = cityobjects[const_name]["attributes"]["energy-uValue"]
                    deltaU_nom_wall_roof += (thermal_bound_area * thermal_bound_uValue)
                    deltaU_denom_wall_roof += thermal_bound_area
                elif boundary_attributes["energy-thermalBoundaryType"] == "sharedWall" and boundary_attributes["calculate_energy_demand"] == "yes":
                    thermal_bound_area = boundary_attributes["energy-area"]
                    const_name = cityobjects[each_boundary]["energy-opaqueConstruction"]
                    thermal_bound_uValue = cityobjects[const_name]["attributes"]["energy-uValue"]
                    deltaU_nom_shared += (thermal_bound_area * thermal_bound_uValue)
                    deltaU_denom_shared += thermal_bound_area
                elif boundary_attributes["energy-thermalBoundaryType"] == "groundSlab":
                    thermal_bound_area = boundary_attributes["energy-area"]
                    const_name = cityobjects[each_boundary]["energy-opaqueConstruction"]
                    thermal_bound_uValue = cityobjects[const_name]["attributes"]["energy-uValue"]
                    bdg_perim = cityobjects[thermal_name]["attributes"]["energy-perimeter"]
                    total_coeff_through_transmission_ground += thermal_bound_area * thermal_bound_uValue + 0.5 * bdg_perim

            deltaU_wall_roof = deltaUfor(deltaU_nom_wall_roof, deltaU_denom_wall_roof)
            for each_boundary in cityobjects[thermal_name]["energy-boundedBy"]:
                boundary_attributes = cityobjects[each_boundary]["attributes"]
                if boundary_attributes["energy-thermalBoundaryType"] == "roof" or boundary_attributes["energy-thermalBoundaryType"] == "outerWall":
                    thermal_bound_area = boundary_attributes["energy-area"]
                    const_name = cityobjects[each_boundary]["energy-opaqueConstruction"]
                    thermal_bound_uValue = cityobjects[const_name]["attributes"]["energy-uValue"]
                    coeff_inside_outside += (thermal_bound_area * (thermal_bound_uValue + deltaU_wall_roof))
                elif boundary_attributes["energy-thermalBoundaryType"] == "sharedWall" and boundary_attributes["calculate_energy_demand"] == "yes":
                    thermal_bound_area = boundary_attributes["energy-area"]
                    const_name = cityobjects[each_boundary]["energy-opaqueConstruction"]
                    thermal_bound_uValue = cityobjects[const_name]["attributes"]["energy-uValue"]
                    coeff_shared_wall += (thermal_bound_area * (thermal_bound_uValue + deltaUfor(deltaU_nom_shared, deltaU_denom_shared)))

            coeff_shared_wall_final = coeff_shared_wall * 0.5  # Add dimensionless reduction factor

            ## Calculate heat coeff. through vertical pipes
            usage_name = cityobjects[thermal_name]["children"][0]
            no_pipes = cityobjects[usage_name]["attributes"]["energy-numberOfResidentialFunctions"]
            no_storey = cityobjects[each_cityobj]["attributes"]["storeysAboveGround"]

            coeff_pipes = heat_coeff_pipes(no_pipes, no_storey)
            total_coeff_through_transmission = coeff_inside_outside + coeff_shared_wall_final + coeff_pipes

            ### Get weather data for indoor and outdoor
            for weather in cityobjects[thermal_name]["attributes"]["energy-weatherData"]:
                if weather["energy-weatherDataLocation"] == "indoor":
                    indoor_time_series_id = weather["energy-values"]
                    indoor_temp_values = cityobjects[indoor_time_series_id]["attributes"]["energy-values"]
                else:
                    outdoor_time_series_id = weather["energy-values"]
                    outdoor_temp_values = cityobjects[outdoor_time_series_id]["attributes"]["energy-values"]
                    avg_out_temp_annual = round(sum(outdoor_temp_values) / len(outdoor_temp_values), 2)

            heat_transfer_through_transmission = []
            for i in range(12):
                if 0 <= i <= 2 or 9 <= i <= 11:
                    trans_coeff_final = (total_coeff_through_transmission * (indoor_temp_values[i] - outdoor_temp_values[i]) + total_coeff_through_transmission_ground * (indoor_temp_values[i] - avg_out_temp_annual)) * 0.001 * length_of_month[i]
                    heat_transfer_through_transmission.append(trans_coeff_final)
                else:
                    heat_transfer_through_transmission.append(0)

            ### Calculate heat transfer through ventilation
            heat_transfer_through_ventilation = []
            density_of_air = 1.205
            heat_capacity_air = 1005
            air_exchange_rate = 0.4
            for each_vol in cityobjects[thermal_name]["attributes"]["energy-volume"]:
                if each_vol["energy-type"] == "energyReferenceVolume":
                    heated_vol = each_vol["energy-value"]
            vent_coeff = (density_of_air * heat_capacity_air * (heated_vol * air_exchange_rate) * 1 * 1) / 3600

            for i in range(12):
                if 0 <= i <= 2 or 9 <= i <= 11:
                    vent_coeff_final = vent_coeff * (indoor_temp_values[i] - outdoor_temp_values[i]) * 0.001 * length_of_month[i]
                    heat_transfer_through_ventilation.append(vent_coeff_final)
                else:
                    heat_transfer_through_ventilation.append(0)

            ### Calculate internal heat gains
            internal_heat_gains = []
            ## Find Occupants object
            occupants_name = cityobjects[usage_name]["energy-occupiedBy"][0]
            ## Find number of residential functions in the building
            num_res_function = cityobjects[usage_name]["attributes"]["energy-numberOfResidentialFunctions"]

            ## Find number of residents in the building
            num_occupants = cityobjects[occupants_name]["attributes"]["energy-numberOfOccupants"]

            for i in range(12):
                if 0 <= i <= 2 or 9 <= i <= 11:
                    heat_gains_final = 180 * num_res_function * num_occupants * 0.001 * length_of_month[i]
                    internal_heat_gains.append(heat_gains_final)
                else:
                    internal_heat_gains.append(0)

            ### Calculate solar gains
            bdg_solar_gains_windows = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            bdg_solar_gains_opaque = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            bdg_solar_gains_opaque_roofs = []
            bdg_solar_gains_final = []
            for each_boundary in cityobjects[thermal_name]["energy-boundedBy"]:
                if cityobjects[each_boundary]["attributes"]["energy-thermalBoundaryType"] == "outerWall" and cityobjects[each_boundary]["attributes"]["energy-windowRatio"] != 0.0 and cityobjects[each_boundary]["attributes"]["energy-area"] > 4:
                    opaque_cons_id = cityobjects[each_boundary]["energy-opaqueConstruction"]
                    transparent_cons_id = cityobjects[each_boundary]["energy-transparentConstruction"]
                    try:
                        const_year = cityobjects[each_cityobj]["attributes"]["yearOfConstruction"]
                    except KeyError:
                        parent_id = cityobjects[each_cityobj]["parents"][0]
                        const_year = cityobjects[parent_id]["attributes"]["yearOfConstruction"]
                    if const_year > 2000:
                        window_ratio = cityobjects[each_boundary]["attributes"]["energy-windowRatio"]
                    else:
                        window_ratio = cityobjects[each_boundary]["attributes"]["energy-windowRatio"]
                    opaque_area = cityobjects[each_boundary]["attributes"]["energy-area"] * (1 - window_ratio)
                    window_area = cityobjects[each_boundary]["attributes"]["energy-area"] * window_ratio
                    inclination = visibility_inclination(cityobjects[each_boundary]["attributes"]["energy-inclination"])
                    opaque_resistance = cityobjects[opaque_cons_id]["attributes"]["energy-rValue"]
                    opaque_uValue = cityobjects[opaque_cons_id]["attributes"]["energy-uValue"]
                    window_resistance = cityobjects[transparent_cons_id]["attributes"]["energy-rValue"]
                    window_uValue = cityobjects[transparent_cons_id]["attributes"]["energy-uValue"]
                    window_gValue = cityobjects[transparent_cons_id]["attributes"]["energy-gValue"]
                    rounded_inclination = round_inc(cityobjects[each_boundary]["attributes"]["energy-inclination"])
                    rounded_slope = round_slope(cityobjects[each_boundary]["attributes"]["energy-slope"])
                    orientation = cityobjects[each_boundary]["attributes"]["energy-orientation"]

                    cur_vis = conn.cursor()
                    cur_vis.execute(
                        """SELECT value FROM weather_table WHERE attribute = %s and inclination_in_degrees = %s """,
                        ("visibility_factor", inclination))
                    query_results = cur_vis.fetchone()
                    visibility_fac = float(query_results[0])

                    extra_heat_flow_opaque = []
                    extra_heat_flow_window = []

                    ## Calculate extra heat flow
                    for i in range(12):
                        if (0 <= i <= 2) or (9 <= i <= 11):
                            heat_flow_q_opaque = 0.001 * visibility_fac * opaque_resistance * opaque_uValue * opaque_area * 4.14 * 11 * length_of_month[i]
                            extra_heat_flow_opaque.append(heat_flow_q_opaque)
                            heat_flow_q_window = 0.001 * visibility_fac * window_resistance * window_uValue * window_area * 4.14 * 11 * length_of_month[i]
                            extra_heat_flow_window.append(heat_flow_q_window)
                        else:
                            extra_heat_flow_opaque.append(0)
                            extra_heat_flow_window.append(0)

                    ## Retrieve solar irradiation and shading reduction values from the database
                    cur_shade = conn.cursor()
                    cur_shade.execute(
                        """SELECT value FROM weather_table WHERE attribute = %s and orientation = %s and slope_in_degrees = %s """,
                        ("shade_reduction", orientation, str(rounded_slope)))
                    shade_query_results = cur_shade.fetchone()
                    shade_array = shade_query_results[0][1:-1].split(", ")
                    shade_array_float = [float(x) for x in shade_array]

                    if rounded_inclination == 0:
                        cur_solar = conn.cursor()
                        cur_solar.execute(
                            """SELECT value FROM weather_table WHERE attribute = %s and orientation is NULL and inclination_in_degrees = %s """,
                            ("solar_irradiation", str(rounded_inclination)))
                        solar_query_results = cur_solar.fetchone()
                        solar_array = solar_query_results[0][1:-1].split(", ")
                        solar_array_float = [float(x) for x in solar_array]
                    elif rounded_inclination == 180:
                        cur_solar = conn.cursor()
                        cur_solar.execute(
                            """SELECT value FROM weather_table WHERE attribute = %s and orientation is NULL and inclination_in_degrees = %s """,
                            ("solar_irradiation", str(rounded_inclination)))
                        solar_query_results = cur_solar.fetchone()
                        solar_array = solar_query_results[0][1:-1].split(", ")
                        solar_array_float = [float(x) for x in solar_array]
                    else:
                        cur_solar = conn.cursor()
                        cur_solar.execute(
                            """SELECT value FROM weather_table WHERE attribute = %s and orientation = %s and inclination_in_degrees = %s """,
                            ("solar_irradiation", orientation, str(rounded_inclination)))
                        solar_query_results = cur_solar.fetchone()
                        solar_array = solar_query_results[0][1:-1].split(", ")
                        solar_array_float = [float(x) for x in solar_array]

                    ## Calculate solar gains for transparent and opaque parts
                    solar_gains_through_windows = []
                    solar_gains_through_opaque = []
                    for i in range(12):
                        if 0 <= i <= 2 or 9 <= i <= 11:
                            window_solar = window_gValue * window_area * (1 - 0.25) * shade_array_float[i] * solar_array_float[i] * 0.001 * length_of_month[i] - extra_heat_flow_window[i]
                            solar_gains_through_windows.append(window_solar)
                            opaque_solar = 0.6 * opaque_resistance * opaque_uValue * opaque_area * 1 * solar_array_float[i] * 0.001 * length_of_month[i] - extra_heat_flow_opaque[i]
                            solar_gains_through_opaque.append(opaque_solar)
                        else:
                            solar_gains_through_windows.append(0)
                            solar_gains_through_opaque.append(0)
                    for x in range(12):
                        bdg_solar_gains_windows[x] += solar_gains_through_windows[x]
                        bdg_solar_gains_opaque[x] += solar_gains_through_opaque[x]
                elif cityobjects[each_boundary]["attributes"]["energy-thermalBoundaryType"] == "roof" or (cityobjects[each_boundary]["attributes"]["energy-thermalBoundaryType"] == "outerWall" and cityobjects[each_boundary]["attributes"]["energy-area"] <= 4):
                    opaque_cons_id = cityobjects[each_boundary]["energy-opaqueConstruction"]
                    opaque_area = cityobjects[each_boundary]["attributes"]["energy-area"]
                    inclination = visibility_inclination(cityobjects[each_boundary]["attributes"]["energy-inclination"])
                    opaque_resistance = cityobjects[opaque_cons_id]["attributes"]["energy-rValue"]
                    opaque_uValue = cityobjects[opaque_cons_id]["attributes"]["energy-uValue"]
                    rounded_inclination = round_inc(cityobjects[each_boundary]["attributes"]["energy-inclination"])
                    rounded_slope = round_slope(cityobjects[each_boundary]["attributes"]["energy-slope"])

                    try:
                        orientation = cityobjects[each_boundary]["attributes"]["energy-orientation"]
                    except KeyError:
                        orientation = "null"

                    cur_vis = conn.cursor()
                    cur_vis.execute(
                        """SELECT value FROM weather_table WHERE attribute = %s and inclination_in_degrees = %s """,
                        ("visibility_factor", inclination))
                    query_results = cur_vis.fetchone()
                    visibility_fac = float(query_results[0])

                    ## Calculate extra heat flow
                    extra_heat_flow_opaque = []
                    for i in range(12):
                        if 0 <= i <= 2 or 9 <= i <= 11:
                            heat_flow_q_opaque = 0.001 * visibility_fac * opaque_resistance * opaque_uValue * opaque_area * 4.14 * 11 * length_of_month[i]
                            extra_heat_flow_opaque.append(heat_flow_q_opaque)
                        else:
                            extra_heat_flow_opaque.append(0)
                    try:
                        cur_shade = conn.cursor()
                        cur_shade.execute(
                            """SELECT value FROM weather_table WHERE attribute = %s and orientation = %s and slope_in_degrees = %s """,
                            ("shade_reduction", orientation, str(rounded_slope)))
                        shade_query_results = cur_shade.fetchone()
                        shade_array = shade_query_results[0][1:-1].split(", ")
                        shade_array_float = [float(x) for x in shade_array]
                    except TypeError:
                        shade_array_float = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]

                    if rounded_inclination == 0:
                        cur_solar = conn.cursor()
                        cur_solar.execute(
                            """SELECT value FROM weather_table WHERE attribute = %s and orientation is NULL and inclination_in_degrees = %s """,
                            ("solar_irradiation", str(rounded_inclination)))
                        solar_query_results = cur_solar.fetchone()
                        solar_array = solar_query_results[0][1:-1].split(", ")
                        solar_array_float = [float(x) for x in solar_array]
                    elif rounded_inclination == 180:
                        cur_solar = conn.cursor()
                        cur_solar.execute(
                            """SELECT value FROM weather_table WHERE attribute = %s and orientation is NULL and inclination_in_degrees = %s """,
                            ("solar_irradiation", str(rounded_inclination)))
                        solar_query_results = cur_solar.fetchone()
                        solar_array = solar_query_results[0][1:-1].split(", ")
                        solar_array_float = [float(x) for x in solar_array]
                    else:
                        cur_solar = conn.cursor()
                        cur_solar.execute(
                            """SELECT value FROM weather_table WHERE attribute = %s and orientation = %s and inclination_in_degrees = %s """,
                            ("solar_irradiation", orientation, str(rounded_inclination)))
                        solar_query_results = cur_solar.fetchone()
                        solar_array = solar_query_results[0][1:-1].split(", ")
                        solar_array_float = [float(x) for x in solar_array]

                    ## Calculate solar gains for opaque parts
                    solar_gains_through_opaque = []
                    for i in range(12):
                        if 0 <= i <= 2 or 9 <= i <= 11:
                            opaque_solar = 0.6 * opaque_resistance * opaque_uValue * opaque_area * 1 * solar_array_float[i] * 0.001 * length_of_month[i] - extra_heat_flow_opaque[i]
                            solar_gains_through_opaque.append(opaque_solar)
                        else:
                            solar_gains_through_opaque.append(0)

                    for x in range(12):
                        bdg_solar_gains_opaque[x] += solar_gains_through_opaque[x]

            for a in range(12):
                total_solar_gain = bdg_solar_gains_windows[a] + bdg_solar_gains_opaque[a]
                bdg_solar_gains_final.append(total_solar_gain)

            ### Calculate final EnergyDemand values
            utilisation_factor = 0.93  # From TABULA
            for month in range(12):
                energy_demand = (heat_transfer_through_transmission[month] + heat_transfer_through_ventilation[month]) - (utilisation_factor * (internal_heat_gains[month] + bdg_solar_gains_final[month]))
                final_energy_demand_values.append(energy_demand)

            ### Store final value in EnergyDemand object
            timeseries_name = "TimeSeriesEnergyDemand" + str(time_num)
            cityobjects[timeseries_name] = {"type": "+Energy-RegularTimeSeries", "attributes": {}}
            cityobjects[timeseries_name]["attributes"]["energy-acquisitionMethod"] = "simulation"
            cityobjects[timeseries_name]["attributes"]["energy-interpolationType"] = "discontinuous"
            cityobjects[timeseries_name]["attributes"]["energy-temporalExtent"] = {"energy-startPeriod": "2021-01-01",
                                                                                   "energy-endPeriod": "2021-12-31"}
            cityobjects[timeseries_name]["attributes"]["energy-timeInterval"] = {"energy-value": 0.0833333, "energy-uom": "year"}
            cityobjects[timeseries_name]["attributes"]["energy-values"] = final_energy_demand_values

            cityobjects[thermal_name]["attributes"]["energy-energyDemand"] = [{"energy-energyAmount": timeseries_name, "energy-endUse": "spaceHeating"}]

            ##Store units of measurement
            data["+unitOfMeasurement"] = {"energy-volume": "m^3", "energy-floorArea": "m^2", "energy-energyDemand": "kWh", "energy-azimuth": "degrees", "energy-inclination": "degrees",
                                          "energy-area": "m^2", "energy-uValue": "W/(m^2K)", "energy-rValue": "(m^2K)/W", "energy-perimeter": "m", "energy-slope": "degrees"}

            time_num += 1

inp_file = open('./out_data/output_energy_demand.json', "w")
json.dump(data, inp_file)
inp_file.close()


