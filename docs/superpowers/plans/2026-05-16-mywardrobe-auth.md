# MyWardrobe Multi-User Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded `USER_ID = 'julio'` with real Supabase Auth so any user can sign up with email/password and access only their own wardrobe and wishlist data.

**Architecture:** The frontend gets a Supabase anon client (VITE env vars) for auth only; all data calls still go through `/api/*` Vercel functions. Each API function verifies the JWT from the `Authorization: Bearer` header using the existing service-role Supabase client, then uses the verified `user.id` instead of the hardcoded constant.

**Tech Stack:** React 18 + Vite, Vercel serverless functions (TypeScript), Supabase Auth (email/password), @supabase/supabase-js (already installed in both frontend and API deps).

---

## Pre-flight: Manual Supabase Setup (do once, not automated)

In the Supabase dashboard for the MyWardrobe project:
1. **Enable Email Auth**: Authentication → Providers → Email → Enable
2. **Copy the anon/public key**: Project Settings → API → "anon public" key
3. **Add Vercel env vars** (Dashboard → Project → Settings → Environment Variables):
   - `VITE_SUPABASE_URL` = same value as existing `SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY` = the anon/public key (NOT the service role key)
4. **Pull env locally**: `cd /Users/juliokoelle/projects/mywardrobe && vercel env pull .env.local`

---

## File Map

| File | Action | What it does |
|------|--------|-------------|
| `api/_auth.ts` | **CREATE** | Shared helper: verifies JWT → returns `user.id` or sends 401 |
| `api/items/index.ts` | **MODIFY** | Replace `USER_ID = 'julio'` with `getAuthUser()` |
| `api/items/[id].ts` | **MODIFY** | Replace `USER_ID = 'julio'` with `getAuthUser()` |
| `api/wishlist/index.ts` | **MODIFY** | Replace `USER_ID = 'julio'` with `getAuthUser()` |
| `api/wishlist/[id].ts` | **MODIFY** | Replace `USER_ID = 'julio'` with `getAuthUser()` |
| `api/upload.ts` | **MODIFY** | Replace `julio/` folder prefix with user id from JWT |
| `src/lib/supabase.ts` | **CREATE** | Frontend Supabase client (anon key, auth only) |
| `src/lib/apiFetch.ts` | **CREATE** | Shared fetch util that injects `Authorization: Bearer` header |
| `src/services/wardrobeApi.ts` | **MODIFY** | Use shared `apiFetch` from `@/lib/apiFetch` |
| `src/services/wishlistApi.ts` | **MODIFY** | Use shared `apiFetch` from `@/lib/apiFetch` |
| `src/contexts/AuthContext.tsx` | **CREATE** | Auth state (user, session, loading, signOut) |
| `src/pages/AuthPage.tsx` | **CREATE** | Login + signup form |
| `src/components/ProtectedRoute.tsx` | **CREATE** | Redirects unauthenticated users to /login |
| `src/App.tsx` | **MODIFY** | Wrap with AuthProvider, add /login route, wrap main routes with ProtectedRoute |
| `src/pages/ProfileScreen.tsx` | **MODIFY** | Show real user email + logout button |

---

## Task 1: Create shared API auth helper

**Files:**
- Create: `api/_auth.ts`

- [ ] **Step 1: Create `api/_auth.ts`**

```typescript
// api/_auth.ts
import { createClient } from '@supabase/supabase-js';
import type { VercelRequest, VercelResponse } from '@vercel/node';

const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_KEY!,
);

export { supabase };

export async function getAuthUser(req: VercelRequest, res: VercelResponse) {
  const token = (req.headers['authorization'] as string | undefined)
    ?.replace('Bearer ', '')
    .trim();
  if (!token) {
    res.status(401).json({ error: 'Unauthorized' });
    return null;
  }
  const { data: { user }, error } = await supabase.auth.getUser(token);
  if (error || !user) {
    res.status(401).json({ error: 'Unauthorized' });
    return null;
  }
  return user;
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/juliokoelle/projects/mywardrobe
git add api/_auth.ts
git commit -m "feat(auth): shared API auth helper — JWT verify → user.id"
```

---

## Task 2: Update API handlers — items

**Files:**
- Modify: `api/items/index.ts`
- Modify: `api/items/[id].ts`

- [ ] **Step 1: Replace `api/items/index.ts`**

Replace the entire file with:

