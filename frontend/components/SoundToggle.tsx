"use client";

import { useEffect, useState } from "react";
import { Volume2, VolumeX } from "lucide-react";
import {
  getMuted,
  isUnlocked,
  playAmbientHum,
  playSound,
  setMuted,
  stopAmbientHum,
  unlockSounds,
} from "../utils/sfx";

const STORAGE_KEY = "anamnesis_sound_muted";

function readStoredMuted(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

function storeMuted(value: boolean) {
  try {
    window.localStorage.setItem(STORAGE_KEY, value ? "1" : "0");
  } catch {
    // Ignore storage errors (private mode, quota, ...).
  }
}

export default function SoundToggle() {
  const [muted, setMutedState] = useState(false);

  // Hydrate the stored preference after mount to avoid SSR mismatch.
  useEffect(() => {
    if (readStoredMuted()) {
      setMuted(true);
      setMutedState(true);
    } else {
      setMutedState(getMuted());
    }
  }, []);

  // Unlock audio on the first user gesture (browser autoplay policy), start
  // the ambient hum, and wire the global UI-tick sound on interactive clicks.
  useEffect(() => {
    const unlock = () => {
      unlockSounds();
      if (!getMuted()) playAmbientHum();
      window.removeEventListener("pointerdown", unlock);
      window.removeEventListener("keydown", unlock);
    };
    window.addEventListener("pointerdown", unlock);
    window.addEventListener("keydown", unlock);

    const onDocumentClick = (event: MouseEvent) => {
      const target = event.target instanceof Element ? event.target : null;
      if (!target || target.closest("[data-nosfx]")) return;
      if (target.closest("button, a, [role='button']")) playSound("tick");
    };
    document.addEventListener("click", onDocumentClick);

    return () => {
      window.removeEventListener("pointerdown", unlock);
      window.removeEventListener("keydown", unlock);
      document.removeEventListener("click", onDocumentClick);
    };
  }, []);

  const toggleMute = () => {
    const next = !getMuted();
    if (!isUnlocked()) unlockSounds(); // this click is a valid gesture
    setMuted(next);
    setMutedState(next);
    storeMuted(next);
    if (next) stopAmbientHum();
    else playAmbientHum();
  };

  return (
    <button
      type="button"
      onClick={toggleMute}
      aria-label={muted ? "Unmute sounds" : "Mute sounds"}
      className="flex items-center gap-1 rounded-lg bg-white/5 px-2 py-1 text-slate-400 hover:text-slate-200"
    >
      {muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
      <span className="text-xs">{muted ? "Unmute" : "Mute"}</span>
    </button>
  );
}
