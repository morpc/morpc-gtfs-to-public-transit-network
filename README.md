# gtfs-to-public-transit-network
This tool is to create the Public Transit Network from GTFS files. It identifies the existing nodes and links in the given network and creates transit-only nodes and links to fill in the gaps. The transit-only links replicate exactly the shape of the route. The transit-only nodes are located as the projection of the missing bus stops to the route.
