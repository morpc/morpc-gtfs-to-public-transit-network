# -*- coding: utf-8 -*-
"""
Created on Nov 2022.

@author: Diego Galdino. Associate Engineer at MORPC.
"""

import pandas as pd
import geopandas as gpd
import os
import numpy as np
from shapely.geometry import  LineString, Point, MultiPoint
import matplotlib.pyplot as plt
import matplotlib
matplotlib.interactive(False)
import networkx as nx
import textwrap
import warnings
warnings.filterwarnings("ignore")
import dbf

def read_network_shp(net_folder, nodes_file, links_file, crs):
    nodes_df = gpd.read_file(os.path.join(net_folder, nodes_file))
    if nodes_df.crs == None:
        nodes_df.crs = crs
    else:
        nodes_df = nodes_df.to_crs(crs)
    links_df = gpd.read_file(os.path.join(net_folder, links_file))
    if links_df.crs == None:
        links_df.crs = crs
    else:
        links_df = links_df.to_crs(crs)
    return nodes_df, links_df

def write_network_csv_shp(scen_dir, nodes_df, links_df, nodes_file, links_file):
    net_folder = os.path.join(scen_dir, 'network')
    # write shp files
    nodes_df.to_file(os.path.join(net_folder, f"{nodes_file.replace('.shp','_wTransit.shp')}"))
    links_df.to_file(os.path.join(net_folder, f"{links_file.replace('.shp','_wTransit.shp')}"))
    # prepare dataframes for csv (without geometry attribute)
    nodes_cols = [c for c in nodes_df.columns if c != 'geometry']
    nodes_df = nodes_df[nodes_cols].copy()
    links_cols = [c for c in links_df.columns if c != 'geometry']
    links_df = links_df[links_cols].copy()
    # write csv files
    pd.DataFrame(nodes_df).to_csv(os.path.join(net_folder, f"{nodes_file.replace('.shp','_wTransit.csv')}"), index=False)
    pd.DataFrame(links_df).to_csv(os.path.join(net_folder, f"{links_file.replace('.shp','_wTransit.csv')}"), index=False)
    # write txt with rename text for CUBE's NODEI and LINKI
    write_net_attributes_renaming_file(nodes_cols, os.path.join(net_folder,'nodes_rename.txt'), os.path.join(net_folder,f"{nodes_file.replace('.shp','_wTransit.dbf')}"), 'NODE')
    write_net_attributes_renaming_file(links_cols, os.path.join(net_folder,'links_rename.txt'), os.path.join(net_folder, f"{links_file.replace('.shp','_wTransit.dbf')}"), 'LINK')
    
def net_cleaning(nodes_df, links_df, nodes_ranges_to_avoid, factype_to_avoid):
    nodes_df, links_df = nodes_df.copy(), links_df.copy()
    for r in nodes_ranges_to_avoid:
        nodes_df.drop(nodes_df[(nodes_df.N >= r[0]) & (nodes_df.N <= r[1])].index, inplace=True)
        links_df.drop(links_df[(links_df.A >= r[0]) & (links_df.B <= r[1])].index, inplace=True)
    for f in factype_to_avoid:
        links_df.drop(links_df[links_df.FACTYPE == f].index, inplace=True)
    return nodes_df, links_df

def read_gtfs(gtfs_folder, crs=None):
    gtfs_stops_df = pd.read_csv(os.path.join(gtfs_folder, 'stops.txt'))
    gtfs_stops_df = gpd.GeoDataFrame(gtfs_stops_df, geometry=gpd.points_from_xy(gtfs_stops_df.stop_lon, gtfs_stops_df.stop_lat), crs="EPSG:4326").to_crs(crs)
    gtfs_shapes_df = pd.read_csv(os.path.join(gtfs_folder, 'shapes.txt'))
    gtfs_shapes_df = gpd.GeoDataFrame(gtfs_shapes_df, geometry=gpd.points_from_xy(gtfs_shapes_df.shape_pt_lon, gtfs_shapes_df.shape_pt_lat), crs="EPSG:4326").to_crs(crs)
    gtfs_trips_df = pd.read_csv(os.path.join(gtfs_folder, 'trips.txt'))
    gtfs_routes_df = pd.read_csv(os.path.join(gtfs_folder, 'routes.txt'))
    gtfs_stop_times_df = pd.read_csv(os.path.join(gtfs_folder, 'stop_times.txt'))
    gtfs_stop_times_df['arrival_time'] = gtfs_stop_times_df.arrival_time.apply(lambda x: pd.to_datetime(x.strip()).strftime('%H:%M:%S') if int(x.strip().split(':')[0]) < 24 else pd.to_datetime(f"{int(x.strip().split(':')[0])-24}:{x.strip().split(':')[1]}:{x.strip().split(':')[2]}").strftime('%H:%M:%S'))
    gtfs_calendar_df = pd.read_csv(os.path.join(gtfs_folder, 'calendar.txt'))
    return gtfs_stops_df, gtfs_shapes_df, gtfs_trips_df, gtfs_routes_df, gtfs_stop_times_df, gtfs_calendar_df

