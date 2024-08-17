import { Matrix4 } from 'three';
import { LocalizationData } from '@openvps/dnsspatialdiscovery';

// All keys from LocalizationData and objectPose
interface LocalizationDataWithObjectPose extends LocalizationData {
    objectPose: Matrix4;
}

async function localize(): Promise<Matrix4> {
    let imageBlob = await globalThis.cameraCapture.fetchCurrentImageBlob(globalThis.canvas);
    let localizationData = await globalThis.mapServer.localize(imageBlob, 'image');

    let objectPose = transformPoseMatrix(localizationData.pose);

    // Add objectPose to localizationData
    let localizationDataWithObjectPose: LocalizationDataWithObjectPose = {
        ...localizationData,
        objectPose: objectPose
    };

    updateBestLocalizationResult(localizationDataWithObjectPose);

    return globalThis.bestLocalizationResult.objectPose;
}

function updateBestLocalizationResult(localizationData: LocalizationDataWithObjectPose) {
    if (!globalThis.bestLocalizationResult) {
        globalThis.bestLocalizationResult = localizationData;
    } else {
        // Update bestLocalizationResult if the new localizationData has a higher confidence
        if (localizationData.serverConfidence > globalThis.bestLocalizationResult.serverConfidence) {
            globalThis.bestLocalizationResult = localizationData;
        }
    }
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

export { localize, LocalizationDataWithObjectPose };