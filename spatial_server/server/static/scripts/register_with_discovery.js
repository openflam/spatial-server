function registerWithDiscovery() {
    const serverAddress = '/register_with_discovery/';
    
    const url = document.getElementById('url-prefix').textContent + document.getElementById('url').value;
    const latitute = document.getElementById('latitude').value;
    const longitute = document.getElementById('longitude').value;
    const resolution = document.getElementById('resolution').value;

    const formData = new FormData();
    formData.append('hostname', url);
    formData.append('latitude', latitute);
    formData.append('longitude', longitute);
    formData.append('resolution', resolution);

    fetch(serverAddress, {
        method: 'POST',
        body: formData,
    })
    .then(response => {
        if (response.ok) {
            alert('Registered successfully!');
        } else {
            alert('Failed to register: ' + response.statusText);
        }
    })
    .catch(error => {
        alert('Error registering: ' + error.message);
    });
}
