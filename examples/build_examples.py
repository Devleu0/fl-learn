"""FL 실습 장르별 예제 곡 생성기.

실행: python examples/build_examples.py
결과:
  examples/<id>.json   각 곡의 프로젝트 파일 ("파일 > 프로젝트 열기"로 열 수 있음)
  examples/index.json  예제 목록 (장르, 설명)
  web/examples.js      앱의 "예제 곡 고르기" 창이 읽는 목록 (프로젝트 포함)

곡을 고치거나 새 장르를 넣으려면 아래 SONGS에 함수를 추가하고 다시 실행한다.
도구의 제약: 채널 7개 고정, 음높이 36~84, 패턴 최대 8마디, 곡 최대 32마디, BPM 60~200.
"""
import json, os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KICK, SNARE, CLAP, HAT, BASS, KEYS, LEAD = range(7)
NOTE = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def N(pos, length, key=60, vel=0.8):
    assert 36 <= key <= 84, f'key {key} out of range'
    assert pos >= 0 and length >= 1
    return {"pos": pos, "len": length, "key": key, "vel": round(max(0.05, min(1, vel)), 2)}


def hits(positions, vel=0.8, key=60):
    """드럼용: 위치 목록 -> 노트. vel은 숫자 또는 위치를 받는 함수."""
    return [N(p, 1, key, vel(p) if callable(vel) else vel) for p in positions]


def sustain(chords, steps_per_chord=16, vel=0.55, length=None):
    return [N(i * steps_per_chord, length or steps_per_chord, k, vel) for i, ch in enumerate(chords) for k in ch]


def rhythm_chords(chords, rhythm, steps_per_chord=16):
    """rhythm: [(pos, len, vel)] 를 코드마다 반복"""
    return [N(i * steps_per_chord + p, l, k, v) for i, ch in enumerate(chords) for (p, l, v) in rhythm for k in ch]


def melody(seq, vel=0.75, accent=0.1):
    return [N(p, l, k, vel + (accent if i % 2 == 0 else 0)) for i, (p, l, k) in enumerate(seq)]


