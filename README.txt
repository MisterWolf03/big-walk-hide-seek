BIG WALK HIDE + SEEK — PROTOTYPE 1.1.0

HOW TO RUN
1. Unzip the folder.
2. Keep index.html and big-walk-map.png together.
3. Open index.html in a modern browser.

WHAT CHANGED IN 0.6
- Rebuilt the interface around a full-screen map.
- Replaced the large permanent sidebar with top navigation tabs:
  Game / Map Tools / Questions / Rules / Settings.
- Each tab opens a compact floating panel over the map.
- Clicking the active tab again, or pressing Hide, closes the panel.
- Match timer stays visible in the top bar.
- Removed the old top-left HUD entirely:
  * no duplicate cursor coordinate readout
  * no remaining-area percentage
  * no zoom percentage
- Hover coordinates remain next to the cursor.

CUSTOM QUESTION TIMING
The Settings tab now lets you change unlock timing without editing code.

Two ways to do it:
1. Quick schedule builder:
   - First question after X minutes
   - Y minutes between each unlock
   - Example: 5 + 15 creates 05:00 / 20:00 / 35:00 / 50:00
2. Individual unlock times:
   - Gridline
   - Nearest tower
   - Tower radius
   - Marker questions

The schedule can be changed before or during a match. Locks update immediately.

DEFAULT SCHEDULE
10:00 — Gridline
20:00 — Nearest tower
30:00 — Tower radius
50:00 — Marker-based questions

OTHER RETAINED FEATURES
- Calibrated Big Walk coordinate grid
- Exact tower locations
- Cursor coordinate tooltip
- Click-to-place YOU marker
- Nearest-tower helper
- Distance + bearing ruler
- Copy coordinates
- Question elimination overlays
- 250-unit minimum radius
- Central-gridline restriction
- Rules tab
- Testing unlock override


WHAT CHANGED IN 0.7
- Marker-direction questions now use only North / East / South / West.
- Cardinal direction elimination uses four broad 90-degree sectors.
- Added manual coordinate entry in Map Tools:
  * enter coordinates in Y, X order
  * accepts comma, space, or labeled formats
  * places the YOU marker directly at those coordinates
  * rejects coordinates outside the mapped texture
- Moved Question History, Undo Question, and Clear Questions to the bottom of the Questions tab.
- Tightened legal gridline questions:
  * X 15 through X 19 only
  * Y 36 through Y 40 only
  * still restricted to whole numbered gridlines (100-unit increments)


WHAT CHANGED IN 0.8
- Fixed cardinal-direction questions from the YOU marker.
- North / East / South / West now use straight half-map cuts through the marker:
  * North = all positions with Y <= marker Y
  * South = all positions with Y >= marker Y
  * East  = all positions with X >= marker X
  * West  = all positions with X <= marker X
- Removed the previous 90-degree cone / wedge behavior.


WHAT CHANGED IN 0.9
- Added a GLOBAL QUESTION COOLDOWN.
- Default cooldown is 5 minutes.
- After any successful question is answered, every unlocked question locks.
- The cooldown counts using match time, so pausing the match also pauses the cooldown.
- Undoing the most recent question immediately cancels the cooldown so an accidental answer can be corrected.
- Clear Questions also clears the current cooldown.
- Added a visible cooldown timer to the Questions tab and top-bar status.
- Added customizable cooldown duration under Settings.
- Default question unlock times remain 10 / 20 / 30 / 50 minutes.
- Added a Changelog tab to the top navigation. Future versions should continue adding entries there.
- Restored marker direction behavior to broad N/E/S/W compass sectors after the short-lived v0.8 half-plane experiment.


WHAT CHANGED IN 1.0
- Added two landmarks:
  - Purple Tunnel: Y 4286, X 1897
  - Microphone: Y 3408, X 1235
- Added landmark questions: nearest landmark and landmark radius.
- Added support for multiple markers instead of only one.
- Marker-based questions now use the active marker.


WHAT CHANGED IN 1.0.1
- Fixed the issue where the map could require one refresh after first opening the site.


WHAT CHANGED IN 1.0.2
- Added live-location integration with BigWalkLivePosition v0.2.0.
- Connect from Map Tools to create a LIVE YOU marker that follows your player.
- Live marker can be used as the active reference marker for questions.


WHAT CHANGED IN 1.1.0
- GitHub Pages-ready static build.
- Hosted-site live-location compatibility with BigWalkLivePosition v0.2.1.
- Added update detection using version.json.
- Added .nojekyll and deployment instructions.
