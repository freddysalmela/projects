import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, SafeAreaView,
  StatusBar, ScrollView, Animated, Platform, Keyboard, Alert,
} from 'react-native';
import * as Speech from 'expo-speech';
import AsyncStorage from '@react-native-async-storage/async-storage';

const SCRIPTS_KEY = 'teleprompter_scripts_v1';

const DEFAULT_SCRIPT = {
  id: 'default',
  title: 'Sample Script',
  body: `Welcome everyone. Thank you for joining us today.

I want to talk about three key topics. First, the current state of our industry. Second, the challenges we face moving forward. And third, the opportunities ahead.

The landscape has shifted dramatically. New technologies are reshaping how we work, communicate, and create value.

The teams that adapt quickly will be the ones that thrive. Our goal is to embrace change together.

Thank you.`,
  updatedAt: Date.now(),
};

function splitSentences(text) {
  return text.match(/[^.!?\n]+[.!?\n]+/g)?.map(s => s.trim()).filter(Boolean) || [text];
}

export default function App() {
  const [screen, setScreen] = useState('list'); // list | edit | present | audioCue
  const [scripts, setScripts] = useState([DEFAULT_SCRIPT]);
  const [activeScript, setActiveScript] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [editBody, setEditBody] = useState('');
  const [editId, setEditId] = useState(null);

  // Presentation state
  const [isPlaying, setIsPlaying] = useState(false);
  const [scrollSpeed, setScrollSpeed] = useState(40);
  const [fontSize, setFontSize] = useState(28);
  const [progress, setProgress] = useState(0);

  // Audio cue mode (for Meta glasses with no display fallback)
  const [cueIndex, setCueIndex] = useState(0);
  const [sentences, setSentences] = useState([]);

  const scrollRef = useRef(null);
  const scrollPos = useRef(0);
  const animFrame = useRef(null);
  const lastTs = useRef(null);
  const scrollHeight = useRef(0);

  useEffect(() => {
    loadScripts();
  }, []);

  async function loadScripts() {
    const raw = await AsyncStorage.getItem(SCRIPTS_KEY);
    if (raw) setScripts(JSON.parse(raw));
  }

  async function saveScripts(updated) {
    setScripts(updated);
    await AsyncStorage.setItem(SCRIPTS_KEY, JSON.stringify(updated));
  }

  function openNewScript() {
    setEditId(null);
    setEditTitle('');
    setEditBody('');
    setScreen('edit');
  }

  function openEditScript(script) {
    setEditId(script.id);
    setEditTitle(script.title);
    setEditBody(script.body);
    setScreen('edit');
  }

  async function handleSaveScript() {
    if (!editTitle.trim()) { Alert.alert('Title required'); return; }
    const script = {
      id: editId || Date.now().toString(),
      title: editTitle.trim(),
      body: editBody,
      updatedAt: Date.now(),
    };
    const updated = editId
      ? scripts.map(s => (s.id === editId ? script : s))
      : [script, ...scripts];
    await saveScripts(updated);
    setScreen('list');
  }

  async function handleDeleteScript(id) {
    Alert.alert('Delete script?', '', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete', style: 'destructive',
        onPress: async () => {
          await saveScripts(scripts.filter(s => s.id !== id));
        },
      },
    ]);
  }

  function startPresenting(script) {
    setActiveScript(script);
    setIsPlaying(true);
    scrollPos.current = 0;
    setProgress(0);
    setScreen('present');
  }

  function startAudioCue(script) {
    const sents = splitSentences(script.body);
    setSentences(sents);
    setCueIndex(0);
    setActiveScript(script);
    setScreen('audioCue');
    Speech.speak(sents[0], { rate: 0.85, pitch: 0.95 });
  }

  // Scroll loop
  const scrollLoop = useCallback((ts) => {
    if (!isPlaying) { lastTs.current = null; return; }
    if (lastTs.current !== null) {
      const delta = (ts - lastTs.current) / 1000;
      scrollPos.current += scrollSpeed * delta;
      const max = scrollHeight.current;
      if (scrollPos.current >= max) {
        scrollPos.current = max;
        setIsPlaying(false);
        cancelAnimationFrame(animFrame.current);
        return;
      }
      scrollRef.current?.scrollTo({ y: scrollPos.current, animated: false });
      setProgress(max > 0 ? Math.round((scrollPos.current / max) * 100) : 0);
    }
    lastTs.current = ts;
    animFrame.current = requestAnimationFrame(scrollLoop);
  }, [isPlaying, scrollSpeed]);

  useEffect(() => {
    if (screen !== 'present') return;
    if (isPlaying) {
      animFrame.current = requestAnimationFrame(scrollLoop);
    } else {
      cancelAnimationFrame(animFrame.current);
      lastTs.current = null;
    }
    return () => cancelAnimationFrame(animFrame.current);
  }, [isPlaying, screen, scrollLoop]);

  function exitPresent() {
    setIsPlaying(false);
    cancelAnimationFrame(animFrame.current);
    Speech.stop();
    setScreen('list');
  }

  // Audio cue controls
  function cueNext() {
    if (cueIndex >= sentences.length - 1) return;
    const next = cueIndex + 1;
    setCueIndex(next);
    Speech.speak(sentences[next], { rate: 0.85, pitch: 0.95 });
  }

  function cuePrev() {
    if (cueIndex <= 0) return;
    const prev = cueIndex - 1;
    setCueIndex(prev);
    Speech.speak(sentences[prev], { rate: 0.85, pitch: 0.95 });
  }

  function cueRepeat() {
    Speech.speak(sentences[cueIndex], { rate: 0.85, pitch: 0.95 });
  }

  const timeLabel = (ts) => {
    const d = new Date(ts);
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  return (
    <SafeAreaView style={s.safe}>
      <StatusBar barStyle="light-content" backgroundColor="#0a0a0f" />

      {/* ── Script List ── */}
      {screen === 'list' && (
        <View style={s.flex}>
          <View style={s.bar}>
            <Text style={s.barTitle}>TELEPROMPTER</Text>
            <TouchableOpacity style={s.newBtn} onPress={openNewScript}>
              <Text style={s.newBtnTxt}>+ NEW</Text>
            </TouchableOpacity>
          </View>
          <ScrollView style={s.listScroll}>
            {scripts.map(script => (
              <View key={script.id} style={s.scriptCard}>
                <View style={s.scriptCardTop}>
                  <Text style={s.scriptTitle}>{script.title}</Text>
                  <Text style={s.scriptMeta}>{timeLabel(script.updatedAt)}</Text>
                </View>
                <Text style={s.scriptPreview} numberOfLines={2}>{script.body}</Text>
                <View style={s.scriptActions}>
                  <TouchableOpacity style={s.actionBtn} onPress={() => startPresenting(script)}>
                    <Text style={s.actionBtnTxt}>▶ PRESENT</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={[s.actionBtn, s.actionBtnAlt]} onPress={() => startAudioCue(script)}>
                    <Text style={s.actionBtnAltTxt}>🕶 GLASSES CUE</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={s.iconBtn} onPress={() => openEditScript(script)}>
                    <Text style={s.iconBtnTxt}>✎</Text>
                  </TouchableOpacity>
                  {script.id !== 'default' && (
                    <TouchableOpacity style={s.iconBtn} onPress={() => handleDeleteScript(script.id)}>
                      <Text style={[s.iconBtnTxt, { color: '#804040' }]}>✕</Text>
                    </TouchableOpacity>
                  )}
                </View>
              </View>
            ))}
          </ScrollView>
          <View style={s.listFooter}>
            <Text style={s.footerNote}>🕶 Glasses Cue whispers lines through your Ray-Ban speakers</Text>
          </View>
        </View>
      )}

      {/* ── Edit Script ── */}
      {screen === 'edit' && (
        <View style={s.flex}>
          <View style={s.bar}>
            <TouchableOpacity onPress={() => setScreen('list')}>
              <Text style={s.backBtn}>← BACK</Text>
            </TouchableOpacity>
            <Text style={s.barTitle}>{editId ? 'EDIT SCRIPT' : 'NEW SCRIPT'}</Text>
            <TouchableOpacity onPress={handleSaveScript}>
              <Text style={s.saveBtn}>SAVE</Text>
            </TouchableOpacity>
          </View>
          <View style={s.editBody}>
            <TextInput
              style={s.titleInput}
              placeholder="Script title"
              placeholderTextColor="#303050"
              value={editTitle}
              onChangeText={setEditTitle}
              returnKeyType="next"
            />
            <TextInput
              style={s.bodyInput}
              placeholder="Paste or type your script here…"
              placeholderTextColor="#303050"
              value={editBody}
              onChangeText={setEditBody}
              multiline
              textAlignVertical="top"
            />
          </View>
        </View>
      )}

      {/* ── Present (phone display scrolling) ── */}
      {screen === 'present' && activeScript && (
        <View style={s.presentContainer}>
          <View style={s.presentStatus}>
            <Text style={s.presentProgress}>{progress}%</Text>
            <Text style={s.presentMode}>PRESENTING</Text>
            <TouchableOpacity onPress={exitPresent}>
              <Text style={s.exitBtn}>✕ EXIT</Text>
            </TouchableOpacity>
          </View>

          {/* Focus line */}
          <View pointerEvents="none" style={s.focusLine} />

          <ScrollView
            ref={scrollRef}
            style={s.presentScroll}
            scrollEnabled={false}
            onContentSizeChange={(_, h) => { scrollHeight.current = h - 600; }}
          >
            <View style={{ height: 300 }} />
            {activeScript.body.split(/\n\n+/).filter(p => p.trim()).map((para, i) => (
              <Text key={i} style={[s.presentText, { fontSize }]}>{para}</Text>
            ))}
            <View style={{ height: 300 }} />
          </ScrollView>

          <View style={s.presentControls}>
            <TouchableOpacity style={s.ctrlBtn} onPress={() => setScrollSpeed(Math.max(10, scrollSpeed - 10))}>
              <Text style={s.ctrlBtnTxt}>− SLOWER</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[s.ctrlBtn, s.ctrlBtnPrimary]} onPress={() => setIsPlaying(p => !p)}>
              <Text style={s.ctrlBtnPrimaryTxt}>{isPlaying ? '⏸ PAUSE' : '▶ PLAY'}</Text>
            </TouchableOpacity>
            <TouchableOpacity style={s.ctrlBtn} onPress={() => setScrollSpeed(Math.min(120, scrollSpeed + 10))}>
              <Text style={s.ctrlBtnTxt}>+ FASTER</Text>
            </TouchableOpacity>
          </View>
          <Text style={s.speedLabel}>Speed: {scrollSpeed}</Text>
        </View>
      )}

      {/* ── Audio Cue Mode (Ray-Ban glasses speakers) ── */}
      {screen === 'audioCue' && activeScript && (
        <View style={s.flex}>
          <View style={s.bar}>
            <TouchableOpacity onPress={() => { Speech.stop(); setScreen('list'); }}>
              <Text style={s.backBtn}>← BACK</Text>
            </TouchableOpacity>
            <Text style={s.barTitle}>GLASSES CUE</Text>
            <Text style={s.cueCounter}>{cueIndex + 1}/{sentences.length}</Text>
          </View>

          <View style={s.cueBody}>
            <View style={s.glassesIcon}>
              <Text style={s.glassesEmoji}>🕶</Text>
              <Text style={s.glassesLabel}>WHISPERING TO GLASSES</Text>
            </View>

            <View style={s.cueCard}>
              {cueIndex > 0 && (
                <Text style={s.cuePrev} numberOfLines={2}>{sentences[cueIndex - 1]}</Text>
              )}
              <Text style={s.cueCurrent}>{sentences[cueIndex]}</Text>
              {cueIndex < sentences.length - 1 && (
                <Text style={s.cueNext} numberOfLines={2}>{sentences[cueIndex + 1]}</Text>
              )}
            </View>

            <Text style={s.cueHint}>Tap NEXT when you've finished the current sentence</Text>

            <View style={s.cueControls}>
              <TouchableOpacity style={s.ctrlBtn} onPress={cuePrev} disabled={cueIndex === 0}>
                <Text style={[s.ctrlBtnTxt, cueIndex === 0 && { opacity: 0.3 }]}>← PREV</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[s.ctrlBtn, s.ctrlBtnPrimary]} onPress={cueNext}
                disabled={cueIndex >= sentences.length - 1}>
                <Text style={[s.ctrlBtnPrimaryTxt, cueIndex >= sentences.length - 1 && { opacity: 0.3 }]}>
                  NEXT →
                </Text>
              </TouchableOpacity>
            </View>
            <TouchableOpacity style={s.repeatBtn} onPress={cueRepeat}>
              <Text style={s.repeatBtnTxt}>↺ REPEAT</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}
    </SafeAreaView>
  );
}