def read_route_mode_id(rte_mode_table, route_id):
    modes_df = pd.read_csv(rte_mode_table)
    try:
        return modes_df.loc[modes_df.ROUTE_ID == route_id, 'MODE'].values[0]
    except:
        raise Exception(f'Route ID {route_id} not found in modes_table.csv.')

def find_nodes_within_shp(nodes, links, shapes):
    nodes_within_shp_list = np.unique(links.A.values.tolist() + links.B.values.tolist())
    nodes_within_shp_df = nodes[nodes.N.isin(nodes_within_shp_list)]
    return nodes_within_shp_df.reset_index(drop=True)

def nearest_node_to_stop(stop, nodes, threshold=np.inf):
    # stop is geometry and nodes is geodataframe
    distances = np.array([stop.distance(n) for n in nodes.geometry])
    if np.min(distances) <= threshold:
        near_node = np.argmin(distances)
        return nodes.N.to_list()[near_node]
    else:
        return None

def match_stops_and_nodes(gtfs_stop_times_df, gtfs_stops_df, nodes_within_shp_df, route_trip_id, threshold=np.inf):
    line_stops = gpd.GeoDataFrame(gtfs_stop_times_df[gtfs_stop_times_df.trip_id == route_trip_id].merge(gtfs_stops_df[['stop_id','geometry']])).sort_values(by='stop_sequence')
    line_stops['N'] = line_stops.geometry.apply(lambda x: nearest_node_to_stop(x, nodes_within_shp_df, threshold))
    return line_stops

def match_stops_and_transit_nodes(line_stops, transit_only_nodes_df, gtfs_stop_times_df, gtfs_stops_df, nodes_within_shp_df, route_trip_id):
    if transit_only_nodes_df.shape[0] != 0:
        line_stops_transit_only = transit_only_nodes_df[transit_only_nodes_df.N.isin(nodes_within_shp_df.N.to_list())].copy()
        if line_stops_transit_only.shape[0] != 0: # Only transit-only nodes related to the current route
            line_stops_transit_only = match_stops_and_nodes(gtfs_stop_times_df, gtfs_stops_df, line_stops_transit_only, route_trip_id, 328)
            for _,s in line_stops_transit_only[~line_stops_transit_only.N.isnull()][['stop_sequence','N']].iterrows():
                line_stops.loc[line_stops.stop_sequence == s.stop_sequence, 'N'] = s.N
    return line_stops.sort_values(by='stop_sequence').reset_index(drop=True)

def create_netx(nodes, links):
    G = nx.DiGraph()
    G.add_nodes_from([(node.N, {'pos':(node.X, node.Y)}) for i,node in nodes.iterrows()])
    G.add_edges_from([(link.A, link.B, {'length':link.geometry.length}) for i,link in links.iterrows()])
    return G

def add_nodes_to_seq(G, source, target, line_node_seq):
    stops_node_seq = nx.shortest_path(G, source=source.N, target=target.N, weight='length')
    stops_node_seq = [int(n) for n in stops_node_seq]
    if len(line_node_seq) != 0:
        line_node_seq.extend(stops_node_seq[1:])
    else:
        line_node_seq.extend(stops_node_seq)
    return line_node_seq

def test_new_link(G, A, B, source, target, new_link, full_link):
    G.add_edges_from([(A, B, {'length':new_link.length})])
    G.add_edges_from([(B, A, {'length':new_link.length})])
    if not nx.has_path(G, source=source.N, target=target.N):
        G.remove_edge(A, B)
        G.remove_edge(B, A)
        A = source.N
        B = target.N
        new_link = full_link
        G.add_edges_from([(A, B, {'length':new_link.length})])
        G.add_edges_from([(B, A, {'length':new_link.length})])
    return A, B, new_link, G
    
