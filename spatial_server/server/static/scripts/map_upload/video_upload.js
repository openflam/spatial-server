function uploadVideo() {
    const serverAddress = '/create_map/video';
    var name = document.getElementById('name').value;
    var videoFile = document.getElementById('video').files[0];
    var numFramesPerc = document.getElementById('num_frames_perc').value;

    if (!name || !videoFile) {
        alert('Please name, and select a video file.');
        return;
    }

    const formData = new FormData();
    formData.append('name', name);
    formData.append('video', videoFile);
    formData.append('num_frames_perc', numFramesPerc);

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
