import json
from store_input import store_input

filename = "./data/input_data_5_bdg.json"
out_filename = store_input(filename)

inp_file = open(out_filename, "r")
data = json.load(inp_file)
inp_file.close()
cityobjects = data["CityObjects"]
for obj in cityobjects.copy():
    if cityobjects[obj]["type"] == "+Energy-ThermalBoundary":
        if cityobjects[obj]["attributes"]["energy-thermalBoundaryType"] == "sharedWall":
            if cityobjects[obj]["attributes"]["adjacent_building_class"] == "Non-residential (single function)" or cityobjects[obj]["attributes"]["adjacent_building_class"] == "Non-residential (multi function)" or cityobjects[obj]["attributes"]["adjacent_building_class"] == "Unknown":
                cityobjects[obj]["attributes"]["calculate_energy_demand"] = "yes"
            else:
                cityobjects[obj]["attributes"]["calculate_energy_demand"] = "no"
        else:
            cityobjects[obj]["attributes"]["calculate_energy_demand"] = "yes"
for each_cityobj in cityobjects.copy():
    if cityobjects[each_cityobj]["type"] == "Building":
        if cityobjects[each_cityobj]["attributes"]["class"] == "Residential" or cityobjects[each_cityobj]["attributes"]["class"] == "Mixed-use":
            if "has_missing_data" not in cityobjects[each_cityobj]["attributes"]:
                if "geometry" in cityobjects[each_cityobj]:
                    lod_2 = 0
                    for i in range(len(cityobjects[each_cityobj]["geometry"])):
                        if cityobjects[each_cityobj]["geometry"][i]["lod"] == "2":
                            lod_2 += 1
                    if lod_2 > 0:
                        cityobjects[each_cityobj]["attributes"]["bdg_in_calculation"] = "yes"
                    else:
                        cityobjects[each_cityobj]["attributes"]["bdg_in_calculation"] = "no"
                else:
                    cityobjects[each_cityobj]["attributes"]["bdg_in_calculation"] = "no"
            else:
                cityobjects[each_cityobj]["attributes"]["bdg_in_calculation"] = "no"
        else:
            cityobjects[each_cityobj]["attributes"]["bdg_in_calculation"] = "no"
    elif cityobjects[each_cityobj]["type"] == "BuildingPart":
        if "has_missing_data" in cityobjects[each_cityobj]["attributes"]:
            cityobjects[each_cityobj]["attributes"]["bdg_in_calculation"] = "no"
        else:
            if "woonfunctie" in cityobjects[each_cityobj]["attributes"]["+energy-function"]:
                if "geometry" in cityobjects[each_cityobj]:
                    lod_2 = 0
                    for i in range(len(cityobjects[each_cityobj]["geometry"])):
                        if cityobjects[each_cityobj]["geometry"][i]["lod"] == "2":
                            lod_2 += 1
                    if lod_2 > 0:
                        cityobjects[each_cityobj]["attributes"]["bdg_in_calculation"] = "yes"
                    else:
                        cityobjects[each_cityobj]["attributes"]["bdg_in_calculation"] = "no"
                else:
                    cityobjects[each_cityobj]["attributes"]["bdg_in_calculation"] = "no"
            else:
                cityobjects[each_cityobj]["attributes"]["bdg_in_calculation"] = "no"

inp_file = open("./out_data/store_input_data_marked.json", "w")
json.dump(data, inp_file)
inp_file.close()