const PURPLE = '#a0a0ff';
const PURPLED = '#5050a0';
const BG = '#0a0a0f';

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: BG },
  flex: { flex: 1 },

  bar: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 16, paddingVertical: 12,
    borderBottomWidth: 1, borderBottomColor: '#1a1a2a', backgroundColor: '#080810',
  },
  barTitle: { fontSize: 12, letterSpacing: 4, color: PURPLED, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  backBtn: { fontSize: 11, letterSpacing: 2, color: '#505080', fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  saveBtn: { fontSize: 11, letterSpacing: 2, color: PURPLE, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  newBtn: { borderWidth: 1, borderColor: PURPLED, borderRadius: 4, paddingHorizontal: 10, paddingVertical: 4 },
  newBtnTxt: { fontSize: 10, letterSpacing: 2, color: PURPLED, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },

  listScroll: { flex: 1, padding: 16 },
  scriptCard: {
    backgroundColor: '#0e0e1a', borderWidth: 1, borderColor: '#1e1e30',
    borderRadius: 8, padding: 14, marginBottom: 12,
  },
  scriptCardTop: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  scriptTitle: { fontSize: 15, color: PURPLE, flex: 1, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  scriptMeta: { fontSize: 10, color: '#404060', fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  scriptPreview: { fontSize: 12, color: '#404060', lineHeight: 18, marginBottom: 12, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  scriptActions: { flexDirection: 'row', gap: 8, alignItems: 'center' },
  actionBtn: {
    flex: 1, backgroundColor: '#141428', borderWidth: 1, borderColor: PURPLED,
    borderRadius: 5, paddingVertical: 8, alignItems: 'center',
  },
  actionBtnTxt: { fontSize: 10, letterSpacing: 2, color: PURPLED, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  actionBtnAlt: { backgroundColor: '#0e1428', borderColor: '#4060a0' },
  actionBtnAltTxt: { fontSize: 10, letterSpacing: 1, color: '#6080c0', fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  iconBtn: { padding: 8 },
  iconBtnTxt: { fontSize: 16, color: '#404060' },

  listFooter: { padding: 14, borderTopWidth: 1, borderTopColor: '#12121e' },
  footerNote: { fontSize: 11, color: '#303050', textAlign: 'center', fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },

  editBody: { flex: 1, padding: 16, gap: 12 },
  titleInput: {
    backgroundColor: '#0e0e1a', borderWidth: 1, borderColor: '#1e1e30', borderRadius: 6,
    color: PURPLE, fontSize: 16, padding: 12,
    fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }),
  },
  bodyInput: {
    flex: 1, backgroundColor: '#0a0a12', borderWidth: 1, borderColor: '#1a1a2a', borderRadius: 6,
    color: '#c0c0e0', fontSize: 14, lineHeight: 22, padding: 14,
    fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }),
  },

  presentContainer: { flex: 1, backgroundColor: '#000' },
  presentStatus: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    padding: 10, backgroundColor: '#08080f', borderBottomWidth: 1, borderBottomColor: '#12122a',
  },
  presentProgress: { fontSize: 11, color: PURPLED, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  presentMode: { fontSize: 10, letterSpacing: 3, color: PURPLED, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  exitBtn: { fontSize: 11, color: '#604040', fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  focusLine: { position: 'absolute', top: '50%', left: 0, right: 0, height: 2, backgroundColor: '#2020504d', zIndex: 10 },
  presentScroll: { flex: 1, paddingHorizontal: 28 },
  presentText: { color: '#d0d0f0', lineHeight: 48, marginBottom: 28, fontFamily: Platform.select({ ios: 'Georgia', default: 'serif' }) },
  presentControls: {
    flexDirection: 'row', gap: 10, padding: 12, backgroundColor: '#08080f',
    borderTopWidth: 1, borderTopColor: '#12122a',
  },
  speedLabel: { textAlign: 'center', color: '#303050', fontSize: 10, paddingBottom: 8, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  ctrlBtn: {
    flex: 1, borderWidth: 1, borderColor: '#1e1e30', borderRadius: 5,
    paddingVertical: 10, alignItems: 'center',
  },
  ctrlBtnTxt: { fontSize: 10, letterSpacing: 2, color: '#505070', fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  ctrlBtnPrimary: { backgroundColor: '#141428', borderColor: PURPLED },
  ctrlBtnPrimaryTxt: { fontSize: 11, letterSpacing: 2, color: PURPLE, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },

  cueBody: { flex: 1, padding: 20, alignItems: 'center', justifyContent: 'center', gap: 20 },
  glassesIcon: { alignItems: 'center', gap: 6 },
  glassesEmoji: { fontSize: 40 },
  glassesLabel: { fontSize: 9, letterSpacing: 3, color: PURPLED, fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  cueCard: {
    width: '100%', backgroundColor: '#0e0e1a', borderWidth: 1, borderColor: '#1e1e30',
    borderRadius: 8, padding: 16, gap: 10,
  },
  cuePrev: { fontSize: 13, color: '#252540', lineHeight: 20, fontFamily: Platform.select({ ios: 'Georgia', default: 'serif' }) },
  cueCurrent: { fontSize: 18, color: '#e0e0ff', lineHeight: 28, borderLeftWidth: 2, borderLeftColor: PURPLED, paddingLeft: 10, fontFamily: Platform.select({ ios: 'Georgia', default: 'serif' }) },
  cueNext: { fontSize: 13, color: '#353558', lineHeight: 20, fontFamily: Platform.select({ ios: 'Georgia', default: 'serif' }) },
  cueHint: { fontSize: 11, color: '#303050', textAlign: 'center', fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  cueCounter: { fontSize: 11, color: '#404060', fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
  cueControls: { flexDirection: 'row', gap: 12, width: '100%' },
  repeatBtn: {
    borderWidth: 1, borderColor: '#1e1e2e', borderRadius: 5,
    paddingVertical: 8, paddingHorizontal: 20, alignItems: 'center',
  },
  repeatBtnTxt: { fontSize: 10, letterSpacing: 2, color: '#404060', fontFamily: Platform.select({ ios: 'Courier', default: 'monospace' }) },
});
