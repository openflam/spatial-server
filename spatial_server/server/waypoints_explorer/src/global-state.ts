import { MapServer } from "@openvps/dnsspatialdiscovery";
import { WebXRCameraCapture } from "./camera-capture/webxr-capture";
import { SceneXR } from "./types/aframe";
import { Entity, THREE } from "aframe";

declare global {
    // MapServer instance for the selected map
    var mapServer: MapServer;

    // WebXR Camera Capture
    var cameraCapture: WebXRCameraCapture;

    // Scene element
    var sceneEl: SceneXR;

    // Canvas element to draw the camera frames
    var canvas: any;

    // A-Frame camera
    var camera: THREE.Object3D;

    // A-frame scene
    var scene: Entity;
}