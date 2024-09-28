// app/static/js/map.js

// Initialize the map
var map = L.map('map', {
    center: [40.730610, -73.935242],  // Default center (New York City)
    zoom: 12
});

// Add tile layer
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

// Default Pin Icon
var defaultPinIcon = L.icon({
    iconUrl: '/static/images/marker-icon.png',  // Ensure this path is correct
    iconSize: [60, 60],  // Standard Leaflet icon size
    iconAnchor: [12, 41],
    popupAnchor: [1, -34]
});

// Function to show the loading icon
function showLoadingIcon() {
    document.getElementById('loading-icon').style.display = 'block';
    document.getElementById('loading-bar').style.display = 'block'; // Updated to match 'loading-bar' ID
}

// Function to hide the loading icon
function hideLoadingIcon() {
    document.getElementById('loading-icon').style.display = 'none';
    document.getElementById('loading-bar').style.display = 'none';
    updateLoadingBar(0);  // Reset progress bar
}

// Variables to store marker and current location
var dropMarker = null;
var currentLat, currentLng;
var circleMarkers = []; // Store circle markers to manage them properly
var lastFetchedTowers = []; // Store fetched towers globally for filtering

// Handle click on the map to place a drop marker
map.on('click', function(e) {
    if (dropMarker) {
        map.removeLayer(dropMarker); // Remove the existing marker
    }

    // Create a new marker
    dropMarker = L.marker(e.latlng, {
        icon: defaultPinIcon
    }).addTo(map)
    .bindPopup("Drop Marker<br>Latitude: " + e.latlng.lat.toFixed(6) + "<br>Longitude: " + e.latlng.lng.toFixed(6))
    .openPopup(); // Open the popup immediately

    currentLat = e.latlng.lat; // Update current latitude
    currentLng = e.latlng.lng; // Update current longitude
});

// Display coordinates on mouse move
map.on('mousemove', function(e) {
    var coords = document.getElementById('coords');
    coords.innerHTML = "Latitude: " + e.latlng.lat.toFixed(6) + ", Longitude: " + e.latlng.lng.toFixed(6);
});

// Function to update loading bar
function updateLoadingBar(progress) {
    document.getElementById('loading-progress').style.width = progress + '%';
}

// Function to get the correct signal quality image URL based on signal quality
function getSignalQualityImage(signalQuality) {
    if (signalQuality <= 10) {
        return '/static/images/signal_low.png';
    } else if (signalQuality <= 30) {
        return '/static/images/signal_mid.png';
    } else if (signalQuality <= 70) {
        return '/static/images/signal_good.png';
    } else {
        return '/static/images/signal_great.png';
    }
}

// Function to get the closest LTE tower or the next closest tower
function getClosestLteSignal(towers) {
    // Find the closest LTE tower
    let closestLteTower = towers.find(tower => tower.type === 'LTE');

    // If no LTE towers are found, pick the next closest tower
    if (!closestLteTower) {
        closestLteTower = towers[0]; // Fallback to the closest available tower
    }

    // Get signal quality image for the popup
    const signalImageUrl = getSignalQualityImage(closestLteTower.signal_quality);

    // Return the image URL and signal quality
    return { signalImageUrl, signalQuality: closestLteTower.signal_quality };
}

// Function to update tower summary list with optional filtering and sorting by signal quality
function updateTowerSummary(towers) {
    const towerList = document.getElementById('tower-list');
    const filterValue = document.getElementById('tower-filter').value; // Get selected filter value
    towerList.innerHTML = ''; // Clear the previous tower data

    // Filter towers based on selected type or show all if "all" is selected
    const filteredTowers = filterValue === 'all'
        ? towers
        : towers.filter(tower => tower.type === filterValue);

    if (filteredTowers.length === 0) {
        towerList.innerHTML = '<li>No towers found for the selected type.</li>';
        return;
    }

    // Sort the filtered towers by signal quality in descending order (highest first)
    filteredTowers.sort((a, b) => b.signal_quality - a.signal_quality);

    filteredTowers.forEach(tower => {
        // Create list item for each tower
        const listItem = document.createElement('li');
        
        // Tower icon
        const iconImg = document.createElement('img');
        iconImg.classList.add('tower-icon');
        iconImg.src = getTowerIconUrl(tower.type);  // Get the correct icon based on tower type
        listItem.appendChild(iconImg);

        // Signal quality image
        const signalImg = document.createElement('img');
        signalImg.src = getSignalQualityImage(tower.signal_quality);
        signalImg.classList.add('signal-quality-icon');
        listItem.appendChild(signalImg);
        
        // Tower details
        const detailsDiv = document.createElement('div');
        detailsDiv.classList.add('tower-details');
        detailsDiv.innerHTML = `
            <p><span>Type:</span> ${tower.type}</p>
            <p><span>Range:</span> ${tower.range} meters</p>
            <p><span>Signal Quality:</span> ${tower.signal_quality.toFixed(2)}%</p>
            <p><span>Distance:</span> ${tower.distance.toFixed(2)} meters</p>
        `;
        listItem.appendChild(detailsDiv);

        // Append to the tower list
        towerList.appendChild(listItem);
    });
}

