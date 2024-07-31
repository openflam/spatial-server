import { initialize } from "./initialize";
import { localize } from "./openvps/localize";

initialize();

setInterval(() => {
    localize();
}, 5000);