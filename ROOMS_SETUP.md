# Rooms backend setup (Firebase Realtime Database)

The map stays hosted on GitHub Pages. Firebase is only used for small shared room state: room membership, roles, match timer state, question history/cooldown, and shared search constraints.

## 1. Create a Firebase project

1. Go to the Firebase console and create a project.
2. Register a **Web** app in that project.
3. Copy the Firebase configuration object shown for the web app.

## 2. Create Realtime Database

1. Open **Realtime Database** in the Firebase console.
2. Create a database.
3. Copy its database URL. The web config used by this site must include `databaseURL`.

## 3. Enable anonymous sign-in

1. Open **Authentication**.
2. Open **Sign-in method**.
3. Enable **Anonymous**.
4. Add the GitHub Pages hostname to Authentication's authorized domains if Firebase asks for it.

## 4. Install the room security rules

Open Realtime Database > Rules and replace the rules with the contents of `firebase.rules.json`, then publish them.

These starter prototype rules require Firebase Authentication and allow authenticated players who know a room code to join it. Once someone is a room member, the client trusts them with room-state writes. That is appropriate for the current friends-only prototype; we can harden per-role/per-action permissions before treating rooms as an untrusted public service.

## 5. Add the web config to this repo

Edit `firebase-config.js` and replace:

```js
window.BIGWALK_FIREBASE_CONFIG = null;
```

with the configuration object from Firebase, for example:

```js
window.BIGWALK_FIREBASE_CONFIG = {
  apiKey: "...",
  authDomain: "...",
  databaseURL: "https://...",
  projectId: "...",
  appId: "..."
};
```

Firebase's web config values identify the project; access control is enforced by Authentication and Realtime Database Security Rules. Do not put private admin credentials or service-account keys in this file.

## Current room prototype

The `v1.2.0-rooms` branch currently supports:

- Create / join with a six-character room code
- Seeker / Hider roles
- Member list and automatic reconnect after refresh
- Host-controlled shared start / pause / reset
- Shared timer, question unlock schedule, question cooldown, question history, and elimination constraints
- Shared timing-setting changes
- Local markers and local live-position data remain private to each browser

The live-position tracker is **not** uploaded to the room in this version.
