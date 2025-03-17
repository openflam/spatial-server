import { MapServer } from "@openvps/dnsspatialdiscovery";
import { WebXRCameraCapture } from "../camera-capture/webxr-capture";
import { SceneXR } from "./aframe";
import { Entity, THREE } from "aframe";
import { LocalizationDataWithObjectPose } from "../openvps/localize";

declare global {
    // From the HTML file template at templates/waypoints_explorer/aframe.html
    const mapname: string;
    const fullHost: string;

    // MapServer instance for the selected map
    var mapServer: MapServer;

    // Best localization result
    var bestLocalizationResult: LocalizationDataWithObjectPose | null;

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