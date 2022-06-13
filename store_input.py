import json
import csv
import math
import psycopg2
import os

def store_input(input_file):
    ## Read input CityJSON file
    inp_file = open(input_file, "r")
    data = json.load(inp_file)
    inp_file.close()
    cityobjects = data["CityObjects"]

    ## Read usable area, accommodations, residents data
    bag_input = open("./data/bag_data.json", "r")
    area_data = json.load(bag_input)
    bag_input.close()

    ## Read building perimeters data
    perim_inp_file = open("./data/perimeters.json", "r")
    perim_data = json.load(perim_inp_file)
    perim_inp_file.close()

    ## Read surfaces' slope data
    slope_inp_file = open("./data/slope_data.json", "r")
    slope_data = json.load(slope_inp_file)
    slope_inp_file.close()

    ## Read building typology data
    building_type = {}
    with open("./data/Building_type.csv", newline="") as csvfile:
        type_reader = csv.reader(csvfile, delimiter=",")
        for row in type_reader:
            building_type[row[0]] = row[1]

    ## Read building functions data
    inp_file = open("./data/building_functions.json", "r")
    building_function_data = json.load(inp_file)
    inp_file.close()

    ## Read database connection file
    db_param = []
    with open("./database_connection.txt") as f:
        lines = f.readlines()
        x = lines[0].split(" ")
        for par in x:
            db_param.append(par)

    host = db_param[0]
    port = int(db_param[1])
    db = db_param[2]
    user = db_param[3]
    passw = db_param[4]

    ## Connect to database
    conn = psycopg2.connect(host=host, port=port, database=db, user=user, password=passw)

    # --------------------------------------------------------------------------------------
    ### Extract the year range
    def extract_year_range(obj_id):
        if cityobjects[obj_id]["type"] == "Building":
            year = cityobjects[obj_id]["attributes"]["yearOfConstruction"]
        elif cityobjects[obj_id]["type"] == "BuildingPart":
            parent_bdg_id = cityobjects[obj_id]["parents"][0]
            year = cityobjects[parent_bdg_id]["attributes"]["yearOfConstruction"]

        if year <= 1964:
            year_range = "(, 1964]"
        elif 1965 <= year <= 1974:
            year_range = "[1965, 1974]"
        elif 1975 <= year <= 1991:
            year_range = "[1975, 1991]"
        elif 1992 <= year <= 2005:
            year_range = "[1992, 2005]"
        elif 2006 <= year <= 2014:
            year_range = "[2006, 2014]"
        else:
            year_range = "[2015, )"

        return year_range

    # --------------------------------------------------------------------------------------
    ### Extract the year range for nicer attribute names
    def extract_year_range_2(obj_id):
        if cityobjects[obj_id]["type"] == "Building":
            year = cityobjects[obj_id]["attributes"]["yearOfConstruction"]
        elif cityobjects[obj_id]["type"] == "BuildingPart":
            parent_bdg_id = cityobjects[obj_id]["parents"][0]
            year = cityobjects[parent_bdg_id]["attributes"]["yearOfConstruction"]

        if year <= 1964:
            year_range = "1100-1964"
        elif 1965 <= year <= 1974:
            year_range = "1965-1974"
        elif 1975 <= year <= 1991:
            year_range = "1975-1991"
        elif 1992 <= year <= 2005:
            year_range = "1992-2005"
        elif 2006 <= year <= 2014:
            year_range = "2006-2014"
        else:
            year_range = "2015-2022"

        return year_range

    # --------------------------------------------------------------------------------------
    ### Store number of residential functions and usable areas with building ids
    usable_area_dict = {}
    num_residents_dict = {}
    res_func_number_dict = {}
    for x in area_data["areas"]:
        usable = x["sum_oppervlakte"]
        num_res_function = x["num_verblijfsobject"]
        avg_num_res = x["no_resident"]
        bdg_id = x["pandid"]
        res_func_number_dict[bdg_id] = num_res_function
        usable_area_dict[bdg_id] = usable
        num_residents_dict[bdg_id] = avg_num_res

    ### Store building functions in dictionary
    building_functions = {}
    # for each_dict in function_data:
    #     building_functions[each_dict["gml_id"]] = each_dict["citygml_function"]
    for each_func in building_function_data:
        try:
            building_functions[each_func["gml_id"]] = each_func["citygml_function"]
        except KeyError:
            continue

    ### Store building perimeters in dictionary
    perimeters_dict = {}
    for perim in perim_data:
        perimeters_dict[perim["gml_id"]] = perim["_perimeter"]

    ### Store surface slopes in dictionary
    slope_dict = {}
    for slope in slope_data:
        for surf in slope:
            slope_dict[surf] = slope[surf]

    # --------------------------------------------------------------------------------------
    ### Create Construction objects
    all_const_dicts = {}
    transp_const_dicts = {}
    const_numb = 0
    year_ranges = ["(, 1964]", "[1965, 1974]", "[1975, 1991]", "[1992, 2005]", "[2006, 2014]", "[2015, )"]
    year_ranges_second = ["1100-1964", "1965-1974", "1975-1991", "1992-2005", "2006-2014", "2015-2022"]
    build_typology = ["SFH", "MFH", "TH", "AB"]
    build_ele = ["outWalls_uValue", "groundShell_uValue", "pitchedRoof_uValue"]
    build_ele_window = ["outWalls_windowTypeId", "pitchedRoof_windowTypeId"]

    ### Extract uValues for opaque elements
    for yrange in range(len(year_ranges)):
        for typol in build_typology:
            for ele in build_ele:
                ele_split = ele.split("_")
                # const_name = "Opaque" + "_" + yrange + "_" + typol + "_" + ele_split[0]
                const_name = ele_split[0] + "_" + typol + "_" + year_ranges_second[yrange]
                cur_u = conn.cursor()
                cur_u.execute(
                    """SELECT value FROM building_data WHERE construction_year = %s and building_type = %s and element is NULL and attribute = %s """,
                    (year_ranges[yrange], typol, ele))
                query_results = cur_u.fetchone()
                u_val = float(query_results[0])
                const_dict = {"type": "+Energy-Construction", "attributes": {"energy-rValue": 0.04, "energy-uValue": u_val}}
                all_const_dicts[const_name] = const_dict

    ### Extract gValues and uValues for transparent elements
    for yrange in range(len(year_ranges)):
        for typol in build_typology:
            for elem in build_ele_window:
                cur3 = conn.cursor()
                cur4 = conn.cursor()
                elem_split = elem.split("_")
                const_name_window = elem_split[0] + "_" + typol + "_" + year_ranges_second[yrange] + "_" + "windows"
                # const_name_window = "Transp" + "_" + yrange + "_" + typol + "_" + elem_split[0]
                # print(const_name_window)
                cur3.execute(
                    """SELECT value FROM building_data WHERE construction_year = %s and building_type = %s and element is NULL and attribute = %s """,
                    (year_ranges[yrange], typol, elem))
                window_id_result = cur3.fetchone()
                cur4.execute(
                    """SELECT gvalue, uvalue FROM window_data WHERE window_id = %s""",
                    (str(window_id_result[0])))
                window_values = cur4.fetchone()
                window_gvalue = float(window_values[0])
                window_uvalue = float(window_values[1])
                const_dict_window = {"type": "+Energy-Construction", "attributes": {"energy-gValue": window_gvalue, "energy-uValue": window_uvalue, "energy-rValue": 0.04}}
                transp_const_dicts[const_name_window] = const_dict_window

    ### Extract uValues for shared walls
    for typol in build_typology:
        cur_shared = conn.cursor()
        ele_name = "sharedWalls_uValue"
        ele_split = ele_name.split("_")
        # const_name_shared = "Opaque" + "_" + typol + "_" + ele_split[0]
        const_name_shared = ele_split[0] + "_" + typol
        cur_shared.execute(
            """SELECT value FROM building_data WHERE construction_year is NULL and building_type = %s and element is NULL and attribute = %s """,
            (typol, ele_name))
        shared_value = cur_shared.fetchone()
        shared_wall_uvalue = float(shared_value[0])
        const_dict_shared_wall = {"type": "+Energy-Construction", "attributes": {"energy-rValue": 0.04, "energy-uValue": shared_wall_uvalue}}
        all_const_dicts[const_name_shared] = const_dict_shared_wall

    # --------------------------------------------------------------------------------------
    # Include Energy extension in the "extensions"
    data["extensions"] = {}
    data["extensions"]["Energy"] = {
        "url": "https://raw.githubusercontent.com/ozgetufan/cjenergy/master/schemas/extensions/energy.ext.json",
        "version": "1.1"}

    run_once = 0
    num = 0

    # Mark buildings with missing data
    for each_cityobj in cityobjects.copy():
        if cityobjects[each_cityobj]["type"] == "Building" or cityobjects[each_cityobj]["type"] == "BuildingPart":
            if cityobjects[each_cityobj]["attributes"]["class"] == "Residential" or cityobjects[each_cityobj]["attributes"]["class"] == "Mixed-use":
                if each_cityobj not in num_residents_dict:
                    cityobjects[each_cityobj]["attributes"]["has_missing_data"] = "yes"

    for each_cityobj in cityobjects.copy():
        new_values = []
        new_surfaces = []
        a = 0
        if "geometry" in cityobjects[each_cityobj] and "has_missing_data" not in cityobjects[each_cityobj]["attributes"]:
            for i in range(len(cityobjects[each_cityobj]["geometry"])):
                if cityobjects[each_cityobj]["geometry"][i]["lod"] == "2":
                    ### Add function(s) as extraAttribute
                    if each_cityobj in building_functions:
                        cityobjects[each_cityobj]["attributes"]["+energy-function"] = building_functions[each_cityobj]

                    ### Delete existing function attribute
                    cityobjects[each_cityobj]["attributes"].pop("function")

                    ### Create thermalZone
                    thermal_name = "ThermalZone" + str(num)
                    cityobjects[thermal_name] = {"type": "+Energy-ThermalZone", "parents": [], "children": [], "attributes": {}, "energy-boundedBy": []}
                    cityobjects[thermal_name]["parents"].append(each_cityobj)
                    cityobjects[each_cityobj]["children"] = [thermal_name]

                    ### Add (heated) volume attribute to ThermalZone
                    volume = float(cityobjects[each_cityobj]["attributes"]["lod2_volume"])
                    heated_volume = volume * 0.8
                    cityobjects[thermal_name]["attributes"]["energy-volume"] = [
                        {"energy-type": "energyReferenceVolume", "energy-value": heated_volume}]

                    ### Extract building class and add isHeated attribute to ThermalZone
                    if cityobjects[each_cityobj]["type"] == "Building":
                        bdg_class = cityobjects[each_cityobj]["attributes"]["class"]
                        if bdg_class == "Residential" or bdg_class == "Mixed-use":
                            cityobjects[thermal_name]["attributes"]["energy-isHeated"] = True
                        else:
                            cityobjects[thermal_name]["attributes"]["energy-isHeated"] = False
                    elif cityobjects[each_cityobj]['type'] == "BuildingPart":
                        parent_id = cityobjects[each_cityobj]["parents"][0]
                        bdg_class = cityobjects[parent_id]["attributes"]["class"]
                        if bdg_class == "Residential":
                            cityobjects[thermal_name]["attributes"]["energy-isHeated"] = True
                        elif bdg_class == "Mixed-use" and "woonfunctie" in cityobjects[each_cityobj]["attributes"]["+energy-function"]:
                            cityobjects[thermal_name]["attributes"]["energy-isHeated"] = True
                        else:
                            cityobjects[thermal_name]["attributes"]["energy-isHeated"] = False

                    ### Add usable area to ThermalZone
                    if each_cityobj in usable_area_dict:
                        cityobjects[thermal_name]["attributes"]["energy-floorArea"] = [{"energy-type": "energyReferenceArea",
                                                                                       "energy-value": usable_area_dict[each_cityobj]}]

                    ## Access surfaces and generic attributes in surface values
                    surfaces = cityobjects[each_cityobj]["geometry"][i]["semantics"]["surfaces"]
                    values = cityobjects[each_cityobj]["geometry"][i]["semantics"]["values"]

                    ### Add building typology as attribute
                    cityobjects[each_cityobj]["attributes"]["+energy-buildingType"] = building_type[each_cityobj]
                    if cityobjects[each_cityobj]["attributes"]["+energy-buildingType"] == "COM" and (bdg_class == "Residential" or bdg_class == "Mixed-use"):
                        cityobjects[each_cityobj]["attributes"]["+energy-buildingType"] = "MFH"

                    for surf in values:
                        ## Add ThermalBoundary objects
                        boundary_id = surfaces[surf]["id"]
                        cityobjects[boundary_id] = {"type": "+Energy-ThermalBoundary", "attributes": {}, "energy-delimits": []}
                        cityobjects[thermal_name]["energy-boundedBy"].append(boundary_id)
                        cityobjects[boundary_id]["energy-delimits"].append(thermal_name)
                        # boundary_num += 1

                        ## Map thermalBoundaryType
                        if surfaces[surf]["type"] == "GroundSurface":
                            cityobjects[boundary_id]["attributes"]["energy-thermalBoundaryType"] = "groundSlab"
                        elif surfaces[surf]["type"] == "RoofSurface":
                            cityobjects[boundary_id]["attributes"]["energy-thermalBoundaryType"] = "roof"
                        elif surfaces[surf]["type"] == "WallSurface":
                            if surfaces[surf]["id"][:18] == "WallSurface_shared":
                                cityobjects[boundary_id]["attributes"]["energy-thermalBoundaryType"] = "sharedWall"
                                adjacent_bdg = cityobjects[each_cityobj]["geometry"][i]["semantics"]["surfaces"][surf]["list_adjacent_buildings"]
                                cityobjects[boundary_id]["attributes"]["adjacent_building_id"] = adjacent_bdg
                                adjacent_bdg_type = cityobjects[each_cityobj]["geometry"][i]["semantics"]["surfaces"][surf]["adjacent_building_class"]
                                cityobjects[boundary_id]["attributes"]["adjacent_building_class"] = adjacent_bdg_type
                            else:
                                cityobjects[boundary_id]["attributes"]["energy-thermalBoundaryType"] = "outerWall"

                        ## Map inclination
                        inclination = surfaces[surf]["inclination"]
                        cityobjects[boundary_id]["attributes"]["energy-inclination"] = float(inclination)

                        ## Map area
                        lod2_area = surfaces[surf]["lod2_area"]
                        cityobjects[boundary_id]["attributes"]["energy-area"] = float(lod2_area)

                        ## Map azimuth
                        azimuth = surfaces[surf]["azimuth"]
                        if azimuth == -1 or azimuth == -1.0:
                            cityobjects[boundary_id]["attributes"]["energy-azimuth"] = None
                        else:
                            cityobjects[boundary_id]["attributes"]["energy-azimuth"] = float(azimuth)

                        ## Map orientation
                        try:
                            orientation = surfaces[surf]["direction"]
                            cityobjects[boundary_id]["attributes"]["energy-orientation"] = orientation
                        except KeyError:
                            pass

                        ## Map slope
                        surface_id = surfaces[surf]["id"]
                        if surface_id in slope_dict:
                            cityobjects[boundary_id]["attributes"]["energy-slope"] = float(slope_dict[surface_id])

                        ## Remove generic attributes from surfaces
                        surfaces[surf] = {"type": surfaces[surf]["type"]}

                        ### Extract construction year and building typology
                        const_year = extract_year_range(each_cityobj)
                        const_year_pretty = extract_year_range_2(each_cityobj)
                        bdg_type = cityobjects[each_cityobj]["attributes"]["+energy-buildingType"]

                        ### Add building physics parameters (uValue, windowRatio etc.)
                        cur2 = conn.cursor()
                        if bdg_class == "Residential" or bdg_class == "Mixed-use":
                            if cityobjects[boundary_id]["attributes"]["energy-thermalBoundaryType"] == "groundSlab":
                                construction_name = "groundShell" + "_" + bdg_type + "_" + const_year_pretty
                                cityobjects[construction_name] = all_const_dicts[construction_name]
                                cityobjects[boundary_id]["energy-opaqueConstruction"] = construction_name
                                cityobjects[boundary_id]["attributes"]["energy-windowRatio"] = 0.0
                            elif cityobjects[boundary_id]["attributes"]["energy-thermalBoundaryType"] == "roof":
                                construction_name = "pitchedRoof" + "_" + bdg_type + "_" + const_year_pretty
                                cityobjects[construction_name] = all_const_dicts[construction_name]
                                cityobjects[boundary_id]["energy-opaqueConstruction"] = construction_name

                                ### Add windowRatio
                                cur2.execute("""SELECT value FROM building_data WHERE construction_year = %s and building_type = %s and element is NULL and attribute = 'pitchedRoof_windowRatio'""",
                                             (const_year, bdg_type))
                                window_result = cur2.fetchone()
                                cityobjects[boundary_id]["attributes"]["energy-windowRatio"] = float(window_result[0])

                                ## Store gValue, uValue of windows as Construction object if windowRatio is not 0.
                                if cityobjects[boundary_id]["attributes"]["energy-windowRatio"] != 0.0:
                                    window_construction_name = "pitchedRoof" + "_" + bdg_type + "_" + const_year_pretty + "_" + "windows"
                                    cityobjects[window_construction_name] = transp_const_dicts[window_construction_name]
                                    cityobjects[boundary_id]["energy-transparentConstruction"] = window_construction_name
                            elif cityobjects[boundary_id]["attributes"]["energy-thermalBoundaryType"] == "outerWall":
                                construction_name = "outWalls" + "_" + bdg_type + "_" + const_year_pretty
                                cityobjects[construction_name] = all_const_dicts[construction_name]
                                cityobjects[boundary_id]["energy-opaqueConstruction"] = construction_name

                                ### Add windowRatio
                                cur2.execute(
                                    """SELECT value FROM building_data WHERE construction_year = %s and building_type = %s and element is NULL and attribute = 'outWalls_windowRatio'""",
                                    (const_year, bdg_type))

                                window_result = cur2.fetchone()
                                if cityobjects[boundary_id]["attributes"]["energy-area"] > 4:
                                    cityobjects[boundary_id]["attributes"]["energy-windowRatio"] = float(window_result[0])
                                else:
                                    cityobjects[boundary_id]["attributes"]["energy-windowRatio"] = 0.0

                                ## Store gValue, uValue of windows as ThermalBound. attribute if windowRatio is not 0.
                                if cityobjects[boundary_id]["attributes"]["energy-windowRatio"] != 0.0:
                                    window_construction_name = "outWalls" + "_" + bdg_type + "_" + const_year_pretty + "_" + "windows"
                                    cityobjects[window_construction_name] = transp_const_dicts[window_construction_name]
                                    cityobjects[boundary_id]["energy-transparentConstruction"] = window_construction_name
                            elif cityobjects[boundary_id]["attributes"]["energy-thermalBoundaryType"] == "sharedWall":
                                construction_name = "sharedWalls" + "_" + bdg_type
                                cityobjects[construction_name] = all_const_dicts[construction_name]
                                cityobjects[boundary_id]["energy-opaqueConstruction"] = construction_name
                                cityobjects[boundary_id]["attributes"]["energy-windowRatio"] = 0.0

                    ## Remove duplicate surface type objects and modify semantics values
                    for k in surfaces:
                        if k not in new_surfaces:
                            new_values.append(a)
                            new_surfaces.append(k)
                            a += 1
                        else:
                            new_values.append(a-1)

                    cityobjects[each_cityobj]["geometry"][i]["semantics"]["surfaces"] = new_surfaces
                    cityobjects[each_cityobj]["geometry"][i]["semantics"]["values"] = new_values

                    ### Add monthly average temperature of the calculation zone with WeatherData
                    ## First create RegularTimeSeries object
                    if bdg_class == "Residential" or bdg_class == "Mixed-use":
                        timeseries_name = "RegularTimeSeries" + str(num)
                        cityobjects[timeseries_name] = {"type": "+Energy-RegularTimeSeries", "attributes": {}}
                        cityobjects[timeseries_name]["attributes"]["energy-acquisitionMethod"] = "estimation"
                        cityobjects[timeseries_name]["attributes"]["energy-interpolationType"] = "discontinuous"
                        cityobjects[timeseries_name]["attributes"]["energy-temporalExtent"] = {"energy-startPeriod": "2021-01-01",
                                                                                               "energy-endPeriod": "2021-12-31"}
                        cityobjects[timeseries_name]["attributes"]["energy-timeInterval"] = {"energy-value": 0.0833333, "energy-uom": "year"}
                        cityobjects[timeseries_name]["attributes"]["energy-values"] = [18.0, 18.0, 18.0, 20.0, 20.0, 20.0, 20.0, 20.0, 20.0, 18.0, 18.0, 18.0]

                        ## Create WeatherData object for each ThermalZone
                        cityobjects[thermal_name]["attributes"]["energy-weatherData"] = [{"energy-weatherElement": "airTemperature", "energy-weatherDataLocation": "indoor", "energy-values": timeseries_name}]
                    else:
                        cityobjects[thermal_name]["attributes"]["energy-weatherData"] = []

                    ### Add average monthly outside temperature with WeatherData
                    ## Create one RegularTimeSeries object for outside temperature
                    temp_time_name = "RegularTimeSeries_outside_temp"
                    if run_once == 0:
                        cityobjects[temp_time_name] = {"type": "+Energy-RegularTimeSeries", "attributes": {}}
                        cityobjects[temp_time_name]["attributes"]["energy-acquisitionMethod"] = "measurement"
                        cityobjects[temp_time_name]["attributes"]["energy-interpolationType"] = "discontinuous"
                        cityobjects[temp_time_name]["attributes"]["energy-temporalExtent"] = {"energy-startPeriod": "2021-01-01",
                                                                                              "energy-endPeriod": "2021-12-31"}
                        cityobjects[temp_time_name]["attributes"]["energy-timeInterval"] = {"energy-value": 0.0833333, "energy-uom": "year"}
                        cityobjects[temp_time_name]["attributes"]["energy-values"] = [3.07, 3.44, 5.81, 9.23, 12.92, 15.88, 17.86, 17.4, 14.26, 10.49, 6.55, 3.74]
                        run_once = 1

                    ## Create WeatherData attribute for each ThermalZone
                    out_temp_dict = {"energy-weatherElement": "airTemperature", "energy-weatherDataLocation": "outdoor", "energy-values": temp_time_name}
                    cityobjects[thermal_name]["attributes"]["energy-weatherData"].append(out_temp_dict)

                    ### Add UsageZone object for each building
                    ## Create UsageZone name
                    usage_name = "UsageZone" + str(num)
                    ## Create UsageZone, parents and children
                    cityobjects[usage_name] = {"type": "+Energy-UsageZone", "parents": [], "children": [], "attributes": {}}
                    cityobjects[usage_name]["parents"].append(thermal_name)
                    ## Add usageZoneType attribute
                    cityobjects[usage_name]["attributes"]["energy-usageZoneType"] = bdg_class
                    ## Add children to ThermalZone
                    cityobjects[thermal_name]["children"].append(usage_name)

                    ### Add Occupants object for each building/usage zone
                    occupant_name = "Occupants" + str(num)
                    cityobjects[occupant_name] = {"type": "+Energy-Occupants", "attributes": {}}
                    if each_cityobj in num_residents_dict:
                        cityobjects[occupant_name]["attributes"]["energy-numberOfOccupants"] = math.floor(num_residents_dict[each_cityobj])

                    ## Add occupiedBy attribute to UsageZone
                    cityobjects[usage_name]["energy-occupiedBy"] = [occupant_name]

                    ### Add number of residential function to each UsageZone as attribute
                    if each_cityobj in res_func_number_dict:
                        cityobjects[usage_name]["attributes"]["energy-numberOfResidentialFunctions"] = res_func_number_dict[each_cityobj]

                    ### Add perimeter attribute to each building
                    cityobjects[thermal_name]["attributes"]["energy-perimeter"] = perimeters_dict[each_cityobj]

                    num += 1
        else:
            continue

    ### Create directory for output files
    out_directory = "./out_data/"
    os.mkdir(out_directory)
    out_filename = "store_input_data.json"

    ### Write to json file
    inp_file = open(out_directory + out_filename, "w")
    json.dump(data, inp_file)
    inp_file.close()

    ### End connection to database
    cur_u.close()
    cur2.close()
    cur3.close()
    cur4.close()
    cur_shared.close()
    conn.close()

    return out_directory + out_filename


