# MyWardrobe Pricing & Delete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add delete to the wishlist card, expand price tracking (retail + paid for wardrobe; retail + target for wishlist), show per-item savings on cards, and add a savings summary chip to the wishlist header.

**Architecture:** DB schema extended with two new columns per table (manual Supabase migration). API handlers updated to map new fields. TypeScript types extended. UI: WishlistCard gains delete button + price block redesign with savings badge; ItemDetail gains dual-price savings display; AddItemSheet + AddWishlistSheet gain new price inputs with live savings calculation; WishlistScreen gains savings chip + modal.

**Tech Stack:** Next.js (Vercel), Supabase (Postgres), React, TypeScript, Tailwind CSS, lucide-react, React Query, Radix UI Switch.

**Project:** `/Users/juliokoelle/projects/mywardrobe`

---

## File Map

| File | Change |
|------|--------|
| Supabase (manual) | `ALTER TABLE` for both tables + `UPDATE` to migrate `price` |
| `src/types/wardrobe.ts` | Add `retailPrice?`, `paidPrice?` to `WardrobeItem` |
| `src/types/wishlist.ts` | Add `retailPrice?`, `targetPrice?` to `WishlistItem` |
| `api/items/index.ts` | Map new fields in `mapRow` / `toRow` |
| `api/items/[id].ts` | Map new fields in `mapRow` / `toPartialRow` |
| `api/wishlist/index.ts` | Map new fields in POST body / `mapRow` |
| `api/wishlist/[id].ts` | Map new fields in PUT handler / `mapRow` |
| `src/components/wishlist/WishlistCard.tsx` | Delete button + price block redesign |
| `src/pages/WishlistScreen.tsx` | Wire `onEdit`/`onDelete` + savings chip + modal |
| `src/pages/ItemDetail.tsx` | Dual price + savings display |
| `src/components/add/AddItemSheet.tsx` | UVP + Bezahlt inputs + live savings |
| `src/components/wishlist/AddWishlistSheet.tsx` | UVP + toggle + Zielpreis inputs |

---

## Task 1: Supabase Migration + TypeScript Types

**Files:**
- Modify: `src/types/wardrobe.ts:80`
- Modify: `src/types/wishlist.ts:12`

### Supabase migration (manual step — run in Supabase SQL editor before proceeding)

```sql
ALTER TABLE wardrobe_items
  ADD COLUMN retail_price DECIMAL(10,2),
  ADD COLUMN paid_price   DECIMAL(10,2);

UPDATE wardrobe_items
  SET paid_price = price
  WHERE price IS NOT NULL;

ALTER TABLE wishlist_items
  ADD COLUMN retail_price DECIMAL(10,2),
  ADD COLUMN target_price DECIMAL(10,2);

UPDATE wishlist_items
  SET target_price = price
  WHERE price IS NOT NULL;
```

- [ ] **Step 1: Run the SQL migration** in the Supabase project's SQL editor. Verify: no errors, `wardrobe_items` now has `retail_price` and `paid_price` columns, `wishlist_items` has `retail_price` and `target_price`.

- [ ] **Step 2: Add `retailPrice` and `paidPrice` to `WardrobeItem`**

In `src/types/wardrobe.ts`, after line 80 (`price?: number;`):

```typescript
  price?: number;
  retailPrice?: number;
  paidPrice?: number;
```

- [ ] **Step 3: Add `retailPrice` and `targetPrice` to `WishlistItem`**

In `src/types/wishlist.ts`, after line 12 (`price?: number;`):

```typescript
  price?: number;
  retailPrice?: number;
  targetPrice?: number;
```

- [ ] **Step 4: TypeScript check**

```bash
cd /Users/juliokoelle/projects/mywardrobe && bun run tsc --noEmit
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
cd /Users/juliokoelle/projects/mywardrobe && git add src/types/wardrobe.ts src/types/wishlist.ts && git commit -m "feat(types): add retailPrice/paidPrice to WardrobeItem, retailPrice/targetPrice to WishlistItem"
```

---

## Task 2: API Layer — Wardrobe Items

**Files:**
- Modify: `api/items/index.ts`
- Modify: `api/items/[id].ts`

- [ ] **Step 1: Update `api/items/index.ts` — `mapRow`**

In `mapRow()` (starting at line 42), after `price: row.price ?? undefined,` (line 58):

```typescript
    price: row.price ?? undefined,
    retailPrice: row.retail_price ?? undefined,
    paidPrice:   row.paid_price   ?? undefined,
```

- [ ] **Step 2: Update `api/items/index.ts` — `toRow`**

In `toRow()` (starting at line 67), after `if (body.price !== undefined) row.price = body.price;` (line 82):

