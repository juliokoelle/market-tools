# Horsefinder Multi-User Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gate the Horsefinder app behind Supabase Auth (email/password) so only registered beta users can access the event browser.

**Architecture:** Horsefinder already has a Supabase client in `src/integrations/supabase/client.ts` using the anon key. Event data remains public (no user-scoped data, no API changes). We add: AuthContext wrapping the Supabase auth state, a Login/Signup page, and a ProtectedRoute that redirects unauthenticated users to `/login`.

**Tech Stack:** React 18 + Vite + TypeScript, Supabase Auth (email/password), `@supabase/supabase-js` ^2 (already installed), React Router v6, TanStack React Query (already present).

---

## Pre-flight: Supabase Auth setup (do once, manual)

In the Supabase dashboard for the horsefinder project (`umklkbohfsrmixdsjcmk`):
1. **Enable Email Auth**: Authentication → Providers → Email → Enable (toggle on)
2. Optionally disable "Confirm email" for easier beta testing: Authentication → Email Templates → uncheck "Confirm email"

No new env vars needed — `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` are already in `.env`.

---

## File Map

| File | Action | What it does |
|------|--------|-------------|
| `src/contexts/AuthContext.tsx` | **CREATE** | Auth state (user, loading, signOut) from Supabase session |
| `src/pages/AuthPage.tsx` | **CREATE** | Login + signup form styled for horsefinder |
| `src/components/ProtectedRoute.tsx` | **CREATE** | Redirects unauthenticated users to /login |
| `src/App.tsx` | **MODIFY** | Wrap with AuthProvider, add /login route, protect all other routes |
| `src/components/Header.tsx` (or wherever nav lives) | **MODIFY** | Add logout button |

---

## Task 1: AuthContext

**Files:**
- Create: `src/contexts/AuthContext.tsx`

- [ ] **Step 1: Read the existing Supabase client to confirm the export name**

```bash
cat /Users/juliokoelle/projects/horsefinder/src/integrations/supabase/client.ts | head -30
```

Expected: exports `supabase` as named export.

- [ ] **Step 2: Create `src/contexts/AuthContext.tsx`**

```typescript
import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import type { User, Session } from '@supabase/supabase-js';
import { supabase } from '@/integrations/supabase/client';

interface AuthContextType {
  user: User | null;
  session: Session | null;
  loading: boolean;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  session: null,
  loading: true,
  signOut: async () => {},
});

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser]       = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  return (
    <AuthContext.Provider value={{
      user,
      session,
      loading,
      signOut: () => supabase.auth.signOut(),
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
```

- [ ] **Step 3: Commit**

```bash
cd /Users/juliokoelle/projects/horsefinder
git add src/contexts/AuthContext.tsx
git commit -m "feat(auth): AuthContext with Supabase session tracking"
```

---

## Task 2: AuthPage (Login + Signup)

**Files:**
- Create: `src/pages/AuthPage.tsx`

- [ ] **Step 1: Check the existing color/theme variables to match horsefinder's style**

```bash
head -50 /Users/juliokoelle/projects/horsefinder/src/index.css
```

Note the primary color variables so the form styling fits the existing design.

- [ ] **Step 2: Create `src/pages/AuthPage.tsx`**

```typescript
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/contexts/AuthContext';

const AuthPage = () => {
  const [mode, setMode]         = useState<'login' | 'signup'>('login');
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState('');
  const [success, setSuccess]   = useState('');
  const navigate                = useNavigate();
  const { user }                = useAuth();

  useEffect(() => {
    if (user) navigate('/', { replace: true });
  }, [user, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      if (mode === 'signup') {
        const { error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        setSuccess('Account erstellt! Bitte E-Mail bestätigen und dann anmelden.');
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        // AuthContext updates → useEffect navigates to /
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Fehler');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm">
        <h1 className="mb-2 text-center text-2xl font-bold tracking-tight">🐴 HorseFinder</h1>
        <p className="mb-8 text-center text-sm text-muted-foreground">Beta</p>
        <div className="rounded-2xl border bg-card p-6 shadow-sm">
          <h2 className="mb-5 text-base font-semibold">
            {mode === 'login' ? 'Anmelden' : 'Account erstellen'}
          </h2>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <input
              type="email"
              placeholder="E-Mail"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoComplete="email"
              className="rounded-xl border bg-background px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary"
            />
            <input
              type="password"
              placeholder="Passwort (min. 6 Zeichen)"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              minLength={6}
              autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
              className="rounded-xl border bg-background px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary"
            />
            {error   && <p className="text-xs text-destructive">{error}</p>}
            {success && <p className="text-xs text-emerald-600">{success}</p>}
            <button
              type="submit"
              disabled={loading}
              className="mt-1 rounded-xl bg-primary py-2.5 text-sm font-semibold text-primary-foreground disabled:opacity-50"
            >
              {loading
                ? '…'
                : mode === 'login'
                ? 'Anmelden'
                : 'Account erstellen'}
            </button>
          </form>
          <button
            onClick={() => {
              setMode(mode === 'login' ? 'signup' : 'login');
              setError('');
              setSuccess('');
            }}
            className="mt-4 w-full text-center text-xs text-muted-foreground hover:text-foreground"
          >
            {mode === 'login'
              ? 'Noch kein Account? Registrieren →'
              : 'Bereits registriert? Anmelden →'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AuthPage;
```

