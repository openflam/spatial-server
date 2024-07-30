import { MapServer } from '@openvps/dnsspatialdiscovery';

const mapServer = new MapServer(fullHost);

async function getWaypoints() {
    let waypoints = await mapServer.queryWaypoints();
    console.log(waypoints);
}

getWaypoints();

export { MapServer };