// Function to get the correct tower icon URL based on tower type
function getTowerIconUrl(towerType) {
    switch (towerType) {
        case 'CDMA': return '/static/images/cdma.png';
        case 'GSM': return '/static/images/gsm.png';
        case 'LTE': return '/static/images/lte.png';
        case 'UMTS': return '/static/images/umts.png';
        case 'NR': return '/static/images/nr.png';
        default: return '/static/images/marker-icon.png';
    }
}

// Event listener to update summary when filter changes
document.getElementById('tower-filter').addEventListener('change', function() {
    // Use last fetched towers for filtering
    updateTowerSummary(lastFetchedTowers);
});

// Move map by location (city, state, country)
document.getElementById('move-map-btn').addEventListener('click', function() {
    var locationInput = document.getElementById('location-input').value.trim();
    
    if (!locationInput) {
        alert('Please enter a location.');
        return;
    }
    
    showLoadingIcon();  // Show loading indicator

    fetch('/geocode-location', {  // Corrected endpoint
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ location: locationInput })
    })
    .then(response => response.json())
    .then(data => {
        hideLoadingIcon();  // Hide loading indicator
        if (data.lat && data.lon) {  // Adjusted to match backend response
            map.setView([data.lat, data.lon], 12); // Move map to the found coordinates
            
            // Optionally, add a marker at the new location
            if (dropMarker) {
                map.removeLayer(dropMarker);
            }
            dropMarker = L.marker([data.lat, data.lon], {
                icon: defaultPinIcon
            }).addTo(map)
              .bindPopup(`<b>${locationInput}</b><br>Latitude: ${data.lat.toFixed(6)}<br>Longitude: ${data.lon.toFixed(6)}`)
              .openPopup();
              
            currentLat = data.lat;
            currentLng = data.lon;
        } else {
            alert(data.error || 'Location not found.');
        }
    })
    .catch(err => {
        hideLoadingIcon();  // Hide loading indicator
        console.error('Error fetching location:', err);
        alert('An error occurred while fetching the location.');
    });
});

// Move map by coordinates
document.getElementById('move-map-coords-btn').addEventListener('click', function() {
    var latInput = parseFloat(document.getElementById('lat-input').value);
    var lngInput = parseFloat(document.getElementById('lon-input').value);
    
    if (!isNaN(latInput) && !isNaN(lngInput)) {
        map.setView([latInput, lngInput], 12); // Move map to the provided coordinates
    } else {
        alert('Please enter valid coordinates.');
    }
});

// Handle "Search Towers" button click
document.getElementById('search-towers-btn').addEventListener('click', function() {
    var carrier = document.getElementById('carrier-dropdown').value;

    if (!carrier) {
        alert('Please select a carrier before searching.');
        return;
    }

    if (currentLat && currentLng) {
        showLoadingIcon();  // Show loading GIF
        var startTime = Date.now(); // Start the timer
        var progress = 0;

        // Clear existing tower markers before adding new ones
        circleMarkers.forEach(circle => map.removeLayer(circle));
        circleMarkers = []; // Reset the array after removing layers

        // Update loading bar function
        function incrementLoadingBar() {
            if (progress < 100) {
                progress += 5; // Increase progress
                updateLoadingBar(progress);
                setTimeout(incrementLoadingBar, 100); // Update every 100ms
            }
        }

        incrementLoadingBar(); // Start the loading bar update

        fetch('/filter-towers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                lat: currentLat,
                lon: currentLng,
                carrier: carrier
            })
        })
        .then(response => response.json())
        .then(closestTowers => {
            console.log('Closest Towers:', closestTowers);

            // Store the fetched towers globally
            lastFetchedTowers = closestTowers;

            // Update tower summary list
            updateTowerSummary(closestTowers);

            // Remove previous markers and circles
            circleMarkers.forEach(circle => map.removeLayer(circle));
            circleMarkers = []; // Reset the markers array

            closestTowers.forEach(function(tower) {
                var towerIconUrl = getTowerIconUrl(tower.type);

                var customIcon = L.icon({
                    iconUrl: towerIconUrl,
                    iconSize: [40, 40],
                    iconAnchor: [20, 40],
                    popupAnchor: [0, -40]
                });

                var circle = L.circle([tower.lat, tower.lon], {
                    color: tower.color,
                    fillColor: tower.color,
                    fillOpacity: 0.1,
                    radius: tower.range
                }).addTo(map); // Add circle to the map

                var marker = L.marker([tower.lat, tower.lon], { icon: customIcon }).addTo(map)
                    .bindPopup(
                        "Type: " + tower.type +
                        "<br>Range: " + tower.range + "m" +
                        "<br>Distance: " + tower.distance.toFixed(2) + "m" +
                        "<br>Signal Quality: " + tower.signal_quality.toFixed(2) + "%"
                    )
                    .on('click', function() {
                        if (map.hasLayer(circle)) {
                            map.removeLayer(circle);
                        } else {
                            circle.addTo(map);
                        }
                    });

                circleMarkers.push(circle);
                circleMarkers.push(marker);
            });
        })
        .catch(err => console.error('Error:', err))
        .finally(() => {
            hideLoadingIcon();  // Hide loading GIF
            progress = 100; // Ensure the bar reaches 100%
            updateLoadingBar(progress);
            // Calculate and display runtime
            var endTime = Date.now();
            var runtime = ((endTime - startTime) / 1000).toFixed(2); // in seconds
            alert('Loading complete! Time taken: ' + runtime + ' seconds');
        });
    } else {
        alert('Please place a pin on the map first.');
    }
});

