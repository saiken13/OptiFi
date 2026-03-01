import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "@/types";

interface AppState {
  user: User | null;
  sidebarOpen: boolean;
  selectedGoalId: string | null;
  theme: "light" | "dark";
  setUser: (user: User | null) => void;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setSelectedGoalId: (id: string | null) => void;
  setTheme: (theme: "light" | "dark") => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      user: null,
      sidebarOpen: true,
      selectedGoalId: null,
      theme: "dark",
      setUser: (user) => set({ user }),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      setSelectedGoalId: (id) => set({ selectedGoalId: id }),
      setTheme: (theme) => set({ theme }),
    }),
    { name: "optifi-app-store", partialize: (s) => ({ theme: s.theme }) }
  )
);
