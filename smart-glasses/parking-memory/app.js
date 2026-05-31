const viewIdle = document.getElementById('view-idle');
const viewSaved = document.getElementById('view-saved');
const viewNavigating = document.getElementById('view-navigating');
const btnSave = document.getElementById('btn-save');
const btnNavigate = document.getElementById('btn-navigate');
const btnClear = document.getElementById('btn-clear');
const btnStopNav = document.getElementById('btn-stop-nav');
const savedAddress = document.getElementById('saved-address');
const savedTime = document.getElementById('saved-time');
const distanceValue = document.getElementById('distance-value');
const distanceUnit = document.getElementById('distance-unit');
const navDistanceValue = document.getElementById('nav-distance-value');
const navDistanceUnit = document.getElementById('nav-distance-unit');
const compassArrow = document.getElementById('compass-arrow');
const navCompassArrow = document.getElementById('nav-compass-arrow');
const navCompassLabel = document.getElementById('nav-compass-label');
const gpsIndicator = document.getElementById('gps-indicator');
const timeEl = document.getElementById('time');
const toast = document.getElementById('toast');
const arrivalBanner = document.getElementById('arrival-banner');

const STORAGE_KEY = 'parking_memory_location';

let savedLocation = null;
let watchId = null;
let currentPosition = null;
let deviceHeading = 0;
let navInterval = null;

// ── Clock ──

function updateClock() {
  const now = new Date();
  timeEl.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

setInterval(updateClock, 1000);
updateClock();

// ── GPS ──

function startGPS() {
  if (!navigator.geolocation) {
    showToast('GPS not available');
    return;
  }
  watchId = navigator.geolocation.watchPosition(
    (pos) => {
      currentPosition = { lat: pos.coords.latitude, lng: pos.coords.longitude };
      gpsIndicator.classList.add('active');
      if (savedLocation) updateNavigation();
    },
    () => {
      gpsIndicator.classList.remove('active');
    },
    { enableHighAccuracy: true, maximumAge: 3000 }
  );
}

// ── Compass (device orientation) ──

function startCompass() {
  if (window.DeviceOrientationEvent) {
    if (typeof DeviceOrientationEvent.requestPermission === 'function') {
      // iOS 13+
      DeviceOrientationEvent.requestPermission().then(state => {
        if (state === 'granted') listenOrientation();
      }).catch(() => {});
    } else {
      listenOrientation();
    }
  }
}

function listenOrientation() {
  window.addEventListener('deviceorientationabsolute', handleOrientation, true);
  window.addEventListener('deviceorientation', handleOrientation, true);
}

function handleOrientation(e) {
  if (e.alpha !== null) {
    deviceHeading = e.webkitCompassHeading || (360 - e.alpha);
  }
}

// ── Geocoding (reverse) ──

async function reverseGeocode(lat, lng) {
  try {
    const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18`;
    const res = await fetch(url, { headers: { 'Accept-Language': 'en' } });
    const data = await res.json();
    const a = data.address;
    if (!a) return `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
    const parts = [
      a.house_number,
      a.road || a.pedestrian,
      a.suburb || a.neighbourhood || a.city_district,
      a.city || a.town || a.village
    ].filter(Boolean);
    return parts.join(', ') || `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
  } catch {
    return `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
  }
}

// ── Haversine distance ──

function haversine(lat1, lng1, lat2, lng2) {
  const R = 6371000;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLng = (lng2 - lng1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// Bearing from current to target in degrees (0 = north)
function bearing(lat1, lng1, lat2, lng2) {
  const dLng = (lng2 - lng1) * Math.PI / 180;
  const y = Math.sin(dLng) * Math.cos(lat2 * Math.PI / 180);
  const x = Math.cos(lat1 * Math.PI / 180) * Math.sin(lat2 * Math.PI / 180) -
    Math.sin(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.cos(dLng);
  return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
}

// ── Navigation update ──

function updateNavigation() {
  if (!currentPosition || !savedLocation) return;

  const dist = haversine(
    currentPosition.lat, currentPosition.lng,
    savedLocation.lat, savedLocation.lng
  );

  const displayDist = dist < 1000
    ? { value: Math.round(dist), unit: 'm' }
    : { value: (dist / 1000).toFixed(1), unit: 'km' };

  distanceValue.textContent = displayDist.value;
  distanceUnit.textContent = displayDist.unit;
  navDistanceValue.textContent = displayDist.value;
  navDistanceUnit.textContent = displayDist.unit;

  const bear = bearing(
    currentPosition.lat, currentPosition.lng,
    savedLocation.lat, savedLocation.lng
  );

  // Rotate arrow relative to device heading
  const relBearing = (bear - deviceHeading + 360) % 360;
  compassArrow.style.transform = `rotate(${relBearing}deg)`;
  navCompassArrow.style.transform = `rotate(${relBearing}deg)`;

  // Cardinal label
  const cardinals = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  navCompassLabel.textContent = cardinals[Math.round(bear / 45) % 8];

  if (dist < 10) {
    arrivalBanner.classList.remove('hidden');
  }
}

// ── Save location ──

btnSave.addEventListener('click', async () => {
  if (!currentPosition) {
    // Use a mock position for demo if GPS unavailable
    currentPosition = { lat: 40.7484, lng: -73.9856 };
  }

  savedLocation = { ...currentPosition, timestamp: Date.now() };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(savedLocation));

  savedAddress.textContent = 'Looking up address…';
  const addr = await reverseGeocode(savedLocation.lat, savedLocation.lng);
  savedAddress.textContent = addr;

  const parkedAt = new Date(savedLocation.timestamp);
  savedTime.textContent = 'Parked at ' + parkedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  showView('saved');
  showToast('Location saved');
  updateNavigation();
});

// ── Navigate ──

btnNavigate.addEventListener('click', () => {
  showView('navigating');
  arrivalBanner.classList.add('hidden');
  startCompass();
  navInterval = setInterval(updateNavigation, 2000);
});

btnStopNav.addEventListener('click', () => {
  clearInterval(navInterval);
  showView('saved');
});

// ── Clear ──

btnClear.addEventListener('click', () => {
  savedLocation = null;
  localStorage.removeItem(STORAGE_KEY);
  clearInterval(navInterval);
  showView('idle');
  showToast('Location cleared');
});

// ── Views ──

function showView(name) {
  [viewIdle, viewSaved, viewNavigating].forEach(v => v.classList.remove('active'));
  document.getElementById('view-' + name).classList.add('active');
}

// ── Toast ──

let toastTimer;

function showToast(msg) {
  toast.textContent = msg;
  toast.classList.remove('hidden');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.add('hidden'), 2500);
}

// ── Init ──

function init() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) {
    savedLocation = JSON.parse(stored);
    const parkedAt = new Date(savedLocation.timestamp);
    savedTime.textContent = 'Parked at ' + parkedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    savedAddress.textContent = 'Restoring address…';
    reverseGeocode(savedLocation.lat, savedLocation.lng).then(addr => {
      savedAddress.textContent = addr;
    });
    showView('saved');
  } else {
    showView('idle');
  }
  startGPS();
}

init();