```typescript
import type { VercelRequest, VercelResponse } from '@vercel/node';
import { supabase, getAuthUser } from '../_auth';

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const user = await getAuthUser(req, res);
  if (!user) return;
  const USER_ID = user.id;

  if (req.method === 'GET') {
    const { data, error } = await supabase
      .from('wardrobe_items')
      .select('*')
      .eq('user_id', USER_ID)
      .order('created_at', { ascending: false });

    if (error) return res.status(500).json({ error: error.message });
    return res.status(200).json((data ?? []).map(mapRow));
  }

  if (req.method === 'POST') {
    const body = req.body;
    const { data, error } = await supabase
      .from('wardrobe_items')
      .insert({
        user_id: USER_ID,
        name: body.name,
        brand: body.brand ?? null,
        image_url: body.imageUrl ?? null,
        category_gender: body.categoryGender,
        category_main: body.categoryMain,
        category_sub: body.categorySub ?? null,
        colors: body.colors ?? [],
        size: body.size ?? '',
        material: body.material ?? null,
        condition: body.condition ?? null,
        season: body.season ?? null,
        tags: body.tags ?? [],
        notes: body.notes ?? null,
        price: body.price ?? null,
        retail_price: body.retailPrice ?? null,
        paid_price: body.paidPrice ?? null,
        quantity: body.quantity ?? 1,
        favorite: body.favorite ?? false,
        ai_suggested: body.aiSuggested ?? false,
      })
      .select()
      .single();

    if (error) return res.status(500).json({ error: error.message });
    return res.status(201).json(mapRow(data));
  }

  return res.status(405).json({ error: 'Method not allowed' });
}

function mapRow(row: Record<string, unknown>) {
  return {
    id: row.id,
    name: row.name,
    brand: row.brand ?? undefined,
    imageUrl: row.image_url ?? undefined,
    categoryGender: row.category_gender,
    categoryMain: row.category_main,
    categorySub: row.category_sub ?? undefined,
    colors: row.colors ?? [],
    size: row.size ?? '',
    material: row.material ?? undefined,
    condition: row.condition ?? undefined,
    season: row.season ?? undefined,
    tags: row.tags ?? [],
    notes: row.notes ?? undefined,
    price: row.price ?? undefined,
    retailPrice: row.retail_price ?? undefined,
    paidPrice: row.paid_price ?? undefined,
    quantity: row.quantity ?? 1,
    favorite: row.favorite ?? false,
    aiSuggested: row.ai_suggested ?? false,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}
```

- [ ] **Step 2: Replace `api/items/[id].ts`**

```typescript
import type { VercelRequest, VercelResponse } from '@vercel/node';
import { supabase, getAuthUser } from '../../_auth';

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const user = await getAuthUser(req, res);
  if (!user) return;
  const USER_ID = user.id;
  const { id } = req.query as { id: string };

  if (req.method === 'PUT') {
    const body = req.body;
    const row = toPartialRow(body);
    const { data, error } = await supabase
      .from('wardrobe_items')
      .update({ ...row, updated_at: new Date().toISOString() })
      .eq('id', id)
      .eq('user_id', USER_ID)
      .select()
      .single();

    if (error) return res.status(500).json({ error: error.message });
    return res.status(200).json(mapRow(data));
  }

  if (req.method === 'DELETE') {
    const { error } = await supabase
      .from('wardrobe_items')
      .delete()
      .eq('id', id)
      .eq('user_id', USER_ID);

    if (error) return res.status(500).json({ error: error.message });
    return res.status(204).end();
  }

  return res.status(405).json({ error: 'Method not allowed' });
}

function mapRow(row: Record<string, unknown>) {
  return {
    id: row.id,
    name: row.name,
    brand: row.brand ?? undefined,
    imageUrl: row.image_url ?? undefined,
    categoryGender: row.category_gender,
    categoryMain: row.category_main,
    categorySub: row.category_sub ?? undefined,
    colors: row.colors ?? [],
    size: row.size ?? '',
    material: row.material ?? undefined,
    condition: row.condition ?? undefined,
    season: row.season ?? undefined,
    tags: row.tags ?? [],
    notes: row.notes ?? undefined,
    price: row.price ?? undefined,
    retailPrice: row.retail_price ?? undefined,
    paidPrice: row.paid_price ?? undefined,
    quantity: row.quantity ?? 1,
    favorite: row.favorite ?? false,
    aiSuggested: row.ai_suggested ?? false,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function toPartialRow(body: Record<string, unknown>) {
  const row: Record<string, unknown> = {};
  if (body.name !== undefined) row.name = body.name;
  if (body.brand !== undefined) row.brand = body.brand;
  if (body.imageUrl !== undefined) row.image_url = body.imageUrl;
  if (body.categoryGender !== undefined) row.category_gender = body.categoryGender;
  if (body.categoryMain !== undefined) row.category_main = body.categoryMain;
  if (body.categorySub !== undefined) row.category_sub = body.categorySub;
  if (body.colors !== undefined) row.colors = body.colors;
  if (body.size !== undefined) row.size = body.size;
  if (body.material !== undefined) row.material = body.material;
  if (body.condition !== undefined) row.condition = body.condition;
  if (body.season !== undefined) row.season = body.season;
  if (body.tags !== undefined) row.tags = body.tags;
  if (body.notes !== undefined) row.notes = body.notes;
  if (body.price !== undefined) row.price = body.price;
  if (body.retailPrice !== undefined) row.retail_price = body.retailPrice;
  if (body.paidPrice !== undefined) row.paid_price = body.paidPrice;
  if (body.quantity !== undefined) row.quantity = body.quantity;
  if (body.favorite !== undefined) row.favorite = body.favorite;
  if (body.aiSuggested !== undefined) row.ai_suggested = body.aiSuggested;
  return row;
}
```

