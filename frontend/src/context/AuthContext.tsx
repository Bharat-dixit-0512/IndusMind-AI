"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { loginApi, registerApi, type AuthToken, type LoginPayload, type RegisterPayload } from "@/lib/api";

interface User { email: string; name: string; role: string; }

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (p: LoginPayload) => Promise<void>;
  register: (p: RegisterPayload) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const storedToken = localStorage.getItem("token");
    const storedUser = localStorage.getItem("user");
    // One-time hydration from localStorage on mount.
    /* eslint-disable react-hooks/set-state-in-effect */
    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
    }
    setIsLoading(false);
    /* eslint-enable react-hooks/set-state-in-effect */
  }, []);

  const saveAuth = (data: AuthToken) => {
    localStorage.setItem("token", data.access_token);
    const u = { email: data.email, name: data.name, role: data.role };
    localStorage.setItem("user", JSON.stringify(u));
    setToken(data.access_token);
    setUser(u);
  };

  const login = useCallback(async (p: LoginPayload) => {
    const data = await loginApi(p);
    saveAuth(data);
    router.push("/dashboard");
  }, [router]);

  const register = useCallback(async (p: RegisterPayload) => {
    const data = await registerApi(p);
    saveAuth(data);
    router.push("/dashboard");
  }, [router]);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setToken(null);
    setUser(null);
    router.push("/");
  }, [router]);

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
