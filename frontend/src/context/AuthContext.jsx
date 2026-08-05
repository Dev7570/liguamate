/**
 * Auth Context — Manages user authentication state
 */

import { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing session
    const token = localStorage.getItem('linguamate_token');
    const savedUser = localStorage.getItem('linguamate_user');
    if (token && savedUser) {
      try {
        setUser(JSON.parse(savedUser));
        // Fetch full profile in background
        api.getProfile().then(profile => {
          const userData = {
            id: profile.id,
            name: profile.name,
            email: profile.email,
            english_level: profile.english_level,
            goal: profile.goal,
            avatar_emoji: profile.avatar_emoji,
          };
          setUser(userData);
          localStorage.setItem('linguamate_user', JSON.stringify(userData));
        }).catch(() => {
          // Token expired
          logout();
        });
      } catch {
        logout();
      }
    }
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    const result = await api.login(email, password);
    const userData = { id: result.user_id, name: result.name };
    setUser(userData);
    return result;
  };

  const signup = async (data) => {
    const result = await api.signup(data);
    const userData = { id: result.user_id, name: result.name };
    setUser(userData);
    return result;
  };

  const logout = () => {
    api.clearToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