- [ ] **Step 3: Commit**

```bash
git add src/pages/AuthPage.tsx
git commit -m "feat(auth): AuthPage with login/signup toggle"
```

---

## Task 3: ProtectedRoute + update App.tsx

**Files:**
- Create: `src/components/ProtectedRoute.tsx`
- Modify: `src/App.tsx`

- [ ] **Step 1: Create `src/components/ProtectedRoute.tsx`**

```typescript
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-foreground/20 border-t-foreground" />
      </div>
    );
  }

  return user ? <>{children}</> : <Navigate to="/login" replace />;
};

export default ProtectedRoute;
```

- [ ] **Step 2: Read current `src/App.tsx`**

```bash
cat /Users/juliokoelle/projects/horsefinder/src/App.tsx
```

- [ ] **Step 3: Update `src/App.tsx`**

Add imports:
```typescript
import { AuthProvider } from '@/contexts/AuthContext';
import AuthPage from '@/pages/AuthPage';
import ProtectedRoute from '@/components/ProtectedRoute';
```

Wrap the entire tree with `<AuthProvider>` and add the `/login` route + protect existing routes:

```typescript
const App = () => (
  <AuthProvider>
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<AuthPage />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Index />
                </ProtectedRoute>
              }
            />
            <Route
              path="/events/:id"
              element={
                <ProtectedRoute>
                  <EventPage />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  </AuthProvider>
);
```

- [ ] **Step 4: Build and verify**

```bash
cd /Users/juliokoelle/projects/horsefinder && npm run build 2>&1 | tail -10
```

Expected: `✓ built` with no TypeScript errors.

- [ ] **Step 5: Commit**

```bash
git add src/components/ProtectedRoute.tsx src/App.tsx
git commit -m "feat(auth): ProtectedRoute + /login route in App.tsx"
```

---

## Task 4: Add logout to the UI

**Files:**
- Modify: wherever the top navigation or header is defined in horsefinder

- [ ] **Step 1: Find the nav/header component**

```bash
grep -r "logout\|signOut\|Abmelden\|header\|nav" /Users/juliokoelle/projects/horsefinder/src --include="*.tsx" -l
grep -r "FilterBar\|Header\|Nav" /Users/juliokoelle/projects/horsefinder/src/pages/Index.tsx | head -10
```

- [ ] **Step 2: Read that file to see how to integrate logout**

Read whichever file renders the top nav or the main app header.

- [ ] **Step 3: Add logout button**

Import `useAuth` and add a logout button in the header or as a floating button:

```typescript
import { useAuth } from '@/contexts/AuthContext';
import { LogOut } from 'lucide-react';

// Inside the component:
const { signOut } = useAuth();

// Add to header/nav:
<button
  onClick={signOut}
  className="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-secondary"
  title="Abmelden"
>
  <LogOut className="h-3.5 w-3.5" />
  <span className="hidden sm:inline">Abmelden</span>
</button>
```

If no obvious header exists, add it as a fixed top-right button in `Index.tsx`:

```typescript
<button
  onClick={signOut}
  className="fixed right-4 top-4 z-50 flex h-8 w-8 items-center justify-center rounded-full border bg-background shadow-sm text-muted-foreground hover:text-destructive"
  title="Abmelden"
>
  <LogOut className="h-4 w-4" />
</button>
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(auth): logout button in horsefinder UI"
```

---

## Task 5: Deploy + smoke test

- [ ] **Step 1: Check if horsefinder is deployed to Vercel**

```bash
cd /Users/juliokoelle/projects/horsefinder && cat .vercel/project.json 2>/dev/null || echo "not linked"
```

If not linked: `vercel link` (select the existing horsefinder project or create new).

- [ ] **Step 2: Deploy**

```bash
vercel --prod
```

Note the production URL from the output.

- [ ] **Step 3: Manual smoke test**

1. Open the production URL → should redirect to `/login`
2. Click "Noch kein Account? Registrieren" → sign up with a test email
3. If email confirmation enabled: confirm in inbox; otherwise login directly
4. Should land on the event browser (Index page)
5. Browse events → works normally
6. Click logout → redirected back to `/login`
7. Log in again → event browser accessible
8. Try opening the URL without being logged in (incognito) → redirected to `/login`
