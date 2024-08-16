import { Matrix4 } from 'three';

async function localize(): Promise<Matrix4> {
    let cameraFramePixels = globalThis.cameraCapture.currentPixelsArray;
    let imageBlob: Blob = await getImageBlobFromArray(
        cameraFramePixels,
        globalThis.cameraCapture.frameWidth,
        globalThis.cameraCapture.frameHeight,
        globalThis.canvas);
    let localizationData = await globalThis.mapServer.localize(imageBlob, 'image');

    let objectPose = transformPoseMatrix(localizationData.pose);
    return objectPose;
}

async function getImageBlobFromArray(
    pixelsArray: Uint8ClampedArray,
    frameWidth: number, frameHeight: number,
    canvas: HTMLCanvasElement): Promise<Blob> {

    // Mirror currentPixels and turn it upside down
    let framePixels_mirror = new Uint8ClampedArray(frameWidth * frameHeight * 4);
    for (let i = 0; i < frameHeight; i++) {
        for (let j = 0; j < frameWidth; j++) {
            framePixels_mirror[(frameHeight - i - 1) * frameWidth * 4 + j * 4] = pixelsArray[i * frameWidth * 4 + j * 4];
            framePixels_mirror[(frameHeight - i - 1) * frameWidth * 4 + j * 4 + 1] = pixelsArray[i * frameWidth * 4 + j * 4 + 1];
            framePixels_mirror[(frameHeight - i - 1) * frameWidth * 4 + j * 4 + 2] = pixelsArray[i * frameWidth * 4 + j * 4 + 2];
            framePixels_mirror[(frameHeight - i - 1) * frameWidth * 4 + j * 4 + 3] = pixelsArray[i * frameWidth * 4 + j * 4 + 3];
        }
    }

    // Convert currentPixels to base64
    canvas.width = frameWidth;
    canvas.height = frameHeight;
    let canvas2DContext = canvas.getContext('2d');
    let imageData = canvas2DContext.createImageData(frameWidth, frameHeight);
    imageData.data.set(framePixels_mirror);
    canvas2DContext.putImageData(imageData, 0, 0);

    let blob: Blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg'));
    return blob;
}

function transpose(matrix: number[][]): number[][] {
    return matrix[0].map((_, colIndex) => matrix.map(row => row[colIndex]));
}

function transformPoseMatrix(poseMatrix: number[][]): Matrix4 {
    // Transpose to column-major format and then flatten
    let localizationPose = transpose(poseMatrix).flat();

    // Invert localizationPose
    let localizationPoseInv = new Matrix4();
    localizationPoseInv.fromArray(localizationPose);
    localizationPoseInv.invert();

    let cameraPose = new AFRAME.THREE.Matrix4();
    globalThis.camera.updateMatrixWorld(true); // force = true
    cameraPose = cameraPose.fromArray(globalThis.camera.matrixWorld.elements);

    // The pose returned by the server is in the coordinate system of the server.
    // Let B be the coordinate system of the server, and A the system of the client.
    // C is the pose of the camera, and O is the pose of an object. What the server returns is C_B.
    // We want: inv(C_B) O_B = inv(C_A) O_A. (ie. Pose of objects relative to the camera is same in both systems).
    // => O_A = C_A inv(C_B) O_B

    let objectPose = new Matrix4();
    objectPose = objectPose.multiplyMatrices(cameraPose, localizationPoseInv);
    return objectPose;
}

export { localize };