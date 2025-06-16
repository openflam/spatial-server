import { WayPoint } from "@openvps/dnsspatialdiscovery";
import { Matrix4, Object3D, Quaternion, Vector3 } from "three";

async function renderWaypoints(objectPose: Matrix4) {
    // Fecth waypoints from the server
    let waypoints = await globalThis.mapServer.queryWaypoints();

    // Create the waypointsGraph entity
    var waypointsGraphEntity = createWaypointsGraphEntity(waypoints);

    // Apply the object pose to the waypointsGraph entity
    applyPoseMatrix(waypointsGraphEntity.object3D, objectPose);

    // If the navGraph already exists, remove it
    var oldwaypointsGraphEntity = document.getElementById('waypoints-graph');
    if (oldwaypointsGraphEntity) {
        globalThis.scene.removeChild(oldwaypointsGraphEntity);
    }
    globalThis.scene.appendChild(waypointsGraphEntity);
}

function createWaypointsGraphEntity(waypoints: WayPoint[]) {
    // Generate waypoints graph root entitrt
    var waypointsGraphEntity = document.createElement('a-entity');
    waypointsGraphEntity.setAttribute('id', 'waypoints-graph');

    // Add the waypoints to the waypoints graph entity
    waypoints.forEach(waypoint => {
        var waypointEntity = document.createElement('a-entity');
        waypointEntity.setAttribute('id', waypoint.name);

        // Set the waypoint component attributes
        waypointEntity.setAttribute('waypoint', { name: waypoint.name });

        // Set the position of the waypoints
        waypointEntity.object3D.position.set(
            waypoint.position[0],
            waypoint.position[1],
            waypoint.position[2],
        );

        // Add the waypoint entity to the waypoints graph entity
        waypointsGraphEntity.appendChild(waypointEntity);

        // Add the waypoint connections to each neighbor
        waypoint.neighbors.forEach(neighborName => {
            let neighborWaypoint = waypoints.find(w => w.name === neighborName);
            if (!neighborWaypoint) {
                return;
            }
            if (waypoint.name > neighborWaypoint.name) {
                // Only create the connection once for a pair of waypoints
                return;
            }
            let connectionEntity = document.createElement('a-entity');
            connectionEntity.setAttribute('id', `${waypoint.name}-${neighborName}`);
            connectionEntity.setAttribute('waypoint-connection', {
                start: {
                    x: waypoint.position[0],
                    y: waypoint.position[1],
                    z: waypoint.position[2],
                },
                end: {
                    x: neighborWaypoint.position[0],
                    y: neighborWaypoint.position[1],
                    z: neighborWaypoint.position[2],
                },
                id: `${waypoint.name}-${neighborName}`,
            });
            waypointsGraphEntity.appendChild(connectionEntity);
        });
    });

    return waypointsGraphEntity;
}

function applyPoseMatrix(obj: Object3D, poseMatrix: Matrix4) {
    // Decompose matrix into position, rotation, and scale
    var position = new Vector3();
    var quaternion = new Quaternion();
    var scale = new Vector3();
    poseMatrix.decompose(position, quaternion, scale);

    // Apply the pose to the object
    obj.position.copy(position);
    obj.quaternion.copy(quaternion);
    obj.scale.copy(scale);
}

export { renderWaypoints };