- [ ] **Step 3: Commit**

```bash
git add api/items/index.ts api/items/[id].ts
git commit -m "feat(auth): require JWT auth in items API endpoints"
```

---

## Task 3: Update API handlers — wishlist

**Files:**
- Modify: `api/wishlist/index.ts`
- Modify: `api/wishlist/[id].ts`

- [ ] **Step 1: Replace `api/wishlist/index.ts`**

```typescript
import type { VercelRequest, VercelResponse } from '@vercel/node';
import { supabase, getAuthUser } from '../_auth';

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const user = await getAuthUser(req, res);
  if (!user) return;
  const USER_ID = user.id;

  if (req.method === 'GET') {
    const { data, error } = await supabase
      .from('wishlist_items')
      .select('*')
      .eq('user_id', USER_ID)
      .eq('purchased', false)
      .order('created_at', { ascending: false });

    if (error) return res.status(500).json({ error: error.message });
    return res.status(200).json((data ?? []).map(mapRow));
  }

  if (req.method === 'POST') {
    const body = req.body;
    const { data, error } = await supabase
      .from('wishlist_items')
      .insert({
        user_id: USER_ID,
        name: body.name,
        brand: body.brand ?? null,
        category: body.category ?? null,
        color: body.color ?? null,
        size: body.size ?? null,
        image_url: body.imageUrl ?? null,
        source_url: body.sourceUrl ?? null,
        price: body.price ?? null,
        retail_price: body.retailPrice ?? null,
        target_price: body.targetPrice ?? null,
        currency: body.currency ?? 'EUR',
        priority: body.priority ?? 2,
        notes: body.notes ?? null,
        purchased: false,
      })
      .select()
      .single();

    if (error) return res.status(500).json({ error: error.message });
    return res.status(201).json(mapRow(data));
  }

  return res.status(405).json({ error: 'Method not allowed' });
}

function mapRow(row: Record<string, unknown>) {
  return {
    id: row.id,
    name: row.name,
    brand: row.brand ?? undefined,
    category: row.category ?? undefined,
    color: row.color ?? undefined,
    size: row.size ?? undefined,
    imageUrl: row.image_url ?? undefined,
    sourceUrl: row.source_url ?? undefined,
    price: row.price ?? undefined,
    retailPrice: row.retail_price ?? undefined,
    targetPrice: row.target_price ?? undefined,
    currency: row.currency ?? 'EUR',
    priority: row.priority ?? 2,
    notes: row.notes ?? undefined,
    purchased: row.purchased ?? false,
    createdAt: row.created_at,
  };
}
```

- [ ] **Step 2: Replace `api/wishlist/[id].ts`**