// Handle "Broad Area Search" button click
document.getElementById('broad-area-search-btn').addEventListener('click', function() {
    if (currentLat && currentLng) {
        showLoadingIcon();  // Show loading GIF
        var startTime = Date.now(); // Start the timer
        var progress = 0;

        // Clear existing tower markers
        circleMarkers.forEach(circle => map.removeLayer(circle));
        circleMarkers = [];

        // Update loading bar function
        function incrementLoadingBar() {
            if (progress < 100) {
                progress += 5; // Increase progress
                updateLoadingBar(progress);
                setTimeout(incrementLoadingBar, 100); // Update every 100ms
            }
        }

        incrementLoadingBar(); // Start the loading bar update

        fetch('/broad-area-search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                lat: currentLat,
                lon: currentLng
            })
        })
        .then(response => response.json())
        .then(allTowers => {
            console.log('All Towers:', allTowers);

            // Store the fetched towers globally
            lastFetchedTowers = allTowers;

            // Update tower summary list
            updateTowerSummary(allTowers);

            // Remove previous markers and circles
            circleMarkers.forEach(circle => map.removeLayer(circle));
            circleMarkers = []; // Reset the markers array

            allTowers.forEach(function(tower) {
                var towerIconUrl = getTowerIconUrl(tower.type);

                var customIcon = L.icon({
                    iconUrl: towerIconUrl,
                    iconSize: [40, 40],
                    iconAnchor: [20, 40],
                    popupAnchor: [0, -40]
                });

                var circle = L.circle([tower.lat, tower.lon], {
                    color: tower.color,
                    fillColor: tower.color,
                    fillOpacity: 0.1,
                    radius: tower.range
                });

                var marker = L.marker([tower.lat, tower.lon], { icon: customIcon }).addTo(map)
                    .bindPopup(
                        "Type: " + tower.type +
                        "<br>Range: " + tower.range + "m" +
                        "<br>Distance: " + tower.distance.toFixed(2) + "m" +
                        "<br>Signal Quality: " + tower.signal_quality.toFixed(2) + "%"
                    )
                    .on('click', function() {
                        if (map.hasLayer(circle)) {
                            map.removeLayer(circle);
                        } else {
                            circle.addTo(map);
                        }
                    });

                circleMarkers.push(circle);
                circleMarkers.push(marker);
            });
        })
        .catch(err => console.error('Error:', err))
        .finally(() => {
            hideLoadingIcon();  // Hide loading GIF
            progress = 100; // Ensure the bar reaches 100%
            updateLoadingBar(progress);
            // Calculate and display runtime
            var endTime = Date.now();
            var runtime = ((endTime - startTime) / 1000).toFixed(2); // in seconds
            alert('Loading complete! Time taken: ' + runtime + ' seconds');
        });
    } else {
        alert('Please place a pin on the map first.');
    }
});

// Handle "Use Current Location" button click
document.getElementById('use-current-location-btn').addEventListener('click', function() {
    // Check if Geolocation is supported
    if (navigator.geolocation) {
        showLoadingIcon();  // Show loading indicator

        navigator.geolocation.getCurrentPosition(
            function(position) {
                hideLoadingIcon();  // Hide loading indicator

                var lat = position.coords.latitude;
                var lon = position.coords.longitude;

                // Update current coordinates
                currentLat = lat;
                currentLng = lon;

                // Center the map on the current location
                map.setView([lat, lon], 14); // Zoom level can be adjusted as needed

                // Remove existing drop marker if any
                if (dropMarker) {
                    map.removeLayer(dropMarker);
                }

                // Add a new drop marker at the current location
                dropMarker = L.marker([lat, lon], {
                    icon: defaultPinIcon
                }).addTo(map)
                .bindPopup("Your Current Location<br>Latitude: " + lat.toFixed(6) + "<br>Longitude: " + lon.toFixed(6))
                .openPopup();
            },
            function(error) {
                hideLoadingIcon();  // Hide loading indicator

                // Handle different error cases
                switch(error.code) {
                    case error.PERMISSION_DENIED:
                        alert("User denied the request for Geolocation.");
                        break;
                    case error.POSITION_UNAVAILABLE:
                        alert("Location information is unavailable.");
                        break;
                    case error.TIMEOUT:
                        alert("The request to get user location timed out.");
                        break;
                    case error.UNKNOWN_ERROR:
                        alert("An unknown error occurred.");
                        break;
                }
            }
        );
    } else {
        alert("Geolocation is not supported by this browser.");
    }
});