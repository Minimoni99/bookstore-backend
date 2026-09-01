# Ebook Store — FastAPI backend

Matches the stack you already use for leadgen: **FastAPI backend** (deploy on
your Hetzner box) + a separate **Next.js frontend** (deploy on Vercel). See
`../bookstore-frontend` for the frontend half.

Storage is plain JSON files under `/data` — no database server needed to get
running. Every data access goes through `app/db.py`, so swapping in Postgres
later touches one file, not the routes.

## 1. Install & run locally

```bash
pip install -r requirements.txt
cp .env.example .env
python seed.py                              # adds one placeholder book
python create_admin.py you@yourdomain.com "a-strong-password"
uvicorn app.main:app --reload --port 8000
```

API docs (auto-generated) live at `http://localhost:8000/docs` — handy for
poking endpoints without the frontend.

Any account that registers through the normal frontend sign-up becomes a
regular customer. Only accounts you promote with `create_admin.py` (or later
via the admin Users page) can reach admin endpoints.

## 2. Card payments (Stripe)

1. Grab your **secret key** from the Stripe dashboard → `STRIPE_SECRET_KEY`.
2. For subscriptions: create a recurring Price in Stripe, put its ID in
   `STRIPE_SUBSCRIPTION_PRICE_ID`. Skip this if you're only selling one-off
   books for now.
3. Add a webhook endpoint in the Stripe dashboard pointing at
   `https://your-backend-domain.com/api/webhooks/stripe`, listening for
   `checkout.session.completed` and `customer.subscription.deleted`. Copy
   the signing secret into `STRIPE_WEBHOOK_SECRET`.
4. **The webhook is what marks an order "paid" and grants the download** — it
   needs to be reachable from the internet. For local testing: `stripe listen
   --forward-to localhost:8000/api/webhooks/stripe`.

## 3. Crypto payments (NOWPayments)

1. Create a NOWPayments account, grab an API key → `NOWPAYMENTS_API_KEY`.
2. Set your IPN callback URL in their dashboard to
   `https://your-backend-domain.com/api/webhooks/nowpayments`, and copy the
   IPN secret into `NOWPAYMENTS_IPN_SECRET`.

Card and crypto are independent — enable just one if you want to start
simpler.

## 4. Deploy to your Hetzner box (same pattern as leadgen)

```bash
pip install -r requirements.txt
# set real env vars (systemd EnvironmentFile, or a proper .env)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Put this behind whatever you already use for the leadgen API (nginx +
systemd, or a process manager like pm2/supervisor). Set `CORS_ORIGINS` to
your actual Vercel domain, and `APP_URL` to your **frontend's** domain (it's
used to build Stripe/NOWPayments redirect URLs back to the site).

The `/data` folder needs to persist across restarts — same volume/disk your
leadgen backend already writes to is fine.

## Project layout

```
app/main.py               – FastAPI app, CORS, router wiring
app/db.py                 – JSON-file data layer
app/auth.py                – JWT sign/verify, current_user / current_admin deps
app/schemas.py             – Pydantic request bodies
app/routes_auth.py         – register / login / me
app/routes_books.py        – public catalog (never exposes downloadUrl)
app/routes_checkout.py     – Stripe + NOWPayments checkout session creation
app/routes_downloads.py    – gated download link (paid order OR active sub)
app/routes_admin.py        – book CRUD, orders/subscriptions/users views
app/routes_webhooks.py     – Stripe + NOWPayments payment confirmation
create_admin.py            – promote/create an admin user from the CLI
seed.py                    – adds one placeholder book on first run
```

## Left for you to decide

- **File delivery**: `downloadUrl` is returned as-is right now. For real
  files, signed/expiring URLs (S3/R2 presigned URLs) are safer than a
  permanent public link — swap that into `routes_downloads.py`.
- **Email** (receipts, password reset) isn't wired up.
- **Database**: JSON files are fine at launch; move to Postgres (or whatever
  you're using for leadgen) once volume grows.