```typescript
import type { VercelRequest, VercelResponse } from '@vercel/node';
import { supabase, getAuthUser } from '../../_auth';

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const user = await getAuthUser(req, res);
  if (!user) return;
  const USER_ID = user.id;
  const { id } = req.query as { id: string };

  if (req.method === 'PUT') {
    const body = req.body;
    const row: Record<string, unknown> = {};
    if (body.name !== undefined)        row.name = body.name;
    if (body.brand !== undefined)       row.brand = body.brand;
    if (body.category !== undefined)    row.category = body.category;
    if (body.color !== undefined)       row.color = body.color;
    if (body.size !== undefined)        row.size = body.size;
    if (body.imageUrl !== undefined)    row.image_url = body.imageUrl;
    if (body.sourceUrl !== undefined)   row.source_url = body.sourceUrl;
    if (body.price !== undefined)       row.price = body.price;
    if (body.retailPrice !== undefined) row.retail_price = body.retailPrice;
    if (body.targetPrice !== undefined) row.target_price = body.targetPrice;
    if (body.currency !== undefined)    row.currency = body.currency;
    if (body.priority !== undefined)    row.priority = body.priority;
    if (body.notes !== undefined)       row.notes = body.notes;
    if (body.purchased !== undefined)   row.purchased = body.purchased;

    const { data, error } = await supabase
      .from('wishlist_items')
      .update(row)
      .eq('id', id)
      .eq('user_id', USER_ID)
      .select()
      .single();

    if (error) return res.status(500).json({ error: error.message });
    return res.status(200).json(mapRow(data));
  }

  if (req.method === 'DELETE') {
    const { error } = await supabase
      .from('wishlist_items')
      .delete()
      .eq('id', id)
      .eq('user_id', USER_ID);

    if (error) return res.status(500).json({ error: error.message });
    return res.status(204).end();
  }

  return res.status(405).json({ error: 'Method not allowed' });
}

function mapRow(row: Record<string, unknown>) {
  return {
    id: row.id,
    name: row.name,
    brand: row.brand ?? undefined,
    category: row.category ?? undefined,
    color: row.color ?? undefined,
    size: row.size ?? undefined,
    imageUrl: row.image_url ?? undefined,
    sourceUrl: row.source_url ?? undefined,
    price: row.price ?? undefined,
    retailPrice: row.retail_price ?? undefined,
    targetPrice: row.target_price ?? undefined,
    currency: row.currency ?? 'EUR',
    priority: row.priority ?? 2,
    notes: row.notes ?? undefined,
    purchased: row.purchased ?? false,
    createdAt: row.created_at,
  };
}
```

- [ ] **Step 3: Commit**

```bash
git add api/wishlist/index.ts api/wishlist/[id].ts
git commit -m "feat(auth): require JWT auth in wishlist API endpoints"
```

---

## Task 4: Update upload API

**Files:**
- Modify: `api/upload.ts`

- [ ] **Step 1: Read the current file to understand the full upload handler**

Read `/Users/juliokoelle/projects/mywardrobe/api/upload.ts`.

- [ ] **Step 2: Replace the hardcoded `julio/` path prefix**

Find the line:
```typescript
const path = `julio/${filename ?? `${Date.now()}.jpg`}`;
```

Replace with JWT-based user id. Add `getAuthUser` import at top of file, call it before building the path:

```typescript
import type { VercelRequest, VercelResponse } from '@vercel/node';
import { getAuthUser, supabase } from './_auth';
// ... (keep existing imports like formidable)

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const user = await getAuthUser(req, res);
  if (!user) return;

  // ... (rest of existing upload logic, but replace path)
  const path = `${user.id}/${filename ?? `${Date.now()}.jpg`}`;
  // ... rest unchanged
}
```

- [ ] **Step 3: Commit**

```bash
git add api/upload.ts
git commit -m "feat(auth): scope image upload path to authenticated user.id"
```

---

## Task 5: Frontend Supabase client + shared apiFetch

**Files:**
- Create: `src/lib/supabase.ts`
- Create: `src/lib/apiFetch.ts`
- Modify: `src/services/wardrobeApi.ts`
- Modify: `src/services/wishlistApi.ts`

- [ ] **Step 1: Create `src/lib/supabase.ts`**

```typescript
import { createClient } from '@supabase/supabase-js';

const url  = import.meta.env.VITE_SUPABASE_URL as string;
const anon = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

export const supabase = createClient(url, anon);
```

- [ ] **Step 2: Create `src/lib/apiFetch.ts`**

```typescript
import { supabase } from './supabase';

const BASE = '/api';

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;

  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      ...(options?.body != null ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });

  if (!res.ok) {
    if (res.status === 401) throw new Error('SESSION_EXPIRED');
    const text = await res.text().catch(() => '');
    throw new Error(`API ${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}
```

- [ ] **Step 3: Update `src/services/wardrobeApi.ts`**

Replace the local `apiFetch` function and `BASE` constant with an import:

```typescript
import { WardrobeItem } from '@/types/wardrobe';
import { apiFetch } from '@/lib/apiFetch';

