# -*- coding: utf-8 -*-
"""
Tool development: Nov 2022 - Feb 2023.

@author:        Diego Galdino, Associate Engineer with MORPC.
@Contributions: Zhuojun Jiang, Transportation Engineer IV with ODOT.
                Yan Liu, Senior Engineer with MORPC.
                Raj Roy, Associate Engineer with MORPC.
"""

#%% Libraries and hard-coded inputs below

import pandas as pd
import geopandas as gpd
import os
# import warnings
# warnings.filterwarnings("ignore")
import time
from gtfs2ptnet import *
import sys

#%% Main process below

if __name__=='__main__':
    #%% Read parameters
    parameters = sys.argv[1]

    ''' parameters.txt: Check readme for instructions and more info about the inputs.
    day_type,
    period_times,
    modes_gtfs,
    transit_only_attributes,
    factype_to_avoid,
    w_bffr,
    i_bffr,
    net_proj,
    plot_bool,
    nodes_files,
    links_file
    '''

    # Read parameters.txt and execute each line
    print(f'Importing parameters/inputs from {parameters}.')
    line_append = ''
    with open(parameters, 'rb') as par_file:
        for line in par_file:
            line = line.strip().decode("utf-8")
            if line[0] != '#':
                if (line.count('{') > line.count('}')) or (line.count('[') > line.count(']')):
                    line_append = line
                    continue
                elif (line.count('{') == line.count('}')) and (line.count('[') == line.count(']')) and (line_append != ''):
                    line_append += line
                    continue
                else:
                    line_append += line
                    line = line_append
                    line_append = ''
        
                exec(line)
                print(f"\tInput: {line}.")
    print('\tDone importing parameters/inputs.')
    
    t0 = time.time()
    # Read network nodes and links
    base_nodes_df, base_links_df = read_network_shp(net_folder, nodes_file, links_file, net_proj)
    new_nodes_from = max(base_nodes_df.N) + 1
    
    # Network cleaning
    nodes_df, links_df = net_cleaning(base_nodes_df, base_links_df, nodes_ranges_to_avoid, factype_to_avoid)
    
    # Read GTFS files
    gtfs_stops_df, gtfs_shapes_df, gtfs_trips_df, gtfs_routes_df, gtfs_stop_times_df, gtfs_calendar_df = read_gtfs(gtfs_path, net_proj)
    
    lines = list()
    transit_only_nodes_df = pd.DataFrame()
    transit_only_links_df = pd.DataFrame()
    for shp_id in gtfs_shapes_df.shape_id.unique():
        t1 = time.time()
        
        # Line/Route ID, mode, and first trip ID
        if shp_id not in gtfs_trips_df.shape_id.tolist():
            print(f"Shape ID {shp_id} not found in GTFS 'trips.txt'.")
            continue
        
        route_id = gtfs_trips_df.loc[gtfs_trips_df.shape_id == shp_id, 'route_id'].unique()[0]
        route_mode = gtfs_routes_df[gtfs_routes_df['route_id'] == route_id].route_type.values[0]
        route_trip_id = gtfs_trips_df.loc[gtfs_trips_df.shape_id == shp_id, 'trip_id'].unique()[0]
        
        if route_mode not in modes_gtfs: # If shp_id's mode not in the list of modes to be processed, move to next shp_id
            print(f"Shape ID {shp_id} is a Route Mode {route_mode} not of interest.")    
            continue
        
        shp_id_headsign = gtfs_trips_df.loc[gtfs_trips_df.shape_id == shp_id,'trip_headsign'].values[0]
        print(f'Processing Shape ID {shp_id}.\n\tRoute headsign: {shp_id_headsign}')
       
        # Create the line dictionary to store line's attributes as id, name, mode, and headways for .LIN file.
        line = dict()
        line['id'] = shp_id
        line['mode'] = read_route_mode_id(rte_mode_table, route_id)
        
        # Line name
        head_sign = gtfs_trips_df.loc[gtfs_trips_df.shape_id == shp_id, 'trip_headsign'].unique()[0]
        line_name = set_line_name(head_sign, shp_id)
        line['name'] = line_name
        
        # Filter gtfs_shapes_df by shp_id and create the shape id line
        shp_id_df = gtfs_shapes_df[gtfs_shapes_df.shape_id == shp_id].copy().reset_index(drop=True)
        shp_id_line = LineString(shp_id_df.geometry.values)
        
        # Find links within route shape and intersecting route shape
        shp_id_line_buffer_w = gpd.GeoDataFrame({'shp_id':shp_id, 'geometry':[shp_id_line.buffer(w_bffr, cap_style=3)]}, crs=shp_id_df.crs)
        links_within_shp_df = gpd.sjoin(links_df, shp_id_line_buffer_w, how='inner', predicate='within')
        links_within_shp_df['AB'] = links_within_shp_df.A.astype('int').astype('str') + '_' + links_within_shp_df.B.astype('int').astype('str')
        links_within_shp_no_transit_df = links_within_shp_df[~links_within_shp_df.AB.isin(transit_only_links_df.AB.to_list())] if transit_only_links_df.shape[0] != 0 else links_within_shp_df
        shp_id_line_buffer_i = gpd.GeoDataFrame({'shp_id':shp_id, 'geometry':[shp_id_line.buffer(i_bffr)]}, crs=shp_id_df.crs)
        links_intersecting_shp_df = gpd.sjoin(links_df, shp_id_line_buffer_i, how='inner', predicate='intersects')
        links_intersecting_shp_df['AB'] = links_intersecting_shp_df.A.astype('int').astype('str') + '_' + links_intersecting_shp_df.B.astype('int').astype('str')
        links_intersecting_shp_no_transit_df = links_intersecting_shp_df[~links_intersecting_shp_df.AB.isin(transit_only_links_df.AB.to_list())] if transit_only_links_df.shape[0] != 0 else links_intersecting_shp_df
        
        # Find nodes within route shape
        nodes_within_shp_df = find_nodes_within_shp(nodes_df, links_within_shp_df, shp_id_df)
        nodes_within_shp_no_transit_df = nodes_within_shp_df[~nodes_within_shp_df.N.isin(transit_only_nodes_df.N.to_list())] if transit_only_nodes_df.shape[0] != 0 else nodes_within_shp_df
        
        # Line's stops matched to nodes
        line_stops = match_stops_and_nodes(gtfs_stop_times_df, gtfs_stops_df, nodes_within_shp_no_transit_df, route_trip_id)
        
        # Set node to None if stop not within original network links
        links_within_shp_buffer_df = gpd.GeoDataFrame({'geometry':[link.buffer(w_bffr, cap_style=3) for link in links_within_shp_no_transit_df.geometry]}, crs=shp_id_df.crs)
        stops_within_links_df = gpd.sjoin(line_stops, links_within_shp_buffer_df, how='inner', predicate='within').sort_values(by='stop_sequence').drop_duplicates(subset=['stop_sequence'])
        line_stops.loc[line_stops.stop_sequence.isin([s for s in line_stops.stop_sequence.to_list() if s not in stops_within_links_df.stop_sequence.to_list()]), 'N'] = None
        
        # Before creating new nodes for the nodes with None values, search for them in the transit-only nodes
        line_stops = match_stops_and_transit_nodes(line_stops, transit_only_nodes_df, gtfs_stop_times_df, gtfs_stops_df, nodes_within_shp_df, route_trip_id)
        
        # Create networkx
        G = create_netx(nodes_within_shp_df, links_within_shp_df)
        
        # Create node and link sequence
        line_node_seq, G, line_stops, transit_only_nodes_df, transit_only_links_df, new_nodes_from = create_node_seq(G, line_stops, transit_only_nodes_df, transit_only_links_df, transit_only_attributes, shp_id_line, nodes_within_shp_df, new_nodes_from, w_bffr, gtfs_stop_times_df, gtfs_stops_df, route_trip_id)
        line_node_seq_df, line_link_seq_df = create_node_and_link_seq_gdf(line_node_seq, line_stops, nodes_within_shp_df, links_within_shp_df, transit_only_nodes_df, transit_only_links_df)
        line["node_seq"] = line_node_seq_df.N.to_list()
        
        # Update nodes and links for next routes
        nodes_df, links_df = update_nodes_links_with_transit_only(nodes_df, links_df, transit_only_nodes_df, transit_only_links_df)
        
        # Calculate headways
        line['headways'] = list()
        for t in period_times:
            period_time = period_times[t]
            arr_times_by_shp_srvc_time = list_arrival_times_by_shp_service_time(gtfs_trips_df, gtfs_calendar_df, gtfs_stop_times_df, shp_id, day_type, period_time)
            headway_by_shp_srvc_time = calculate_headway(arr_times_by_shp_srvc_time)
            line['headways'].append(headway_by_shp_srvc_time)
        
        # Append line to list of lines that will be saved later as PTlines.LIN
        lines.append(line)
        print(f'\tShape ID {shp_id} processing done. Total time {time.time()-t1:.2f} seconds.')
        
        # Plot and save figure
        if plot_bool == 1:
            t2 = time.time()
            title = f'{shp_id_headsign} - Shape ID {shp_id}'
            plot(scen_dir, shp_id_df, gtfs_trips_df, line_node_seq_df, line_link_seq_df, links_intersecting_shp_no_transit_df, transit_only_nodes_df, transit_only_links_df, w_bffr, i_bffr, title, figsize=(20,20))
            print(f'\tFigure saved. Total time for plotting and saving figure {time.time()-t2:.2f} seconds.')
        
    # Save new base_nodes.shp and base_links.shp
    new_base_nodes_df, new_base_links_df = update_nodes_links_with_transit_only(base_nodes_df, base_links_df, transit_only_nodes_df, transit_only_links_df)
    write_network_csv_shp(scen_dir, new_base_nodes_df, new_base_links_df, nodes_file, links_file)
    print('New nodes and links shapefiles saved.')
    
    # Write lin file
    write_lin_file(lines, os.path.join(scen_dir,'transit-only','PTlines.lin'))
    print('PTLines.lin file saved.')
    
    # Save transit only nodes and links file (CSV and DBF)
    if transit_only_nodes_df.shape[0] != 0:
        nodes_cols = list(transit_only_nodes_df.columns)
        nodes_cols.remove('geometry')
        nodes_csv = os.path.join(scen_dir,'transit-only','PTOnlyNodes.csv')
        transit_only_nodes_df[nodes_cols].to_csv(nodes_csv, index=False)
        nodes_dbf = nodes_csv.replace('csv','dbf')
        write_nodes_dbf(transit_only_nodes_df[nodes_cols], nodes_dbf)
        print('PTOnlyNodes CSV and DBF files saved.')
    if transit_only_links_df.shape[0] != 0:
        links_cols = list(transit_only_links_df.columns)
        links_cols = [c for c in links_cols if c not in ['AB', 'geometry']]
        links_csv = os.path.join(scen_dir,'transit-only','PTOnlyLinks.csv')
        transit_only_links_df[links_cols].to_csv(links_csv, index=False)
        links_dbf = links_csv.replace('csv','dbf')
        write_links_dbf(transit_only_links_df[links_cols], links_dbf)
        print('PTOnlyLinks CSV and DBF files saved.')
    
    print(f'GTFS to Public Transit Network done. Total time {time.time()-t0:.2f} seconds.')
