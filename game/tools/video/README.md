# Video tour

A scripted tour that uses every control on the boat, recorded frame by frame from the real game.

- `director.js` runs inside the game page. It is a list of shots: each one walks the player somewhere,
  uses a station with the same keys a player would press, and shows a caption. It keeps the tour tidy
  (no random hits or enemy waves; every scene makes its own leak, fire or flood).
- `record.cjs` opens the game in headless Chromium in capture mode (`?capture=1`: the game clock only
  moves when the recorder steps it), steps the tour one video frame at a time and saves each frame as a
  JPEG. It is resumable: run it again and it skips the frames already saved.
- `sample.cjs` renders one frame from the middle of every shot, for a quick check before a long recording.

```bash
# from the repository root: serve the files, then record (Playwright and Chromium needed)
python3 -m http.server 8765 --bind 127.0.0.1 &
node game/tools/video/record.cjs /tmp/tour 1e9 20          # frames -> /tmp/tour/frames, 20 fps
ffmpeg -framerate 20 -i /tmp/tour/frames/f%05d.jpg -c:v libx264 -pix_fmt yuv420p -crf 23 -movflags +faststart tour.mp4
```

With software rendering it takes about two seconds per frame at 960×540.
