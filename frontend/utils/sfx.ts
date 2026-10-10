type SoundName = "tick" | "whoosh" | "chime" | "hum";

type SoundBoard = Record<SoundName, HTMLAudioElement> | null;

/**
 * Sound assets live in frontend/public/sounds/ and are served at /sounds/*.
 *
 * To use your own audio, drop real files at these exact paths:
 *   /sounds/tick.mp3   - short UI click
 *   /sounds/whoosh.mp3 - tab / view transitions
 *   /sounds/chime.mp3  - report-ready notification
 *   /sounds/hum.mp3    - ambient background loop (seamless loop recommended)
 *
 * Each sound prefers the .mp3 and automatically falls back to the bundled
 * .wav when the mp3 is missing or unreadable.
 */
const SOUND_CANDIDATES: Record<SoundName, string[]> = {
  tick: ["/sounds/tick.mp3", "/sounds/tick.wav"],
  whoosh: ["/sounds/whoosh.mp3", "/sounds/whoosh.wav"],
  chime: ["/sounds/chime.mp3", "/sounds/chime.wav"],
  hum: ["/sounds/hum.mp3", "/sounds/hum.wav"],
};

const SOUND_VOLUMES: Record<SoundName, number> = {
  tick: 0.4,
  whoosh: 0.35,
  chime: 0.45,
  hum: 0.18,
};

let soundBoard: SoundBoard = null;
let muted = false;
let unlocked = false;

function createAudio(candidates: string[], volume: number): HTMLAudioElement {
  const audio = new Audio(candidates[0]);
  audio.preload = "auto";
  audio.volume = volume;
  audio.dataset.baseVolume = String(volume);
  if (candidates.length > 1) {
    let index = 0;
    const onError = () => {
      index += 1;
      if (index >= candidates.length) {
        audio.removeEventListener("error", onError);
        return;
      }
      audio.src = candidates[index];
      void audio.load();
    };
    audio.addEventListener("error", onError);
  }
  return audio;
}

export function getMuted() {
  return muted;
}

export function isUnlocked() {
  return unlocked;
}

export function setMuted(nextMuted: boolean) {
  muted = nextMuted;
  if (!soundBoard) return;
  Object.values(soundBoard).forEach((audio) => {
    audio.volume = muted ? 0 : Number(audio.dataset.baseVolume || "0.45");
  });
  if (muted) soundBoard.hum.pause();
}

export function toggleMuted() {
  setMuted(!muted);
  return muted;
}

export function unlockSounds() {
  if (unlocked && soundBoard) return;
  unlocked = true;
  if (!soundBoard) {
    soundBoard = {
      tick: createAudio(SOUND_CANDIDATES.tick, SOUND_VOLUMES.tick),
      whoosh: createAudio(SOUND_CANDIDATES.whoosh, SOUND_VOLUMES.whoosh),
      chime: createAudio(SOUND_CANDIDATES.chime, SOUND_VOLUMES.chime),
      hum: createAudio(SOUND_CANDIDATES.hum, SOUND_VOLUMES.hum),
    };
    soundBoard.hum.loop = true;
    if (muted) {
      Object.values(soundBoard).forEach((audio) => {
        audio.volume = 0;
      });
    }
  }
}

export function ensureSoundBoard() {
  if (!soundBoard) unlockSounds();
  return soundBoard;
}

export function playSound(name: SoundName, { force = false } = {}) {
  if (!unlocked) return;
  const board = ensureSoundBoard();
  if (!board) return;
  const audio = board[name];
  if (muted && !force) return;
  try {
    audio.currentTime = 0;
    void audio.play().catch(() => undefined);
  } catch {
    // Intentionally silent: audio can fail before a user gesture.
  }
}

export function playAmbientHum() {
  if (!unlocked || muted) return;
  const board = ensureSoundBoard();
  if (!board) return;
  const audio = board.hum;
  if (audio.paused) {
    audio.volume = Number(audio.dataset.baseVolume || "0.18");
    void audio.play().catch(() => undefined);
  }
}

export function stopAmbientHum() {
  if (!soundBoard) return;
  const hum = soundBoard.hum;
  hum.pause();
  hum.currentTime = 0;
}
