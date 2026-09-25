import { create } from "zustand"

export type ThemeMode = "light" | "dark" | "system"
export type AccentColor = "blue"

interface ThemeState {
  mode: ThemeMode
  accent: AccentColor
  compactMode: boolean
  animations: boolean
  highContrast: boolean

  setMode: (mode: ThemeMode) => void
  setAccent: (accent: AccentColor) => void
  setCompactMode: (compact: boolean) => void
  setAnimations: (animations: boolean) => void
  setHighContrast: (highContrast: boolean) => void
  initTheme: () => void
}

function applyTheme(mode: ThemeMode) {
  if (typeof window === "undefined") return

  const root = document.documentElement
  const isDark =
    mode === "dark" ||
    (mode === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches)

  if (isDark) {
    root.classList.add("dark")
  } else {
    root.classList.remove("dark")
  }

  // Remove any legacy inline primary/ring overrides so pure corporate blue CSS variables apply cleanly
  root.style.removeProperty("--primary")
  root.style.removeProperty("--ring")
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  mode: "light",
  accent: "blue",
  compactMode: false,
  animations: true,
  highContrast: false,

  setMode: (mode) => {
    localStorage.setItem("theme_mode", mode)
    set({ mode })
    applyTheme(mode)
  },

  setAccent: (_accent) => {
    localStorage.setItem("theme_accent", "blue")
    set({ accent: "blue" })
    applyTheme(get().mode)
  },

  setCompactMode: (compactMode) => {
    localStorage.setItem("theme_compact", String(compactMode))
    set({ compactMode })
  },

  setAnimations: (animations) => {
    localStorage.setItem("theme_animations", String(animations))
    set({ animations })
  },

  setHighContrast: (highContrast) => {
    localStorage.setItem("theme_high_contrast", String(highContrast))
    set({ highContrast })
  },

  initTheme: () => {
    if (typeof window === "undefined") return

    // Clean up any legacy non-blue accents
    localStorage.removeItem("theme_accent")

    const savedMode = (localStorage.getItem("theme_mode") as ThemeMode) || "light"
    const savedCompact = localStorage.getItem("theme_compact") === "true"
    const savedAnimations = localStorage.getItem("theme_animations") !== "false"
    const savedHighContrast = localStorage.getItem("theme_high_contrast") === "true"

    set({
      mode: savedMode,
      accent: "blue",
      compactMode: savedCompact,
      animations: savedAnimations,
      highContrast: savedHighContrast,
    })

    applyTheme(savedMode)

    // Listen for OS theme changes if in system mode
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
      if (get().mode === "system") {
        applyTheme("system")
      }
    })
  },
}))