```typescript
  if (body.price       !== undefined) row.price        = body.price;
  if (body.retailPrice !== undefined) row.retail_price = body.retailPrice;
  if (body.paidPrice   !== undefined) row.paid_price   = body.paidPrice;
```

- [ ] **Step 3: Update `api/items/[id].ts` — `mapRow`**

In `mapRow()` (starting at line 44), after `price: row.price ?? undefined,` (line 60):

```typescript
    price: row.price ?? undefined,
    retailPrice: row.retail_price ?? undefined,
    paidPrice:   row.paid_price   ?? undefined,
```

- [ ] **Step 4: Update `api/items/[id].ts` — `toPartialRow`**

In `toPartialRow()` (starting at line 69), after `if (body.price !== undefined) row.price = body.price;`:

Find the block that maps `body.price` and add after it:

```typescript
  if (body.price       !== undefined) row.price        = body.price;
  if (body.retailPrice !== undefined) row.retail_price = body.retailPrice;
  if (body.paidPrice   !== undefined) row.paid_price   = body.paidPrice;
```

- [ ] **Step 5: TypeScript check**

```bash
cd /Users/juliokoelle/projects/mywardrobe && bun run tsc --noEmit
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
cd /Users/juliokoelle/projects/mywardrobe && git add api/items/index.ts "api/items/[id].ts" && git commit -m "feat(api): map retailPrice/paidPrice in wardrobe items endpoints"
```

---

## Task 3: API Layer — Wishlist Items

**Files:**
- Modify: `api/wishlist/index.ts`
- Modify: `api/wishlist/[id].ts`

- [ ] **Step 1: Update `api/wishlist/index.ts` — POST body**

In the POST handler inline insert object (around line 30–42), after `price: body.price ?? null,`:

```typescript
        price:        body.price ?? null,
        retail_price: body.retailPrice ?? null,
        target_price: body.targetPrice ?? null,
```

- [ ] **Step 2: Update `api/wishlist/index.ts` — `mapRow`**

In `mapRow()` (starting at line 53), after `price: row.price ?? undefined,` (line 63):

```typescript
    price:       row.price        ?? undefined,
    retailPrice: row.retail_price ?? undefined,
    targetPrice: row.target_price ?? undefined,
```

- [ ] **Step 3: Update `api/wishlist/[id].ts` — PUT handler**

In the PUT handler (starting at line 14), after `if (body.price !== undefined) row.price = body.price;` (line 24):

```typescript
    if (body.price       !== undefined) row.price        = body.price;
    if (body.retailPrice !== undefined) row.retail_price = body.retailPrice;
    if (body.targetPrice !== undefined) row.target_price = body.targetPrice;
```

- [ ] **Step 4: Update `api/wishlist/[id].ts` — `mapRow`**

In `mapRow()` (starting at line 56), after `price: row.price ?? undefined,` (line 66):

```typescript
    price:       row.price        ?? undefined,
    retailPrice: row.retail_price ?? undefined,
    targetPrice: row.target_price ?? undefined,
```

- [ ] **Step 5: TypeScript check**

```bash
cd /Users/juliokoelle/projects/mywardrobe && bun run tsc --noEmit
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
cd /Users/juliokoelle/projects/mywardrobe && git add api/wishlist/index.ts "api/wishlist/[id].ts" && git commit -m "feat(api): map retailPrice/targetPrice in wishlist items endpoints"
```

---

## Task 4: WishlistCard — Delete Button + Price Block Redesign

**Files:**
- Modify: `src/components/wishlist/WishlistCard.tsx`

The card gets three changes: (1) delete button beside the edit button, (2) fixed-height price block replacing the single price span, (3) card layout uses `flex-1` so the info area grows while the price block stays pinned at the bottom.

- [ ] **Step 1: Replace `WishlistCard.tsx` with the new implementation**

