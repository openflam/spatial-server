async function localize() {
    let cameraFramePixels = globalThis.cameraCapture.currentPixelsArray;
    let imageBlob: Blob = await getImageBlobFromArray(
        cameraFramePixels,
        globalThis.cameraCapture.frameWidth,
        globalThis.cameraCapture.frameHeight,
        globalThis.canvas);
    let localizationData = await globalThis.mapServer.localize(imageBlob, 'image');
    console.log(localizationData);
    return localizationData;
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

export { localize };