def update_nodes_when_new_link(nodes_df, new_node, cols=['N','X','Y','geometry']):
    if isinstance(new_node, gpd.GeoDataFrame) or isinstance(new_node, pd.DataFrame):
        nodes_temp_df = new_node[cols].copy()
    elif isinstance(new_node, gpd.GeoSeries) or isinstance(new_node, pd.Series):
        nodes_temp_df = gpd.GeoDataFrame({str(c):None for c in nodes_df.columns}, index=[0])
        for c in cols:
            if c == 'X':
                nodes_temp_df[c] = new_node['geometry'].x
            elif c == 'Y':
                nodes_temp_df[c] = new_node['geometry'].y
            else:
                nodes_temp_df[c] = new_node[c]
    else:
        raise Exception(f"new_link must be pandas/geopandas DataFrame or pandas/geopandas GeoSeries. Type {type(new_node)} not acceptable.")
    return nodes_df.append(nodes_temp_df, ignore_index=True)

def update_links_when_new_link(links_df, new_link, cols=['A','B','geometry']):
    if isinstance(new_link, gpd.GeoDataFrame) or isinstance(new_link, pd.DataFrame):
        links_temp_df = new_link[cols].copy()
    elif isinstance(new_link, gpd.GeoSeries) or isinstance(new_link, pd.Series):
        links_temp_df = gpd.GeoDataFrame({str(c):None for c in links_df.columns}, index=[0])
        for c in cols:
            links_temp_df[c] = new_link[c]
    else:
        raise Exception(f"new_link must be GeoDataFrame or GeoSeries. Type {type(new_link)} not acceptable.")
    return links_df.append(links_temp_df, ignore_index=True)

def update_links_buffer_when_new_link(links_within_shp_buffer_df, w_bffr, new_link):
    # new_link is linestring
    links_within_shp_buffer_df.loc[links_within_shp_buffer_df.shape[0],'geometry'] = new_link.buffer(w_bffr, cap_style=3)
    return links_within_shp_buffer_df

def find_near_shp_points_to_source_target(shp_nodes, source, target):
    if pd.isnull(source.N):
        source['N'] = 1 # temporarily assign a node number to source if None
    if pd.isnull(target.N):
        target['N'] = 2 # temporarily assign a node number to target if None
    source_target_nodes_df = gpd.GeoDataFrame(pd.DataFrame([source, target]))
    source_target_nodes_df['N'] = source_target_nodes_df.N.astype('int')
    for ft_dist in range(164,820+1,82):
        shp_nodes['NEAR_SHP_POINTS'] = shp_nodes.apply(lambda x: nearest_node_to_stop(x.geometry, source_target_nodes_df, ft_dist), axis=1)
        shp_nodes_not_null = shp_nodes[~shp_nodes.NEAR_SHP_POINTS.isnull()]
        near_point_to_source, near_point_to_target = None, None
        for _,n in shp_nodes_not_null.iterrows():
            if int(n.NEAR_SHP_POINTS) == int(source.N):
                near_point_to_source = int(n.N)
            if not pd.isnull(near_point_to_source) and int(n.NEAR_SHP_POINTS) == int(target.N):
                near_point_to_target = int(n.N)
                break
        if not pd.isnull(near_point_to_source) and not pd.isnull(near_point_to_target):
            break
    shp_points_gap_df = shp_nodes[(shp_nodes.N >= near_point_to_source) & (shp_nodes.N <= near_point_to_target)]
    shp_nodes = shp_nodes[shp_nodes.N >= near_point_to_target]
    return shp_points_gap_df, shp_nodes, near_point_to_source, near_point_to_target

