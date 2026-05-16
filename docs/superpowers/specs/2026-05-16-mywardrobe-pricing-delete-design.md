# MyWardrobe — Pricing & Delete v1 Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add delete to the wishlist card, expand price tracking (retail + paid for wardrobe; retail + target for wishlist), show per-item savings on cards, and add a savings summary button to the wishlist header.

**Architecture:** DB schema extended with two new columns per table. API handlers updated to map new fields. Types updated. UI: WishlistCard gains delete button + price block redesign; ItemDetail gains dual-price display; AddItemSheet + AddWishlistSheet gain new price inputs with live savings calculation; WishlistScreen header gains savings chip + modal.

**Tech Stack:** Next.js (Vercel), Supabase (Postgres), React, TypeScript, Tailwind CSS, lucide-react, React Query.

**Project:** `/Users/juliokoelle/projects/mywardrobe`

---

## Data Model Changes

### `wardrobe_items` table

Add two columns:

```sql
ALTER TABLE wardrobe_items
  ADD COLUMN retail_price DECIMAL(10,2),
  ADD COLUMN paid_price   DECIMAL(10,2);

UPDATE wardrobe_items
SET paid_price = price
WHERE price IS NOT NULL;
```

Existing `price` column is kept but ignored in new UI (paid_price takes over). The `price` column is not dropped to avoid breaking any external reads.

### `wishlist_items` table

Add two columns:

```sql
ALTER TABLE wishlist_items
  ADD COLUMN retail_price DECIMAL(10,2),
  ADD COLUMN target_price DECIMAL(10,2);

UPDATE wishlist_items
SET target_price = price
WHERE price IS NOT NULL;
```

Same approach: `price` column kept for backward compat, `target_price` is the active field.

---

## Type Changes

### `src/types/wardrobe.ts`

Add to `WardrobeItem`:
```typescript
retailPrice?: number;  // UVP / original retail price
paidPrice?: number;    // What was actually paid (e.g. Vinted)
```

### `src/types/wishlist.ts`

Add to `WishlistItem`:
```typescript
retailPrice?: number;  // UVP reference price
targetPrice?: number;  // Expected purchase price
```

---

## API Changes

### `api/items/index.ts` and `api/items/[id].ts`

In `mapRow()` (DB → JS):
```typescript
retailPrice: row.retail_price ?? undefined,
paidPrice:   row.paid_price   ?? undefined,
```

In `toRow()` / `toPartialRow()` (JS → DB):
```typescript
if (body.retailPrice !== undefined) row.retail_price = body.retailPrice;
if (body.paidPrice   !== undefined) row.paid_price   = body.paidPrice;
```

### `api/wishlist/index.ts` and `api/wishlist/[id].ts`

Same pattern:
```typescript
// mapRow:
retailPrice: row.retail_price  ?? undefined,
targetPrice: row.target_price  ?? undefined,

// toRow / body handling:
if (body.retailPrice !== undefined) row.retail_price = body.retailPrice;
if (body.targetPrice !== undefined) row.target_price = body.targetPrice;
```

---

## UI Changes

### 1. WishlistCard — Delete button + price block

**File:** `src/components/wishlist/WishlistCard.tsx`

**Delete button:** Add `Trash2` from `lucide-react` as a 28×28px icon button top-left, next to the existing `Pencil` button. Both use the same style: `bg-black/55 rounded-md`. Delete triggers a confirmation modal before calling `removeItem(item.id)`.

Confirmation modal text:
> **"{item.name}" löschen?**
> Dieser Artikel wird dauerhaft aus der Wishlist entfernt.
> [Abbrechen] [Löschen]

**Price block:** Replace the existing single price display with a fixed-height block (height: `66px`, `bg` one shade darker than card). The block always occupies the same space regardless of which prices are set:

| State | Display |
|-------|---------|
| `retailPrice` + `targetPrice` | UVP crossed out (gray) · Zielpreis (emerald) · "Spart €X · Y%" badge |
| only `targetPrice` | Zielpreis (emerald) · "Zielpreis" label |
| only `retailPrice` | UVP (gray) · "UVP" label |
| neither | "Kein Preis" centered in gray |

Savings badge style: `bg-emerald-900/40 text-emerald-400 text-[9px] rounded px-1.5 py-0.5`

Savings calculation: `savings = retailPrice - targetPrice`, `pct = Math.round((savings / retailPrice) * 100)`

### 2. WishlistCard — Card size stays uniform

The card frame must have a fixed height regardless of price block state. Use flexbox column layout with `flex: 1` on the content area and `mt-auto` on the price block, so image and name area always take the same space.

### 3. ItemDetail — Dual price display (wardrobe)

**File:** `src/pages/ItemDetail.tsx`

Replace the single `price` attribute display with:

