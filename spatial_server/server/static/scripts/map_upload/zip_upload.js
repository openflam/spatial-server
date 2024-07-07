function uploadZip(serverAddress) {
    var name = document.getElementById('name').value;
    var zipFile = document.getElementById('zip').files[0];

    if (!name || !zipFile) {
        alert('Please name, and select a zip file.');
        return;
    }

    const formData = new FormData();
    formData.append('name', name);
    formData.append('zip', zipFile);

    fetch(serverAddress, {
        method: 'POST',
        body: formData,
    })
        .then(response => {
            if (response.ok) {
                alert('Uplaoded zip file successfully to ' + serverAddress);
            } else {
                alert('Failed to upload zip to the server. Server response: ' + response.statusText);
            }
        })
        .catch(error => {
            alert('Error uploading zip to the server: ' + error.message);
        });
}
