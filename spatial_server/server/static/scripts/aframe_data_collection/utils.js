async function getImageBlobFromArray(pixelsArray, frameWidth, frameHeight, canvas) {
    // Mirror currentPixels and turn it upside down
    var framePixels_mirror = new Uint8ClampedArray(frameWidth * frameHeight * 4);
    for (var i = 0; i < frameHeight; i++) {
        for (var j = 0; j < frameWidth; j++) {
            framePixels_mirror[(frameHeight - i - 1) * frameWidth * 4 + j * 4] = pixelsArray[i * frameWidth * 4 + j * 4];
            framePixels_mirror[(frameHeight - i - 1) * frameWidth * 4 + j * 4 + 1] = pixelsArray[i * frameWidth * 4 + j * 4 + 1];
            framePixels_mirror[(frameHeight - i - 1) * frameWidth * 4 + j * 4 + 2] = pixelsArray[i * frameWidth * 4 + j * 4 + 2];
            framePixels_mirror[(frameHeight - i - 1) * frameWidth * 4 + j * 4 + 3] = pixelsArray[i * frameWidth * 4 + j * 4 + 3];
        }
    }

    // Convert currentPixels to base64
    canvas.width = frameWidth;
    canvas.height = frameHeight;
    var canvas2DContext = canvas.getContext('2d');
    var imageData = canvas2DContext.createImageData(frameWidth, frameHeight);
    imageData.data.set(framePixels_mirror);
    canvas2DContext.putImageData(imageData, 0, 0);

    // Send the image to the server
    blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg'));
    return blob;
}

async function fetchJSON(url, formData) {
    return fetch(url, {
        method: 'POST',
        body: formData
    }).then(response => {
        if (!response.ok) {
            throw new Error('Failed to fetch from URL: ' + url);
        }
        return response.json();
    });
}
