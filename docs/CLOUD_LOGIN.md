# Cloud deployment and device sign-in

## Run from your Windows Jupyter session

Extract Vedika-Cloud-Setup.zip into D:\Astro\VedikaCloud and run Deploy_Vedika.py using runpy (the notebook cell is supplied in chat). The script uses Python's standard library; it does not need Docker, Git or a local web server. It opens locally installed Chrome when it can find it; existing browser sessions are reused by Chrome. It does not inspect browser tabs, read passwords or copy browser cookies.

Prerequisites: your own GitHub and Render accounts. The script opens their API-token pages. Enter a GitHub token with public_repo permission and a Render API key only into the local hidden prompts. Enter the chosen app password in the local password prompt, then confirm it. The login username defaults to the username requested in chat. Never paste provider API keys into chat.

The script prepares the source and presents a DEPLOY confirmation before creating a PUBLIC source repository and a single Render web service with plan=free. The public repository contains only allowlisted app source/data/licenses; no birth inputs, app password/hash, cookie key, provider tokens or deployment-state file is uploaded. Authentication secrets are sent to Render's environment configuration over HTTPS. Only non-secret repository/service identifiers and the URL are saved in deployment-state.json so the script can resume without creating duplicate resources.

The script polls the build, verifies that unauthenticated status is false, tests the chosen login and cookie when freshly deployed, and prints/opens the actual HTTPS onrender.com URL returned by Render. API account eligibility, permissions and provider billing-verification requirements can block creation even for the free plan; the script does not select a paid plan as a fallback. Actual account creation/deployment cannot be tested here without the user's accounts and authorization tokens.

## Device behavior

Anyone with the link can open the login page. The shared username and password are needed the first time on each browser/device. An HttpOnly, Secure, SameSite=Lax first-party cookie then keeps that browser signed in for up to 365 days, renewed during active use. Browser storage policy can shorten this. It is not a permanent identity bound to physical hardware. Private browsing, cleared cookies, logout, expiry or password/signing-key changes require sign-in again.

Only the authentication cookie persists. Personal birth details still clear on page refresh/Clear and are not saved as profiles. The cookie has no birth details. Operational cloud-provider logs follow that provider's policy; app access logging is disabled.

Incorrect logins are limited to ten attempts per address per 15-minute window per process. Changing the password hash or signing secret in Render invalidates existing device cookies. Sign out clears the current browser's cookie; a copied/stolen token cannot be individually revoked without rotating the shared secret/password. Account roles, separate user registrations, MFA and administrator/session dashboards are outside this shared-login build.

## Free hosting limits

Official Render documentation checked 12 November 2026: free web services sleep after 15 minutes of inactivity and have monthly compute/bandwidth/build limits. The first visit after sleep may take around a minute. See https://render.com/docs/free and https://render.com/docs/faq . These are hobby/testing resources, not an always-on uptime guarantee.
