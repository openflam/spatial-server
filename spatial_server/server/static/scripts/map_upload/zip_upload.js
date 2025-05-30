function uploadZip(serverAddress, progressBar, submitButton, options = null) {
    var name = document.getElementById('name').value;
    var zipFile = document.getElementById('zip').files[0];

    if (!name || !zipFile) {
        alert('Please name, and select a zip file.');
        return;
    }

    const formData = new FormData();
    formData.append('name', name);
    formData.append('zip', zipFile);

    // Add any additional options to the form data
    if (options) {
        for (let key in options) {
            formData.append(key, options[key]);
        }
    }

    // Make the progress bar visible and set its width to 0% 
    progressBar.style.visibility = 'visible';
    progressBar.style.width = '0%';

    const xhr = new XMLHttpRequest();
    xhr.open('POST', serverAddress, true);

    xhr.upload.onprogress = function (event) {
        if (event.lengthComputable) {
            const percentComplete = (event.loaded / event.total) * 100;
            progressBar.style.width = percentComplete + '%';
            progressBar.innerText = Math.round(percentComplete) + '%';
        }
    };

    xhr.onload = function () {
        if (xhr.status === 200) {
            alert('Uploded zip file successfully to ' + serverAddress);

            progressBar.style.width = '100%';
            submitButton.disabled = true;
        } else {
            alert('Failed to upload zip to the server. Server response: ' + xhr.statusText);
            submitButton.disabled = true;
        }
    };

    xhr.send(formData);
}
