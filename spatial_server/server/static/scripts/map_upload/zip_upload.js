function uploadZip(serverAddress, progressBar, submitButton) {
    var name = document.getElementById('name').value;
    var zipFile = document.getElementById('zip').files[0];

    if (!name || !zipFile) {
        alert('Please name, and select a zip file.');
        return;
    }

    const formData = new FormData();
    formData.append('name', name);
    formData.append('zip', zipFile);

    // Make the progress bar visible and set its width to 0% 
    progressBar.style.visibility = 'visible';
    progressBar.style.width = '0%';

    const xhr = new XMLHttpRequest();
    xhr.open('POST', serverAddress, true);

    xhr.upload.onprogress = function (event) {
        if (event.lengthComputable) {
            const percentComplete = (event.loaded / event.total) * 100;
            progressBar.style.width = percentComplete + '%';
        }
    };

    xhr.onload = function () {
        if (xhr.status === 200) {
            alert('Uplaoded zip file successfully to ' + serverAddress);

            progressBar.style.width = '100%';
            submitButton.disabled = true;
        } else {
            alert('Failed to upload zip to the server. Server response: ' + response.statusText);
            submitButton.disabled = true;
        }
    };

    xhr.send(formData);
}
