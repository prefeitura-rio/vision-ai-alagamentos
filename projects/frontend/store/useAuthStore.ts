import { create } from "zustand";
import axios from "axios";
import Cookies from "js-cookie";
import qs from "qs";

import api from "@/utils/api";

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: Cookies.get("token") || null,
  isAuthenticated: !!Cookies.get("token"),

  login: async (username, password) => {
    try {
      const response = await api.post(
        "/auth/token",
        qs.stringify({
          username,
          password,
        }),
        {
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
        },
      );
      const { access_token } = response.data;
      Cookies.set("token", access_token, { expires: 1 });
      set({ token: access_token, isAuthenticated: true });
    } catch (error) {
      console.error("Login failed:", error);
      // Handle error, e.g., show a notification
    }
  },

  logout: () => {
    Cookies.remove("token");
    set({ token: null, isAuthenticated: false });
  },
}));