```tsx
import { useState } from 'react';
import { ExternalLink, Pencil, Trash2 } from 'lucide-react';
import { WishlistItem, Priority, PRIORITY_LABELS, PRIORITY_COLORS } from '@/types/wishlist';

interface WishlistCardProps {
  item: WishlistItem;
  onMarkPurchased: (id: string) => void;
  onEdit: (item: WishlistItem) => void;
  onDelete: (id: string) => void;
}

const PRIORITY_EMOJI: Record<Priority, string> = { 1: '🔴', 2: '🟡', 3: '🟢' };

const WishlistCard = ({ item, onMarkPurchased, onEdit, onDelete }: WishlistCardProps) => {
  const [confirmPurchase, setConfirmPurchase] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const savings =
    item.retailPrice != null && item.targetPrice != null
      ? item.retailPrice - item.targetPrice
      : null;
  const savingsPct =
    savings != null && item.retailPrice
      ? Math.round((savings / item.retailPrice) * 100)
      : null;

  return (
    <>
      <div
        className="flex flex-col overflow-hidden rounded-xl border border-amber-200 bg-card shadow-sm"
        style={{ borderTopWidth: 3, borderTopColor: PRIORITY_COLORS[item.priority as Priority] }}
      >
        {/* Image */}
        <div className="relative aspect-[3/4] w-full overflow-hidden bg-muted">
          {item.imageUrl ? (
            <img
              src={item.imageUrl}
              alt={item.name}
              className="h-full w-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-4xl">🛍️</div>
          )}
          {/* Priority badge */}
          <span
            className="absolute right-2 top-2 rounded-full px-1.5 py-0.5 text-[10px] font-bold leading-none shadow"
            style={{ backgroundColor: PRIORITY_COLORS[item.priority as Priority], color: '#fff' }}
          >
            {PRIORITY_EMOJI[item.priority as Priority]} {PRIORITY_LABELS[item.priority as Priority]}
          </span>
          {/* Edit + Delete buttons */}
          <div className="absolute left-2 top-2 flex gap-1">
            <button
              onClick={() => onEdit(item)}
              className="flex h-7 w-7 items-center justify-center rounded-md bg-black/55 text-white"
            >
              <Pencil className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => setConfirmDelete(true)}
              className="flex h-7 w-7 items-center justify-center rounded-md bg-black/55 text-white"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* Name + brand — flex-1 keeps cards uniform height */}
        <div className="flex min-h-[52px] flex-1 flex-col gap-1 px-3 pb-2 pt-3">
          <h3 className="truncate text-sm font-semibold leading-tight">{item.name}</h3>
          {item.brand && (
            <span className="text-xs text-muted-foreground">{item.brand}</span>
          )}
        </div>

        {/* Price block — always 66px tall */}
        <div className="flex h-[66px] flex-col justify-center bg-muted/60 px-3">
          {item.retailPrice != null && item.targetPrice != null ? (
            <div className="flex flex-col gap-0.5">
              <div className="flex items-baseline gap-1.5">
                <span className="text-[11px] text-muted-foreground line-through">
                  €{item.retailPrice.toFixed(2)}
                </span>
                <span className="text-sm font-bold text-emerald-500">
                  €{item.targetPrice.toFixed(2)}
                </span>
              </div>
              <span className="inline-flex w-fit items-center rounded bg-emerald-900/40 px-1.5 py-0.5 text-[9px] text-emerald-400">
                Spart €{savings!.toFixed(0)} · {savingsPct}%
              </span>
            </div>
          ) : item.targetPrice != null ? (
            <div className="flex flex-col gap-0.5">
              <span className="text-sm font-bold text-emerald-500">
                €{item.targetPrice.toFixed(2)}
              </span>
              <span className="text-[10px] text-muted-foreground">Zielpreis</span>
            </div>
          ) : item.retailPrice != null ? (
            <div className="flex flex-col gap-0.5">
              <span className="text-sm text-muted-foreground">
                €{item.retailPrice.toFixed(2)}
              </span>
              <span className="text-[10px] text-muted-foreground">UVP</span>
            </div>
          ) : item.price != null ? (
            <span className="text-sm font-bold text-emerald-600">
              €{item.price.toFixed(2)}
            </span>
          ) : (
            <span className="text-center text-[11px] text-muted-foreground/50">Kein Preis</span>
          )}
        </div>

        {/* Action row */}
        <div className="flex items-center gap-1.5 px-3 pb-3 pt-2">
          <button
            onClick={() => setConfirmPurchase(true)}
            className="flex-1 rounded-lg bg-amber-100 px-2 py-1.5 text-xs font-semibold text-amber-800 transition-colors hover:bg-amber-200 active:scale-95"
          >
            ✓ Purchased
          </button>
          {item.sourceUrl && (
            <a
              href={item.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex h-7 w-7 items-center justify-center rounded-lg border text-muted-foreground hover:bg-secondary"
            >
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
        </div>
      </div>

      {/* Purchase confirm dialog */}
      {confirmPurchase && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/30 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-sm rounded-2xl bg-card p-6 shadow-xl">
            <h3 className="mb-1 text-base font-semibold">Move to Wardrobe?</h3>
            <p className="mb-5 text-sm text-muted-foreground">
              <span className="font-medium text-foreground">{item.name}</span> wird aus der Wishlist
              entfernt und in die Wardrobe übertragen.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmPurchase(false)}
                className="flex-1 rounded-xl border py-2.5 text-sm font-medium"
              >
                Abbrechen
              </button>
              <button
                onClick={() => { onMarkPurchased(item.id); setConfirmPurchase(false); }}
                className="flex-1 rounded-xl py-2.5 text-sm font-semibold text-white"
                style={{ backgroundColor: '#d97706' }}
              >
                Moved 🎉
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirm dialog */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/30 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-sm rounded-2xl bg-card p-6 shadow-xl">
            <h3 className="mb-1 text-base font-semibold">"{item.name}" löschen?</h3>
            <p className="mb-5 text-sm text-muted-foreground">
              Dieser Artikel wird dauerhaft aus der Wishlist entfernt.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmDelete(false)}
                className="flex-1 rounded-xl border py-2.5 text-sm font-medium"
              >
                Abbrechen
              </button>
              <button
                onClick={() => { onDelete(item.id); setConfirmDelete(false); }}
                className="flex-1 rounded-xl bg-destructive py-2.5 text-sm font-semibold text-destructive-foreground"
              >
                Löschen
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default WishlistCard;
```