def roll(bars=2, start_vel=0.35, end_vel=0.95):
    """빌드업 스네어 롤: 4분 -> 8분 -> 16분"""
    total = bars * 16
    pos = list(range(0, total // 2, 4)) + list(range(total // 2, total * 3 // 4, 2)) + list(range(total * 3 // 4, total))
    return [N(p, 1, 60, start_vel + (end_vel - start_vel) * p / total) for p in pos]


def curve(points, n=33):
    """{마디: 값} 사이를 선형으로 채운 자동화 값"""
    xs = sorted(points)
    out = []
    for i in range(n):
        if i <= xs[0]: out.append(points[xs[0]]); continue
        if i >= xs[-1]: out.append(points[xs[-1]]); continue
        a = max(x for x in xs if x <= i); b = min(x for x in xs if x >= i)
        out.append(points[a] if a == b else round(points[a] + (points[b] - points[a]) * (i - a) / (b - a), 3))
    return out


CH_DEF = [("Kick", "kick", "#e0703c"), ("Snare", "snare", "#e0c040"), ("Clap", "clap", "#e05a7a"), ("Hat", "hat", "#3cc8c0"),
          ("808 Bass", "bass", "#c95ad6"), ("Keys", "keys", "#4f9de0"), ("Lead", "lead", "#5cc275")]
PAT_COLORS = ['#4f9de0', '#3cc8c0', '#c95ad6', '#5cc275', '#8a8ff0', '#e0703c', '#e05a7a', '#e0c040', '#e0a040', '#9aa3af', '#6fcf97', '#f2994a']


def make_project(name, bpm, swing, scale, patterns_def, arrangement, auto_points, ch_vol=None, mix=None, view_pattern=None):
    ch_vol = ch_vol or {}
    patterns, pid = [], {}
    for i, (pname, bars, notes_by_ch) in enumerate(patterns_def):
        assert 1 <= bars <= 8
        for ch, notes in notes_by_ch.items():
            for n in notes:
                assert n["pos"] + n["len"] <= bars * 16, f'{name}/{pname}: note past pattern end {n}'
        patterns.append({"id": i + 1, "name": pname, "color": PAT_COLORS[i % len(PAT_COLORS)], "minBars": bars,
                         "notes": {str(ch): notes for ch, notes in notes_by_ch.items()}})
        pid[pname] = i + 1
    clips = []
    for i, (pname, track, start, length) in enumerate(arrangement):
        assert 0 <= track <= 7 and start + length <= 32, f'{name}: clip {pname} out of range'
        clips.append({"id": i + 1, "patternId": pid[pname], "track": track, "start": start, "len": length})
    channels = [{"id": i, "name": n, "inst": inst, "color": c, "insert": i + 1, "vol": ch_vol.get(i, 0.8), "mute": False}
                for i, (n, inst, c) in enumerate(CH_DEF)]
    tracks = [{"vol": 0.85}] + [{"vol": 0.8, "pan": 0, "mute": False, "route": 0, "scSource": 0, "scDepth": 0.7} for _ in range(8)]
    for idx, over in (mix or {}).items():
        tracks[idx].update(over)
    songbars = max(c["start"] + c["len"] for c in clips)
    return {
        "format": "pattern-lab-project", "version": 1, "app": "FL 실습",
        "savedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"), "name": name,
        "song": {"bpm": bpm, "swing": swing, "channels": channels, "patterns": patterns, "nextPatternId": len(patterns) + 1,
                 "clips": clips, "nextClipId": len(clips) + 1, "tracks": tracks,
                 "automation": {"enabled": True, "values": curve(auto_points)}, "scale": scale},
        "view": {"curPattern": pid.get(view_pattern, 1), "curChannel": KEYS, "mode": "song"},
    }, songbars


DRUM_BUS = {i: {"route": 8} for i in (1, 2, 3, 4)}


def merge(*ds):
    out = {}
    for d in ds:
        for k, v in d.items():
            out.setdefault(k, {}).update(v)
    return out


# =====================================================================
# 1. Future Bass
# =====================================================================
def future_bass():
    chords = [[53, 57, 60, 64, 67], [55, 59, 62, 64, 69], [52, 55, 59, 62, 67], [57, 60, 64, 67, 71]]  # Fmaj9 G6/9 Em7 Am9
    roots = [41, 43, 40, 45]
    stab = [(0, 3, 0.9), (3, 3, 0.7), (6, 2, 0.75), (8, 2, 0.85), (10, 3, 0.7), (14, 2, 0.6)]
    bass = [n for b, r in enumerate(roots) for n in (N(b*16, 7, r, .95), N(b*16+8, 4, r, .8), N(b*16+13, 2, r+12, .65))]
    lead = melody([(0,2,76),(2,2,79),(4,2,81),(6,3,79),(10,2,76),(12,4,74),(16,2,74),(18,2,76),(20,2,79),(22,3,81),(26,2,79),(28,4,83),
                   (32,2,79),(34,2,76),(36,4,74),(40,2,76),(42,2,74),(44,4,71),(48,2,72),(50,2,74),(52,4,76),(56,6,72)], 0.65, 0.15)
    lead_verse = melody([(0,8,76),(8,8,79),(16,8,74),(24,8,79),(32,8,79),(40,8,76),(48,16,72)], 0.6, 0)
    hats8 = lambda on=.55, off=.35: hits(range(0, 16, 2), lambda p: on if p % 4 == 0 else off)
    pats = [
        ("Chords Pad", 4, {KEYS: sustain(chords)}),
        ("Chord Stabs", 4, {KEYS: rhythm_chords(chords, stab)}),
        ("808", 4, {BASS: bass}),
        ("Lead Drop", 4, {LEAD: lead}),
        ("Lead Verse", 4, {LEAD: lead_verse}),
        ("Drop Drums", 1, {KICK: hits([0, 10], lambda p: 1 if p == 0 else .85), SNARE: hits([8], .9), CLAP: hits([8], .75),
                           HAT: hats8() + hits([13, 15], lambda p: .3 if p == 13 else .4)}),
        ("Drop Fill", 1, {KICK: hits([0], 1), SNARE: hits([8], .9) + hits([12, 13, 14, 15], lambda p: .5 + (p - 12) * .13),
                          CLAP: hits([8], .75), HAT: hats8(.5, .3)[:6]}),
        ("Verse Drums", 1, {KICK: hits([0], .85), CLAP: hits([8], .6), HAT: hats8(.4, .25)}),
        ("Build Roll", 2, {SNARE: roll(2), KICK: hits(range(0, 16, 4), .7)}),
        ("Intro Hats", 1, {HAT: hats8(.35, .2)}),
    ]
    arr = [("Chords Pad", 2, 0, 4), ("Intro Hats", 0, 2, 2),
           ("Chords Pad", 2, 4, 8), ("Verse Drums", 0, 4, 6), ("Lead Verse", 4, 4, 8), ("Build Roll", 1, 10, 2),
           ("Drop Drums", 0, 12, 7), ("Drop Fill", 0, 19, 1), ("Chord Stabs", 2, 12, 8), ("808", 3, 12, 8), ("Lead Drop", 4, 12, 8),
           ("Chords Pad", 2, 20, 4), ("Lead Verse", 4, 20, 4), ("Chord Stabs", 2, 24, 2), ("Build Roll", 1, 24, 2),
           ("Drop Drums", 0, 26, 5), ("Drop Fill", 0, 31, 1), ("Chord Stabs", 2, 26, 6), ("808", 3, 26, 6), ("Lead Drop", 4, 26, 6)]
    auto = {0: .12, 3: .62, 4: .8, 9: .8, 10: .5, 11: .78, 12: 1, 19: 1, 20: .42, 22: .45, 23: .55, 24: .6, 25: .82, 26: 1}
    mix = merge(DRUM_BUS, {4: {"pan": .15}, 3: {"pan": -.1}, 5: {"scSource": 1, "scDepth": .75}, 6: {"scSource": 1, "scDepth": .65},
                           7: {"vol": .7}, 8: {"vol": .85}})
    return dict(
        id="future-bass", title="Future Bass - Daybreak", bpm=150, scale={"root": 0, "type": "major"},
        genre={"ko": "퓨처 베이스", "en": "Future Bass"},
        desc={"ko": "풍성한 메이저 7·9 코드를 잘게 끊고, 킥 사이드체인으로 코드 전체가 펌핑하는 하프타임 드롭.",
              "en": "Lush major 7th/9th chords chopped into stabs, with kick sidechain pumping the whole chord in half-time drops."},
        traits={"ko": ["코드 스탭", "사이드체인 펌핑", "하프타임 드롭", "빌드업 스네어 롤"],
                "en": ["Chord stabs", "Sidechain pumping", "Half-time drop", "Snare-roll build-up"]},
        args=("Future Bass - Daybreak", 150, 0, {"root": 0, "type": "major"}, pats, arr, auto,
              {0: .9, 1: .75, 2: .7, 3: .6, 4: .85, 5: .9, 6: .75}, mix, "Chord Stabs"))


# =====================================================================
# 2. Trap
# =====================================================================
def trap():
    chords = [[69, 72, 76], [65, 69, 72], [62, 65, 69], [64, 68, 71]]       # Am F Dm E (하모닉 마이너의 V)
    roots = [45, 41, 38, 40]
    arp_pos, arp_idx = [0, 3, 6, 8, 11, 14], [0, 1, 2, 1, 2, 0]
    bells = [N(b*16 + p, 2, ch[i], .7 if j % 3 == 0 else .55) for b, ch in enumerate(chords) for j, (p, i) in enumerate(zip(arp_pos, arp_idx))]
    bass = [n for b, r in enumerate(roots) for n in (N(b*16, 6, r, .95), N(b*16+7, 3, r, .8), N(b*16+10, 4, r, .9), N(b*16+14, 2, r+12, .6))]
    hook = melody([(0,3,76),(4,2,79),(6,2,76),(8,4,74),(12,4,72),(16,3,72),(20,2,74),(22,2,72),(24,8,69),
                   (32,3,74),(36,2,76),(38,2,74),(40,4,72),(44,4,74),(48,3,76),(52,2,79),(54,2,81),(56,8,76)], .7, .1)
    hat_a = hits([0, 2, 4, 6, 7, 8, 10, 12, 13, 14, 15], lambda p: {7: .3, 13: .3, 14: .4, 15: .5}.get(p, .55 if p % 4 == 0 else .4))
    hat_b = hits([0, 2, 4, 5, 6, 8, 10, 11, 12, 14], lambda p: {5: .35, 11: .35}.get(p, .55 if p % 4 == 0 else .4))
    pats = [
        ("Bells", 4, {KEYS: bells}),
        ("Hook", 4, {LEAD: hook}),
        ("808 Trap", 4, {BASS: bass}),
        ("Trap Drums A", 1, {KICK: hits([0, 7, 10], lambda p: 1 if p == 0 else .85), SNARE: hits([8], .9), CLAP: hits([8], .7), HAT: hat_a}),
        ("Trap Drums B", 1, {KICK: hits([0, 3, 10, 11], lambda p: 1 if p == 0 else .8), SNARE: hits([8], .9) + hits([15], .35),
                             CLAP: hits([8], .7), HAT: hat_b}),
        ("Intro Hats", 1, {HAT: hits(range(0, 16, 4), .35)}),
    ]
    def hook_section(start):
        return [("Trap Drums A", 0, start, 3), ("Trap Drums B", 0, start + 3, 1), ("Trap Drums A", 0, start + 4, 3), ("Trap Drums B", 0, start + 7, 1),
                ("808 Trap", 3, start, 8), ("Bells", 2, start, 8), ("Hook", 4, start, 8)]
    arr = ([("Bells", 2, 0, 4), ("Hook", 4, 0, 4), ("Intro Hats", 0, 2, 2)] + hook_section(4) +
           [("Trap Drums A", 0, 12, 7), ("Trap Drums B", 0, 19, 1), ("808 Trap", 3, 12, 8), ("Bells", 2, 12, 8)] +
           hook_section(20) + [("Bells", 2, 28, 4)])
    auto = {0: .3, 3: .75, 4: 1, 27: 1, 28: .8, 32: .2}
    mix = merge(DRUM_BUS, {4: {"pan": .12}, 5: {"vol": .9, "scSource": 1, "scDepth": .3}, 6: {"vol": .7}, 7: {"vol": .7}, 8: {"vol": .9}})
    return dict(
        id="trap", title="Trap - Night Drive", bpm=140, scale={"root": 9, "type": "minor"},
        genre={"ko": "트랩", "en": "Trap"},
        desc={"ko": "어두운 마이너 벨 아르페지오 위에, 킥을 따라가는 808과 빠르게 쪼개지는 하이햇.",
              "en": "Dark minor bell arpeggios over an 808 that follows the kick, with fast-rolling hi-hats."},
        traits={"ko": ["킥을 따라가는 808", "하이햇 롤", "하프타임 스네어", "훅 - 벌스 - 훅"],
                "en": ["808 following the kick", "Hi-hat rolls", "Half-time snare", "Hook - verse - hook"]},
        args=("Trap - Night Drive", 140, 0, {"root": 9, "type": "minor"}, pats, arr, auto,
              {0: .95, 1: .75, 2: .65, 3: .6, 4: .9, 5: .75, 6: .7}, mix, "Bells"))


# =====================================================================
# 3. House
# =====================================================================
def house():
    chords = [[57, 60, 64, 67], [57, 60, 64, 67], [53, 57, 60, 64], [53, 57, 60, 64]]   # Am7 Am7 Dm9(F A C E) Dm9
    roots = [45, 45, 38, 38]
    stab = [(2, 2, .75), (6, 1, .55), (10, 2, .8), (13, 2, .6)]
    bass = [N(b*16 + p, 2, r + (12 if p == 14 else 0), .85 if p != 14 else .7) for b, r in enumerate(roots) for p in (2, 6, 10, 14)]
    riff = melody([(0,2,76),(3,2,76),(6,2,79),(10,2,76),(13,3,74),(16,2,72),(19,2,72),(22,2,74),(26,4,76),
                   (32,2,77),(35,2,77),(38,2,81),(42,2,77),(45,3,76),(48,2,74),(51,2,72),(54,2,74),(58,6,69)], .65, .12)
    hats = hits(range(16), lambda p: .6 if p % 4 == 2 else (.2 if p % 2 else .3))
    pats = [
        ("Stabs", 4, {KEYS: rhythm_chords(chords, stab)}),
        ("Pad", 4, {KEYS: sustain(chords, vel=.5)}),
        ("Offbeat Bass", 4, {BASS: bass}),
        ("Riff", 4, {LEAD: riff}),
        ("House Groove", 1, {KICK: hits([0, 4, 8, 12], .95), CLAP: hits([4, 12], .75), HAT: hats}),
        ("Kick Intro", 1, {KICK: hits([0, 4, 8, 12], .9), HAT: hits([2, 6, 10, 14], .45)}),
        ("Build Roll", 2, {SNARE: roll(2, .3, .85)}),
    ]
    arr = [("Kick Intro", 0, 0, 8),
           ("House Groove", 0, 8, 8), ("Offbeat Bass", 3, 8, 8), ("Stabs", 2, 8, 8),
           ("Pad", 2, 16, 4), ("Riff", 4, 16, 4),
           ("Build Roll", 1, 20, 2), ("Pad", 2, 20, 2),
           ("House Groove", 0, 22, 10), ("Offbeat Bass", 3, 22, 10), ("Stabs", 2, 22, 10), ("Riff", 4, 22, 10)]
    auto = {0: .45, 7: .85, 8: 1, 15: 1, 16: .45, 19: .6, 21: .95, 22: 1}
    mix = merge(DRUM_BUS, {4: {"pan": .1}, 5: {"scSource": 1, "scDepth": .55}, 6: {"scSource": 1, "scDepth": .5}, 7: {"vol": .65}})
    return dict(
        id="house", title="House - Sunset Groove", bpm=124, scale={"root": 9, "type": "minor"},
        genre={"ko": "하우스", "en": "House"},
        desc={"ko": "네 박 모두 킥이 들어가는 four-on-the-floor 위에 엇박 베이스와 마이너 7 코드 스탭.",
              "en": "Four-on-the-floor kick with an offbeat bass and minor 7th chord stabs."},
        traits={"ko": ["Four-on-the-floor", "엇박 베이스와 하이햇", "브레이크다운 후 드롭", "킥 사이드체인"],
                "en": ["Four-on-the-floor", "Offbeat bass and hats", "Breakdown into drop", "Kick sidechain"]},
        args=("House - Sunset Groove", 124, 0, {"root": 9, "type": "minor"}, pats, arr, auto,
              {0: .9, 1: .7, 2: .75, 3: .55, 4: .85, 5: .85, 6: .7}, mix, "Stabs"))


# =====================================================================
# 4. Lo-fi Hip-hop
# =====================================================================
def lofi():
    chords = [[50, 53, 57, 60, 64], [53, 59, 64, 67], [52, 55, 59, 62], [60, 64, 67, 71]]   # Dm9 G13 Cmaj9 Am9 (rootless voicings)
    roots, fifths = [38, 43, 36, 45], [45, 50, 43, 52]
    rhodes = rhythm_chords(chords, [(0, 12, .5), (12, 4, .38)])
    bass = [n for b, (r, f) in enumerate(zip(roots, fifths)) for n in (N(b*16, 6, r, .8), N(b*16+8, 2, f, .6), N(b*16+10, 4, r, .7))]
    mel = melody([(2,4,72),(6,2,74),(8,6,77),(18,2,76),(20,4,74),(26,4,71),(32,6,72),(40,2,76),(42,4,79),(50,4,76),(54,2,74),(56,8,72)], .55, .08)
    boom_a = {KICK: hits([0, 7, 10], lambda p: .9 if p == 0 else .7), SNARE: hits([4, 12], .65),
              HAT: hits([0, 2, 3, 4, 6, 8, 10, 11, 12, 14], lambda p: .2 if p in (3, 11) else (.38 if p % 4 == 0 else .28))}
    boom_b = {KICK: hits([0, 3, 10, 13], lambda p: .85 if p == 0 else .65), SNARE: hits([4, 12], .65) + hits([15], .25),
              HAT: hits([0, 2, 4, 6, 8, 10, 12, 14], lambda p: .36 if p % 4 == 0 else .26)}
    pats = [
        ("Rhodes", 4, {KEYS: rhodes}),
        ("Bass", 4, {BASS: bass}),
        ("Melody", 4, {LEAD: mel}),
        ("Boom Bap A", 1, boom_a),
        ("Boom Bap B", 1, boom_b),
    ]
    def beat(start, bars):
        return [(("Boom Bap A" if (i % 4) != 3 else "Boom Bap B"), 0, start + i, 1) for i in range(bars)]
    arr = ([("Rhodes", 2, 0, 4)] +
           beat(4, 8) + [("Bass", 3, 4, 8), ("Rhodes", 2, 4, 8)] +
           beat(12, 8) + [("Bass", 3, 12, 8), ("Rhodes", 2, 12, 8), ("Melody", 4, 12, 8)] +
           beat(20, 8) + [("Bass", 3, 20, 8), ("Rhodes", 2, 20, 8), ("Melody", 4, 20, 8)] +
           [("Rhodes", 2, 28, 4), ("Melody", 4, 28, 4)])
    auto = {0: .45, 3: .68, 4: .72, 27: .72, 28: .6, 32: .3}
    mix = merge(DRUM_BUS, {8: {"vol": .75}, 4: {"pan": -.15}, 7: {"vol": .6, "pan": .1}})
    return dict(
        id="lofi", title="Lo-fi - Rainy Window", bpm=80, scale={"root": 0, "type": "major"},
        genre={"ko": "로파이 힙합", "en": "Lo-fi Hip-hop"},
        desc={"ko": "스윙을 건 붐뱁 드럼과 재즈 코드(ii-V-I-vi). 마스터 필터를 살짝 닫아 먹먹한 질감을 냅니다.",
              "en": "Swung boom-bap drums with jazz chords (ii-V-I-vi). The master filter stays slightly closed for a muffled tone."},
        traits={"ko": ["스윙 45%", "재즈 7·9·13 코드", "붐뱁 드럼", "필터로 만든 로파이 질감"],
                "en": ["45% swing", "Jazz 7th/9th/13th chords", "Boom-bap drums", "Lo-fi tone via filter"]},
        args=("Lo-fi - Rainy Window", 80, 0.45, {"root": 0, "type": "major"}, pats, arr, auto,
              {0: .85, 1: .6, 2: .5, 3: .5, 4: .8, 5: .9, 6: .6}, mix, "Rhodes"))


# =====================================================================
# 5. Synthwave
# =====================================================================
def synthwave():
    chords = [[57, 60, 64, 69], [53, 57, 60, 65], [55, 60, 64, 67], [55, 59, 62, 67]]   # Am F C G
    roots = [45, 41, 48, 43]
    tones = [[69, 72, 76, 81], [65, 69, 72, 77], [67, 72, 76, 79], [67, 71, 74, 79]]
    order = [0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 2, 1, 0, 1, 2, 3]
    arp = [N(b*16 + s, 1, t[o], .6 if s % 4 == 0 else .45) for b, t in enumerate(tones) for s, o in enumerate(order)]
    bass = [N(b*16 + p, 2, r + (12 if p in (6, 14) else 0), .85 if p % 4 == 0 else .7) for b, r in enumerate(roots) for p in range(0, 16, 2)]
    mel = melody([(0,4,76),(4,4,79),(8,6,81),(14,2,79),(16,6,77),(22,2,76),(24,8,72),(32,4,76),(36,4,79),(40,6,84),(46,2,83),
                  (48,8,79),(56,4,74),(60,4,76)], .7, .1)
    drive = {KICK: hits([0, 6, 8], lambda p: .95 if p != 6 else .7), SNARE: hits([4, 12], .95), CLAP: hits([4, 12], .6),
             HAT: hits(range(0, 16, 2), lambda p: .45 if p % 4 == 2 else .3)}
    fill = {KICK: hits([0, 8], .95), SNARE: hits([4, 12, 13, 14, 15], lambda p: .95 if p in (4, 12) else .55 + (p - 13) * .15),
            CLAP: hits([4, 12], .6), HAT: hits(range(0, 12, 2), .35)}
    pats = [
        ("Pad", 4, {KEYS: sustain(chords, vel=.5)}),
        ("Arp", 4, {LEAD: arp}),
        ("Melody", 4, {LEAD: mel}),
        ("Drive Bass", 4, {BASS: bass}),
        ("Drive", 1, drive),
        ("Fill", 1, fill),
    ]
    def drums(start, bars):
        return [("Drive", 0, start, bars - 1), ("Fill", 0, start + bars - 1, 1)]
    arr = ([("Pad", 2, 0, 4), ("Arp", 4, 0, 4)] +
           drums(4, 8) + [("Drive Bass", 3, 4, 8), ("Pad", 2, 4, 8), ("Arp", 4, 4, 8)] +
           drums(12, 8) + [("Drive Bass", 3, 12, 8), ("Pad", 2, 12, 8), ("Melody", 4, 12, 8)] +
           [("Pad", 2, 20, 4), ("Arp", 4, 20, 4)] +
           drums(24, 8) + [("Drive Bass", 3, 24, 8), ("Pad", 2, 24, 8), ("Melody", 4, 24, 8)])
    auto = {0: .25, 3: .85, 4: 1, 19: 1, 20: .5, 23: .9, 24: 1}
    mix = merge(DRUM_BUS, {2: {"vol": .9}, 4: {"pan": .2}, 6: {"scSource": 1, "scDepth": .3}, 7: {"vol": .7}})
    return dict(
        id="synthwave", title="Synthwave - Neon Highway", bpm=108, scale={"root": 9, "type": "minor"},
        genre={"ko": "신스웨이브", "en": "Synthwave"},
        desc={"ko": "8분음표로 달리는 베이스, 16분 아르페지오, 크게 울리는 2·4박 스네어의 80년대풍 사운드.",
              "en": "An 80s-style sound with a driving 8th-note bass, 16th-note arpeggios and a big snare on 2 and 4."},
        traits={"ko": ["8분 드라이브 베이스", "16분 아르페지오", "Am-F-C-G 진행", "벌스 - 코러스 - 브릿지"],
                "en": ["8th-note driving bass", "16th-note arpeggio", "Am-F-C-G progression", "Verse - chorus - bridge"]},
        args=("Synthwave - Neon Highway", 108, 0, {"root": 9, "type": "minor"}, pats, arr, auto,
              {0: .85, 1: .9, 2: .6, 3: .55, 4: .8, 5: .8, 6: .7}, mix, "Arp"))


# =====================================================================
# 6. Drum & Bass (Liquid)
# =====================================================================
def dnb():
    chords = [[52, 55, 59, 62, 66], [48, 52, 55, 59, 62], [55, 59, 62, 66], [50, 54, 57, 62]]   # Em9 Cmaj9 Gmaj7 D
    roots = [40, 36, 43, 38]
    reese = [n for c, r in enumerate(roots) for n in (N(c*32, 12, r, .9), N(c*32+14, 4, r, .7), N(c*32+20, 8, r, .85), N(c*32+28, 4, r+7, .6))]
    lead = melody([(0,8,79),(8,4,78),(12,4,76),(16,12,74),(32,8,76),(40,4,79),(44,4,81),(48,12,79),
                   (64,8,83),(72,4,81),(76,4,79),(80,12,78),(96,8,76),(104,4,74),(108,4,71),(112,16,76)], .6, .1)
    two_a = {KICK: hits([0, 10], .95), SNARE: hits([4, 12], .9) + hits([7, 15], .25),
             HAT: hits([0, 2, 3, 4, 6, 8, 10, 11, 12, 14], lambda p: .2 if p in (3, 11) else (.45 if p % 4 == 2 else .35))}
    two_b = {KICK: hits([0, 6, 10], lambda p: .95 if p != 6 else .7), SNARE: hits([4, 12], .9) + hits([9], .25),
             HAT: hits(range(0, 16, 2), lambda p: .45 if p % 4 == 2 else .35)}
    pats = [
        ("Pad", 8, {KEYS: sustain(chords, 32, .45)}),
        ("Reese", 8, {BASS: reese}),
        ("Lead", 8, {LEAD: lead}),
        ("Two-Step A", 1, two_a),
        ("Two-Step B", 1, two_b),
        ("Intro Hats", 1, {HAT: hits(range(0, 16, 2), lambda p: .35 if p % 4 == 2 else .2)}),
        ("Roll", 2, {SNARE: roll(2, .3, .9)}),
    ]
    def drums(start, bars):
        return [(("Two-Step A" if i % 4 != 3 else "Two-Step B"), 0, start + i, 1) for i in range(bars)]
    arr = ([("Pad", 2, 0, 8), ("Intro Hats", 0, 2, 4), ("Roll", 1, 6, 2)] +
           drums(8, 16) + [("Reese", 3, 8, 8), ("Reese", 3, 16, 8), ("Pad", 2, 8, 8), ("Pad", 2, 16, 8), ("Lead", 4, 8, 8), ("Lead", 4, 16, 8)] +
           [("Pad", 2, 24, 4), ("Roll", 1, 26, 2)] +
           drums(28, 4) + [("Reese", 3, 28, 4), ("Pad", 2, 28, 4)])
    auto = {0: .2, 5: .7, 7: .9, 8: 1, 23: 1, 24: .5, 26: .7, 27: .95, 28: 1}
    mix = merge(DRUM_BUS, {4: {"pan": .1}, 5: {"vol": .8, "scSource": 1, "scDepth": .4}, 6: {"vol": .75}, 7: {"vol": .65}, 8: {"vol": .9}})
    return dict(
        id="dnb", title="Drum & Bass - Liquid Sky", bpm=174, scale={"root": 4, "type": "minor"},
        genre={"ko": "드럼 앤 베이스", "en": "Drum & Bass"},
        desc={"ko": "174 BPM 투스텝 브레이크비트 위에 길게 이어지는 리스 베이스와 몽환적인 리퀴드 패드.",
              "en": "A 174 BPM two-step breakbeat under a long reese bass and dreamy liquid pads."},
        traits={"ko": ["174 BPM", "투스텝 브레이크비트", "리스 베이스", "8마디 패턴"],
                "en": ["174 BPM", "Two-step breakbeat", "Reese bass", "8-bar patterns"]},
        args=("Drum & Bass - Liquid Sky", 174, 0, {"root": 4, "type": "minor"}, pats, arr, auto,
              {0: .9, 1: .8, 2: .6, 3: .6, 4: .85, 5: .8, 6: .65}, mix, "Pad"))


SONGS = [future_bass, trap, house, lofi, synthwave, dnb]


def main():
    index, full = [], []
    for fn in SONGS:
        s = fn()
        project, bars = make_project(*s["args"])
        path = os.path.join(HERE, s["id"] + ".json")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(project, f, ensure_ascii=False, indent=1)
        meta = {"id": s["id"], "title": s["title"], "file": s["id"] + ".json", "bpm": s["bpm"], "scale": s["scale"], "bars": bars,
                "genre": s["genre"], "desc": s["desc"], "traits": s["traits"]}
        index.append(meta)
        full.append(dict(meta, project=project))
        notes = sum(len(v) for p in project["song"]["patterns"] for v in p["notes"].values())
        key = NOTE[s["scale"]["root"]] + (" major" if s["scale"]["type"] == "major" else " minor")
        print(f'{s["id"]:12} {s["bpm"]:3} BPM  {key:9} {bars:2} bars  {len(project["song"]["patterns"]):2} patterns  {len(project["song"]["clips"]):2} clips  {notes:4} notes')
    with open(os.path.join(HERE, "index.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    with open(os.path.join(ROOT, "web", "examples.js"), "w", encoding="utf-8", newline="\n") as f:
        f.write("/* examples/build_examples.py 가 만든 파일입니다. 직접 고치지 말고 생성기를 고친 뒤 다시 실행하세요. */\n")
        f.write("window.FL_EXAMPLES = " + json.dumps(full, ensure_ascii=False, separators=(",", ":")) + ";\n")


if __name__ == "__main__":
    main()
