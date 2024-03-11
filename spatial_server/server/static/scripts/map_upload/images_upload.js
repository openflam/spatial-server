function uploadImages() {
    const serverAddress = '/create_map/images';
    const name = document.getElementById('name').value;
    const imagesZipFile = document.getElementById('imagesZip').files[0];

    if (!name || !imagesZipFile) {
        alert('Please name, and select an images zip file.');
        return;
    }

    const formData = new FormData();
    formData.append('name', name);
    formData.append('imagesZip', imagesZipFile);

    fetch(serverAddress, {
        method: 'POST',
        body: formData,
    })
    .then(response => {
        if (response.ok) {
            alert('Images uploaded successfully.');
        } else {
            alert('Failed to upload images to the server. Server response: ' + response.statusText);
        }
    })
    .catch(error => {
        alert('Error uploading images to the server: ' + error.message);
    });
}
