import { createContext, useContext, useState, ReactNode, useEffect } from "react";
import { authApi, type AuthResponse } from "@/lib/api";

export interface User {
  id: string;
  name: string;
  email: string;
  avatar?: string;
}

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => Promise<void>;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem("finflow_user");
    return saved ? JSON.parse(saved) : null;
  });
  const [isLoading, setIsLoading] = useState(true);

  // 초기 로드 시 토큰 확인
  useEffect(() => {
    const token = localStorage.getItem("finflow_access_token");
    const savedUser = localStorage.getItem("finflow_user");
    
    if (token && savedUser) {
      try {
        const userData = JSON.parse(savedUser);
        setUser(userData);
      } catch (e) {
        // 토큰은 있지만 사용자 정보가 없으면 로그아웃 처리
        localStorage.removeItem("finflow_access_token");
        localStorage.removeItem("finflow_refresh_token");
        localStorage.removeItem("finflow_user");
      }
    }
    setIsLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const response = await authApi.login({ email, password });
      if (response.success && response.data) {
        const { accessToken, refreshToken, user: userData } = response.data;
        localStorage.setItem("finflow_access_token", accessToken);
        localStorage.setItem("finflow_refresh_token", refreshToken);
        localStorage.setItem("finflow_user", JSON.stringify(userData));
        setUser(userData);
      } else {
        throw new Error(response.error?.message || "로그인 실패");
      }
    } catch (error: any) {
      throw new Error(error.message || "로그인 중 오류가 발생했습니다.");
    }
  };

  const register = async (email: string, password: string, name: string) => {
    try {
      const response = await authApi.register({ email, password, name });
      if (response.success && response.data) {
        const { accessToken, refreshToken, user: userData } = response.data;
        localStorage.setItem("finflow_access_token", accessToken);
        localStorage.setItem("finflow_refresh_token", refreshToken);
        localStorage.setItem("finflow_user", JSON.stringify(userData));
        setUser(userData);
      } else {
        throw new Error(response.error?.message || "회원가입 실패");
      }
    } catch (error: any) {
      throw new Error(error.message || "회원가입 중 오류가 발생했습니다.");
    }
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch (error) {
      // 로그아웃 API 실패해도 클라이언트에서는 로그아웃 처리
      console.error("Logout API error:", error);
    } finally {
      setUser(null);
      localStorage.removeItem("finflow_access_token");
      localStorage.removeItem("finflow_refresh_token");
      localStorage.removeItem("finflow_user");
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
