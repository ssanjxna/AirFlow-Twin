// 1. Setup the 3D Scene, Camera, and Renderer
const container = document.getElementById('3d-container');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0f172a); // Dark slate background
scene.fog = new THREE.Fog(0x0f172a, 50, 200);

const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
camera.position.set(40, 30, 40); // Position camera for a good overview

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(container.clientWidth, container.clientHeight);
renderer.shadowMap.enabled = true;
container.appendChild(renderer.domElement);

// 2. Add Camera Controls (Orbit around the airport)
const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.target.set(0, 0, 0);

// 3. Add Lighting
const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
scene.add(ambientLight);

const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(50, 50, 50);
dirLight.castShadow = true;
scene.add(dirLight);

// 4. Build the Airport Environment from Scratch

// A. The Ground (Tarmac)
const groundGeo = new THREE.PlaneGeometry(200, 200);
const groundMat = new THREE.MeshStandardMaterial({ color: 0x1e293b });
const ground = new THREE.Mesh(groundGeo, groundMat);
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

// B. The Runway
const runwayGeo = new THREE.PlaneGeometry(10, 150);
const runwayMat = new THREE.MeshStandardMaterial({ color: 0x334155 });
const runway = new THREE.Mesh(runwayGeo, runwayMat);
runway.rotation.x = -Math.PI / 2;
runway.position.y = 0.01;
scene.add(runway);

// Runway markings (simple white lines)
const lineGeo = new THREE.PlaneGeometry(0.5, 10);
const lineMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
for(let i = -70; i < 70; i += 15) {
    const line = new THREE.Mesh(lineGeo, lineMat);
    line.rotation.x = -Math.PI / 2;
    line.position.set(0, 0.02, i);
    scene.add(line);
}

// C. The Terminal Building
const terminalGeo = new THREE.BoxGeometry(40, 8, 10);
const terminalMat = new THREE.MeshStandardMaterial({ color: 0x475569 });
const terminal = new THREE.Mesh(terminalGeo, terminalMat);
terminal.position.set(25, 4, 0);
terminal.castShadow = true;
terminal.receiveShadow = true;
scene.add(terminal);

// Terminal Roof (Glass look)
const roofGeo = new THREE.BoxGeometry(42, 1, 12);
const roofMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, transparent: true, opacity: 0.8 });
const roof = new THREE.Mesh(roofGeo, roofMat);
roof.position.set(25, 8.5, 0);
scene.add(roof);

// 5. Function to create 3D Airplanes based on data
const planeMeshes = [];

function createAirplane(flightData, index) {
    // Determine color based on AI risk score
    let color = 0x22c55e; // Green
    if (flightData.risk > 70) color = 0xef4444; // Red
    else if (flightData.risk > 40) color = 0xf97316; // Orange

    const planeGroup = new THREE.Group();

    // Fuselage
    const bodyGeo = new THREE.CylinderGeometry(0.8, 0.8, 6, 16);
    const bodyMat = new THREE.MeshStandardMaterial({ color: color });
    const body = new THREE.Mesh(bodyGeo, bodyMat);
    body.rotation.x = Math.PI / 2;
    body.castShadow = true;
    planeGroup.add(body);

    // Wings
    const wingGeo = new THREE.BoxGeometry(8, 0.2, 2);
    const wingMat = new THREE.MeshStandardMaterial({ color: 0xffffff });
    const wings = new THREE.Mesh(wingGeo, wingMat);
    wings.castShadow = true;
    planeGroup.add(wings);

    // Position the plane along the terminal
    const startX = 15;
    const startZ = -20;
    const spacing = 8;
    
    planeGroup.position.set(startX, 1, startZ + (index * spacing));
    planeGroup.userData = flightData; // Store flight data for clicking later
    
    scene.add(planeGroup);
    planeMeshes.push(planeGroup);
}

// 6. Fetch data from Flask backend and render
async function loadAirportData() {
    try {
        const response = await fetch('/api/flights');
        const data = await response.json();
        
        const flightList = document.getElementById('flight-list');
        flightList.innerHTML = '';
        let highRiskCount = 0;

        data.flights.forEach((flight, index) => {
            // Create 3D plane
            createAirplane(flight, index);

            // Update UI list
            let riskColor = flight.risk > 70 ? 'text-red-400' : (flight.risk > 40 ? 'text-orange-400' : 'text-green-400');
            if (flight.risk > 70) highRiskCount++;

            flightList.innerHTML += `
                <div class="flex justify-between items-center bg-slate-900 p-3 rounded border border-slate-700 cursor-pointer hover:bg-slate-700">
                    <div>
                        <span class="font-bold text-sm">${flight.id}</span>
                        <span class="text-xs text-slate-400 ml-2">${flight.status}</span>
                    </div>
                    <span class="text-xs font-bold ${riskColor}">${flight.risk}%</span>
                </div>
            `;
        });

        document.getElementById('high-risk-count').textContent = highRiskCount;

    } catch (error) {
        console.error('Error loading airport data:', error);
    }
}

// 7. Animation Loop
function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

// Initialize
loadAirportData();
animate();

// Handle window resize
window.addEventListener('resize', () => {
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
});