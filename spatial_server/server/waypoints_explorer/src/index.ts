import { initialize } from "./initialize";
import { localize } from "./openvps/localize";
import { renderWaypoints } from "./render-waypoints/render-waypoints";

initialize();

// Poll for localization every 5 seconds
setInterval(() => {
    localize().then((objectPose) => {
        renderWaypoints(objectPose);
    });
}, 5000);