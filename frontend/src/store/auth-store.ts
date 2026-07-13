import { create } from "zustand"
import type { UserResponse } from "@/types/api"
import { api } from "@/lib/api-client"

interface AuthState {
  user: UserResponse | null
  isLoading: boolean
  isAuthenticated: boolean
  error: string | null

  setUser: (user: UserResponse | null) => void
  fetchUser: () => Promise<void>
  logout: () => Promise<void>
  clearError: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,
  isAuthenticated: false,
  error: null,

  setUser: (user) =>
    set({
      user,
      isAuthenticated: !!user,
      isLoading: false,
    }),

  fetchUser: async () => {
    try {
      set({ isLoading: true, error: null })
      const user = await api.getCurrentUser()
      set({ user, isAuthenticated: true, isLoading: false })
    } catch (err: unknown) {
      api.clearTokens()
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: err instanceof Error ? err.message : "Authentication failed",
      })
    }
  },

  logout: async () => {
    try {
      await api.logout()
    } catch {
      // Ignore logout errors
    }
    api.clearTokens()
    set({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    })
  },

  clearError: () => set({ error: null }),
}))