def create_new_link(source, target, transit_only_nodes_df, nodes_within_shp_df, shp_points_gap_df):
    shp_points_gap_df['NEAR_NET_NODE'] = shp_points_gap_df.apply(lambda x: nearest_node_to_stop(x.geometry, nodes_within_shp_df, 328), axis=1)
    shp_points_gap_full_df = shp_points_gap_df.copy()
    A, B = int(source.N), int(target.N)
    if shp_points_gap_df[~shp_points_gap_df.NEAR_NET_NODE.isnull()].shape[0] != 0:
        source_is_transit_bool = False if transit_only_nodes_df.shape[0]==0 else True if source.N in transit_only_nodes_df.N.to_list() else False
        target_is_transit_bool = False if transit_only_nodes_df.shape[0]==0 else True if target.N in transit_only_nodes_df.N.to_list() else False
        if source_is_transit_bool and not target_is_transit_bool: # only source is transit-only
            inter_shp_points_gap_df = shp_points_gap_df[(~shp_points_gap_df.NEAR_NET_NODE.isnull()) & (shp_points_gap_df.NEAR_NET_NODE != A)]
            if inter_shp_points_gap_df.shape[0] != 0:
                intermediary_net_node_ind = inter_shp_points_gap_df.index[0]
                shp_points_gap_df = shp_points_gap_df.loc[:intermediary_net_node_ind]
                B = int(shp_points_gap_df.loc[intermediary_net_node_ind,'NEAR_NET_NODE'])
                target = nodes_within_shp_df.loc[nodes_within_shp_df.N == B].iloc[0]
        elif not source_is_transit_bool and target_is_transit_bool: # only target is transit-only
            inter_shp_points_gap_df = shp_points_gap_df[(~shp_points_gap_df.NEAR_NET_NODE.isnull()) & (shp_points_gap_df.NEAR_NET_NODE != B)]
            if inter_shp_points_gap_df.shape[0] != 0:
                intermediary_net_node_ind = inter_shp_points_gap_df.index[-1]
                shp_points_gap_df = shp_points_gap_df.loc[intermediary_net_node_ind:]
                A = int(shp_points_gap_df.loc[intermediary_net_node_ind,'NEAR_NET_NODE'])
                source = nodes_within_shp_df.loc[nodes_within_shp_df.N == A].iloc[0]
    new_link = LineString([source.geometry] + shp_points_gap_df.geometry.to_list() + [target.geometry])
    full_link = LineString([source.geometry] + shp_points_gap_full_df.geometry.to_list() + [target.geometry])
    return A, B, new_link, full_link

