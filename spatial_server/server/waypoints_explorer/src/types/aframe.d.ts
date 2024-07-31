import { Scene } from "aframe";

interface SceneXR extends Scene {
    hasWebXR?: boolean;
    xrSession?: XRSession;
}

interface XRViewCamera extends XRView {
    camera: any;
}

interface XRWebGLBindingCamera extends XRWebGLBinding {
    getCameraImage?: any;
}


export { SceneXR, XRViewCamera, XRWebGLBindingCamera };