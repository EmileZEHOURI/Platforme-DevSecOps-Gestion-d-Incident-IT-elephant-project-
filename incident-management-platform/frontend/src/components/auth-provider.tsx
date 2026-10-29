"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { ApiError } from "@/lib/api";
import { getMe } from "@/services/auth.service";
import type { User } from "@/types/auth";

type Session = {
  user: User | null;
  loading: boolean;
  error: string;
  refresh: () => Promise<void>;
};
const AuthContext = createContext<Session | null>(null);
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const pending = useRef(false);
  const refresh = useCallback(async () => {
    if (pending.current) return;
    pending.current = true;
    try {
      const result = await getMe();
      setError("");
      setUser(result.is_active ? result : null);
    } catch (err) {
      setUser(null);
      setError(
        err instanceof ApiError && err.status === 401
          ? ""
          : err instanceof Error
            ? err.message
            : "La session ne peut pas être vérifiée.",
      );
    } finally {
      setLoading(false);
      pending.current = false;
    }
  }, []);
  useEffect(() => {
    void Promise.resolve().then(refresh);
    const check = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    const timer = window.setInterval(check, 60000);
    window.addEventListener("focus", check);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", check);
    };
  }, [refresh]);
  return (
    <AuthContext.Provider value={{ user, loading, error, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}
export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("AuthProvider manquant");
  return value;
}
