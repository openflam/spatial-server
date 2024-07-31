import { SceneXR, XRViewCamera, XRWebGLBindingCamera } from "../types/aframe";

class WebXRCameraCapture {
    // Current camera frame pixels
    currentPixelsArray: Uint8ClampedArray = null;

    // Frame width and height
    frameWidth: number = 0;
    frameHeight: number = 0;

    // WebXR WebGL binding
    glBinding: XRWebGLBindingCamera = null;

    // Frame buffer
    fb: WebGLFramebuffer = null;

    // WebGL rendering context
    gl: WebGLRenderingContext = null;

    // XR session
    xrSession: XRSession = null;

    // XR reference space
    xrRefSpace: XRReferenceSpace = null;

    // Singleton instance
    static instance: WebXRCameraCapture = null;

    constructor(sceneEl: SceneXR) {
        // singleton
        if (WebXRCameraCapture.instance) {
            return WebXRCameraCapture.instance;
        }
        WebXRCameraCapture.instance = this;

        if (sceneEl.hasWebXR && navigator.xr && navigator.xr.addEventListener) {
            const { optionalFeatures } = sceneEl.systems.webxr.data;
            optionalFeatures.push('camera-access');
            sceneEl.setAttribute('optionalFeatures', optionalFeatures);

            sceneEl.renderer.xr.addEventListener('sessionstart', () => {
                if (sceneEl.is('ar-mode')) {
                    // Update XR Globals
                    this.xrSession = sceneEl.xrSession;
                    this.gl = sceneEl.renderer.getContext();
                    this.frameWidth = this.gl.canvas.width;
                    this.frameHeight = this.gl.canvas.height;
                    this.currentPixelsArray = new Uint8ClampedArray(
                        this.frameWidth * this.frameHeight * 4
                    );

                    // Get the WebXR WebGL binding
                    this.glBinding = new XRWebGLBinding(this.xrSession, this.gl);
                    this.fb = this.gl.createFramebuffer();
                    this.xrSession.requestReferenceSpace('viewer').then((refSpace) => {
                        this.xrRefSpace = refSpace;
                        this.xrSession.requestAnimationFrame(this.onXRFrame);
                    });
                }
            });
        }
    }

    onXRFrame: XRFrameRequestCallback = (time, frame) => {
        const { session } = frame;
        session.requestAnimationFrame(this.onXRFrame);
        const pose = frame.getViewerPose(this.xrRefSpace);

        if (!pose) return;

        pose.views.forEach((view: XRViewCamera) => {
            if (view.camera) {
                this.getCameraFramePixels(time, session, view);
            }
        });
    }

    getCameraFramePixels(time: number, session: XRSession, view: XRViewCamera) {
        const glLayer = session.renderState.baseLayer;
        if (this.frameWidth !== view.camera.width || this.frameHeight !== view.camera.height) {
            this.frameWidth = view.camera.width;
            this.frameHeight = view.camera.height;
            this.currentPixelsArray = new Uint8ClampedArray(
                this.frameWidth * this.frameHeight * 4
            ); // RGBA image (4 values per pixel)
        }

        // get camera image as texture
        const texture = this.glBinding.getCameraImage(view.camera);

        // bind the framebuffer, attach texture and read pixels
        this.gl.bindFramebuffer(this.gl.FRAMEBUFFER, this.fb);
        this.gl.framebufferTexture2D(
            this.gl.FRAMEBUFFER,
            this.gl.COLOR_ATTACHMENT0,
            this.gl.TEXTURE_2D,
            texture,
            0
        );
        this.gl.readPixels(
            0,
            0,
            this.frameWidth,
            this.frameHeight,
            this.gl.RGBA,
            this.gl.UNSIGNED_BYTE,
            this.currentPixelsArray
        );
        // bind back to xr session's framebuffer
        this.gl.bindFramebuffer(this.gl.FRAMEBUFFER, glLayer.framebuffer);
    }
}

export { WebXRCameraCapture };