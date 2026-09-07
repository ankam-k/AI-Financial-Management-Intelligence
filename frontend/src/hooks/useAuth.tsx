/**
 * Session state for the whole app.
 *
 * One provider fetches the current account once on load, decides between the
 * login screen, onboarding, and the app, and exposes the four actions that move
 * between them (log in, register, enter the demo, log out). It also owns the
 * "onboarding done yet?" bit, read from the profile, so the shell can gate the
 * first-run flow without every page knowing about it.
 *
 * The session itself is an HttpOnly cookie the browser holds; this context never
 * sees a token. A 401 from *any* request — an expired cookie, a deleted account
 * — is caught centrally (via `setUnauthorizedHandler`) and drops the app back to
 * the login screen rather than leaving a stale, half-authenticated view.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { setUnauthorizedHandler } from '../api/client';
import {
  enterDemo as apiEnterDemo,
  getMe,
  getProfile,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
} from '../api/endpoints';
import type { AuthUser, Profile } from '../api/types';

type Status = 'loading' | 'anon' | 'authed';

interface AuthContextValue {
  status: Status;
  user: AuthUser | null;
  profile: Profile | null;
  /** True once signed in but before onboarding has been finished or skipped. */
  needsOnboarding: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  enterDemo: () => Promise<void>;
  logout: () => Promise<void>;
  /** Adopt a freshly-returned profile (onboarding submit, Settings save). */
  setProfile: (profile: Profile) => void;
  /** Re-read the profile from the server (e.g. after a Settings change). */
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>('loading');
  const [user, setUser] = useState<AuthUser | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const mounted = useRef(true);

  const enterSession = useCallback(async (account: AuthUser) => {
    // The account is signed in; its profile carries the onboarding bit.
    const loaded = await getProfile();
    if (!mounted.current) return;
    setUser(account);
    setProfile(loaded);
    setStatus('authed');
  }, []);

  const goAnonymous = useCallback(() => {
    if (!mounted.current) return;
    setUser(null);
    setProfile(null);
    setStatus('anon');
  }, []);

  // Any 401 anywhere in the app means the session is gone: reset to login.
  useEffect(() => {
    mounted.current = true;
    setUnauthorizedHandler(goAnonymous);
    return () => {
      mounted.current = false;
      setUnauthorizedHandler(null);
    };
  }, [goAnonymous]);

  // Resolve the session once on load.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const account = await getMe();
        if (!cancelled) await enterSession(account);
      } catch {
        if (!cancelled) goAnonymous();
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [enterSession, goAnonymous]);

  const login = useCallback(
    async (email: string, password: string) => {
      const account = await apiLogin({ email, password });
      await enterSession(account);
    },
    [enterSession],
  );

  const register = useCallback(
    async (email: string, password: string, displayName?: string) => {
      const account = await apiRegister({
        email,
        password,
        ...(displayName ? { display_name: displayName } : {}),
      });
      await enterSession(account);
    },
    [enterSession],
  );

  const enterDemo = useCallback(async () => {
    const account = await apiEnterDemo();
    await enterSession(account);
  }, [enterSession]);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } finally {
      goAnonymous();
    }
  }, [goAnonymous]);

  const refreshProfile = useCallback(async () => {
    const loaded = await getProfile();
    if (mounted.current) setProfile(loaded);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      profile,
      needsOnboarding: status === 'authed' && profile !== null && !profile.onboarding_completed,
      login,
      register,
      enterDemo,
      logout,
      setProfile,
      refreshProfile,
    }),
    [status, user, profile, login, register, enterDemo, logout, refreshProfile],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (value === null) {
    throw new Error('useAuth must be used within an <AuthProvider>.');
  }
  return value;
}
