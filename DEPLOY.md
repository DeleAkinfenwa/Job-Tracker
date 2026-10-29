# Deploying Job Tracker for free

This guide puts the whole project online at no cost. It takes about 30 minutes, and you don't need a credit card
for any of these services' free plans at the time of writing.

| Part | Host | What you'll get |
|---|---|---|
| Database | [Neon](https://neon.tech) | A PostgreSQL connection string |
| API | [Render](https://render.com) | A URL like `https://job-tracker-django.onrender.com` |
| Website | [Netlify](https://netlify.com) | A URL like `https://job-tracker-dele.netlify.app` |

Before you start, push this project to a GitHub repository. Render and Netlify both deploy straight from GitHub,
and redeploy automatically whenever you push.

## 1. Create the database on Neon

1. Sign up at [neon.tech](https://neon.tech) (signing in with GitHub is quickest).
2. Create a project. Any name and region work; pick the region closest to where you'll host the API.
3. On the project dashboard, click **Connect** and copy the connection string. It looks like
   `postgresql://user:password@ep-something.neon.tech/neondb?sslmode=require`.

Keep this string private: it's the password to your database.

## 2. Deploy the API on Render

1. Sign up at [render.com](https://render.com) with your GitHub account.
2. Click **New → Blueprint** and choose your repository. Render reads `render.yaml` and sets up the service.
3. When it asks for environment variables:
   - `DATABASE_URL`: paste the Neon connection string.
   - `CORS_ALLOWED_ORIGINS`: enter `http://localhost:5173` for now. You'll change it in step 4.
4. Click **Apply** and wait for the first deploy to finish (a few minutes).
5. Open `https://<your-service>.onrender.com/api/docs/`. If you see the API documentation, it's working.

On every start, the server sets up the database tables and resets the demo account, so there's nothing else to run.

To use the Django admin, open the service's **Shell** tab and run `python manage.py createsuperuser`, then go to
`/admin/`.

## 3. Deploy the website on Netlify

1. Sign up at [netlify.com](https://netlify.com) with your GitHub account.
2. Click **Add new site → Import an existing project** and choose your repository. Netlify reads `netlify.toml`,
   so the build settings are filled in for you.
3. Under **Environment variables**, add `VITE_API_URL` with your Render URL, for example
   `https://job-tracker-django.onrender.com` (no slash at the end).
4. Click **Deploy**. When it's done, Netlify gives you a URL. You can change the name under
   **Site configuration → Change site name**.

## 4. Connect the two

The API only accepts requests from websites it knows about, so tell it your Netlify address:

1. In Render, open your service, go to **Environment**, and set `CORS_ALLOWED_ORIGINS` to your Netlify URL, for
   example `https://job-tracker-dele.netlify.app` (no slash at the end).
2. Save. Render redeploys automatically.

Now open your Netlify URL and click **Explore the demo**.

## Good to know

- **The API sleeps when idle.** Render's free plan pauses the API after about 15 minutes without visitors. The next
  visit wakes it, which takes up to a minute; the website shows a "waking up the server" message meanwhile.
- **Neon's free plan** also pauses the database when idle and wakes it in about a second, so you won't notice.
- **Free plans change.** If a step above no longer matches what you see, check the host's current free plan.

## Troubleshooting

| What you see | Likely cause |
|---|---|
| Website says it can't reach the server, but `/api/docs/` works | `CORS_ALLOWED_ORIGINS` on Render doesn't exactly match your Netlify URL (check `https`, and no slash at the end) |
| Website calls `localhost:8000` | `VITE_API_URL` wasn't set on Netlify before the build. Set it, then **Deploys → Trigger deploy** |
| Render deploy fails while connecting to the database | `DATABASE_URL` is missing or was copied incompletely |
| Refreshing a page on the website gives "Page not found" | `netlify.toml` is missing from the repository root |
