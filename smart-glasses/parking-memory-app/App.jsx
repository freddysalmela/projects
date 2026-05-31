import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, SafeAreaView,
  StatusBar, Animated, Platform, Linking, Vibration, ScrollView,
} from 'react-native';
import * as Location from 'expo-location';
import * as Speech from 'expo-speech';
import { Magnetometer } from 'expo-sensors';
import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY = 'parking_memory_v1';
const HISTORY_KEY = 'parking_memory_history_v1';
const ARRIVAL_THRESHOLD = 15; // meters

function haversine(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function bearingTo(lat1, lon1, lat2, lon2) {
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const y = Math.sin(dLon) * Math.cos(lat2 * Math.PI / 180);
  const x =
    Math.cos(lat1 * Math.PI / 180) * Math.sin(lat2 * Math.PI / 180) -
    Math.sin(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.cos(dLon);
  return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
}

async function reverseGeocode(lat, lng) {
  try {
    const results = await Location.reverseGeocodeAsync({ latitude: lat, longitude: lng });
    if (results.length > 0) {
      const r = results[0];
      return [r.streetNumber, r.street, r.city].filter(Boolean).join(', ') ||
        `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
    }
  } catch {}
  return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
}

function formatDistance(meters) {
  if (meters >= 1000) return `${(meters / 1000).toFixed(1)} km`;
  return `${Math.round(meters)} m`;
}

function timeAgo(timestamp) {
  const mins = Math.round((Date.now() - timestamp) / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

export default function App() {
  const [screen, setScreen] = useState('idle');
  const [savedSpot, setSavedSpot] = useState(null);
  const [history, setHistory] = useState([]);
  const [currentPos, setCurrentPos] = useState(null);
  const [distance, setDistance] = useState(null);
  const [navBearing, setNavBearing] = useState(0);
  const [deviceHeading, setDeviceHeading] = useState(0);
  const [arrived, setArrived] = useState(false);
  const [gpsReady, setGpsReady] = useState(false);
  const [toast, setToast] = useState('');
  const [showHistory, setShowHistory] = useState(false);

  const locationSub = useRef(null);
  const magnetSub = useRef(null);
  const lastAnnouncedRef = useRef(Infinity);
  const toastTimer = useRef(null);
  const compassAnim = useRef(new Animated.Value(0)).current;
  const prevCompassVal = useRef(0);

  useEffect(() => {
    loadSavedSpot();
    startGPS();
    return () => {
      locationSub.current?.remove();
      magnetSub.current?.remove();
    };
  }, []);

  async function loadSavedSpot() {
    const [spotRaw, histRaw] = await Promise.all([
      AsyncStorage.getItem(STORAGE_KEY),
      AsyncStorage.getItem(HISTORY_KEY),
    ]);
    if (spotRaw) {
      setSavedSpot(JSON.parse(spotRaw));
      setScreen('saved');
    }
    if (histRaw) setHistory(JSON.parse(histRaw));
  }

  async function startGPS() {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') {
      showToast('Location permission required');
      return;
    }
    setGpsReady(true);
    locationSub.current = await Location.watchPositionAsync(
      { accuracy: Location.Accuracy.High, timeInterval: 3000, distanceInterval: 5 },
      (loc) => setCurrentPos({ lat: loc.coords.latitude, lng: loc.coords.longitude })
    );
  }

  // Recompute navigation whenever position, spot, or screen changes
  useEffect(() => {
    if (!currentPos || !savedSpot) return;

    const dist = haversine(currentPos.lat, currentPos.lng, savedSpot.lat, savedSpot.lng);
    const bear = bearingTo(currentPos.lat, currentPos.lng, savedSpot.lat, savedSpot.lng);
    setDistance(Math.round(dist));
    setNavBearing(bear);

    if (screen !== 'navigating') return;

    // Announce milestones
    for (const milestone of [500, 200, 100, 50, 20]) {
      if (lastAnnouncedRef.current > milestone && dist <= milestone) {
        Speech.speak(`${milestone} meters to your car`, { rate: 0.9 });
        lastAnnouncedRef.current = dist;
        break;
      }
    }

    if (dist <= ARRIVAL_THRESHOLD && !arrived) {
      setArrived(true);
      Speech.speak('You have arrived at your car', { rate: 0.9 });
      Vibration.vibrate([0, 200, 100, 200, 100, 400]);
    }
  }, [currentPos, savedSpot, screen]);

  // Compass: only subscribe while navigating
  useEffect(() => {
    if (screen !== 'navigating') {
      magnetSub.current?.remove();
      magnetSub.current = null;
      return;
    }
    Magnetometer.setUpdateInterval(300);
    magnetSub.current = Magnetometer.addListener(({ x, y }) => {
      let angle = Math.atan2(y, x) * (180 / Math.PI);
      if (angle < 0) angle += 360;
      setDeviceHeading(angle);
    });
    return () => {
      magnetSub.current?.remove();
      magnetSub.current = null;
    };
  }, [screen]);

  // Animate compass arrow
  useEffect(() => {
    const relBearing = (navBearing - deviceHeading + 360) % 360;
    // Avoid spinning the long way around
    let diff = relBearing - prevCompassVal.current;
    if (diff > 180) diff -= 360;
    if (diff < -180) diff += 360;
    const target = prevCompassVal.current + diff;
    prevCompassVal.current = target;
    Animated.spring(compassAnim, { toValue: target, useNativeDriver: true }).start();
  }, [navBearing, deviceHeading]);

  async function handleSaveParking() {
    if (!currentPos) {
      showToast('Waiting for GPS signal…');
      return;
    }
    const address = await reverseGeocode(currentPos.lat, currentPos.lng);
    const spot = { lat: currentPos.lat, lng: currentPos.lng, address, timestamp: Date.now() };

    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(spot));
    setSavedSpot(spot);

    // Add to history (keep last 10)
    const newHistory = [spot, ...history].slice(0, 10);
    setHistory(newHistory);
    await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(newHistory));

    setScreen('saved');
    Speech.speak(`Parking saved at ${address}`, { rate: 0.9 });
    showToast('Location saved');
    Vibration.vibrate(100);
  }

  function handleNavigate() {
    setArrived(false);
    lastAnnouncedRef.current = Infinity;
    setScreen('navigating');
    const dist = distance !== null ? formatDistance(distance) : '';
    Speech.speak(`Navigating to your car. ${dist} away.`, { rate: 0.9 });
  }

  async function handleClear() {
    await AsyncStorage.removeItem(STORAGE_KEY);
    setSavedSpot(null);
    setDistance(null);
    setScreen('idle');
    showToast('Location cleared');
  }

  function handleOpenMaps() {
    if (!savedSpot) return;
    const { lat, lng } = savedSpot;
    const url = Platform.OS === 'ios'
      ? `maps://?daddr=${lat},${lng}`
      : `geo:${lat},${lng}?q=${lat},${lng}`;
    Linking.openURL(url);
  }

  function showToast(msg) {
    setToast(msg);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(''), 2500);
  }

  const spin = compassAnim.interpolate({ inputRange: [-360, 360], outputRange: ['-360deg', '360deg'] });

  return (
    <SafeAreaView style={s.safe}>
      <StatusBar barStyle="light-content" backgroundColor="#050508" />

      {/* Status bar */}
      <View style={s.bar}>
        <View style={[s.gpsPill, gpsReady && s.gpsPillOn]}>
          <Text style={[s.gpsText, gpsReady && s.gpsTextOn]}>GPS</Text>
        </View>
        <Text style={s.appTitle}>PARKING MEMORY</Text>
        <TouchableOpacity onPress={() => setShowHistory(!showHistory)}>
          <Text style={s.histBtn}>{showHistory ? 'BACK' : 'HISTORY'}</Text>
        </TouchableOpacity>
      </View>

      {/* History overlay */}
      {showHistory ? (
        <ScrollView style={s.historyList}>
          {history.length === 0 && (
            <Text style={s.emptyHist}>No parking history yet</Text>
          )}
          {history.map((h, i) => (
            <View key={i} style={s.histItem}>
              <Text style={s.histAddr}>{h.address}</Text>
              <Text style={s.histTime}>{new Date(h.timestamp).toLocaleDateString()} · {timeAgo(h.timestamp)}</Text>
            </View>
          ))}
        </ScrollView>
      ) : (
        <View style={s.body}>

          {/* ── Idle ── */}
          {screen === 'idle' && (
            <View style={s.center}>
              <Text style={s.hint}>No parking location saved</Text>
              <TouchableOpacity style={s.primaryBtn} onPress={handleSaveParking}>
                <Text style={s.primaryBtnTxt}>SAVE PARKING LOCATION</Text>
              </TouchableOpacity>
              <Text style={s.subHint}>Tap when you leave your car</Text>
            </View>
          )}

          {/* ── Saved ── */}
          {screen === 'saved' && savedSpot && (
            <View style={s.center}>
              <View style={s.card}>
                <Text style={s.cardLabel}>PARKED</Text>
                <Text style={s.cardAddr}>{savedSpot.address}</Text>
                <Text style={s.cardMeta}>{timeAgo(savedSpot.timestamp)}</Text>
              </View>
              {distance !== null && (
                <Text style={s.distBadge}>{formatDistance(distance)} away</Text>
              )}
              <TouchableOpacity style={s.primaryBtn} onPress={handleNavigate}>
                <Text style={s.primaryBtnTxt}>NAVIGATE BACK</Text>
              </TouchableOpacity>
              <View style={s.row}>
                <TouchableOpacity style={s.secondaryBtn} onPress={handleOpenMaps}>
                  <Text style={s.secondaryBtnTxt}>OPEN IN MAPS</Text>
                </TouchableOpacity>
                <TouchableOpacity style={s.secondaryBtn} onPress={handleClear}>
                  <Text style={s.secondaryBtnTxt}>CLEAR</Text>
                </TouchableOpacity>
              </View>
            </View>
          )}

          {/* ── Navigating ── */}
          {screen === 'navigating' && (
            <View style={s.center}>
              <Text style={s.navLabel}>NAVIGATING TO CAR</Text>
              <View style={s.compassRing}>
                <Animated.Text style={[s.compassArrow, { transform: [{ rotate: spin }] }]}>
                  ▲
                </Animated.Text>
              </View>
              {distance !== null && (
                <View style={s.distBlock}>
                  <Text style={s.distBig}>
                    {distance >= 1000 ? (distance / 1000).toFixed(1) : distance}
                  </Text>
                  <Text style={s.distUnit}>{distance >= 1000 ? 'km' : 'm'}</Text>
                </View>
              )}
              {arrived && (
                <View style={s.arrivalBanner}>
                  <Text style={s.arrivalTxt}>YOU HAVE ARRIVED</Text>
                </View>
              )}
              <TouchableOpacity style={s.secondaryBtn} onPress={() => setScreen('saved')}>
                <Text style={s.secondaryBtnTxt}>STOP NAVIGATION</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      )}

      {toast !== '' && (
        <View style={s.toast}>
          <Text style={s.toastTxt}>{toast}</Text>
        </View>
      )}
    </SafeAreaView>
  );
}

const G = '#00e0a0';
const GD = '#00905a';
const BG = '#050508';

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: BG },

  bar: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 16, paddingVertical: 10,
    borderBottomWidth: 1, borderBottomColor: '#00402e', backgroundColor: '#050a08',
  },
  gpsPill: { borderWidth: 1, borderColor: '#003020', borderRadius: 3, paddingHorizontal: 7, paddingVertical: 2 },
  gpsPillOn: { borderColor: G },
  gpsText: { fontSize: 10, letterSpacing: 2, color: '#003020', fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  gpsTextOn: { color: G },
  appTitle: { fontSize: 12, letterSpacing: 4, color: GD, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  histBtn: { fontSize: 10, letterSpacing: 2, color: '#006050', fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },

  body: { flex: 1 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24, gap: 18 },

  hint: { fontSize: 14, color: '#006050', letterSpacing: 1, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  subHint: { fontSize: 11, color: '#004030', letterSpacing: 1, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },

  primaryBtn: {
    backgroundColor: '#081a14', borderWidth: 1, borderColor: '#00805a',
    borderRadius: 8, paddingVertical: 14, paddingHorizontal: 32,
    minWidth: 240, alignItems: 'center',
  },
  primaryBtnTxt: { color: G, fontSize: 12, letterSpacing: 3, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },

  secondaryBtn: {
    borderWidth: 1, borderColor: '#003020', borderRadius: 6,
    paddingVertical: 10, paddingHorizontal: 18, alignItems: 'center',
  },
  secondaryBtnTxt: { color: '#006050', fontSize: 11, letterSpacing: 2, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },

  row: { flexDirection: 'row', gap: 12 },

  card: {
    width: '100%', backgroundColor: '#050f0c', borderWidth: 1,
    borderColor: '#00402e', borderRadius: 8, padding: 16,
  },
  cardLabel: { fontSize: 9, letterSpacing: 3, color: GD, marginBottom: 6, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  cardAddr: { fontSize: 16, color: G, lineHeight: 24, marginBottom: 4, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  cardMeta: { fontSize: 11, color: '#006050', letterSpacing: 1, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },

  distBadge: { fontSize: 13, color: GD, letterSpacing: 2, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },

  navLabel: { fontSize: 10, letterSpacing: 4, color: GD, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },

  compassRing: {
    width: 150, height: 150, borderRadius: 75, borderWidth: 2, borderColor: '#00805a',
    alignItems: 'center', justifyContent: 'center',
    shadowColor: G, shadowOpacity: 0.2, shadowRadius: 24,
  },
  compassArrow: { fontSize: 52, color: G },

  distBlock: { alignItems: 'center', marginTop: 4 },
  distBig: { fontSize: 60, color: G, lineHeight: 68, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  distUnit: { fontSize: 14, color: GD, letterSpacing: 3, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },

  arrivalBanner: { borderWidth: 1, borderColor: G, borderRadius: 4, paddingHorizontal: 22, paddingVertical: 9 },
  arrivalTxt: { color: G, fontSize: 16, letterSpacing: 3, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },

  historyList: { flex: 1, padding: 16 },
  emptyHist: { color: '#006050', fontSize: 13, textAlign: 'center', marginTop: 40, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  histItem: { borderBottomWidth: 1, borderBottomColor: '#001a12', paddingVertical: 14 },
  histAddr: { color: GD, fontSize: 14, marginBottom: 3, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  histTime: { color: '#005040', fontSize: 11, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },

  toast: {
    position: 'absolute', bottom: 40, alignSelf: 'center',
    backgroundColor: '#081a14', borderWidth: 1, borderColor: '#00805a',
    borderRadius: 4, paddingHorizontal: 20, paddingVertical: 8,
  },
  toastTxt: { color: G, fontSize: 12, letterSpacing: 2, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
});