```tsx
// Only paidPrice set
{item.paidPrice != null && item.retailPrice == null && (
  <Attribute label="Bezahlt" value={`€${item.paidPrice.toFixed(2)}`} />
)}

// Both set — show savings
{item.paidPrice != null && item.retailPrice != null && (
  <div className="...">
    <Attribute label="UVP" value={`€${item.retailPrice.toFixed(2)}`} strikethrough />
    <Attribute label="Bezahlt" value={`€${item.paidPrice.toFixed(2)}`} highlight="emerald" />
    <div className="text-emerald-400 text-xs">
      Gespart: €{(item.retailPrice - item.paidPrice).toFixed(2)}
      ({Math.round(((item.retailPrice - item.paidPrice) / item.retailPrice) * 100)}%)
    </div>
  </div>
)}

// Only retailPrice set
{item.retailPrice != null && item.paidPrice == null && (
  <Attribute label="UVP" value={`€${item.retailPrice.toFixed(2)}`} />
)}
```

### 4. AddItemSheet — Wardrobe form price fields

**File:** `src/components/add/AddItemSheet.tsx`

Replace the single price input with two fields:

**UVP (Neupreis)** — optional, labeled "Neupreis (UVP)", hint "Optional — Referenzpreis"

**Bezahlt** — optional, labeled "Bezahlt", e.g. "z. B. Vinted-Preis"

Below both fields, show live savings when both are filled:
```
Ersparnis: €75 (63%)   ← emerald text, only visible when both set
```

State: `const [retailPrice, setRetailPrice] = useState(...)` and `const [paidPrice, setPaidPrice] = useState(...)`

On save: include `retailPrice` and `paidPrice` in the item payload.

### 5. AddWishlistSheet — Wishlist form price fields

**File:** `src/components/wishlist/AddWishlistSheet.tsx`

Replace single price input with:

**UVP (Neupreis)** — optional number input

**Toggle "Kaufe zum Neupreis"** — `Switch` component (existing Radix/Tailwind pattern in project). When ON, `targetPrice` input is disabled and mirrored to `retailPrice` value. Label: "Kaufe zum Neupreis".

**Zielpreis** — number input; disabled + shows "= UVP" suffix when toggle is ON.

Below Zielpreis, show live savings when both `retailPrice` and `targetPrice` are set:
```
Erwartete Ersparnis: €60 (50%)   ← emerald text
```

State:
```typescript
const [retailPrice, setRetailPrice] = useState('');
const [buyAtRetail, setBuyAtRetail] = useState(false);
const [targetPrice, setTargetPrice] = useState('');

const effectiveTargetPrice = buyAtRetail
  ? parseFloat(retailPrice) || undefined
  : parseFloat(targetPrice) || undefined;
```

On save: include `retailPrice` and `targetPrice: effectiveTargetPrice`.

### 6. WishlistScreen — Savings header chip + modal

**File:** `src/pages/WishlistScreen.tsx`

**Header chip:** In the screen header, add a green chip next to the "Wishlist" title:

```tsx
const totalRetail = items.reduce((s, i) => s + (i.retailPrice ?? 0), 0);
const totalTarget = items.reduce((s, i) => s + (i.targetPrice ?? i.price ?? 0), 0);
const totalSavings = totalRetail - totalTarget;
const itemsWithSavings = items.filter(i => i.retailPrice != null).length;
```

Only show chip when `totalSavings > 0`:
```tsx
<button
  onClick={() => setShowSavingsModal(true)}
  className="bg-emerald-950 text-emerald-400 text-xs font-semibold px-2.5 py-1 rounded-lg flex items-center gap-1.5"
>
  <TrendingDown size={12} />
  Spart €{totalSavings.toFixed(0)}
</button>
```

**Modal content** — centered overlay modal using the same `fixed inset-0 bg-black/70` + centered card pattern as the existing delete confirmation modal in ItemDetail:

| Row | Value |
|-----|-------|
| Artikel gesamt | `items.length` |
| Mit UVP | `itemsWithSavings` |
| Gesamtwert (UVP) | `€{totalRetail.toFixed(2)}` |
| Zielpreis gesamt | `€{totalTarget.toFixed(2)}` |
| **Erwartete Ersparnis** | **`€{totalSavings.toFixed(2)}`** (emerald, large) |
| % unter UVP | `{pct}%` (emerald, small) |

---

## File Changes Summary

| File | Change |
|------|--------|
| Supabase (manual) | `ALTER TABLE` for both tables + `UPDATE` to migrate `price` |
| `src/types/wardrobe.ts` | Add `retailPrice?`, `paidPrice?` |
| `src/types/wishlist.ts` | Add `retailPrice?`, `targetPrice?` |
| `api/items/index.ts` | Map new fields in `mapRow` / `toRow` |
| `api/items/[id].ts` | Map new fields in `mapRow` / `toPartialRow` |
| `api/wishlist/index.ts` | Map new fields |
| `api/wishlist/[id].ts` | Map new fields |
| `src/components/wishlist/WishlistCard.tsx` | Delete button + price block redesign |
| `src/pages/ItemDetail.tsx` | Dual price + savings display |
| `src/components/add/AddItemSheet.tsx` | UVP + Bezahlt inputs + live savings |
| `src/components/wishlist/AddWishlistSheet.tsx` | UVP + toggle + Zielpreis inputs |
| `src/pages/WishlistScreen.tsx` | Savings chip + modal |

---

## Out of Scope

- Wardrobe grid card (ItemCard.tsx): unchanged, still shows `paidPrice ?? price`
- Currency handling: all prices assumed EUR, no currency selector changes
- Price history / tracking over time
- Bulk edit of prices
