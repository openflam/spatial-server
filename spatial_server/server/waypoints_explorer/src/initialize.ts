import { MapServer } from "@openvps/dnsspatialdiscovery";
import { WebXRCameraCapture } from "./camera-capture/webxr-capture";
import { SceneXR } from "./types/aframe";

export function initialize() {
    // Initialize the map server
    globalThis.mapServer = new MapServer(fullHost);

    // Initialize the camera capture
    const sceneEl: SceneXR = document.querySelector('a-scene');
    if (sceneEl.hasLoaded) {
        globalThis.cameraCapture = new WebXRCameraCapture(sceneEl);
    } else {
        sceneEl.addEventListener('loaded', () => {
            globalThis.cameraCapture = new WebXRCameraCapture(sceneEl);
        });
    }

    // Initialize the canvas
    globalThis.canvas = document.createElement('canvas');
}