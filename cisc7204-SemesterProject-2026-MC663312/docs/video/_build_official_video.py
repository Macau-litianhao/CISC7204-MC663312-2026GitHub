"""
Build the Team 01 introductory video — official-voice (edge-tts) route.

Takes the 16-slide deck already exported to ``deck/png/slide-01..16.png``
(2560x1440) and the 16 narration segments from ``video_script.md``, synthesises
one narration clip per slide with a Microsoft neural voice, then muxes image +
audio into a single 1920x1080 H.264 + AAC mp4 with captions burned in.

Usage (from the repository root):

    D:/Anaconda/python.exe docs/video/_build_official_video.py

Outputs:
  docs/video/assets/narration/official/01..16.mp3   (the 16 spoken clips)
  docs/video/Team01_IntroVideo.srt                  (captions)
  docs/video/Team01_IntroVideo.mp4                  (the finished video)
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
import tempfile

VOICE = os.environ.get("TEAM01_TTS_VOICE", "en-US-AndrewMultilingualNeural")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIDEO_DIR = os.path.join(ROOT, "docs", "video")
SLIDE_DIR = os.path.join(VIDEO_DIR, "deck", "png")
NARR_DIR = os.path.join(VIDEO_DIR, "assets", "narration", "official")
MP4 = os.path.join(VIDEO_DIR, "Team01_IntroVideo.mp4")
SRT = os.path.join(VIDEO_DIR, "Team01_IntroVideo.srt")

# Speech target: ~620 words at ~130 wpm ~= 285 s; 16 x 0.45 s pauses -> ~4:52.
TARGET_AUDIO = 285.0
PAUSE = 0.45

# --------------------------------------------------------------------------
# narration — slide by slide, in a student-voice register ("we found ...",
# "we want to be honest ..."). Numbers and acronyms are spelled out so the
# neural voice reads them correctly.
# --------------------------------------------------------------------------

NARRATION = [
    # 1 cover — just the project, no course info
    ("Hi everyone, welcome to our project. We looked at why flights get "
     "delayed in the United States: where the delays come from, how they build "
     "up through the day, and what a traveller can actually do about it."),
    # 2 team — class + team, members in general (no names / IDs read out)
    ("We are Class K, Team One. The slide shows our six team members, and "
     "together we cover the different roles this project needs. We'll take you "
     "through what we found."),
    # 3 abstract
    ("Let me start with our main conclusion, because it shapes everything that "
     "follows. After studying ten years of flights, we found delay is "
     "predictable in its structure, even though individual flights aren't. "
     "About three quarters comes from the airline itself, and a few flights "
     "carry most of the pain. I'll walk you through the problem, the data, and "
     "the five findings behind it."),
    # 4 problem
    ("Here's the problem that got us interested. Every year the United States "
     "publishes one average delay, and that single number hides two different "
     "stories. The typical flight lands about six minutes early, while the "
     "average says seven minutes late, because a handful of really bad flights "
     "drag it up. So the question is: which story should we believe?"),
    # 5 four questions
    ("That led us to four questions. Where do delay minutes actually come "
     "from, and is that split stable over ten years? How much delay passes "
     "from one flight to the next? Do airports group into their own delay "
     "patterns? And can we turn all this into a tool a traveller can act on? "
     "These four questions map directly onto the rest of the talk."),
    # 6 data
    ("To answer these, we brought together five public datasets: flight-level "
     "records, the delay-cause cross-check, hourly weather from N O A A, "
     "airport details, and airline codes. Everything is public, so anyone can "
     "check our work. In total, that's over sixty-three million rows, and that "
     "scale is what makes our results believable."),
    # 7 method
    ("Our whole analysis runs as one pipeline with six stages: acquire, "
     "attribute, analyse the heavy tail, trace the cascade, model, and "
     "communicate. Each stage is a script, so one command regenerates every "
     "figure, and fifty-three tests pin every number back to its source. We "
     "built it this way so nothing is a black box, and anyone can reproduce "
     "our results."),
    # 8 finding 1
    ("Our first finding answers where delay comes from. Seventy-three point "
     "three percent traces back to the airline itself, and only twenty-six "
     "point seven percent to the system around it. What surprised us is how "
     "stable this is: it barely moved across the whole decade, which tells us "
     "where airlines can actually make a difference."),
    # 9 finding 2
    ("Our second finding is about concentration. The Gini index is zero point "
     "eight seven six, meaning a tiny share of flights creates most of the "
     "delay. In plain terms, a few bad flights cause most of the misery. So we "
     "report percentiles and the heavy tail, and we re-run every headline with "
     "the pandemic years removed."),
    # 10 finding 3
    ("Our third finding is about how delay spreads through the day. Late "
     "aircraft is the biggest single cause, at thirty-eight point eight "
     "percent. About six percent of flights start already behind, and some of "
     "that delay is inherited from an earlier leg. So one delayed flight can "
     "quietly push the next one late too."),
    # 11 findings 4+5
    ("Findings four and five are where we're careful. Airports do sort into "
     "five delay profiles, but that grouping isn't very stable, so we report "
     "it with caution. And our model can rank risky flights, but it can't "
     "promise an exact arrival time. Being honest about what we can't claim is "
     "part of the result."),
    # 12 dashboard
    ("All of this comes together in one interactive dashboard. Change the "
     "year, the airline, or the month, and every panel recomputes live. We "
     "also ran a usability check, with three timed tasks, using someone who "
     "isn't a data specialist. So the insight isn't locked in a report; it's "
     "something you can actually play with."),
    # 13 teamwork — brief
    ("On how we work together: we split the eight course roles among the six "
     "of us and rotate them halfway through. We decide things as a group, and "
     "every piece of work gets checked by someone else."),
    # 14 schedule — brief
    ("For our timeline, we planned backwards from the deadline. We've already "
     "finished the proposal and this video, we'll present in class later this "
     "month, and we'll wrap up the project by early December."),
    # 15 success & honesty — brief
    ("Finally, we set clear quality checks for ourselves, and we're upfront "
     "about what the model can and can't do: it's good at ranking risk, but it "
     "won't promise exact arrival times."),
    # 16 close — just thanks
    ("Thank you for watching. That's our project."),
]

N = len(NARRATION)


# --------------------------------------------------------------------------
# ffmpeg helpers
# --------------------------------------------------------------------------

def _ffmpeg_exe() -> str:
    import imageio_ffmpeg  # noqa: PLC0415
    return imageio_ffmpeg.get_ffmpeg_exe()


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", *args],
                          capture_output=True, text=True)


def _dur(path: str) -> float:
    r = subprocess.run([_ffmpeg_exe(), "-hide_banner", "-i", path],
                       capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", r.stderr)
    if not m:
        raise RuntimeError(f"cannot read duration of {path}: {r.stderr[-300:]}")
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


# --------------------------------------------------------------------------
# step 1 — synthesise narration (once, natural rate), then time-stretch to hit
# the 4:45-5:00 window with ffmpeg atempo (pitch-preserving, deterministic).
# --------------------------------------------------------------------------

def _synth(texts: list[str], out_dir: str, rate: str) -> list[str]:
    import edge_tts  # noqa: PLC0415

    async def one(text: str, dest: str) -> None:
        last = None
        for attempt in range(4):
            try:
                await edge_tts.Communicate(text, VOICE, rate=rate).save(dest)
                return
            except Exception as e:  # noqa: BLE001
                last = e
                await asyncio.sleep(1.5 * (attempt + 1))
        raise last

    async def main() -> None:
        for i, t in enumerate(texts):
            await one(t, os.path.join(out_dir, f"{i + 1:02d}.mp3"))
            await asyncio.sleep(0.25)

    asyncio.run(main())
    return [os.path.join(out_dir, f"{i + 1:02d}.mp3") for i in range(len(texts))]


def build_narration(work: str) -> list[str]:
    os.makedirs(NARR_DIR, exist_ok=True)

    # fast path: reuse already-synthesised (and already time-stretched) clips
    existing = [os.path.join(NARR_DIR, f"{i + 1:02d}.mp3") for i in range(N)]
    if all(os.path.exists(p) and os.path.getsize(p) > 0 for p in existing):
        print("  reusing existing narration clips")
        wavs = []
        for i, m in enumerate(existing):
            w = os.path.join(work, f"n_{i + 1:02d}.wav")
            _run(["-i", m, "-ar", "44100", "-ac", "2", w])
            wavs.append(w)
        total = sum(_dur(w) for w in wavs)
        print(f"  speech {total:.1f}s (projected {(total + PAUSE * N) / 60:.2f} min)")
        return wavs

    raw = os.path.join(work, "raw_tts")
    os.makedirs(raw, exist_ok=True)

    print("  synthesising at natural rate")
    mp3s = _synth(NARRATION, raw, "+0%")

    # decode once to measure the true speech length
    wavs = []
    for i, m in enumerate(mp3s):
        w = os.path.join(raw, f"{i + 1:02d}.wav")
        _run(["-i", m, "-ar", "44100", "-ac", "2", w])
        wavs.append(w)
    total = sum(_dur(w) for w in wavs)

    tempo = total / TARGET_AUDIO
    print(f"  natural speech {total:.1f}s -> tempo {tempo:.3f}")
    if tempo < 0.98 or tempo > 1.02:
        stretched = []
        for i, m in enumerate(mp3s):
            w = os.path.join(work, f"st_{i + 1:02d}.wav")
            _run(["-i", m, "-filter:a", f"atempo={tempo:.4f}",
                  "-ar", "44100", "-ac", "2", w])
            stretched.append(w)
        wavs = stretched

    total2 = sum(_dur(w) for w in wavs)
    print(f"  speech after stretch {total2:.1f}s "
          f"(projected {(total2 + PAUSE * N) / 60:.2f} min)")

    for i, w in enumerate(wavs):
        _run(["-i", w, os.path.join(NARR_DIR, f"{i + 1:02d}.mp3")])
    print(f"  narration -> {NARR_DIR}/ (voice {VOICE})")
    return wavs


# --------------------------------------------------------------------------
# step 2 — captions
# --------------------------------------------------------------------------

def _wrap(text: str, width: int = 46) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= width:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def write_srt(timeline: list[tuple[float, float]]) -> None:
    def ts(t: float) -> str:
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = t % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

    out, n = [], 0
    for i, (start, end) in enumerate(timeline):
        lines = _wrap(NARRATION[i])
        step = (end - start) / len(lines)
        for j, line in enumerate(lines):
            n += 1
            s = start + j * step
            e = start + (j + 1) * step
            out.append(f"{n}\n{ts(s)} --> {ts(e)}\n{line}\n")
    with open(SRT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))
    print(f"  captions -> {SRT}")


# --------------------------------------------------------------------------
# step 3 — mux
# --------------------------------------------------------------------------

def build_video(pngs: list[str], wavs: list[str], work: str) -> str:
    seg_dir = os.path.join(work, "segs")
    os.makedirs(seg_dir, exist_ok=True)

    silence = os.path.join(work, "silence.wav")
    _run(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{PAUSE}", silence])

    segs, timeline, clock = [], [], 0.0
    for i, (png, audio) in enumerate(zip(pngs, wavs)):
        dur = _dur(audio)
        padded = os.path.join(work, f"pad_{i + 1:02d}.wav")
        lst = os.path.join(work, f"list_{i + 1:02d}.txt")
        with open(lst, "w", encoding="utf-8") as fh:
            for p in (audio, silence):
                fh.write(f"file '{p.replace(chr(92), '/')}'\n")
        _run(["-f", "concat", "-safe", "0", "-i", lst,
              "-ar", "44100", "-ac", "2", padded])

        seg = os.path.join(seg_dir, f"seg_{i + 1:02d}.mp4")
        _run(["-loop", "1", "-framerate", "25", "-t", f"{dur + PAUSE:.3f}", "-i", png,
              "-i", padded,
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
              "-tune", "stillimage", "-pix_fmt", "yuv420p",
              "-vf", "scale=1920:1080",
              "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
              "-shortest", "-movflags", "+faststart", seg])
        segs.append(seg)
        timeline.append((clock, clock + dur))
        clock += dur + PAUSE

    total = sum(_dur(s) for s in segs)
    print(f"  {len(segs)} segments, {total / 60:.2f} min")

    write_srt(timeline)

    lst = os.path.join(work, "concat.txt")
    with open(lst, "w", encoding="utf-8") as fh:
        for s in segs:
            fh.write(f"file '{s.replace(chr(92), '/')}'\n")
    raw = os.path.join(work, "raw.mp4")
    _run(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", raw])

    # burn captions; on a Windows drive letter the colon must be escaped.
    srt_arg = SRT.replace("\\", "/").replace(":", r"\:")
    style = ("FontName=Arial,Fontsize=12,PrimaryColour=&H00FFFFFF,"
             "OutlineColour=&H90000000,Outline=2,Shadow=0,MarginV=16")
    r = _run(["-i", raw,
              "-vf", f"subtitles='{srt_arg}':force_style='{style}'",
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
              "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
              "-movflags", "+faststart", MP4])
    if r.returncode != 0 or not os.path.exists(MP4):
        print("  (subtitle burn failed - writing clean cut)")
        _run(["-i", raw, "-c", "copy", "-movflags", "+faststart", MP4])

    size = os.path.getsize(MP4) / (1024 * 1024)
    print(f"  video -> {MP4}  ({size:.1f} MB, {_dur(MP4) / 60:.2f} min)")
    return MP4


def main() -> int:
    pngs = sorted((os.path.join(SLIDE_DIR, f) for f in os.listdir(SLIDE_DIR)
                   if f.lower().endswith(".png")),
                  key=lambda p: int(re.search(r"(\d+)", os.path.splitext(p)[0]).group(1)))
    if len(pngs) != N:
        raise RuntimeError(f"expected {N} slide PNGs, found {len(pngs)}")

    work = tempfile.mkdtemp(prefix="team01_official_")
    try:
        print(f"[1/3] synthesising narration ({VOICE})")
        wavs = build_narration(work)
        print("[2/3] muxing slides + audio")
        build_video(pngs, wavs, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