- [ ] **Step 2: TypeScript check**

```bash
cd /Users/juliokoelle/projects/mywardrobe && bun run tsc --noEmit
```

Expected: error about WishlistScreen not passing `onEdit`/`onDelete` props — that's fixed in the next task.

- [ ] **Step 3: Commit**

```bash
cd /Users/juliokoelle/projects/mywardrobe && git add src/components/wishlist/WishlistCard.tsx && git commit -m "feat(wishlist): delete button + fixed-height price block with savings badge on WishlistCard"
```

---

## Task 5: WishlistScreen — Wire onEdit/onDelete + Savings Chip + Modal

**Files:**
- Modify: `src/pages/WishlistScreen.tsx`

WishlistScreen currently does not pass `onEdit` to WishlistCard (line 117–121) and there is no edit state. This task wires up `onEdit`, `onDelete`, adds savings computations, and adds the header chip + modal.

- [ ] **Step 1: Replace `WishlistScreen.tsx` with the new implementation**

```tsx
import { useState } from 'react';
import { Plus, Bookmark, TrendingDown, X } from 'lucide-react';
import AppShell from '@/components/layout/AppShell';
import WishlistCard from '@/components/wishlist/WishlistCard';
import AddWishlistSheet from '@/components/wishlist/AddWishlistSheet';
import { useWishlist } from '@/hooks/useWishlist';
import { useWardrobe } from '@/hooks/useWardrobe';
import { WishlistItem, Priority } from '@/types/wishlist';
import { useToast } from '@/hooks/use-toast';

type PriorityFilter = 'all' | 1 | 2 | 3;

const FILTER_OPTIONS: { value: PriorityFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 1,     label: '🔴 High' },
  { value: 2,     label: '🟡 Medium' },
  { value: 3,     label: '🟢 Low' },
];

const WishlistScreen = () => {
  const { items, isLoading, addItem, markPurchased, editItem: updateWishlistItem, removeItem } = useWishlist();
  const { addItem: addToWardrobe } = useWardrobe();
  const { toast } = useToast();
  const [sheetOpen, setSheetOpen]             = useState(false);
  const [filter, setFilter]                   = useState<PriorityFilter>('all');
  const [editingItem, setEditingItem]         = useState<WishlistItem | undefined>(undefined);
  const [showSavingsModal, setShowSavingsModal] = useState(false);

  const filtered   = filter === 'all' ? items : items.filter((i) => i.priority === filter);
  const totalValue = items.reduce((sum, i) => sum + (i.price ?? 0), 0);

  const totalRetail      = items.reduce((s, i) => s + (i.retailPrice ?? 0), 0);
  const totalTarget      = items.reduce((s, i) => s + (i.targetPrice ?? i.price ?? 0), 0);
  const totalSavings     = totalRetail - totalTarget;
  const itemsWithSavings = items.filter((i) => i.retailPrice != null).length;
  const savingsPct       = totalRetail > 0 ? Math.round((totalSavings / totalRetail) * 100) : 0;

  const handleMarkPurchased = async (id: string) => {
    const item = items.find((i) => i.id === id);
    if (!item) return;

    await markPurchased(id);

    await addToWardrobe({
      name: item.name,
      brand: item.brand,
      imageUrl: item.imageUrl,
      categoryGender: 'Unisex',
      categoryMain: 'Tops',
      colors: [],
      size: item.size ?? 'M',
      tags: [],
      notes: item.notes,
      price: item.price,
      quantity: 1,
      favorite: false,
      sourceUrl: item.sourceUrl,
    });

    toast({ title: 'Moved to Wardrobe 🎉', description: item.name });
  };

  const handleEdit = (item: WishlistItem) => {
    setEditingItem(item);
    setSheetOpen(true);
  };

  const handleSheetClose = (open: boolean) => {
    setSheetOpen(open);
    if (!open) setEditingItem(undefined);
  };

  return (
    <>
      <AppShell>
        <div className="flex flex-col gap-4 px-4 pb-32 pt-4">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Wishlist</p>
              {totalValue > 0 && !totalSavings && (
                <p className="mt-0.5 text-xs font-semibold text-emerald-600">
                  Total: €{totalValue.toFixed(2)}
                </p>
              )}
            </div>
            <div className="flex items-center gap-2">
              {totalSavings > 0 && (
                <button
                  onClick={() => setShowSavingsModal(true)}
                  className="flex items-center gap-1.5 rounded-lg bg-emerald-950 px-2.5 py-1 text-xs font-semibold text-emerald-400"
                >
                  <TrendingDown size={12} />
                  Spart €{totalSavings.toFixed(0)}
                </button>
              )}
              <span className="text-xs text-muted-foreground">{items.length} items</span>
            </div>
          </div>

          {/* Priority filter */}
          {items.length > 0 && (
            <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
              {FILTER_OPTIONS.map((opt) => (
                <button
                  key={String(opt.value)}
                  onClick={() => setFilter(opt.value)}
                  className={`flex-shrink-0 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                    filter === opt.value
                      ? 'border-amber-400 bg-amber-50 text-amber-800'
                      : 'border-border bg-card text-foreground hover:bg-secondary'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}

          {/* Empty state */}
          {!isLoading && items.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-center gap-4">
              <div className="flex h-20 w-20 items-center justify-center rounded-full bg-amber-50">
                <Bookmark className="h-9 w-9 text-amber-400" strokeWidth={1.2} />
              </div>
              <div>
                <p className="text-base font-semibold">Wishlist is empty</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Füge Produkte hinzu, die du haben möchtest.
                </p>
              </div>
              <button
                onClick={() => setSheetOpen(true)}
                className="mt-2 rounded-xl px-5 py-2.5 text-sm font-semibold text-white"
                style={{ backgroundColor: '#d97706' }}
              >
                + Erstes Item hinzufügen
              </button>
            </div>
          )}

          {/* Grid */}
          {filtered.length > 0 && (
            <div className="grid grid-cols-2 gap-3">
              {filtered.map((item) => (
                <WishlistCard
                  key={item.id}
                  item={item}
                  onMarkPurchased={handleMarkPurchased}
                  onEdit={handleEdit}
                  onDelete={removeItem}
                />
              ))}
            </div>
          )}

          {/* No results for filter */}
          {!isLoading && items.length > 0 && filtered.length === 0 && (
            <p className="py-12 text-center text-sm text-muted-foreground">
              Keine Items in dieser Priorität.
            </p>
          )}
        </div>
      </AppShell>

      {/* FAB */}
      {items.length > 0 && (
        <button
          onClick={() => setSheetOpen(true)}
          className="fixed bottom-24 right-4 z-30 flex h-12 w-12 items-center justify-center rounded-full shadow-lg text-white transition-transform hover:scale-105 active:scale-95"
          style={{ backgroundColor: '#d97706' }}
          aria-label="Add to wishlist"
        >
          <Plus className="h-6 w-6" />
        </button>
      )}

      <AddWishlistSheet
        open={sheetOpen}
        onOpenChange={handleSheetClose}
        onSave={addItem}
        editItem={editingItem}
        onUpdate={updateWishlistItem}
      />

      {/* Savings modal */}
      {showSavingsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/30 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-sm rounded-2xl bg-card p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-base font-semibold">Ersparnis-Übersicht</h3>
              <button
                onClick={() => setShowSavingsModal(false)}
                className="rounded-full p-1 hover:bg-secondary"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="flex flex-col gap-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Artikel gesamt</span>
                <span>{items.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Mit UVP</span>
                <span>{itemsWithSavings}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Gesamtwert (UVP)</span>
                <span>€{totalRetail.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Zielpreis gesamt</span>
                <span>€{totalTarget.toFixed(2)}</span>
              </div>
              <div className="mt-2 border-t pt-3">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-emerald-400">Erwartete Ersparnis</span>
                  <span className="text-xl font-extrabold text-emerald-400">
                    €{totalSavings.toFixed(2)}
                  </span>
                </div>
                <p className="mt-0.5 text-right text-xs text-emerald-400">
                  {savingsPct}% unter UVP
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default WishlistScreen;
```

- [ ] **Step 2: TypeScript check**

```bash
cd /Users/juliokoelle/projects/mywardrobe && bun run tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd /Users/juliokoelle/projects/mywardrobe && git add src/pages/WishlistScreen.tsx && git commit -m "feat(wishlist): wire onEdit/onDelete, add savings chip and summary modal to WishlistScreen"
```

---

## Task 6: ItemDetail — Dual Price Display

**Files:**
- Modify: `src/pages/ItemDetail.tsx`

The `Attribute` component at line 34 already handles `undefined` gracefully (returns null). We replace the single `price` display at line 117 with a conditional dual-price block.

- [ ] **Step 1: Replace the single price attribute line in `ItemDetail.tsx`**

Find and replace this block (around line 117):

```tsx
          {item.price != null && <Attribute label="Price" value={`€${item.price.toFixed(2)}`} />}
```

Replace with:

```tsx
          {/* Dual price: paidPrice + retailPrice with savings */}
          {item.paidPrice != null && item.retailPrice == null && (
            <Attribute label="Bezahlt" value={`€${item.paidPrice.toFixed(2)}`} />
          )}
          {item.paidPrice != null && item.retailPrice != null && (
            <>
              <Attribute label="UVP" value={`€${item.retailPrice.toFixed(2)}`} />
              <Attribute label="Bezahlt" value={`€${item.paidPrice.toFixed(2)}`} />
              <div className="flex flex-col gap-0.5">
                <dt className="text-xs text-muted-foreground">Gespart</dt>
                <dd className="text-sm font-medium text-emerald-500">
                  €{(item.retailPrice - item.paidPrice).toFixed(2)}{' '}
                  ({Math.round(((item.retailPrice - item.paidPrice) / item.retailPrice) * 100)}%)
                </dd>
              </div>
            </>
          )}
          {item.retailPrice != null && item.paidPrice == null && (
            <Attribute label="UVP" value={`€${item.retailPrice.toFixed(2)}`} />
          )}
          {item.price != null && item.paidPrice == null && item.retailPrice == null && (
            <Attribute label="Preis" value={`€${item.price.toFixed(2)}`} />
          )}
```

- [ ] **Step 2: TypeScript check**

```bash
cd /Users/juliokoelle/projects/mywardrobe && bun run tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd /Users/juliokoelle/projects/mywardrobe && git add src/pages/ItemDetail.tsx && git commit -m "feat(wardrobe): dual price display with savings in ItemDetail"
```

---

## Task 7: AddItemSheet — UVP + Bezahlt Price Fields

**Files:**
- Modify: `src/components/add/AddItemSheet.tsx`

The current form has a single `price` input with a currency toggle (lines 331–354). We replace it with two separate fields (`retailPrice` / `paidPrice`) and add a live savings line. The legacy `price` state is kept for the `onSave` payload to avoid breaking existing API behavior while users transition.

- [ ] **Step 1: Add `retailPrice` and `paidPrice` state after the existing `price` state (line 45)**

```tsx
  const [price, setPrice] = useState(editItem?.price != null ? String(editItem.price) : '');
  const [retailPrice, setRetailPrice] = useState(
    editItem?.retailPrice != null ? String(editItem.retailPrice) : ''
  );
  const [paidPrice, setPaidPrice] = useState(
    editItem?.paidPrice != null ? String(editItem.paidPrice) : ''
  );
```

- [ ] **Step 2: Update the `useEffect` that resets form state (starting line 57) to also reset the new fields**

In the `useEffect` block, after `setPrice(editItem?.price != null ? String(editItem.price) : '');` (line 68), add:

```tsx
    setRetailPrice(editItem?.retailPrice != null ? String(editItem.retailPrice) : '');
    setPaidPrice(editItem?.paidPrice != null ? String(editItem.paidPrice) : '');
```

- [ ] **Step 3: Update `resetForm()` to reset the new fields**

Find `resetForm` (around line 158). After the `setPrice('')` call, add:

```tsx
    setRetailPrice('');
    setPaidPrice('');
```

- [ ] **Step 4: Update `handleSave` to include new fields in the payload**

In `handleSave` (around line 123), find where `priceNum` is built and the `onSave` call. Change the payload to include:

```tsx
    const priceNum       = price.trim()       ? parseFloat(price.replace(',', '.'))       : undefined;
    const retailPriceNum = retailPrice.trim() ? parseFloat(retailPrice.replace(',', '.')) : undefined;
    const paidPriceNum   = paidPrice.trim()   ? parseFloat(paidPrice.replace(',', '.'))   : undefined;
```

And in the object passed to `onSave`, add alongside `price: priceNum`:

```tsx
      price:       priceNum,
      retailPrice: retailPriceNum,
      paidPrice:   paidPriceNum,
```

- [ ] **Step 5: Replace the Price input block (lines 331–354) with the two new fields**

Find and replace the entire `{/* Price */}` block:

```tsx
            {/* Price */}
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Price</label>
              <div className="flex gap-2">
                <div className="relative flex flex-1 items-center">
                  <span className="absolute left-3 text-sm text-muted-foreground">{currency === 'EUR' ? '€' : '$'}</span>
                  <input
                    type="number"
                    value={price}
                    onChange={e => setPrice(e.target.value)}
                    placeholder="0"
                    min="0"
                    step="0.01"
                    className="w-full rounded-lg border bg-card py-2.5 pl-8 pr-3 text-sm outline-none focus:ring-1 focus:ring-ring"
                  />
                </div>
                <button
                  onClick={() => setCurrency(currency === 'EUR' ? 'USD' : 'EUR')}
                  className="rounded-lg border bg-card px-3 text-xs font-medium transition-colors hover:bg-secondary"
                >
                  {currency}
                </button>
              </div>
            </div>
```

Replace with:

```tsx
            {/* UVP (Neupreis) */}
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                Neupreis (UVP)
              </label>
              <div className="relative flex items-center">
                <span className="absolute left-3 text-sm text-muted-foreground">€</span>
                <input
                  type="number"
                  value={retailPrice}
                  onChange={(e) => setRetailPrice(e.target.value)}
                  placeholder="0"
                  min="0"
                  step="0.01"
                  className="w-full rounded-lg border bg-card py-2.5 pl-8 pr-3 text-sm outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <p className="mt-1 text-[10px] text-muted-foreground">Optional — Referenzpreis</p>
            </div>

            {/* Bezahlt */}
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                Bezahlt
              </label>
              <div className="relative flex items-center">
                <span className="absolute left-3 text-sm text-muted-foreground">€</span>
                <input
                  type="number"
                  value={paidPrice}
                  onChange={(e) => setPaidPrice(e.target.value)}
                  placeholder="0"
                  min="0"
                  step="0.01"
                  className="w-full rounded-lg border bg-card py-2.5 pl-8 pr-3 text-sm outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <p className="mt-1 text-[10px] text-muted-foreground">z. B. Vinted-Preis</p>
              {retailPrice && paidPrice &&
               parseFloat(retailPrice) > 0 &&
               parseFloat(paidPrice) > 0 &&
               parseFloat(retailPrice) > parseFloat(paidPrice) && (
                <p className="mt-1 text-[10px] font-medium text-emerald-500">
                  Ersparnis: €{(parseFloat(retailPrice) - parseFloat(paidPrice)).toFixed(0)} (
                  {Math.round(
                    ((parseFloat(retailPrice) - parseFloat(paidPrice)) / parseFloat(retailPrice)) * 100,
                  )}
                  %)
                </p>
              )}
            </div>
```

- [ ] **Step 6: TypeScript check**

```bash
cd /Users/juliokoelle/projects/mywardrobe && bun run tsc --noEmit
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
cd /Users/juliokoelle/projects/mywardrobe && git add src/components/add/AddItemSheet.tsx && git commit -m "feat(wardrobe): UVP + Bezahlt price fields with live savings in AddItemSheet"
```

---

## Task 8: AddWishlistSheet — UVP + Toggle + Zielpreis Fields

**Files:**
- Modify: `src/components/wishlist/AddWishlistSheet.tsx`

The current form has a single `price` state (line 26) and single "Preis (€)" input (lines 147–158). We replace it with three new fields: `retailPrice` (UVP), `buyAtRetail` (toggle), `targetPrice` (Zielpreis), and a live savings preview.

- [ ] **Step 1: Add `Switch` import**

At the top of `AddWishlistSheet.tsx`, add to the existing imports:

```tsx
import { Switch } from '@/components/ui/switch';
```

- [ ] **Step 2: Add three new state variables after `const [price, setPrice] = useState('');` (line 26)**

```tsx
  const [price, setPrice]               = useState('');
  const [retailPrice, setRetailPrice]   = useState('');
  const [buyAtRetail, setBuyAtRetail]   = useState(false);
  const [targetPrice, setTargetPrice]   = useState('');
```

- [ ] **Step 3: Update the `useEffect` reset block (lines 35–48) to load and reset the new fields**

In the `if (editItem)` branch, after `setPrice(editItem.price != null ? String(editItem.price) : '');` (line 42), add:

```tsx
      setRetailPrice(editItem.retailPrice != null ? String(editItem.retailPrice) : '');
      setTargetPrice(editItem.targetPrice != null ? String(editItem.targetPrice) : '');
      setBuyAtRetail(false);
```

In the `else` branch, after `setPrice('');` (line 47), add:

```tsx
      setRetailPrice(''); setBuyAtRetail(false); setTargetPrice('');
```

- [ ] **Step 4: Compute `effectiveTargetPrice` and update `handleSave` payload**

In `handleSave` (line 72), before building the payload, add:

```tsx
    const effectiveTargetPrice = buyAtRetail
      ? (parseFloat(retailPrice) || undefined)
      : (parseFloat(targetPrice) || undefined);
    const retailPriceNum = parseFloat(retailPrice) || undefined;
```

In the payload object, after `price: price ? parseFloat(price) : undefined,`, add:

```tsx
        price:       price ? parseFloat(price) : undefined,
        retailPrice: retailPriceNum,
        targetPrice: effectiveTargetPrice,
```

- [ ] **Step 5: Replace the single "Preis (€)" input block (lines 147–158) with the three new fields**

Find and replace the entire `{/* Price */}` block:

```tsx
          {/* Price */}
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">Preis (€)</label>
            <input
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="89.99"
              type="number"
              inputMode="decimal"
              className="w-full rounded-xl border bg-background px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-amber-400"
            />
          </div>
```

Replace with:

```tsx
          {/* UVP (Neupreis) */}
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Neupreis (UVP)
            </label>
            <input
              value={retailPrice}
              onChange={(e) => setRetailPrice(e.target.value)}
              placeholder="120.00"
              type="number"
              inputMode="decimal"
              className="w-full rounded-xl border bg-background px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-amber-400"
            />
          </div>

          {/* Kaufe zum Neupreis toggle */}
          <div className="flex items-center justify-between rounded-xl border bg-background px-3 py-2.5">
            <span className="text-sm text-muted-foreground">Kaufe zum Neupreis</span>
            <Switch checked={buyAtRetail} onCheckedChange={setBuyAtRetail} />
          </div>

          {/* Zielpreis */}
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Zielpreis
            </label>
            <div className="relative">
              <input
                value={buyAtRetail ? (retailPrice || '') : targetPrice}
                onChange={(e) => !buyAtRetail && setTargetPrice(e.target.value)}
                disabled={buyAtRetail}
                placeholder={buyAtRetail ? '= UVP' : '60.00'}
                type="number"
                inputMode="decimal"
                className="w-full rounded-xl border bg-background px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-amber-400 disabled:opacity-50"
              />
              {buyAtRetail && (
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                  = UVP
                </span>
              )}
            </div>
            {!buyAtRetail && retailPrice && targetPrice &&
             parseFloat(retailPrice) > 0 &&
             parseFloat(targetPrice) > 0 &&
             parseFloat(retailPrice) > parseFloat(targetPrice) && (
              <p className="mt-1 text-[10px] font-medium text-emerald-500">
                Erwartete Ersparnis: €
                {(parseFloat(retailPrice) - parseFloat(targetPrice)).toFixed(0)} (
                {Math.round(
                  ((parseFloat(retailPrice) - parseFloat(targetPrice)) /
                    parseFloat(retailPrice)) *
                    100,
                )}
                %)
              </p>
            )}
          </div>
```

- [ ] **Step 6: TypeScript check**

```bash
cd /Users/juliokoelle/projects/mywardrobe && bun run tsc --noEmit
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
cd /Users/juliokoelle/projects/mywardrobe && git add src/components/wishlist/AddWishlistSheet.tsx && git commit -m "feat(wishlist): UVP + toggle + Zielpreis fields with live savings in AddWishlistSheet"
```

---

## Final Verification

- [ ] **Run full TypeScript check**

```bash
cd /Users/juliokoelle/projects/mywardrobe && bun run tsc --noEmit
```

Expected: no errors across all files.

- [ ] **Run test suite**

```bash
cd /Users/juliokoelle/projects/mywardrobe && bun run test
```

- [ ] **Start dev server and verify manually**

```bash
cd /Users/juliokoelle/projects/mywardrobe && bun run dev
```

Checklist:
1. Wishlist: Edit button (pencil) and Delete button (trash) appear on each card overlay
2. Delete button shows confirmation modal with item name, Abbrechen + Löschen
3. Löschen removes item from list
4. WishlistCard price block is always 66px tall regardless of which prices are set
5. When both UVP + Zielpreis set: shows crossed-out UVP, green Zielpreis, savings badge
6. Savings chip appears in WishlistScreen header when totalSavings > 0
7. Savings chip opens modal with correct breakdown
8. AddWishlistSheet: UVP + toggle + Zielpreis fields; toggle mirrors Zielpreis = UVP; live savings preview
9. AddItemSheet: Neupreis (UVP) + Bezahlt fields replace old single price; live savings preview
10. ItemDetail (wardrobe item): shows UVP + Bezahlt + savings when both set; graceful fallback when only one or neither