def create_node_seq(G, line_stops, transit_only_nodes_df, transit_only_links_df, transit_only_attributes, shp_id_line, nodes_within_shp_df, new_nodes_from, w_bffr, gtfs_stop_times_df, gtfs_stops_df, route_trip_id):
    line_node_seq = list()
    shp_distances = np.arange(0, shp_id_line.length, 30)
    shp_points = MultiPoint([shp_id_line.interpolate(d) for d in shp_distances] + [Point(np.array(shp_id_line.coords)[-1])])
    shp_nodes = gpd.GeoDataFrame({'N':[p for p in range(len(shp_points.geoms))], 'X':[p.x for p in shp_points.geoms], 'Y':[p.y for p in shp_points.geoms], 'geometry':[shp_points.geoms[p] for p in range(len(shp_points.geoms))]})
    for ind in range(0, line_stops.shape[0]-1):
        source = line_stops.loc[ind]
        target = line_stops.loc[ind+1]
        
        if not pd.isnull(source.N) and not pd.isnull(target.N): # both nodes exist
            if int(source.N) == int(target.N):
                continue
            if nx.has_path(G, source=source.N, target=target.N): # with connection
                line_node_seq = add_nodes_to_seq(G, source, target, line_node_seq)
            else: # without connection
                shp_points_gap_df, shp_nodes, near_point_to_source, near_point_to_target = find_near_shp_points_to_source_target(shp_nodes, source, target)
                
                A, B, new_link, full_link = create_new_link(source, target, transit_only_nodes_df, nodes_within_shp_df, shp_points_gap_df)
                A, B, new_link, G = test_new_link(G, A, B, source, target, new_link, full_link)

                nodes_within_shp_df = update_nodes_when_new_link(nodes_within_shp_df, source)
                nodes_within_shp_df = update_nodes_when_new_link(nodes_within_shp_df, target)
                transit_only_links_df = append_transit_only_links(transit_only_links_df, {'A':A, 'B':B, 'geometry':new_link}, transit_only_attributes)
                transit_only_links_df = append_transit_only_links(transit_only_links_df, {'A':B, 'B':A, 'geometry':LineString(list(new_link.coords)[::-1])}, transit_only_attributes)
                line_node_seq = add_nodes_to_seq(G, source, target, line_node_seq)
        elif pd.isnull(source.N) and not pd.isnull(target.N): # source does not exist
            shp_points_gap_df, shp_nodes, near_point_to_source, near_point_to_target = find_near_shp_points_to_source_target(shp_nodes, source, target)
            
            new_node = {'N': new_nodes_from, # projecting stop to route shape
                        'X': shp_points_gap_df.loc[shp_points_gap_df.N == near_point_to_source, 'X'].values[0], 
                        'Y': shp_points_gap_df.loc[shp_points_gap_df.N == near_point_to_source, 'Y'].values[0], 
                        'geometry': shp_points_gap_df.loc[shp_points_gap_df.N == near_point_to_source, 'geometry'].values[0]}
            transit_only_nodes_df = append_transit_only_nodes(transit_only_nodes_df, new_node, transit_only_attributes)
            new_nodes_from += 1
            line_stops.loc[ind, 'N'] = new_node['N']
            source = line_stops.loc[ind]
            source['geometry'] = new_node['geometry'] # update new geometry of the projected stop to the route
            G.add_nodes_from([(new_node['N'], {'pos':(new_node['X'], new_node['Y'])})])
            
            A, B, new_link, full_link = create_new_link(source, target, transit_only_nodes_df, nodes_within_shp_df, shp_points_gap_df)
            A, B, new_link, G = test_new_link(G, A, B, source, target, new_link, full_link)

            nodes_within_shp_df = update_nodes_when_new_link(nodes_within_shp_df, source)
            transit_only_links_df = append_transit_only_links(transit_only_links_df, {'A':A, 'B':B, 'geometry':new_link}, transit_only_attributes)
            transit_only_links_df = append_transit_only_links(transit_only_links_df, {'A':B, 'B':A, 'geometry':LineString(list(new_link.coords)[::-1])}, transit_only_attributes)
            line_node_seq = add_nodes_to_seq(G, source, target, line_node_seq)
        elif not pd.isnull(source.N) and pd.isnull(target.N): # target does not exist
            shp_points_gap_df, shp_nodes, near_point_to_source, near_point_to_target = find_near_shp_points_to_source_target(shp_nodes, source, target)
            new_node = {'N': new_nodes_from, # projecting stop to route shape
                        'X': shp_points_gap_df.loc[shp_points_gap_df.N == near_point_to_target, 'X'].values[0], 
                        'Y': shp_points_gap_df.loc[shp_points_gap_df.N == near_point_to_target, 'Y'].values[0], 
                        'geometry': shp_points_gap_df.loc[shp_points_gap_df.N == near_point_to_target, 'geometry'].values[0]}
            transit_only_nodes_df = append_transit_only_nodes(transit_only_nodes_df, new_node, transit_only_attributes)
            new_nodes_from += 1
            line_stops.loc[ind+1, 'N'] = new_node['N']
            target = line_stops.loc[ind+1]
            target['geometry'] = new_node['geometry'] # update new geometry of the projected stop to the route
            G.add_nodes_from([(new_node['N'], {'pos':(new_node['X'], new_node['Y'])})])
            
            A, B, new_link, full_link = create_new_link(source, target, transit_only_nodes_df, nodes_within_shp_df, shp_points_gap_df)
            A, B, new_link, G = test_new_link(G, A, B, source, target, new_link, full_link)

            nodes_within_shp_df = update_nodes_when_new_link(nodes_within_shp_df, target)
            transit_only_links_df = append_transit_only_links(transit_only_links_df, {'A':A, 'B':B, 'geometry':new_link}, transit_only_attributes)
            transit_only_links_df = append_transit_only_links(transit_only_links_df, {'A':B, 'B':A, 'geometry':LineString(list(new_link.coords)[::-1])}, transit_only_attributes)
            line_node_seq = add_nodes_to_seq(G, source, target, line_node_seq)
        elif pd.isnull(source.N) and pd.isnull(target.N): # neither source or target exist
            shp_points_gap_df, shp_nodes, near_point_to_source, near_point_to_target = find_near_shp_points_to_source_target(shp_nodes, source, target)
            
            new_node = {'N': new_nodes_from, # projecting stop to route shape
                        'X': shp_points_gap_df.loc[shp_points_gap_df.N == near_point_to_source, 'X'].values[0], 
                        'Y': shp_points_gap_df.loc[shp_points_gap_df.N == near_point_to_source, 'Y'].values[0], 
                        'geometry': shp_points_gap_df.loc[shp_points_gap_df.N == near_point_to_source, 'geometry'].values[0]}
            transit_only_nodes_df = append_transit_only_nodes(transit_only_nodes_df, new_node, transit_only_attributes)
            new_nodes_from += 1
            line_stops.loc[ind, 'N'] = new_node['N']
            source = line_stops.loc[ind]
            source['geometry'] = new_node['geometry'] # update new geometry of the projected stop to the route
            G.add_nodes_from([(new_node['N'], {'pos':(new_node['X'], new_node['Y'])})])
            
            new_node = {'N': new_nodes_from, # projecting stop to route shape
                        'X': shp_points_gap_df.loc[shp_points_gap_df.N == near_point_to_target, 'X'].values[0], 
                        'Y': shp_points_gap_df.loc[shp_points_gap_df.N == near_point_to_target, 'Y'].values[0], 
                        'geometry': shp_points_gap_df.loc[shp_points_gap_df.N == near_point_to_target, 'geometry'].values[0]}
            transit_only_nodes_df = append_transit_only_nodes(transit_only_nodes_df, new_node, transit_only_attributes)
            new_nodes_from += 1
            line_stops.loc[ind+1, 'N'] = new_node['N']
            target = line_stops.loc[ind+1]
            target['geometry'] = new_node['geometry'] # update new geometry of the projected stop to the route
            G.add_nodes_from([(new_node['N'], {'pos':(new_node['X'], new_node['Y'])})])
            
            A, B, new_link, full_link = create_new_link(source, target, transit_only_nodes_df, nodes_within_shp_df, shp_points_gap_df)
            A, B, new_link, G = test_new_link(G, A, B, source, target, new_link, full_link)

            nodes_within_shp_df = update_nodes_when_new_link(nodes_within_shp_df, source)
            nodes_within_shp_df = update_nodes_when_new_link(nodes_within_shp_df, target)
            transit_only_links_df = append_transit_only_links(transit_only_links_df, {'A':A, 'B':B, 'geometry':new_link}, transit_only_attributes)
            transit_only_links_df = append_transit_only_links(transit_only_links_df, {'A':B, 'B':A, 'geometry':LineString(list(new_link.coords)[::-1])}, transit_only_attributes)
            line_node_seq = add_nodes_to_seq(G, source, target, line_node_seq)
        # Before creating new nodes for the nodes with None values, search for them in the transit-only nodes
        line_stops = match_stops_and_transit_nodes(line_stops, transit_only_nodes_df, gtfs_stop_times_df, gtfs_stops_df, nodes_within_shp_df, route_trip_id)
    line_node_seq = [int(n) for n in line_node_seq]
    return line_node_seq, G, line_stops, transit_only_nodes_df, transit_only_links_df, new_nodes_from

