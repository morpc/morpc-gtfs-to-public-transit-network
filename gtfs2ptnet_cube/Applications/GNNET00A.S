;;<<Default Template>><<NETWORK>><<Default>>;;
; Do not change filenames or add or remove FILEI/FILEO statements using an editor. Use Cube/Application Manager.
RUN PGM=NETWORK PRNFILE="C:\Diego Galdino\GTFS_To_Public_Transit_Network\GTFS2PTNET_CUBE\APPLICATIONS\GNNET00A.PRN" MSG='Convert Links/Nodes .DBF to .NET'
FILEO NETO = "{SCENARIO_DIR}\network\NETWORK.NET"
READ FILE = "{SCENARIO_DIR}\NETWORK\LINKS_RENAME.TXT"
READ FILE = "{SCENARIO_DIR}\NETWORK\NODES_RENAME.TXT"

PROCESS  PHASE=INPUT
;Use this phase to modify data as it is read, such as recoding node numbers.


ENDPROCESS


PROCESS  PHASE=NODEMERGE  
; Use this phase to make computations and selections of any data on the NODEI files.


ENDPROCESS


PROCESS  PHASE=LINKMERGE  
; Use this phase to make computations and selections of any data on the LINKI files.


ENDPROCESS


PROCESS  PHASE=SUMMARY   
; Use this phase for combining and reporting of working variables.


ENDPROCESS

ENDRUN
