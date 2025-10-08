import { create } from 'zustand';
import { User, Orchard } from '../types';
import { getUser, getMyOrchards } from '../services/apiClient';

const FIFTEEN_MINUTES = 15 * 60 * 1000;

interface AppState {
  user: User | null;
  orchard: Orchard | null;
  isLoading: boolean;
  error: string | null;
  lastFetched: Date | null;
  fetchInitialData: () => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  user: null,
  orchard: null,
  isLoading: true,
  error: null,
  lastFetched: null,
  fetchInitialData: async () => {
    const { lastFetched, orchard } = get();
    const now = new Date();

    // If we have an orchard and fetched data within the last 15 minutes, do nothing.
    if (orchard && lastFetched && now.getTime() - lastFetched.getTime() < FIFTEEN_MINUTES) {
      set({ isLoading: false }); // Ensure loading is off
      return;
    }

    try {
      set({ isLoading: true, error: null });
      const userResponse = await getUser();
      const user = userResponse.data;
      if (user) {
        const orchardsResponse = await getMyOrchards();
        const mainOrchard = orchardsResponse.data[0] || null;
        set({ 
          user, 
          orchard: mainOrchard, 
          isLoading: false, 
          lastFetched: new Date() 
        });
      } else {
        throw new Error("User not found");
      }
    } catch (err) {
      const error = err instanceof Error ? err.message : "An unknown error occurred";
      set({ error, isLoading: false });
      localStorage.removeItem('authToken');
    }
  },
}));