// ... (keep all existing exported functions unchanged — fetchItems, createItem, updateItemApi, deleteItemApi)
// Just remove the local apiFetch definition and BASE constant since they're now imported.
```

The exported functions (`fetchItems`, `createItem`, `updateItemApi`, `deleteItemApi`) stay exactly the same — only remove the local `async function apiFetch` and `const BASE` declarations.

- [ ] **Step 4: Update `src/services/wishlistApi.ts`**

Same change: remove local `apiFetch` and `BASE`, import from `@/lib/apiFetch`:

```typescript
import { WishlistItem } from '@/types/wishlist';
import { apiFetch } from '@/lib/apiFetch';

export type NewWishlistItem = Omit<WishlistItem, 'id' | 'purchased' | 'createdAt'>;

export const fetchWishlist = (): Promise<WishlistItem[]> =>
  apiFetch<WishlistItem[]>('/wishlist');

export const createWishlistItem = (item: NewWishlistItem): Promise<WishlistItem> =>
  apiFetch<WishlistItem>('/wishlist', { method: 'POST', body: JSON.stringify(item) });

export const updateWishlistItem = (
  id: string,
  updates: Partial<Omit<WishlistItem, 'id' | 'createdAt'>>,
): Promise<WishlistItem> =>
  apiFetch<WishlistItem>(`/wishlist/${id}`, { method: 'PUT', body: JSON.stringify(updates) });

export const deleteWishlistItem = (id: string): Promise<void> =>
  apiFetch<void>(`/wishlist/${id}`, { method: 'DELETE' });
```

- [ ] **Step 5: Run build to check for errors**

```bash
cd /Users/juliokoelle/projects/mywardrobe && npm run build 2>&1 | tail -15
```

Expected: `✓ built` with no TypeScript errors. If VITE_SUPABASE_URL is not yet in .env.local, add a placeholder to get past the env check:
```bash
echo 'VITE_SUPABASE_URL=placeholder\nVITE_SUPABASE_ANON_KEY=placeholder' >> .env.local
```

- [ ] **Step 6: Commit**

```bash
git add src/lib/supabase.ts src/lib/apiFetch.ts src/services/wardrobeApi.ts src/services/wishlistApi.ts
git commit -m "feat(auth): frontend Supabase client + shared apiFetch with Bearer token"
```

---

## Task 6: AuthContext

**Files:**
- Create: `src/contexts/AuthContext.tsx`

- [ ] **Step 1: Create `src/contexts/AuthContext.tsx`**

```typescript
import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import type { User, Session } from '@supabase/supabase-js';
import { supabase } from '@/lib/supabase';

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

  const signOut = async () => {
    await supabase.auth.signOut();
  };

  return (
    <AuthContext.Provider value={{ user, session, loading, signOut }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
```

- [ ] **Step 2: Commit**

```bash
git add src/contexts/AuthContext.tsx
git commit -m "feat(auth): AuthContext with session tracking and signOut"
```

---

## Task 7: AuthPage (Login + Signup)

**Files:**
- Create: `src/pages/AuthPage.tsx`

- [ ] **Step 1: Create `src/pages/AuthPage.tsx`**

```typescript
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '@/lib/supabase';
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
        setSuccess('Account erstellt! Bitte E-Mail bestätigen, dann anmelden.');
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        // AuthContext will update, useEffect above navigates to /
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
        <p className="mb-8 text-center text-sm font-semibold uppercase tracking-[0.15em] text-foreground/70">
          MyWardrobe
        </p>
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
              className="rounded-xl border bg-background px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#c07a2a]"
            />
            <input
              type="password"
              placeholder="Passwort (min. 6 Zeichen)"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              minLength={6}
              autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
              className="rounded-xl border bg-background px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#c07a2a]"
            />
            {error   && <p className="text-xs text-destructive">{error}</p>}
            {success && <p className="text-xs text-emerald-600">{success}</p>}
            <button
              type="submit"
              disabled={loading}
              className="mt-1 rounded-xl py-2.5 text-sm font-semibold text-white disabled:opacity-50"
              style={{ backgroundColor: '#c07a2a' }}
            >
              {loading
                ? '…'
                : mode === 'login'
                ? 'Anmelden'
                : 'Account erstellen'}
            </button>
          </form>
          <button
            onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError(''); setSuccess(''); }}
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

