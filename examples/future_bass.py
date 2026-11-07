"""Future bass 예제 곡을 FL 실습 프로젝트 JSON으로 만든다.
- 150 BPM, C 메이저 (A 마이너), 하프타임 드롭
- 코드: Fmaj9 - G6/9 - Em7 - Am9 (IV - V - iii - vi, future bass에서 흔한 진행)
- 코드 스탭에 킥 사이드체인을 걸어 future bass 특유의 펌핑
"""
import json, sys
from datetime import datetime, timezone

def N(pos, length, key, vel=0.8):
    assert 36 <= key <= 84, key
    return {"pos": pos, "len": length, "key": key, "vel": round(vel, 2)}

KICK, SNARE, CLAP, HAT, BASS, KEYS, LEAD = range(7)

# ---------- 화성 ----------
CHORDS = [
    [53, 57, 60, 64, 67],   # Fmaj9  (F A C E G)
    [55, 59, 62, 64, 69],   # G6/9   (G B D E A)
    [52, 55, 59, 62, 67],   # Em7    (E G B D + G)
    [57, 60, 64, 67, 71],   # Am9    (A C E G B)
]
ROOTS = [41, 43, 40, 45]    # F2 G2 E2 A2

# 1. 코드 패드: 마디마다 길게
pad = [N(b*16, 16, k, 0.55) for b, ch in enumerate(CHORDS) for k in ch]

# 2. 코드 스탭: 드롭의 잘게 끊긴 코드 리듬
STAB = [(0, 3, 0.9), (3, 3, 0.7), (6, 2, 0.75), (8, 2, 0.85), (10, 3, 0.7), (14, 2, 0.6)]
stabs = [N(b*16 + p, l, k, v) for b, ch in enumerate(CHORDS) for (p, l, v) in STAB for k in ch]

# 3. 808: 근음, 마디 끝에 옥타브 위로 튕김
bass = []
for b, r in enumerate(ROOTS):
    bass += [N(b*16, 7, r, 0.95), N(b*16 + 8, 4, r, 0.8), N(b*16 + 13, 2, r + 12, 0.65)]

# 4. 드롭 리드 (보컬 찹 느낌의 짧은 음)
MEL = [(0,2,76),(2,2,79),(4,2,81),(6,3,79),(10,2,76),(12,4,74),
       (16,2,74),(18,2,76),(20,2,79),(22,3,81),(26,2,79),(28,4,83),
       (32,2,79),(34,2,76),(36,4,74),(40,2,76),(42,2,74),(44,4,71),
       (48,2,72),(50,2,74),(52,4,76),(56,6,72)]
lead = [N(p, l, k, 0.8 if i % 2 == 0 else 0.65) for i, (p, l, k) in enumerate(MEL)]

# 5. 벌스 리드: 같은 선율의 뼈대만 길게
lead_verse = [N(p, l, k, 0.6) for (p, l, k) in
              [(0,8,76),(8,8,79),(16,8,74),(24,8,79),(32,8,79),(40,8,76),(48,16,72)]]

# ---------- 드럼 ----------
def hats_8ths(vel_on=0.5, vel_off=0.3):
    return [N(i, 1, 60, vel_on if i % 4 == 0 else vel_off) for i in range(0, 16, 2)]

# 6. 드롭 드럼 (하프타임: 킥 1박, 스네어+클랩 3박, 트랩 하이햇 롤)
drop_hats = hats_8ths(0.55, 0.35) + [N(13, 1, 60, 0.3), N(15, 1, 60, 0.4)]
drop_drums = {KICK: [N(0,1,60,1.0), N(10,1,60,0.85)],
              SNARE: [N(8,1,60,0.9)], CLAP: [N(8,1,60,0.75)], HAT: drop_hats}
# 7. 드롭 필: 마디 끝에 스네어 롤
drop_fill = {KICK: [N(0,1,60,1.0)],
             SNARE: [N(8,1,60,0.9), N(12,1,60,0.5), N(13,1,60,0.6), N(14,1,60,0.75), N(15,1,60,0.9)],
             CLAP: [N(8,1,60,0.75)], HAT: hats_8ths(0.5, 0.3)[:6]}
# 8. 벌스 드럼: 가볍게
verse_drums = {KICK: [N(0,1,60,0.85)], CLAP: [N(8,1,60,0.6)], HAT: hats_8ths(0.4, 0.25)}
# 9. 빌드업 스네어 롤 (2마디: 4분 -> 8분 -> 16분, 점점 세게)
roll = [N(p, 1, 60, 0.35 + 0.012*p) for p in list(range(0, 16, 4)) + list(range(16, 24, 2)) + list(range(24, 32))]
build = {SNARE: roll, KICK: [N(p, 1, 60, 0.7) for p in range(0, 16, 4)]}
# 10. 인트로 하이햇
intro_hats = {HAT: hats_8ths(0.35, 0.2)}

