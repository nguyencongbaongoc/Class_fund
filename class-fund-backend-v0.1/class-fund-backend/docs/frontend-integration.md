# Frontend integration examples

## Upload receipt

```ts
const form = new FormData();
form.append("file", file);
form.append("uploader_name", displayName);

const res = await fetch(`${API}/api/v1/uploads`, {
  method: "POST",
  body: form,
});
const upload = await res.json();
// upload.id, upload.status
```

Frontend sau đó poll:

```ts
const state = await fetch(`${API}/api/v1/uploads/${upload.id}`).then(r => r.json());
// PENDING | PROCESSING | NEEDS_REVIEW | VERIFIED | DUPLICATE | REJECTED
```

## Fund dashboard

```ts
const fund = await fetch(`${API}/api/v1/public/fund`).then(r => r.json());
// fund.current_balance is authoritative; do not recompute it client-side.
```

## Manual debit

```ts
await fetch(`${API}/api/v1/fund/debit`, {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json",
    "Idempotency-Key": crypto.randomUUID(),
  },
  body: JSON.stringify({
    account_id,
    amount: 120000,
    currency: "VND",
    note: "Mua dụng cụ",
  }),
});
```

## Revert UI

Frontend chỉ gửi `reason` + `Idempotency-Key`; không sửa trực tiếp amount/status/balance.