- [ ] **Step 2: Commit**

```bash
git add src/pages/AuthPage.tsx
git commit -m "feat(auth): AuthPage with login/signup toggle"
```

---

## Task 8: ProtectedRoute + update App.tsx

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
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-foreground/30 border-t-foreground" />
      </div>
    );
  }

  return user ? <>{children}</> : <Navigate to="/login" replace />;
};

export default ProtectedRoute;
```

- [ ] **Step 2: Read current `src/App.tsx` to see all imports and providers**

Read `/Users/juliokoelle/projects/mywardrobe/src/App.tsx`.

- [ ] **Step 3: Update `src/App.tsx`**

Add these imports at the top:
```typescript
import { AuthProvider } from '@/contexts/AuthContext';
import AuthPage from '@/pages/AuthPage';
import ProtectedRoute from '@/components/ProtectedRoute';
```

Wrap the entire `<QueryClientProvider>` with `<AuthProvider>`:
```typescript
const App = () => (
  <AuthProvider>
    <QueryClientProvider client={queryClient}>
      {/* ... existing providers ... */}
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<AuthPage />} />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                {/* existing routes and UI */}
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </AuthProvider>
);
```

Keep all existing route definitions, providers, modals, and the `<BottomTabBar>` inside the ProtectedRoute wrapper so unauthenticated users see only the login page.

- [ ] **Step 4: Build and verify no errors**

```bash
cd /Users/juliokoelle/projects/mywardrobe && npm run build 2>&1 | tail -10
```

Expected: `✓ built` with no errors.

- [ ] **Step 5: Commit**

```bash
git add src/components/ProtectedRoute.tsx src/App.tsx
git commit -m "feat(auth): ProtectedRoute + /login route in App.tsx"
```

---

## Task 9: Update ProfileScreen with real user info + logout

**Files:**
- Modify: `src/pages/ProfileScreen.tsx`

- [ ] **Step 1: Read current `src/pages/ProfileScreen.tsx`**

Read `/Users/juliokoelle/projects/mywardrobe/src/pages/ProfileScreen.tsx`.

- [ ] **Step 2: Replace hardcoded "Julio Koelle" with real user email + add logout**

Find the section that renders the user's name/profile info. Replace or extend it:

```typescript
import { useAuth } from '@/contexts/AuthContext';
import { LogOut } from 'lucide-react';

// Inside the component:
const { user, signOut } = useAuth();

// Replace hardcoded name with:
<p className="text-base font-semibold">{user?.email ?? '—'}</p>

// Add logout button (e.g. at bottom of page or in header area):
<button
  onClick={signOut}
  className="flex items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-destructive"
>
  <LogOut className="h-4 w-4" />
  Abmelden
</button>
```

- [ ] **Step 3: Commit**

```bash
git add src/pages/ProfileScreen.tsx
git commit -m "feat(auth): ProfileScreen shows real user email + logout button"
```

---

## Task 10: Add VITE env vars to Vercel + deploy

- [ ] **Step 1: Add env vars to Vercel**

In the Vercel dashboard for mywardrobe, or via CLI:
```bash
cd /Users/juliokoelle/projects/mywardrobe
vercel env add VITE_SUPABASE_URL production
# paste the same value as SUPABASE_URL
vercel env add VITE_SUPABASE_ANON_KEY production
# paste the anon/public key from Supabase dashboard
```

- [ ] **Step 2: Build locally with real env vars to verify**

```bash
vercel env pull .env.local
npm run build 2>&1 | tail -10
```

Expected: `✓ built` (no "Missing VITE_SUPABASE_URL" errors).

- [ ] **Step 3: Deploy to production**

```bash
vercel --prod
```

- [ ] **Step 4: Manual smoke test**

1. Open https://mywardrobe-dun.vercel.app — should redirect to `/login`
2. Click "Noch kein Account? Registrieren" — sign up with a test email
3. If email confirmation required: confirm in email inbox
4. Log in → should land on Wardrobe screen
5. Add a wardrobe item → should appear
6. Delete the item → should disappear
7. Add a wishlist item → should appear
8. Delete it → should disappear
9. Log out → should redirect to `/login`
10. Log in again → wardrobe should still contain the added item
11. Open in a second browser with a NEW account → wardrobe should be empty (data isolation)

- [ ] **Step 5: Final commit if any fixes needed**

```bash
git add -A
git commit -m "feat(auth): multi-user Supabase auth complete — MyWardrobe"
```