COLORS = ['#4f9de0', '#3cc8c0', '#c95ad6', '#5cc275', '#8a8ff0', '#e0703c', '#e05a7a', '#e0c040', '#e0a040', '#9aa3af']
patterns_def = [
    ("Chords Pad", 4, {KEYS: pad}),
    ("Chord Stabs", 4, {KEYS: stabs}),
    ("808", 4, {BASS: bass}),
    ("Lead Drop", 4, {LEAD: lead}),
    ("Lead Verse", 4, {LEAD: lead_verse}),
    ("Drop Drums", 1, drop_drums),
    ("Drop Fill", 1, drop_fill),
    ("Verse Drums", 1, verse_drums),
    ("Build Roll", 2, build),
    ("Intro Hats", 1, intro_hats),
]
patterns = [{"id": i + 1, "name": name, "color": COLORS[i], "minBars": bars,
             "notes": {str(ch): notes for ch, notes in notes_by_ch.items()}}
            for i, (name, bars, notes_by_ch) in enumerate(patterns_def)]
PID = {p["name"]: p["id"] for p in patterns}

# ---------- 편곡 (32마디) ----------
# 트랙: 0 드럼, 1 롤/필, 2 코드, 3 베이스, 4 리드
ARR = [
    # 인트로 0-3: 패드 + 필터가 열림
    ("Chords Pad", 2, 0, 4), ("Intro Hats", 0, 2, 2),
    # 벌스 4-11: 패드, 가벼운 드럼, 리드 뼈대, 마지막 2마디 빌드업
    ("Chords Pad", 2, 4, 8), ("Verse Drums", 0, 4, 6), ("Lead Verse", 4, 4, 8), ("Build Roll", 1, 10, 2),
    # 드롭 1 12-19
    ("Drop Drums", 0, 12, 7), ("Drop Fill", 0, 19, 1), ("Chord Stabs", 2, 12, 8), ("808", 3, 12, 8), ("Lead Drop", 4, 12, 8),
    # 브레이크 20-23
    ("Chords Pad", 2, 20, 4), ("Lead Verse", 4, 20, 4),
    # 빌드업 2 24-25
    ("Chord Stabs", 2, 24, 2), ("Build Roll", 1, 24, 2),
    # 드롭 2 26-31
    ("Drop Drums", 0, 26, 5), ("Drop Fill", 0, 31, 1), ("Chord Stabs", 2, 26, 6), ("808", 3, 26, 6), ("Lead Drop", 4, 26, 6),
]
clips = []
for i, (name, track, start, length) in enumerate(ARR):
    assert start + length <= 32
    clips.append({"id": i + 1, "patternId": PID[name], "track": track, "start": start, "len": length})

# ---------- 자동화: 마스터 필터 (마디별 0~1) ----------
auto = [1.0] * 33
for bar, v in {0:0.12, 1:0.28, 2:0.45, 3:0.62, 4:0.8, 9:0.8, 10:0.5, 11:0.78, 12:1.0, 19:1.0,
               20:0.42, 22:0.45, 23:0.55, 24:0.6, 25:0.82, 26:1.0}.items():
    auto[bar] = v
# 지정하지 않은 마디는 앞뒤 값 사이를 선형으로 채운다
keys = sorted({0:0,4:0,9:0,10:0,11:0,12:0,19:0,20:0,22:0,23:0,24:0,25:0,26:0,1:0,2:0,3:0})
for a, b in zip(keys, keys[1:]):
    for x in range(a + 1, b):
        auto[x] = round(auto[a] + (auto[b] - auto[a]) * (x - a) / (b - a), 3)

# ---------- 채널과 믹서 ----------
CH = [("Kick","kick","#e0703c",1,0.9), ("Snare","snare","#e0c040",2,0.75), ("Clap","clap","#e05a7a",3,0.7),
      ("Hat","hat","#3cc8c0",4,0.6), ("808 Bass","bass","#c95ad6",5,0.85), ("Keys","keys","#4f9de0",6,0.9),
      ("Lead","lead","#5cc275",7,0.75)]
channels = [{"id": i, "name": n, "inst": inst, "color": c, "insert": ins, "vol": v, "mute": False}
            for i, (n, inst, c, ins, v) in enumerate(CH)]
tracks = [{"vol": 0.85}]
for i in range(1, 9):
    tracks.append({"vol": 0.8, "pan": 0, "mute": False, "route": 0, "scSource": 0, "scDepth": 0.7})
for i in (1, 2, 3, 4):              # 드럼 -> Insert 8 버스
    tracks[i]["route"] = 8
tracks[4]["pan"] = 0.15; tracks[3]["pan"] = -0.1
tracks[5].update(scSource=1, scDepth=0.75)   # 808: 킥 사이드체인
tracks[6].update(scSource=1, scDepth=0.65)   # 코드: 킥 사이드체인 (future bass 펌핑)
tracks[7].update(vol=0.7)
tracks[8].update(vol=0.85)

project = {
    "format": "pattern-lab-project", "version": 1, "app": "FL 실습",
    "savedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "name": "Future Bass - Daybreak",
    "song": {"bpm": 150, "swing": 0, "channels": channels, "patterns": patterns,
             "nextPatternId": len(patterns) + 1, "clips": clips, "nextClipId": len(clips) + 1,
             "tracks": tracks, "automation": {"enabled": True, "values": auto},
             "scale": {"root": 0, "type": "major"}},
    "view": {"curPattern": PID["Chord Stabs"], "curChannel": KEYS, "mode": "song"},
}
json.dump(project, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
n = sum(len(v) for p in patterns for v in p["notes"].values())
print(f"patterns {len(patterns)}, clips {len(clips)}, notes {n}, auto {auto[:14]}")