def create_node_and_link_seq_gdf(line_node_seq, line_stops, nodes_within_shp_df, links_within_shp_df, transit_only_nodes_df, transit_only_links_df):
    nodes_within_shp_df = update_nodes_when_new_link(nodes_within_shp_df, transit_only_nodes_df[~transit_only_nodes_df.N.isin(nodes_within_shp_df.N.to_list())])
    line_node_seq_df = gpd.GeoDataFrame(pd.DataFrame({'N':line_node_seq}).merge(pd.DataFrame(nodes_within_shp_df), how='left'))
    links_within_shp_df = update_links_when_new_link(links_within_shp_df, transit_only_links_df[~transit_only_links_df.AB.isin(links_within_shp_df.AB.to_list())])
    line_link_seq_df = gpd.GeoDataFrame(pd.DataFrame({'A':line_node_seq[:-1], 'B':line_node_seq[1:]}).merge(pd.DataFrame(links_within_shp_df), how='left'))
    
    # Set stop nodes to negative
    line_node_seq_df['N'] = line_node_seq_df['N'].apply(lambda x: abs(x) * (-1) if x not in line_stops.N.to_list() else x)
    line_link_seq_df['A'] = line_link_seq_df['A'].apply(lambda x: abs(x) * (-1) if x not in line_stops.N.to_list() else x)
    line_link_seq_df['B'] = line_link_seq_df['B'].apply(lambda x: abs(x) * (-1) if x not in line_stops.N.to_list() else x)
    return line_node_seq_df, line_link_seq_df

def update_nodes_links_with_transit_only(nodes_df, links_df, transit_only_nodes_df, transit_only_links_df):
    nodes_df, links_df, transit_only_nodes_df, transit_only_links_df = nodes_df.copy(), links_df.copy(), transit_only_nodes_df.copy(), transit_only_links_df.copy()
    nodes_cols = transit_only_nodes_df.columns.to_list()
    nodes_df = update_nodes_when_new_link(nodes_df, transit_only_nodes_df[~transit_only_nodes_df.N.isin(nodes_df.N.to_list())], nodes_cols)
    links_df['AB'] = abs(links_df.A).astype('int').astype('str') + '_' + abs(links_df.B).astype('int').astype('str')
    links_cols = transit_only_links_df.columns.to_list()
    links_df = update_links_when_new_link(links_df, transit_only_links_df[~transit_only_links_df.AB.isin(links_df.AB.to_list())], links_cols)
    return nodes_df, links_df

def append_transit_only_nodes(transit_only_nodes_df, transit_only_nodes, transit_only_attributes):
    transit_only_nodes_df = transit_only_nodes_df.append(pd.DataFrame(transit_only_nodes, index=[0]))
    return transit_only_nodes_df

