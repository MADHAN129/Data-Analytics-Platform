import { create } from "zustand"

export type ThemeMode = "light" | "dark" | "system"
export type AccentColor = "blue" | "emerald" | "violet" | "rose" | "amber"

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

const ACCENT_COLORS: Record<AccentColor, { primary: string; ring: string }> = {
  blue: { primary: "221.2 83.2% 53.3%", ring: "221.2 83.2% 53.3%" },
  emerald: { primary: "142.1 76.2% 36.3%", ring: "142.1 76.2% 36.3%" },
  violet: { primary: "262.1 83.3% 57.8%", ring: "262.1 83.3% 57.8%" },
  rose: { primary: "346.8 77.2% 49.8%", ring: "346.8 77.2% 49.8%" },
  amber: { primary: "24.6 95% 53.1%", ring: "24.6 95% 53.1%" },
}

function applyTheme(mode: ThemeMode, accent: AccentColor) {
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

  // Apply accent color
  const colors = ACCENT_COLORS[accent] || ACCENT_COLORS.blue
  root.style.setProperty("--primary", colors.primary)
  root.style.setProperty("--ring", colors.ring)
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
    applyTheme(mode, get().accent)
  },

  setAccent: (accent) => {
    localStorage.setItem("theme_accent", accent)
    set({ accent })
    applyTheme(get().mode, accent)
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

    const savedMode = (localStorage.getItem("theme_mode") as ThemeMode) || "light"
    const savedAccent = (localStorage.getItem("theme_accent") as AccentColor) || "blue"
    const savedCompact = localStorage.getItem("theme_compact") === "true"
    const savedAnimations = localStorage.getItem("theme_animations") !== "false"
    const savedHighContrast = localStorage.getItem("theme_high_contrast") === "true"

    set({
      mode: savedMode,
      accent: savedAccent,
      compactMode: savedCompact,
      animations: savedAnimations,
      highContrast: savedHighContrast,
    })

    applyTheme(savedMode, savedAccent)

    // Listen for OS theme changes if in system mode
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
      if (get().mode === "system") {
        applyTheme("system", get().accent)
      }
    })
  },
}))
