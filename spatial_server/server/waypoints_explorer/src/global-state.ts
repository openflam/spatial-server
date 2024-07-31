import { MapServer } from "@openvps/dnsspatialdiscovery";
import { WebXRCameraCapture } from "./camera-capture/webxr-capture";
import { SceneXR } from "./types/aframe";

declare global {
    // MapServer instance for the selected map
    var mapServer: MapServer;

    // WebXR Camera Capture
    var cameraCapture: WebXRCameraCapture;

    // Scene element
    var sceneEl: SceneXR;

    // Canvas element to draw the camera frames
    var canvas: any;
}