def append_transit_only_links(transit_only_links_df, transit_only_links, transit_only_attributes):
    transit_only_links_temp_df = pd.DataFrame(transit_only_links, index=[0])
    for att in transit_only_attributes:
        transit_only_links_temp_df[att] = transit_only_attributes[att]
    transit_only_links_temp_df['DIST'] = transit_only_links_temp_df.geometry.apply(lambda x: x.length/5280)
    transit_only_links_temp_df['AB'] = abs(transit_only_links_temp_df.A).astype('int').astype('str') + '_' + abs(transit_only_links_temp_df.B).astype('int').astype('str')
    transit_only_links_temp_df = transit_only_links_temp_df[['A','B','AB','DIST'] + list(transit_only_attributes.keys()) + ['geometry']]
    transit_only_links_df = transit_only_links_df.append(transit_only_links_temp_df)
    return transit_only_links_df

def plot(scen_dir, shp_id_df, gtfs_trips_df, line_node_seq_df, line_link_seq_df, links_intersecting_shp_df, transit_only_nodes_df, transit_only_links_df, w_bffr, i_bffr, title, figsize=(20,20)):
    # Setting dataframes
    shp_id_line_df = gpd.GeoDataFrame({'geometry':[LineString(shp_id_df.geometry.values)]})
    line_link_seq_df['AB'] = abs(line_link_seq_df.A).astype('int').astype('str') + '_' +  abs(line_link_seq_df.B).astype('int').astype('str')
    net_links = line_link_seq_df[~line_link_seq_df.AB.isin(transit_only_links_df.AB.to_list())].drop_duplicates(subset=['AB'])
    created_links = line_link_seq_df[line_link_seq_df.AB.isin(transit_only_links_df.AB.to_list())].drop_duplicates(subset=['AB'])
    net_nodes = line_node_seq_df[line_node_seq_df.N<0].drop_duplicates(subset=['N'])
    net_stops = line_node_seq_df[(line_node_seq_df.N>0) & (~abs(line_node_seq_df.N).isin(transit_only_nodes_df.N.to_list()))].drop_duplicates(subset=['N'])
    created_stops = line_node_seq_df[(line_node_seq_df.N>0) & (abs(line_node_seq_df.N).isin(transit_only_nodes_df.N.to_list()))].drop_duplicates(subset=['N'])
    # Fig below
    fig, ax = plt.subplots(figsize=figsize)
    links_intersecting_shp_df.plot(ax=ax, color='grey', linewidth=1, alpha=0.3, zorder=1, label=f'Highway links in a range of {i_bffr} ft (~{i_bffr/3281:.2f} km)')
    shp_id_line_df.plot(ax=ax, color='green', linewidth=10, alpha=0.25, zorder=2, label="Line shape buffer.")
    net_links.plot(ax=ax, color='black', linestyle='solid', linewidth=2, zorder=3, label="Highway links already coded.")
    created_links.plot(ax=ax, color='yellow', linestyle='dotted', linewidth=2, zorder=4, label="Transit-only links created.")
    net_nodes.plot(ax=ax, color='blue', alpha=0.6, marker="s", markersize=25, zorder=4, label="Non-stop highway nodes already coded.")
    net_stops.plot(ax=ax, color='red', alpha=0.6, marker="o", markersize=25, zorder=5, label="Stop highway nodes already coded.")
    created_stops.plot(ax=ax, color='magenta', alpha=0.6, marker="^", markersize=25, zorder=5, label="Transit-only stop nodes created.")
    
    ax.set_xlabel('X', fontsize=16)
    ax.set_ylabel('Y', fontsize=16)
    ax.set_title(title, fontsize=20)
    ax.legend(fontsize=16, loc='upper right', framealpha=0.3)
    
    filename = valid_filename_alphanumeric_spaces(f'{title}.jpeg')
    fig.savefig(os.path.join(scen_dir, 'images', filename), dpi=600, bbox_inches = 'tight', pad_inches = 0.2)
    plt.close(fig)
    
def valid_filename_alphanumeric_spaces(filename):
    return "".join(x for x in filename if x.isalnum() or x.isspace() or x == '.')

def list_arrival_times_by_shp_service_time(gtfs_trips_df, gtfs_calendar_df, gtfs_stop_times_df, shp_id, day_type, period_time):
    srvc_id = gtfs_calendar_df.loc[gtfs_calendar_df[day_type] == 1,'service_id'].values[0]
    gtfs_trips_df = gtfs_trips_df.copy()
    gtfs_stop_times_df = gtfs_stop_times_df.copy()
    gtfs_trips_df = gtfs_trips_df.merge(gtfs_stop_times_df[gtfs_stop_times_df.stop_sequence == 1][['trip_id','arrival_time']])
    arr_times_by_shp_srvc_time = dict()
    start_time, end_time = period_time
    arr_times_by_shp_srvc_time = gtfs_trips_df[(gtfs_trips_df.shape_id == shp_id) & 
                                        (gtfs_trips_df.service_id == srvc_id) & 
                                        (gtfs_trips_df.arrival_time >= start_time) &
                                        (gtfs_trips_df.arrival_time < end_time)].arrival_time.to_list()
    return arr_times_by_shp_srvc_time

