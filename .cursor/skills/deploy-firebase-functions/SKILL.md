---
name: deploy-firebase-functions
description: Deploy Firebase Cloud Functions by name; if any function has hosting rewrites in firebase.json, also deploy hosting. Use when the user asks to deploy functions, deploy by function name, or "haz el deploy de la función".
---

# Deploy Firebase functions (and hosting when needed)

## Purpose

Deploy one or more Firebase Cloud Functions by name. If any of the requested functions appear in `firebase.json` under `hosting.rewrites[].function`, include **hosting** in the same deploy so the rewrites stay in sync.

## When to use

- User says: "deploy the function X", "haz el deploy de user_route", "deploy functions and hosting"
- User gives one or more function names and wants them deployed
- User wants to deploy only certain functions (not all)

## Steps

1. **Get function names from the user**  
   They are the Cloud Function identifiers (e.g. `user_route`, `events`, `event_detail`). Same names as in `functions/main.py` and in Firebase.

2. **Resolve requested names**  
   - Normalize: strip spaces, accept comma-separated or list.  
   - If the user says "user_route" or "events", use that exact name (Firebase is case-sensitive).  
   - If the user says "all" or "todas", deploy all functions: read the function names from `functions/main.py` (the symbols exported and used there are the deployed names).

3. **Decide if hosting must be included**  
   - Open `firebase.json` in the project root.  
   - Under `hosting.rewrites`, collect every `"function"` value (e.g. `user_route`, `events`, `event_detail`).  
   - If **any** of the functions to deploy appears in that set, add `hosting` to the deploy target.

4. **Build the deploy target**  
   - Functions: `functions:name1,functions:name2,...`  
   - If hosting is needed: append `,hosting`  
   - Example: `functions:user_route,hosting`  
   - Example: `functions:events,event_detail,hosting`  
   - Example (only functions): `functions:create_competitor_user`

5. **Run deploy**  
   - Working directory: **project root** (where `firebase.json` and `functions/` live).  
   - Command:  
     `firebase deploy --only TARGET`  
     with `TARGET` from step 4.  
   - Use a reasonable timeout (e.g. 120000 ms); deploy can take over a minute.

6. **Report result**  
   - Show the command used and whether it succeeded or failed.  
   - If hosting was deployed, mention the Hosting URL from the output (e.g. `https://system-track-monitor.web.app`).

## Examples

**User:** "Deploy user_route"  
- Deploy: `user_route`.  
- `firebase.json` has rewrites for `user_route` → add hosting.  
- Run: `firebase deploy --only functions:user_route,hosting` from project root.

**User:** "Deploy events and event_detail"  
- Both have rewrites → include hosting.  
- Run: `firebase deploy --only functions:events,functions:event_detail,hosting`.

**User:** "Deploy create_competitor_user"  
- Check rewrites: if that function is not in any rewrite, deploy only functions.  
- Run: `firebase deploy --only functions:create_competitor_user`.

**User:** "Deploy all functions"  
- List all function names from `main.py` (e.g. `user_route`, `events`, `event_detail`, …).  
- Build `functions:fn1,functions:fn2,...`.  
- Because many have rewrites, add `hosting`.  
- Run: `firebase deploy --only functions:...,hosting`.

## Notes

- Function names must match exactly what Firebase has (same as in `main.py`).  
- Always run `firebase deploy` from the **project root**, not from `functions/`.  
- If the user does not specify names, ask which function(s) to deploy, or offer "all".
