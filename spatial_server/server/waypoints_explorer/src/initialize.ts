import { MapServer } from "@openvps/dnsspatialdiscovery";
import { WebXRCameraCapture } from "./camera-capture/webxr-capture";
import { SceneXR } from "./types/aframe";

export function initialize() {
    // Initialize the map server
    globalThis.mapServer = new MapServer(fullHost);

    // Initialize the canvas
    globalThis.canvas = document.createElement('canvas');

    // Assign the scene
    globalThis.scene = document.querySelector('a-scene');

    // Assign the camera
    globalThis.camera = document.querySelector('#camera').object3D;

    // Initialize the camera capture
    const sceneEl: SceneXR = document.querySelector('a-scene');
    if (sceneEl.hasLoaded) {
        globalThis.cameraCapture = new WebXRCameraCapture(sceneEl);
    } else {
        sceneEl.addEventListener('loaded', () => {
            globalThis.cameraCapture = new WebXRCameraCapture(sceneEl);
        });
    }
}