def calculate_headway(start_times):
		start_times.sort()
		headways = [(pd.to_datetime(t) - pd.to_datetime(s)).total_seconds() for s, t in zip(start_times, start_times[1:])]
		if headways:
			return round(sum(headways)/(len(headways)*60))
		else:
			return 0.0
        
def set_line_name(head_sign, shp_id):
    shp_id = str(shp_id)[-3:]
    tot_len = 10
    return head_sign[:tot_len-len(shp_id)-1] + '_' + shp_id

def write_lin_file(lines, outfile):
#     header = ''';;<<PT>><<LINE>>;;
# ; 2018 Local bus lines
# ; LOCALBUS.LIN
# ; MORPC Travel Forecasting Model
# ; Local Bus Transit Lines'''
    with open(outfile, 'w') as file:
        # file.write(header)
        for line in lines:
            if lines.index(line) != 0:
                file.write('\n')
            line_content = f'LINE NAME="{line["name"]}", MODE={line["mode"]},'
            hdw_nmbr = 1
            for hdw in line["headways"]:
                line_content += f' HEADWAY[{hdw_nmbr}]={hdw:.2f},'
                hdw_nmbr += 1
            line_content += ' ONEWAY=T, ALLSTOPS=F, VEHICLETYPE=1,\nN='
            nodes_string = ''
            for node in line["node_seq"]:
                nodes_string += f' {int(node)},'
            line_content += textwrap.fill(nodes_string, width=254).replace(' ','')
            line_content += ' CIRCULAR=F'
            file.write(textwrap.fill(line_content, width=254))

def column_dbf_type(col_df):
    f_type = None
    if col_df.dtype in [int, np.int32, np.int64]:
        f_length = len(max(col_df.astype('str'), key=len))
        if f_length > 32:
            raise Exception('f_length too big. (>32)')
        f_type = f'N({f_length},0)'
    elif col_df.dtype in [float, np.float32, np.float64]:
        f_length = len(max((col_df // 1).astype('str'), key=len).split('.')[0])
        f_decimals = 6
        if f_length < 32:
            while f_length + f_decimals + 1 > 32:
                f_decimals -= 1
        else:
            raise Exception('f_length too big. (>=32)')
        f_type = f'N({f_length + f_decimals + 1},{f_decimals})'
    elif col_df.dtype in [str, object]:
        f_length = len(max(col_df.to_list(), key=len))
        f_type = f'C({f_length})'
    return f_type

def write_nodes_dbf(nodes_df, nodes_dbf):
    field_types = ';'.join([f'{c} {column_dbf_type(nodes_df[c])}' for c in nodes_df.columns])
    nodes_dbf_tbl = dbf.Table(nodes_dbf, field_types) #length and decimals in Numeric must be: L_informed = L_int + (D+1); D_informed = D. This is to avoid errors in the dbf library.
    nodes_dbf_tbl.open(mode=dbf.READ_WRITE)
    for node in list(nodes_df.itertuples(index=False, name=None)):
        nodes_dbf_tbl.append(node)
    nodes_dbf_tbl.close()
        
def write_links_dbf(links_df, links_dbf):
    field_types = ';'.join([f'{c} {column_dbf_type(links_df[c])}' for c in links_df.columns])
    links_dbf_tbl = dbf.Table(links_dbf, field_types)  #length and decimals in Numeric must be: L_informed = L_int + (D+1); D_informed = D. This is to avoid errors in the dbf library.
    links_dbf_tbl.open(mode=dbf.READ_WRITE)
    for link in list(links_df.itertuples(index=False, name=None)):
        links_dbf_tbl.append(link)
    links_dbf_tbl.close()
    
def write_net_attributes_renaming_file(cols, outfile, dbf_filename, link_or_node):
    text = f"FILEI {link_or_node.upper()}I[1] = \"{dbf_filename}\""
    if len(cols) != 0:
        text += ", RENAME="
        for c in cols:
            if len(c) > 10:
                text += f"{c[:10]}-{c}, "
        text = text[:-2]
    with open(outfile, 'w') as file:
        file.write(text)  