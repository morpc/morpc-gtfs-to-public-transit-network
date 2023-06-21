# GTFS To Public Transit Network

This tool creates transit line file from GTFS for Cube 6 models. It identifies the existing nodes and links in the given network and creates transit-only nodes and links to fill in the gaps. The transit-only links replicate exactly the shape of the route. The transit-only nodes are located as the projection of the missing bus stops to the route.

Go to `./BASE/morpc/images` for figures of the 2018 COTA route variations (i.e., shape IDs) like the one below.
<p align="center">
  <img
    src="/Base/morpc/images/7%20MOUNT%20VERNON%20TO%20AIRPORT%20%20Shape%20ID%2046344.jpeg"
    alt="2018 COTA Network, Route 7 MOUNT VERNON TO AIRPORT, Shape ID 46344"
    title="2018 COTA Network, Route 7 MOUNT VERNON TO AIRPORT, Shape ID 46344"
    style="display: inline-block; width: 600px; height: 450px">
</p>

# Contents
- [Observations](#observations-of-the-current-version-mar-16th-2023)
- [Inputs](#inputs)
  - [GTFS](#gtfs)
  - [Network](#network)
  - [Route Information](#route-information)
- [Outputs](#outputs)
	- [network](#network)
	- [transit-only](#transit-only)
	- [images](#images)
- [Before running the script](#before-running-the-script)
	- [Installing Python (Anaconda)](#installing-python-anaconda)
	- [Creating a virtual environment and installing requirements.txt](#creating-a-virtual-environment-and-installing-requirementstxt)
- [Running the tool](#running-the-tool)

## Observations of the current version (Mar 16th, 2023)
- There is no checking for circular routes. All routes are assigned the value `False` for CIRCULAR in line file. In future, we may read this info from the `modes_table.csv`.
- Circular routes are still a challenging with this approach. This script is not recommended for them.
- This approach relies on the quality of the GTFS and the network's trueshape.
- Small values (e.g., 50ft) in `w_bffr` (buffer used in the route shape to find network links within) will produce more transit-only nodes/links. Large values (e.g., 500ft) may also produce more transit-only nodes/links or mess up the original routing because of finding parallel roads that are also within the shape. Early tests show that the ideal buffer should be between 100ft and 300ft for the 2018 COTA routes. Test different buffers for your network and assess the results visually with the images or statistically with the stats presented in file `... (stats not available yet)`.
  
## Inputs
### GTFS
Per [gtfs.org](https://gtfs.org/),
<blockquote>"The General Transit Feed Specification (GTFS) is a data specification that allows public transit agencies to publish their transit data in a format that can be consumed by a wide variety of software applications."</blockquote>

You can find GTFS feeds in [database.mobilitydata.org](https://database.mobilitydata.org). Download their CSV spreadsheet and filter by city or agency to find the link to the GTFS that you are looking for.

The GTFS files usually come zipped in one `.zip` file. Unzip all `.txt` files to `./inputs/YOUR_PROJECT_FOLDER/gtfs`.

### Network
MORPC's network is kept as a `.net` file. A proprietary file format of CUBE (Bentley Systems). This application requires nodes and links as `.shp`, a more universal GIS file format. Fortunately, you can easily export your `.net` in CUBE to `.shp` for links and nodes, one at a time. If by any chance your `.shp` files are zipped, unzip them all to `./inputs/YOUR_PROJECT_FOLDER/network`.

### Route Information
The last input is a `.csv` file named as `modes_table.csv`. This name cannot be different. This file needs to contain the following four columns.
- `ROUTE_ID`: ALL route IDs found in GTFS.
- `ROUTE_NO`: ALL route numbers or short names if no number (e.g., CMAX, AirConnect, Night OWL).
- `LONG_NAME`: ALL route long names.
- `MODE`: Attention here! This is the mode number that you want to be associated with the route and to be used in the final `.lin` file. You can create whatever mode number you want to categorize the routes accordingly. There is an input variable named `mode` in the main script but it is related to the mode numbers in GTFS (See below [Running the tool](#running-the-tool)).

You can create this table in Excel but remember to export as `.csv` and store in `./inputs/YOUR_PROJECT_FOLDER/route-info`.
The file `modes_table_for_your_reference_only.csv` is just for your reference and it is not used in this application. Consider it as a cheat sheet if you want to know what mode number to use in `modes_table.csv`.

## Outputs
### network
- Links and nodes of the network updated with the newly generated transit-only links and nodes as shapefile. The shapefile is usually exported as a set of files with the same name but different extensions. All extensions are `.dbf`, `.shp`, `.shx`, and `.cpg`.
- Links and nodes of the network updated with the newly generated transit-only links and nodes as `.csv`.
- `links_rename.txt` and `nodes_rename.txt` contain, respectively, the columns names in links and nodes that originally had more than 10 characters and were forced to a limit of 10 characters in `.dbf` outputs. The provided Cube app use both of them when recreating the network file from the nodes and links `.dbf` files to make sure that the attributes in the new network file are correctly named.
- The fourth process in the Cube app produces the final `.net` that will be stored as `NETWORK.NET` in `./BASE/YOUR_SCENARIO_FOLDER/network`.

### transit-only
- Transit-only links and nodes exported as `.csv` and `.dbf` files.
- The line file containing line basic information and sequence of nodes (stop or non-stop nodes). The file is named as `PTlines.lin`. The current line information included are the following. They are hard-coded, but in future we can make it more flexible to read the wanted information from `./inputs/YOUR_PROJECT_FOLDER/route-info/modes_table.csv` or other idea.
  - `LINE NAME`: 10 characters long. The last 3 characters are the last 3 digits of ROUTE_ID found in GTFS. The first 7 characters are the first 7 characters of `ROUTE_NAME` in GTFS.
  - `MODE`: Mode code for the route found in `./inputs/YOUR_PROJECT_FOLDER/route-info/modes_table.csv`.
  - `HEADWAY`: As many as items found in the dictionary variable `period_times` (check the input variables in [Running the tool](#running-the-tool) section). If two items are given to `period_times`, e.g., `AM` and `PM` periods, two HEADWAY information will be found in `PTlines.lin` as: HEADWAY[1]=X, HEADWAY[2]=Y. X and Y are the calculated headway for each period.
  - `ONEWAY`: T (true) or F (false) if route is only one way. Currently, all routes are assigned `ONEWAY=T`. In future, we may read this info from `./inputs/route-info/modes_table.csv` or identify it from data.
  - `ALLSTOPS`: T (true) or F (false) if (...). Currently, all routes are assigned `ALLSTOPS=F`. In future, we may read this info from `./inputs/route-info/modes_table.csv` or identify it from data.
  - `VEHICLETYPE`: Type of vehicle (...). Currently, all routes are assigned `VEHICLETYPE=F`. In future, we may read this info from `./inputs/route-info/modes_table.csv` or identify it from data.
  - `CIRCULAR`: T (true) or F (false) whether the route is circular or not. Currently, all routes are assigned `CIRCULAR=F`. In future, we may read this info from `./inputs/route-info/modes_table.csv` or identify it from data.
  
### images

Figures of the routes in the given network as the one shown above.

## Before running the script
### Installing Python (Anaconda)

Per Wikipedia,
<blockquote>"Anaconda is a distribution of the Python and R programming languages for scientific computing, that aims to simplify package management and deployment. The distribution includes data-science packages suitable for Windows, Linux, and macOS."</blockquote>

With Anaconda, you will have installed at once the Python interpreter and the most commonly used Python libraries. Highly recommended.

However, make sure you install an Anaconda version that comes with `Python 3.9.X`. We recommend you to install `Anaconda 2022.10` ([here](https://repo.anaconda.com/archive/Anaconda3-2022.10-Windows-x86_64.exe)).

### Creating a virtual environment and installing requirements.txt

The Python scripts for this tool were written based on certain packages with specific versions that may not be the same as the ones installed in your base Python envrionment. To avoid overwritting the versions that you already have, it is necessary to create a venv (virtual environment) for this project only. The new venv must be named as `gtfs2ptnet_venv` and be installed in the project's folder for consistency with the Cube app. Do the following (for `Windows only`).
- Open the terminal from the project's folder
  - For Windows 10 or newer, you can left-click anywhere in the project's folder and select "Open in terminal".
  - Or you can run `cmd (Command Prompt)` and change the base directory to project's folder by entering
    ```bash
    cd PATH\TO\PROJECT
    ```
- In the terminal, enter the following to create the venv named as `gtfs2ptnet_venv`. A folder with this name will be created in the project's folder.
  ```bash
  python -m venv gtfs2ptnet_venv
  ```
  - then, enter the following to activate the newly created venv
    ```bash
    gtfs2ptnet_venv\Scripts\activate
    ```
  - finally, enter the following to install all the necessary packages from `requirements.txt` to your venv.
    ```bash
    pip install -r requirements.txt
    ```

## Running the tool

You have two options to run this tool:
- Open the Cube catalog file `gtfs2net.cat` and create a scenario with your inputs (`preferred!`).
- Or run the Python script directly from the terminal by doing the following
  - Edit the `parameters.txt` with your inputs (recommended location `./BASE/YOUR_SCENARIO_FOLDER/parameters.txt`).
  - Open the terminal from the project's folder (check how in section [Creating a virtual environment and installing requirements.txt](#creating-a-virtual-environment-and-installing-requirementstxt)).
  - Enter the folllwing to activade the venv.
    ```bash
    gtfs2ptnet_venv\Scripts\activate
    ```
  - Finally, enter the following to run the script with the specified `parameters.txt` (use the full path to this file).
    ```bash
    python gtfs2ptnet_main.py "FULL/PATH/TO/parameters.txt"
    ```

The second option will give you real-time feedback on what bus lines are being processed at the time and when the outputs are generated and the script is done. The first option will give you a black screen terminal with no feedback while the script is being run and it will be closed when it is done.

The necessary inputs to be included in `parameters.txt` are:

- `day_type`: Typical day of the week with the service pattern that you want to process. Only lowercase. 
  - For weekdays, use: `day_type = 'monday'`
  - For weekends, use: `day_type = 'saturday'`
- `period_times`: A dictionary with the time periods of interest with lists with beginning time and end time for each period. The times must be strings as 'HH:MM:SS', where HH is the hour with two digits, MM the minutes with two digits, and SS the seconds with two digits. Inform times in 24-h format (i.e., use '15:30:00' for 3:30 pm).
  - For 'AM' and 'PM' periods, you could use: `period_times = {'AM':['06:00:00','09:00:00'], 'PM':['15:00:00','19:00:00']}`
- `modes_gtfs`: List with all modes, per GTFS, that you desire to include in the work. This mode code is known as `route_type` and is required in the GTFS file `routes.txt`. We may rename this input in future to avoid confusion with `MODE` found in the input file `modes_table.csv`. The modes, or route types, are the following ([here](https://developers.google.com/transit/gtfs/reference?hl=en#routestxt)).
  - For a `.lin` file that includes routes that are either light rail or bus, for example, use: `modes_gtfs = [2,3]`
  - Modes or route types:
    - 0 - Tram, Streetcar, Light rail.
    - 1 - Subway, Metro. Any underground rail system within a metropolitan area.
    - 2 - Rail. Used for intercity or long-distance travel.
    - 3 - Bus. Used for short- and long-distance bus routes.
    - 4 - Ferry. Used for short- and long-distance boat service.
    - 5 - Cable tram. Used for street-level rail cars where the cable runs beneath the vehicle, e.g., cable car in San Francisco.
    - 6 - Aerial lift, suspended cable car (e.g., gondola lift, aerial tramway). Cable transport where cabins, cars, gondolas or open chairs are suspended by means of one or more cables.
    - 7 - Funicular. Any rail system designed for steep inclines.
    - 11 - Trolleybus. Electric buses that draw power from overhead wires using poles.
    - 12 - Monorail. Railway in which the track consists of a single rail or a beam.
- `transit_only_attributes`: A dictionary with all constant attributes that you want to specify for transit-only links.
  - At MORPC we use: `transit_only_attributes = {'FACTYPE':65, 'LINKGRP':22, 'CSPEEDAM':15, 'CSPEEDMD':15, 'CSPEEDPM':15, 'CSPEEDNT':15, 'NOTE':'BUS'}`
- `factype_to_avoid`: A list with all facility types that you want to avoid in the network. If you have already pre-processed the links to filter out unwanted links, just use an empty list here (i.e., []).
  - To avoid facility type 70, for example, use: `factype_to_avoid = [70]`
- `nodes_ranges_to_avoid`: A list of lists that contain the beginning and end nodes (both inclusive) that you want to avoid in the network. If you have already pre-processed the nodes to filter out unwanted nodes, just use an empty list here (i.e., []).
  - To avoid nodes from 0 to 2,500, use: `nodes_ranges_to_avoid = [[0,2500]]`
  - To avoid nodes from 0 to 2,500 AND from 7,000 to 8,999, use: `nodes_ranges_to_avoid = [[0,2500], [7000,8999]]`
- `w_bffr`: An integer buffer, in feet, of the route shape that will be used when searching for links and nodes that are within the buffer. For reference, 164 ft ~ 50 m.
  - For a buffer of 300 ft, use: `w_bffr = 300`
- `i_bffr`: An integer buffer, in feet, of the route shape that will be used when searching for links and nodes that intersect the buffer. This is only used in the figures as the grey network. If not interested in plotting the figures, use whatever integer low number but different than 0 (e.g., 10) for not crashing the script. For reference, 32000 ft ~ 10 km.
  - For a buffer of 16,400 ft, use: `i_bffr = 16400`
- `net_proj`: Projection as EPSG or ESRI code ([here](https://spatialreference.org/)) of your network. For buffers in feet, use a projection that has feet as standard unit.
  - At MORPC, we use the projection 'NAD 1983 StatePlane Ohio South FIPS 3402 Feet' ([here](https://spatialreference.org/ref/esri/102723/)). In our case, we use: `net_proj = "ESRI:102723"`
- `plot_bool`: Boolean (1 or 0) for plotting the figures or not.
  - If you want to plot the figures and have them stored in `./outputs/images`, use: `plot_bool = 1`
- `nodes_file`: Shapefile name, stored in `./inputs/network` that contains the nodes. Include the file extension `.shp`.
  - For example: `nodes_file = 'MOR18_nodes.shp'`
- `links_file`: Shapefile name, stored in `./inputs/network` that contains the links. Include the file extension `.shp`.
  - For example: `links_file = 'MOR18_links.shp'`
- `gtfs_path`: Quoted full path of the folder containing the GTFS files.
- `net_folder`: Quoted full path of the folder containing the network files.
- `rte_mode_table`: Quoted full path of the file `modes_table.csv`.
- `scen_dir`: Quoted full path of the folder containing the output folders `images`, `network`, `transit-only`. If using the Cube app, this will be the scenario directory (i.e., `./BASE/YOUR_SCENARIO_FOLDER`).
