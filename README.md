# Vedika cloud web app

Five Vedic astrology report sections, English/Hindi/Marathi PDFs and a responsive desktop/mobile interface. Calculations run in this Python server. Personal birth inputs and generated reports are not persisted; users may deliberately download PDFs.

The cloud app is password-gated. Login username, salted PBKDF2 password hash and cookie signing key are configured as server environment variables, never in the repository. Device cookies are Secure/HttpOnly/SameSite=Lax and can keep an active browser signed in for up to one year, with rolling renewal. Clearing cookies, private browsing, logout, expiry or credential/key rotation can require sign-in again.

This source is AGPL-3.0-or-later with third-party notices and corresponding wrapper source. Geographic data and fonts carry their own licenses. No uploaded personal horoscope, original books, passwords, API keys or birth-profile database belong in this repository.

The Docker build decompresses `data/places.sqlite3.gz`, installs Linux Python packages and serves the app. Configure VEDIKA_CLOUD=1, VEDIKA_AUTH_USERNAME, VEDIKA_PASSWORD_HASH and VEDIKA_SESSION_SECRET. Missing authentication configuration fails closed. Render service plan must be explicitly `free`; free-tier sleep, bandwidth/build limits and eligibility apply. No guaranteed uptime or unlimited free hosting is claimed.

Astrological interpretations are traditional indicators, not established health diagnoses or guaranteed marriage/career outcomes.
