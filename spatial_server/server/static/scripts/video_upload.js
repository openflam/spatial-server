function uploadVideo() {
    const serverAddress = '/create_map/video';
    const name = document.getElementById('name').value;
    const videoFile = document.getElementById('video').files[0];

    if (!name || !videoFile) {
        alert('Please name, and select a video file.');
        return;
    }

    const formData = new FormData();
    formData.append('name', name);
    formData.append('video', videoFile);

    fetch(serverAddress, {
        method: 'POST',
        body: formData,
    })
    .then(response => {
        if (response.ok) {
            alert('Video uploaded successfully.');
        } else {
            alert('Failed to upload video to the server. Server response: ' + response.statusText);
        }
    })
    .catch(error => {
        alert('Error uploading video to the server: ' + error.message);
    });
}
