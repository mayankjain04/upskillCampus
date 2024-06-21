// Fetch latitude and longitude from script tag data attributes
const scriptTag = document.querySelector('script[src*="traffic.js"]');
const latitude = scriptTag.getAttribute('data-latitude');
const longitude = scriptTag.getAttribute('data-longitude');
const dataRadius = scriptTag.getAttribute('radius');

// Initialize the map
var map = L.map('map').setView([latitude, longitude], 13);

// Set up the OpenStreetMap layer
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
}).addTo(map);

// Add a circle to indicate the radius of the area
var radius = dataRadius; // 500 meters
L.circle([latitude, longitude], {
    color: 'blue',
    fillColor: '#blue',
    fillOpacity: 0.1,
    radius: radius
}).addTo(map);

// Add a marker for the user's location
L.marker([latitude, longitude]).addTo(map)
    .bindPopup('You are here')

// Fetch and display traffic data
fetch(`/traffic_data?latitude=${latitude}&longitude=${longitude}&radius=${radius}`)
    .then(response => response.json())
    .then(data => {
        // Access the traffic data from the 'Results' key
        const results = data.Results;
        if (results && results.length > 0) {
            const traffic_data = results[0];
            // Access the 'flows' key within the first element of 'Results'
            traffic_data.flows.forEach(flow => {
                var coordinates = flow.coordinates;
                var length = flow.length; // Optional: Use this for additional features
                var polyline = L.polyline(coordinates, { color: 'red' }).addTo(map);
                // Optional: Add length or other info as a tooltip or popup
                polyline.bindTooltip(`Length: ${length} meters`);
            });
            traffic_data.routeData.forEach(route => {
                // Add additional data beside the map
                var trafficInfo = document.getElementById('traffic-info');
                var info = document.createElement('div');
                const liveText = route.reliabilityFactor > 0.7 ? "LIVE" : "";
                info.classList.add('traffic-info-entry');
                let feedReliability = "";
                if (typeof route.reliabilityFactor === 'number') {
                    feedReliability = `
                    <p>Feed Reliability: <span class="text-success">${route.reliabilityFactor * 100}% <span id="live">${liveText}</span></span></p>
                    `;
                }
                info.innerHTML = `
                <p class="text-dark">Route Name: ${route.routeName}</p>
                <p>Route Length: ${route.routeLength} meters</p>
                <p>Status: <span class="text-success">${route.status}</span></p>
                <p>Jam Status: <span class="text-success">${route.jamStatus * 10}%</span></p>
                ${feedReliability}
                <hr>
            `;
                trafficInfo.appendChild(info);
            })
        }
    })
    .catch(error => console.error('Error fetching traffic data:', error));
