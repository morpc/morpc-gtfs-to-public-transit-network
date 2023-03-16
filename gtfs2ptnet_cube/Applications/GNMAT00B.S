;;<<Default Template>><<MATRIX>><<Default>>;;
; Do not change filenames or add or remove FILEI/FILEO statements using an editor. Use Cube/Application Manager.
RUN PGM=MATRIX PRNFILE="C:\Diego Galdino\GTFS_To_Public_Transit_Network\GTFS2PTNET_CUBE\APPLICATIONS\GNMAT00A.PRN" MSG='Create parameters.txt file'
FILEO PRINTO[1] = "{SCENARIO_DIR}\parameters.txt"

zones=1

print printo=1, list='### Enter your parameters below ###'
print printo=1, list='### Check the readme file for better instructions on what to type for each variable below ###'

print printo=1, list='day_type=', '"', '{day_type}', '"'

per1 = '{period_times_1}'
per2 = '{period_times_2}'
per3 = '{period_times_3}'
per4 = '{period_times_4}'
per5 = '{period_times_5}'
print printo=1, list='period_times={','\n',per1,',','\n',per2,',','\n',per3,',','\n',per4,',','\n',per5,'}'

modes = ''
IF ({bus}=1) modes = modes + '3,'
modes = '[' + leftstr(modes, strlen(modes)-1) + ']'
print printo=1, list='modes_gtfs=',modes

transit_att = '{transit_only_attributes}'
print printo=1, list='transit_only_attributes={', transit_att, '}'

print printo=1, list='factype_to_avoid=[', '{factype_to_avoid}', ']'

print printo=1, list='nodes_ranges_to_avoid=[', '{nodes_ranges_to_avoid}', ']'

print printo=1, list='w_bffr=', '{w_bffr}'

print printo=1, list='i_bffr=', '{i_bffr}'

print printo=1, list='net_proj=', '"', '{net_proj}', '"'

print printo=1, list='plot_bool=', '{plot}'

x = replacestr('{gtfs_path}', '\', '\\', 0)
print printo=1, list='gtfs_path=', '"', x, '"'

x = replacestr('{net_folder}', '\', '\\', 0)
print printo=1, list='net_folder=', '"', x, '"'

print printo=1, list='nodes_file=', '"', '{nodes_file}', '"'

print printo=1, list='links_file=', '"', '{links_file}', '"'

x = replacestr('{rte_mode_table}', '\', '\\', 0)
print printo=1, list='rte_mode_table=', '"', x, '"'

;print out scenario output foler
x = replacestr('{SCENARIO_DIR}', '\', '\\', 0)
print printo=1, list='scen_dir=', '"', x, '"'

ENDRUN
