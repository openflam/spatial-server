function uploadWaypoints() {
    const serverAddress = '/upload_waypoints';
    var map_name = document.getElementById('map_name').value;
    var waypoints_csv = document.getElementById('waypoints_csv').files[0];

    if (!map_name || !waypoints_csv) {
        alert('Please select map name and csv file.');
        return;
    }

    const formData = new FormData();
    formData.append('map_name', map_name);
    formData.append('waypoints_csv', waypoints_csv);

    fetch(serverAddress, {
        method: 'POST',
        body: formData,
    })
    .then(response => {
        if (response.ok) {
            alert('Waypoints uploaded successfully.');
        } else {
            alert('Failed to upload waypoints to the server. Server response: ' + response.statusText);
        }
    })
    .catch(error => {
        alert('Error uploading waypoints to the server: ' + error.message);
    });
}
