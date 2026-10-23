import { useSyncExternalStore } from "react";

export type Palette = "botanical" | "herbarium" | "mineral";
export type Appearance = "system" | "light" | "dark";
export interface ThemeSnapshot {
  palette: Palette;
  appearance: Appearance;
  effectiveAppearance: "light" | "dark";
  persistent: boolean;
}
interface AppearanceStore {
  getSnapshot: () => ThemeSnapshot;
  subscribe: (listener: () => void) => () => void;
  setPalette: (palette: Palette) => void;
  setAppearance: (appearance: Appearance) => void;
  cycleAppearance: () => void;
  dispose: () => void;
}
declare global {
  interface Window {
    florabaseAppearance: AppearanceStore;
  }
}

export const paletteLabels: Record<Palette, string> = {
  botanical: "Botanical",
  herbarium: "Herbarium",
  mineral: "Mineral",
};
export const appearanceLabels: Record<Appearance, string> = {
  system: "System",
  light: "Light",
  dark: "Dark",
};

export function useAppearance() {
  const store = window.florabaseAppearance;
  return {
    ...useSyncExternalStore(store.subscribe, store.getSnapshot),
    setPalette: store.setPalette,
    setAppearance: store.setAppearance,
    cycleAppearance: store.cycleAppearance,
  };
}
