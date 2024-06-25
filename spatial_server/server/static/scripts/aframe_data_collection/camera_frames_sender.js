const time_interval_ms = 5000;
const serverURL = "/save_image_pose/" + mapname;

// Scene elements
const sceneEl = document.querySelector('a-scene');
const aframeCameraEl = document.querySelector('#camera').object3D;
const canvas = document.createElement('canvas');
const buttonEl = document.querySelector('#capture-button');

// XR Globals
var currentPixelsArray = null, // Current camera frame pixels
    frameWidth = 0,
    frameHeight = 0,
    glBinding = null, // WebXR WebGL binding
    fb = null, // Frame buffer
    gl = null, // WebGL rendering context
    xrSession = null, // XR session
    xrRefSpace = null; // XR reference space


async function sendCameraFrame() {
    // Get current image and pose to send to the server
    imageBlob = await getImageBlobFromArray(currentPixelsArray, frameWidth, frameHeight, canvas);
    var formData = new FormData();
    formData.append('image', imageBlob, 'image.jpeg');
    aframeCameraEl.updateMatrixWorld(force = true);
    formData.append('aframe_camera_matrix_world', aframeCameraEl.matrixWorld.toArray());

    // Send the image to the server
    response = await fetchJSON(serverURL, formData);
    return response;
}

function onXRFrame(time, frame) {
    const { session } = frame;
    session.requestAnimationFrame(onXRFrame);
    const pose = frame.getViewerPose(xrRefSpace);

    if (!pose) return;

    pose.views.forEach((view) => {
        if (view.camera) {
            getCameraFramePixels(time, session, view);
        }
    });
}

function getCameraFramePixels(time, session, view) {
    const glLayer = session.renderState.baseLayer;
    if (frameWidth !== view.camera.width || frameHeight !== view.camera.height) {
        frameWidth = view.camera.width;
        frameHeight = view.camera.height;
        currentPixelsArray = new Uint8ClampedArray(frameWidth * frameHeight * 4); // RGBA image (4 values per pixel)
    }

    // get camera image as texture
    const texture = glBinding.getCameraImage(view.camera);

    // bind the framebuffer, attach texture and read pixels
    gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);
    gl.readPixels(
        0,
        0,
        frameWidth,
        frameHeight,
        gl.RGBA,
        gl.UNSIGNED_BYTE,
        currentPixelsArray
    );
    // bind back to xr session's framebuffer
    gl.bindFramebuffer(gl.FRAMEBUFFER, glLayer.framebuffer);
}

function initXRSession() {
    if (sceneEl.hasWebXR && navigator.xr && navigator.xr.addEventListener) {
        const { optionalFeatures } = sceneEl.systems.webxr.data;
        optionalFeatures.push('camera-access');
        sceneEl.systems.webxr.sceneEl.setAttribute('optionalFeatures', optionalFeatures);

        sceneEl.renderer.xr.addEventListener('sessionstart', () => {
            if (sceneEl.is('ar-mode')) {
                // Update XR Globals
                xrSession = sceneEl.xrSession;
                gl = sceneEl.renderer.getContext();
                frameWidth = gl.canvas.width;
                frameHeight = gl.canvas.height;
                currentPixelsArray = new Uint8Array(frameWidth * frameHeight * 4);

                // Get the WebXR WebGL binding
                glBinding = new XRWebGLBinding(xrSession, gl);
                fb = gl.createFramebuffer();
                xrSession.requestReferenceSpace('viewer').then((refSpace) => {
                    xrRefSpace = refSpace;
                    xrSession.requestAnimationFrame(onXRFrame);
                    
                    // Send camera frames to the server
                    buttonEl.addEventListener('click', sendCameraFrame);
                });
            }
        });
    }
}

if (sceneEl.hasLoaded) {
    initXRSession();
} else {
    sceneEl.addEventListener('loaded', initXRSession);
}
