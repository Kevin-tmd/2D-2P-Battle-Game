import pygame, sys, math, random, os
from abc import ABC, abstractmethod

# ══════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════
SCREEN_W, SCREEN_H = 1280, 720
FPS        = 60
GRAVITY    = 1200
JUMP_VEL   = -620
MOVE_SPEED = 320
FLOOR_Y    = 580
GAME_TIME  = 300
BASE_HP    = 100
BASE_MP    = 100
MP_REGEN   = 8.0   # per second
HP_REGEN   = 1.0    # per second (stops at 60s left)

LATE_DMG_BONUS_TIME  = 120   # last 2 min → +10% dmg
LATE_NOHEAL_TIME     =  60   # last 1 min → no hp regen

COLORS = {
    "bg":       (10, 10, 22),
    "floor":    (50, 55, 85),
    "p1":       (80, 160, 255),
    "p2":       (255, 90, 90),
    "hp_bg":    (60, 20, 20),
    "hp_fg":    (220, 60, 60),
    "mp_bg":    (20, 20, 60),
    "mp_fg":    (60, 120, 255),
    "white":    (255, 255, 255),
    "black":    (0, 0, 0),
    "yellow":   (255, 220, 60),
    "gray":     (120, 120, 120),
    "darkgray": (30, 30, 48),
    "green":    (80, 220, 100),
    "orange":   (255, 160, 40),
    "purple":   (180, 80, 255),
    "cyan":     (60, 220, 220),
    "thorn":    (120, 120, 120),
    "bomb":     (220, 120, 30),
    "reflect":  (180, 220, 255),
}

# ══════════════════════════════════════════════════════
#  FONTS
# ══════════════════════════════════════════════════════
_FONT_PATHS = [
    "/usr/share/fonts/truetype/nanum/NanumGothicCodingBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf",
]

class Fonts:
    _cache: dict = {}
    @classmethod
    def get(cls, size, bold=True):
        k = (size, bold)
        if k in cls._cache: return cls._cache[k]
        f = None
        for p in _FONT_PATHS:
            try: f = pygame.font.Font(p, size); break
            except: pass
        if f is None: f = pygame.font.SysFont("arial", size, bold=bold)
        cls._cache[k] = f
        return f
    @classmethod
    def r(cls, size): return cls.get(size)       # retro
    @classmethod
    def sm(cls, size): return cls.get(size, False)  # small

# ══════════════════════════════════════════════════════
#  SKILL DEFINITIONS
#
#  Fields: (id, name, tier, mp, cd, type, params)
#  tier: "low"|"mid"|"high"|"ult"
#  type: "projectile"|"dash"|"thorn"|"bomb"|"heal"|"meteor"|"reflect"
#  params: dict with type-specific keys
# ══════════════════════════════════════════════════════
# ── Projectile param keys ──────────────────────────────
# dirs: list of (dx_factor, dy_factor)  (+1=fwd, -1=bk)
# size, speed, damage, burst, burst_delay
# ── Thorn param keys ──────────────────────────────────
# count, spacing (px), delay_each, rise_height, damage
# ── Meteor param keys ─────────────────────────────────
# target: "fwd"|"bk"|"enemy"   dist: px  count, burst_delay
# size, speed, damage
# ── Bomb params ───────────────────────────────────────
# fuse, radius, damage
# ── Dash params ───────────────────────────────────────
# dir_sign (+1 fwd / -1 bk)   post: optional thorn/proj after dash
RAW_SKILLS = [
    # Skills with '#' (annotated) are temporarily removed from the game, so IGNORE them.
    (1, "Quick Burst",       "atk",  13, 0.8,  "projectile",
     {"dirs":[(1,0)],         "size":9,  "speed":560, "damage":5, "burst":3, "burst_delay":0.09}),
    (2, "[ULT] Super Burst",         "ult",  35, 35.0, "projectile",
     {"dirs":[(1,0)],         "size":13,  "speed":560, "damage":12, "burst":12, "burst_delay":0.12}),
    (3, "Foward Shot",         "atk",  8, 0.8, "projectile",
     {"dirs":[(1,0)],         "size":12,  "speed":560, "damage":12, "burst":1, "burst_delay":0.0}),
    (4, "[ULT] Twin Burst",      "ult",  45, 40.0, "projectile",
     {"dirs":[(1,0),(-1,0)],  "size":13,  "speed":560, "damage":12, "burst":12, "burst_delay":0.12}),
    (5, "Twin Shot",        "atk",  14, 0.9, "projectile",
     {"dirs":[(1,0),(-1,0)],  "size":12,  "speed":560, "damage":14, "burst":2, "burst_delay":0.12}),
    (6, "Twin Heavy",        "high",  26, 4.8, "projectile",
     {"dirs":[(1,0),(-1,0)],  "size":18,  "speed":540, "damage":24, "burst":1, "burst_delay":0.0}),
    (7, "Heavy Shot",      "high",  18, 4.2, "projectile",
     {"dirs":[(1,0)],         "size":18, "speed":540, "damage":24, "burst":1, "burst_delay":0.0}),
    (8, "Twin Mega",     "high",  38, 8.2, "projectile",
     {"dirs":[(1,0),(-1,0)],  "size":26, "speed":520, "damage":34, "burst":1, "burst_delay":0.0}),
    (9, "Heavy Burst",   "high",  28, 7.2, "projectile",
     {"dirs":[(1,0)],         "size":18, "speed":540, "damage":24, "burst":2, "burst_delay":0.18}),
    (11,"Mega Shot",        "high", 34, 7.8, "projectile",
     {"dirs":[(1,0)],         "size":26, "speed":520, "damage":34, "burst":1, "burst_delay":0.0}),
    (13,"[ULT] Giant Shot","ult",  44, 30.0, "projectile",
     {"dirs":[(1,0)],         "size":42, "speed":840, "damage":62, "burst":1, "burst_delay":0.0}),

    # DASH
    (14,"Fwd Dash",       "uty",  8, 0.8, "dash",
     {"dir":+1, "post":None}),
    (15,"Back Dash",      "uty",  6, 0.4, "dash",
     {"dir":-1, "post":None}),
    (20,"Dash Shot","uty", 14, 1.0,"dash",
     {"dir":-1, "post":"shot3fwd"}),

    (16,"Fwd Thorns",     "atk",  12, 0.5, "thorn",
     {"dirs":[+1], "count":6, "spacing":32, "delay_each":0.05, "rise_h":20, "damage":4}),
    (18,"[ULT] Radial Thorns","ult", 30, 15.0, "radial_thorn",
     {"rays":12, "per_ray":2, "spread_deg":8, "speed":440, "damage":1, "size":8}),

    # ── BOMB ──
    (21,"Bomb",           "uty",  8, 0.2, "bomb",
     {"fuse":2.0, "radius":100, "damage":26}),
    # ── HEAL ──
    (22,"Heal",     "uty",  28, 60.0,"heal",
     {"amount":25}),
    # ── METEORS (enemy-tracking) ──
    (23,"Meteor",         "uty",  6, 0.6, "meteor",
     {"count":1, "burst_delay":0.15, "size":12, "speed":1600, "damage":6}),
    (24,"Meteor Burst",      "uty",  18, 1.2, "meteor",
     {"count":5, "burst_delay":0.15, "size":12, "speed":1600, "damage":6}),
    (25,"Heavy Meteor",   "uty",  12, 0.8, "meteor",
     {"count":1, "burst_delay":0.15, "size":28, "speed":1400, "damage":12}),
    (26,"[ULT] Meteor Rain","ult",  54, 75.0, "meteor",
     {"count":34, "burst_delay":0.10,"size":12, "speed":1200, "damage":6}),
 
    (27,"[ULT] Reflect",  "ult",  14, 2.0, "reflect",
     {"duration":1.8, "w":110, "h":110}),
    # ── NEW SKILLS ──
    (28,"[ULT] Slow Field","ult", 20, 45.0, "slowfield",
     {"radius":350, "duration":5.0}),
    (29,"[ULT] Clone",    "ult",  25, 135.0, "clone",
     {"count":3}),
    (51,"[ULT] Dummy",    "ult",  35, 35, "dummy",
     {"count":1}),
    (30,"Boomerang",      "ult",  22, 3.8, "boomerang",
     {"size":14, "speed":480, "damage":14, "max_dist":500}),
    (31,"Double Jump",    "uty",  12,  1.2, "doublejump",
     {}),
    (35,"[ULT] Super Jump", "ult", 16, 5.0, "superjump",{}),
    (36,"[ULT] Planet",     "ult", 70, 70.0, "planet",  {"size":52,"damage":34,"split_dmg":8,"split_count":24,"delay":1.5}),
    (38,"[ULT] Sanctum",    "ult", 20, 130.0, "sanctum", {"radius":500,"duration":15.0}),
    (39,"Homing",           "atk", 16, 8.0, "homing",  {"size":10,"speed":280,"damage":8}),
    (40,"Smash",            "atk",  16, 1.1, "melee",   {"style":"smash","damage":13}),
    (41,"Thrust",           "atk",  16, 1.3, "melee",   {"style":"thrust","damage":14}),

    (45,"Up Shots",      "atk",  6, 0.4, "projectile",
     {"dirs":[(0,-1)], "size":12,"speed":500,"damage":12,"burst":2,"burst_delay":0.0}),
    (46,"Up Burst",     "atk", 8, 0.6, "projectile",
     {"dirs":[(0,-1)], "size":8,"speed":510,"damage":8,"burst":4,"burst_delay":0.1}),
    (47,"Up Split",     "atk", 18, 0.8, "projectile",
     {"dirs":[(0,-1),(-0.6,-0.8),(0.6,-0.8)], "size":7,"speed":490,"damage":7,"burst":2,"burst_delay":0.12}),
    (48,"Down Shot",    "atk",  6, 0.4, "projectile",
     {"dirs":[(0,1)],  "size":12,"speed":500,"damage":12,"burst":2,"burst_delay":0.0}),
    (49,"Down Split",   "atk", 18, 0.8, "projectile",
     {"dirs":[(0,1),(-0.6,0.8),(0.6,0.8)], "size":7,"speed":490,"damage":7,"burst":2,"burst_delay":0.12}),
    (50,"[ULT] Mega Heal",     "ult",  30, 80.0,"heal",
     {"amount":50}),

    (52,"[ULT] Replica",    "ult",  80, 115.0, "replica",
     {"count":1}),
    (53,"Super Dash",       "ult",  34, 10.0, "super_dash",
     {"dir":+1, "post":None}),

    #(54,"[ULT] Decoy",            "ult",  25, 90.0, "decoy",
    # {"duration":75.0}),
    (55,"[ULT] Bomb Rain",  "ult",  70, 70.0, "bomb_rain",
     {"count":24, "burst_delay":0.25, "fuse":2.0, "radius":100, "damage":26}),
    (56,"[ULT] Confusion",  "ult",  12, 0.2, "confusion",
     {"duration":1.0, "teleport_interval":3.0}),
    
    #(57,"[ULT] Homing Burst",           "atk", 45, 62.0, "homing_burst",  {"size":10,"speed":280,"damage":10}),

    # ── NEW SKILLS ────────────────────────────────────────────────────────
    # 58: Charge Shot — atk 슬롯. 버튼 누르는 동안 차지(최대 0.8s).
    #     차지량에 따라 데미지 8→28, 투사체 크기 7→20 선형 스케일.
    #     차지 중 이동 잠금(giant_charging과 동일 메커니즘 활용).
    (58,"Charge Shot",    "atk",  14, 2.2, "charge_shot",
     {"min_damage":8, "max_damage":20, "min_size":7, "max_size":20,
      "speed":580, "max_charge":0.8}),

    # 59: Burst Step — uty 슬롯. 짧은 앞대시 + 착지 시 충격파.
    #     대시 거리는 앞대시의 약 60%. 착지 폭발: 반경 70px, 데미지 10.
    #     앞대시 대체재이자 근접 보상형 이동기.
    (59,"Burst Step",     "uty",  14, 2.0, "burst_step",
     {"dash_speed":540, "dash_time":0.24, "blast_radius":70, "blast_damage":8}),

    # 60: Arc Shot — atk 슬롯. 포물선 궤도 투사체.
    #     발사 각도 45°(위 + 전방). 중력 영향을 받아 포물선 낙하.
    #     공중의 상대나 플랫폼 위를 간접 타격. 데미지 16.
    (60,"Arc Short",       "atk",  16, 0.6, "arc_shot",
     {"size":12, "speed":740, "damage":8, "gravity_scale":1.2}),
    
    (62,"Arc Long",       "atk", 16, 0.6, "arc_shot",
     {"size":12, "speed":760, "damage":8, "gravity_scale":0.8}),
    
    (64,"Arc Reverse",       "atk", 16, 0.6, "arc_reverse",
     {"size":12, "speed":760, "damage":8, "gravity_scale":0.8}),

    (63,"[ULT] Arc Burst",       "ult",  48, 45, "arc_burst",
     {"size":12, "speed":740, "damage":8, "gravity_scale":1.2}),

    # 61: Quick Stab — atk 슬롯. 극초단 전방 근접 히트박스.
    #     사거리 매우 짧지만 CD 0.35s, MP 8로 콤보 연계용.
    #     넉백 없음 → 연속 스탭으로 파고들기.
    (61,"Quick Stab",     "atk",   8, 0.3, "quick_stab",
     {"damage":6, "range":52}),

    

]

# Build lookup maps
SKILL_MAP   = {s[0]: s for s in RAW_SKILLS}
SKILLS_BY_TIER = {}
for s in RAW_SKILLS:
    t = s[2]
    SKILLS_BY_TIER.setdefault(t, []).append(s[0])

# Slot assignment rules
# slot 0: low    slot 1: low | mid    slot 2: mid | high    slot 3: ult
SLOT_TIERS = [
    ["atk"],
    ["uty",],
    ["high"],
    ["ult"],
]

def pick_skills():
    chosen = []
    for allowed in SLOT_TIERS:
        pool = []
        for t in allowed:
            pool += SKILLS_BY_TIER.get(t, [])
        pool = [sid for sid in pool if sid not in chosen]
        chosen.append(random.choice(pool))
    return chosen


# ══════════════════════════════════════════════════════
#  CHARACTER ROSTER  (30 characters — Season 4)
#  Each entry: (name, [skill1, skill2, skill3, ult], passive_index)
#
#  Slot rules:  0→atk  1→uty  2→high  3→ult
#
#  Passives:
#    0: MP Regen    (+30% MP회복)
#    1: Tough       (방어+20%, HP+5)
#    2: Glass Cannon(공격+35%, 이속+5%, 방어-30%)
#    3: Curse       (HP-15, MP회복+20%, 공격+10%)
#    4: Agility     (HP+10, 이속+12%)
#    5: Aggressive  (공격+15%, HP+10)
# ══════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════
#  CHARACTER ROSTER  (40 characters — Season 5)
#  Slot rules:  0→atk  1→uty  2→high  3→ult
#
#  [NEW] atk: 58=Charge Shot, 60=Arc Shot, 61=Quick Stab
#  [NEW] uty: 59=Burst Step
#
#  Passives:
#    0: MP Regen  (+30% MP회복)
#    1: Tough     (방어+20%, HP+5)
#    2: Glass Cannon (공격+35%, 이속+5%, 방어-30%)
#    3: Curse     (HP-15, MP회복+20%, 공격+10%)
#    4: Agility   (HP+10, 이속+12%)
#    5: Aggressive (공격+15%, HP+10)
# ══════════════════════════════════════════════════════
CHARACTERS = [

    # ══ 연사 압박형 ══

    # 1. 앞대시 진입 후 퀵버스트 스팸, 슈퍼버스트 마무리. 기본기 완성형
    ("Blitz Gunner",     [1,  14, 9,  2],  5),

    # 2. 포샷 견제 → 대시샷 역기습 3발 → 슈퍼버스트. MP리젠으로 쿨 유지
    ("Rapid Press",      [3,  20, 9,  2],  0),

    # 3. 트윈샷 전후방 견제 + 앞대시 간격조절 + 트윈버스트 전후 동시 마무리
    ("Twin Burst",       [5,  14, 6,  4],  5),

    # 4. 트윈샷 + 더블점프 공중 트윈메가 + 트윈버스트. 공중 전후방 폭딜
    ("Twin Mega",        [5,  31, 8,  4],  4),

    # ══ 저격·단타형 ══

    # 5. 포샷 견제 + 메가샷 확정 + 자이언트샷 풀위력. 유리대포 극딜
    ("Glass Sniper",     [3,  14, 11, 13], 2),

    # 6. 퀵버스트 난사 + 헤비버스트 2발 + 자이언트샷 마무리
    ("Heavy Diver",      [1,  14, 9,  13], 5),

    # 7. 차지샷 풀차지(20)+메가샷(34)+자이언트샷(62). 3단계 고데미지 연계. 유리대포
    ("Charge Sniper",    [58, 14, 11, 13], 2),

    # 8. 차지샷 + 버스트스텝 착지폭발 + 헤비버스트 + 슈퍼버스트. MP리젠 지속압박
    ("Charge Blaster",   [58, 59, 9,  2],  0),

    # ══ 근접 격투형 ══

    # 9. 앞대시 진입→쓰러스트→헤비샷 연계. 슈퍼대시 22dmg 돌진 마무리
    ("Blade Dancer",     [41, 14, 7,  53], 5),

    # 10. 스매시 범위타 + 앞대시 + 트윈헤비 전후방 + 슈퍼대시 돌격
    ("Smash Lord",       [40, 14, 6,  53], 5),

    # 11. 퀵스탭 CD0.3s 넉백없음 연속찌르기 → 버스트스텝 착지폭발 → 슈퍼대시
    ("Stab Chain",       [61, 59, 9,  53], 5),

    # 12. 스매시 근접 → 대시샷 후퇴+3발 역기습. 유리대포 메가샷+슈퍼대시 극딜
    ("Iron Fist",        [40, 20, 11, 53], 2),

    # 13. 저주 HP희생 + 쓰러스트+헤비버스트 근접공세 + 플래닛 마무리. 단기결전
    ("Berserker",        [41, 14, 9,  36], 3),

    # 14. 퀵스탭 근접 + 앞대시 + 트윈헤비 전후방 + 슈퍼대시. 기동성 근접형
    ("Quick Blade",      [61, 14, 6,  53], 4),

    # 15. 쓰러스트 + 버스트스텝 착지폭발 + 트윈메가 전후방 + 슬로우필드. 진입+제압
    ("Thrust Control",   [41, 59, 8,  28], 0),

    # ══ 아크샷 활용형 ══

    # 16. 아크숏(빠른낙하)+앞대시+메가샷+슬로우필드. 슬로우 후 아크샷 간접확정타
    ("Arc Mage",         [60, 14, 11, 28], 0),

    # 17. 아크롱(완만한낙하)+더블점프+트윈메가+자이언트샷. 공중 원거리 간접폭딜. 유리대포
    ("Arc Sniper",       [62, 31, 8,  13], 2),

    # 18. 아크리버스(역포물선)+앞대시+트윈헤비+트윈버스트. 아래서 위로 치는 독특한 각도
    ("Reverse Arc",      [64, 14, 6,  4],  5),

    # 19. 아크숏+폭탄 선치기+트윈헤비+봄레인. 폭탄+아크샷 겹치기 필드제압. 저주 단기결전
    ("Arc Bomber",       [60, 21, 6,  55], 3),

    # 20. 아크롱+버스트스텝+헤비버스트+아크버스트. 버스트스텝 진입+아크버스트 전방위
    ("Arc Burst Rush",   [62, 59, 9,  63], 4),

    # 21. 아크리버스+더블점프+메가샷+슬로우필드. 역방향 포물선+슬로우 예측불가 압박
    ("Reverse Slow",     [64, 31, 11, 28], 0),

    # ══ 리플렉트 카운터형 ══

    # 22. 포샷+앞대시+메가샷+리플렉트. 메가샷 유도 후 리플렉트 반사반격
    ("Reflect Master",   [3,  14, 11, 27], 4),

    # 23. 쓰러스트+더블점프+헤비샷+리플렉트. 근접 후 리플렉트 카운터. Tough 방어
    ("Counter Blade",    [41, 31, 7,  27], 1),

    # 24. 차지샷 위협+앞대시+트윈헤비+리플렉트. 차지샷 강제 반응 유도→리플렉트 역이용
    ("Charge Reflect",   [58, 14, 6,  27], 4),

    # 25. 아크롱+앞대시+트윈메가+리플렉트. 아크샷 간접+리플렉트 이중 방어선
    ("Arc Reflect",      [62, 14, 8,  27], 1),

    # ══ 슬로우 컨트롤형 ══

    # 26. 퀵버스트+앞대시+메가샷+슬로우필드. 슬로우 후 메가샷 확정. MP리젠 유지
    ("Slow Mage",        [1,  14, 11, 28], 0),

    # 27. 호밍+폭탄 선치기+헤비버스트+슬로우필드. 슬로우+폭탄+호밍 트리플 트랩
    ("Slow Bomber",      [39, 21, 9,  28], 0),

    # 28. 트윈샷+버스트스텝 착지+트윈메가+슬로우필드. 버스트스텝 진입→슬로우→트윈메가
    ("Slow Twin",        [5,  59, 8,  28], 2),

    # 29. 차지샷+앞대시+헤비버스트+슬로우필드. 슬로우 후 차지샷 풀차지 확정타
    ("Charge Slow",      [58, 14, 9,  28], 0),

    # ══ 생존·방어형 ══

    # 30. 퀵버스트+더블점프+헤비샷+클론. 클론 3기 방어선+공중 헤비샷. Tough
    ("Clone Wall",       [1,  31, 7,  29], 1),

    # 31. 쏜+앞대시+헤비샷+레플리카. 레플리카 HP탱킹+쏜 근접방어+헤비샷 후방딜
    ("Replica Fort",     [16, 14, 7,  52], 1),

    # 32. 퀵버스트+힐+헤비버스트+메가힐. 힐+메가힐(50hp) 자급자족 지속전. Tough
    ("Heal Fighter",     [1,  22, 9,  50], 1),

    # 33. 아크숏+힐+트윈헤비+더미. 더미 방어막+아크샷 간접압박+힐 유지. Tough
    ("Dummy Guard",      [60, 22, 6,  51], 1),

    # 34. 포샷+힐+메가샷+메가힐. 힐 사이클 돌리며 메가샷 지속딜. Tough 방어
    ("Heal Sniper",      [3,  22, 11, 50], 1),

    # ══ 생텀 거점형 ══

    # 35. 퀵버스트+앞대시+헤비버스트+생텀. 생텀 CD단축으로 헤비버스트 스팸
    ("Sanctum Gunner",   [1,  14, 9,  38], 0),

    # 36. 차지샷+앞대시+메가샷+생텀. 생텀 안 CD단축으로 차지샷 연속사용+메가샷 병행
    ("Sanctum Charge",   [58, 14, 11, 38], 5),

    # 37. 퀵스탭+힐+헤비버스트+생텀. 생텀 CD단축 퀵스탭 루프+힐 자가회복. Tough
    ("Stab Sanctum",     [61, 22, 9,  38], 1),

    # ══ 컨퓨전 기습형 ══

    # 38. 포샷+앞대시+헤비버스트+컨퓨전. 텔포 위치혼란→포샷+헤비버스트 순간기습
    ("Ghost Striker",    [3,  14, 9,  56], 4),

    # 39. 퀵스탭+버스트스텝+메가샷+컨퓨전. 텔포→퀵스탭 연속→버스트스텝→메가샷 폭딜. 유리대포
    ("Stab Phantom",     [61, 59, 11, 56], 2),

    # 40. 아크롱+앞대시+트윈헤비+컨퓨전. 텔포로 위치 노출 최소화+아크롱 간접타격
    ("Arc Phantom",      [62, 14, 6,  56], 4),

    # ══ 플래닛 마무리형 ══

    # 41. 스매시+앞대시+헤비버스트+플래닛. 근접전 HP소모 후 플래닛 투하 마무리
    ("Planet Rush",      [40, 14, 9,  36], 5),

    # 42. 호밍+앞대시+트윈헤비+플래닛. 호밍 지속딜 후 플래닛. MP리젠 유지
    ("Planet Mage",      [39, 14, 6,  36], 0),

    # 43. 차지샷+앞대시+헤비버스트+플래닛. 저주 HP희생 대신 딜+MP 보상으로 빠른 플래닛
    ("Charge Planet",    [58, 14, 9,  36], 3),

    # ══ 라디알쏜 폭발형 ══

    # 44. 퀵버스트+더블점프+트윈헤비+라디알쏜. 공중에서 전방위 36발 동시폭발+트윈헤비
    ("Radial Burst",     [1,  31, 6,  18], 5),

    # 45. 아크롱+더블점프+메가샷+라디알쏜. 아크롱 공중압박+라디알쏜 중거리 전방위. MP리젠
    ("Radial Arc",       [62, 31, 11, 18], 0),

    # 46. 차지샷+앞대시+트윈헤비+라디알쏜. 차지샷 위협+라디알쏜 근접전방위. Aggressive
    ("Radial Charge",    [58, 14, 6,  18], 5),

    # ══ 혼합·특수형 ══

    # 47. 부메랑+더블점프+헤비샷+슈퍼점프. 부메랑 왕복히트+슈퍼점프+더블점프 공중기동
    ("Boomerang Ace",    [30, 31, 7,  35], 4),

    # 48. 쏜+폭탄+트윈헤비+봄레인. 폭탄 5개 선치기+쏜 접근차단+봄레인 초토화. 저주 단기결전
    ("Bomb Zone",        [16, 21, 6,  55], 3),

    # 49. 트윈샷+버스트스텝+트윈헤비+트윈버스트. 버스트스텝 착지→트윈 전후방 압박→트윈버스트
    ("Step Twin",        [5,  59, 6,  4],  5),

    # 50. 아크리버스+버스트스텝+트윈메가+아크버스트. 역포물선+버스트스텝 착지폭발+아크버스트
    ("Reverse Burst",    [64, 59, 8,  63], 4),

]

def get_character_skills(char_idx):
    _, skill_ids, _ = CHARACTERS[char_idx]
    return skill_ids

def get_character_passive(char_idx):
    _, _, passive_idx = CHARACTERS[char_idx]
    return PASSIVE_DATA[passive_idx]

# ══════════════════════════════════════════════════════
#  PASSIVES
# ══════════════════════════════════════════════════════
PASSIVE_DATA = [
    # 0: MP Regen  — MP 회복 +30% (기존 +25% → 조금 더 차별화)
    #   장점: 고쿨기 반복사용, 지속전 강함 / 단점: 직접적 딜/서바이벌 보너스 없음
    {"name":"MP Regen",   "mp_regen_mult":1.30,"hp_bonus":0,   "dmg_mult":1.0, "spd_mult":1.0,"def_mult":1.0, "curse":False,"max_mp_bonus":0},

    # 1: Tough      — 방어 +20%, HP +5 (기존 방어만 +15% → HP 소폭 추가로 실용성↑)
    #   장점: 맞을수록 이득, 지속전 강함 / 단점: 딜 보너스 없음
    {"name":"Tough",      "mp_regen_mult":1.0, "hp_bonus":5,   "dmg_mult":1.0, "spd_mult":1.0,"def_mult":0.80,"curse":False,"max_mp_bonus":0},

    # 2: Glass Cannon — 공격 +35%, 방어 -30% (기존 공격+40%/방어-40% → 리스크 살짝 완화)
    #   장점: 투사체 한 방 위력 압도적 / 단점: 방어 불리 → 히트앤런 필수
    {"name":"Glass Cannon","mp_regen_mult":1.0,"hp_bonus":0,   "dmg_mult":1.35,"spd_mult":1.05,"def_mult":1.30,"curse":False,"max_mp_bonus":0},

    # 3: Curse       — HP -20, MP 회복 +20%, 공격 +10% (기존 HP-20만 → 보상 강화)
    #   장점: 짧은 게임이면 MP가 넘침 + 딜 소폭↑ / 단점: 체력이 항상 부족
    {"name":"Curse",      "mp_regen_mult":1.20,"hp_bonus":-20, "dmg_mult":1.10,"spd_mult":1.0,"def_mult":1.0, "curse":True, "max_mp_bonus":0},

    # 4: Agility     — HP +10, 이동속도 +12% (기존 +10% → 조금 더 차별화)
    #   장점: 포지셔닝 유리, 회피 쉬움 / 단점: 딜/방어 보너스 없음
    {"name":"Agility",    "mp_regen_mult":1.0, "hp_bonus":10,  "dmg_mult":1.0, "spd_mult":1.12,"def_mult":1.0, "curse":False,"max_mp_bonus":0},

    # 5: Aggressive  — 공격 +15%, HP +10 (기존 동일 — 무난한 올라운더)
    #   장점: 딜+생존 모두 소폭 상승 / 단점: 특화 특성 대비 단일 수치는 낮음
    {"name":"Aggressive", "mp_regen_mult":1.0, "hp_bonus":10,  "dmg_mult":1.15,"spd_mult":1.0,"def_mult":1.0, "curse":False,"max_mp_bonus":0},
]


# ══════════════════════════════════════════════════════
#  PARTICLES
# ══════════════════════════════════════════════════════
class Particle:
    __slots__=('x','y','vx','vy','life','max_life','color','size','gravity')
    def __init__(self,x,y,vx,vy,life,color,size=4,gravity=0.0):
        self.x=float(x);self.y=float(y);self.vx=float(vx);self.vy=float(vy)
        self.life=self.max_life=float(life);self.color=color;self.size=size;self.gravity=gravity
    def update(self,dt):
        self.x+=self.vx*dt;self.y+=self.vy*dt;self.vy+=self.gravity*dt
        self.life-=dt;self.vx*=0.90;self.vy*=0.90
    def draw(self,surf):
        ratio=max(0.0,self.life/self.max_life);a=int(255*ratio);r=max(1,int(self.size*ratio))
        s=pygame.Surface((r*2+2,r*2+2),pygame.SRCALPHA)
        pygame.draw.circle(s,(*self.color,a),(r+1,r+1),r);surf.blit(s,(int(self.x)-r-1,int(self.y)-r-1))

class ParticleSystem:
    def __init__(self): self.p=[]
    def add(self,p): self.p.append(p)
    def burst(self,x,y,col,count=12,spd=150,sz=5,life=0.5,grav=300):
        for _ in range(count):
            a=random.uniform(0,math.tau);s=random.uniform(spd*0.3,spd)
            self.add(Particle(x,y,math.cos(a)*s,math.sin(a)*s,life+random.uniform(-0.1,0.2),col,sz+random.randint(-1,2),grav))
    def sparks(self,x,y,col,dx=1,count=10,spd=260):
        for _ in range(count):
            a=math.atan2(0,dx)+random.uniform(-1.0,1.0);s=random.uniform(80,spd)
            self.add(Particle(x,y,math.cos(a)*s,math.sin(a)*s-random.uniform(0,80),random.uniform(0.3,0.65),col,random.randint(2,5),500))
    def trail(self,x,y,col,sz=6):
        self.add(Particle(x,y,random.uniform(-15,15),random.uniform(-15,15),random.uniform(0.08,0.22),col,sz,0))
    def land_dust(self,x,y,col):
        for _ in range(10):
            self.add(Particle(x+random.uniform(-20,20),y,random.uniform(-120,120),random.uniform(-70,-10),
                              random.uniform(0.3,0.6),tuple(min(255,c+80) for c in col),random.randint(3,7),500))
    def heal_ring(self,x,y):
        for i in range(20):
            a=(i/20)*math.tau
            self.add(Particle(x+math.cos(a)*22,y+math.sin(a)*22,math.cos(a)*50,math.sin(a)*50-90,0.9,COLORS["green"],5,-60))
    def update(self,dt):
        alive=[]
        for p in self.p:
            p.update(dt)
            if p.life>0: alive.append(p)
        self.p=alive
    def draw(self,surf):
        for p in self.p: p.draw(surf)

# ══════════════════════════════════════════════════════
#  SCREEN FX
# ══════════════════════════════════════════════════════
class ScreenFX:
    def __init__(self):
        self.shake_t=self.shake_max=self.shake_i=0.0
        self.flash_t=self.flash_max=0.0;self.flash_col=(255,255,255);self.offset=(0,0)
    def shake(self,i=8,d=0.15): self.shake_i=i;self.shake_t=self.shake_max=d
    def flash(self,col=(255,255,255),d=0.08): self.flash_col=col;self.flash_t=self.flash_max=d
    def flash_if(self,enabled,col=(255,255,255),d=0.08):
        if enabled: self.flash(col,d)
    def update(self,dt):
        if self.shake_t>0:
            self.shake_t-=dt; s=max(0,int(self.shake_i*(self.shake_t/max(0.001,self.shake_max))))
            self.offset=(random.randint(-s,s) if s>0 else 0,random.randint(-s,s) if s>0 else 0)
        else: self.offset=(0,0)
        if self.flash_t>0: self.flash_t-=dt
    def draw_flash(self,surf):
        if self.flash_t>0:
            a=int(40*self.flash_t/max(0.001,self.flash_max))
            if a>0:
                s=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA);s.fill((*self.flash_col,min(40,a)));surf.blit(s,(0,0))

# ══════════════════════════════════════════════════════
#  DAMAGE NUMBER
# ══════════════════════════════════════════════════════
class DmgNum:
    def __init__(self,x,y,val,col):
        self.x=float(x);self.y=float(y);self.vy=-110.0;self.val=int(val);self.col=col;self.life=1.0
    def update(self,dt): self.y+=self.vy*dt;self.vy*=0.90;self.life-=dt
    def draw(self,surf):
        a=int(255*max(0,self.life));lbl=f"-{self.val}" if self.val>0 else f"+{-self.val}"
        col=self.col if self.val>0 else COLORS["green"]
        txt=Fonts.r(20).render(lbl,True,col);s=pygame.Surface(txt.get_size(),pygame.SRCALPHA)
        s.blit(txt,(0,0));s.set_alpha(a);surf.blit(s,(int(self.x)-txt.get_width()//2,int(self.y)))

# ══════════════════════════════════════════════════════
#  PROJECTILE
# ══════════════════════════════════════════════════════
class Projectile:
    def __init__(self,x,y,vx,vy,size,damage,owner,is_thorn=False):
        self.x=float(x);self.y=float(y);self.vx=float(vx);self.vy=float(vy)
        self.size=size;self.damage=damage;self.owner=owner
        self.alive=True;self.age=0.0;self.trail_t=0.0
        self.is_thorn=is_thorn  # thorns can't be reflected
        self._is_arc=False          # set to True for Arc Shot projectiles
        self._arc_gravity=1.0       # gravity multiplier (arc shots use >1.0)
    def update(self,dt,particles):
        if self._is_arc:
            self.vy += GRAVITY * self._arc_gravity * dt
        self.x+=self.vx*dt;self.y+=self.vy*dt;self.age+=dt
        self.trail_t-=dt
        if self.trail_t<=0:
            self.trail_t=0.025
            col=COLORS["thorn"] if self.is_thorn else (COLORS["p1"] if self.owner==0 else COLORS["p2"])
            particles.trail(self.x,self.y,col,max(2,self.size-2))
        if self.x<-120 or self.x>SCREEN_W+120 or self.y<-400 or self.y>SCREEN_H+120: self.alive=False
    def get_rect(self): return pygame.Rect(self.x-self.size,self.y-self.size,self.size*2,self.size*2)
    def draw(self,surf):
        if self.is_thorn:
            col=COLORS["thorn"];bright=tuple(min(255,c+80) for c in col)
        else:
            col=COLORS["p1"] if self.owner==0 else COLORS["p2"]
            bright=tuple(min(255,c+110) for c in col)
        pulse=1.0+0.18*math.sin(self.age*22)
        for r2,a in [(int((self.size+8)*pulse),50),(int((self.size+3)*pulse),130)]:
            gs=pygame.Surface((r2*2,r2*2),pygame.SRCALPHA)
            pygame.draw.circle(gs,(*col,a),(r2,r2),r2);surf.blit(gs,(int(self.x)-r2,int(self.y)-r2))
        pygame.draw.circle(surf,bright,(int(self.x),int(self.y)),max(2,self.size))
        pygame.draw.circle(surf,COLORS["white"],(int(self.x),int(self.y)),max(1,self.size//3))

# ══════════════════════════════════════════════════════
#  BOMB
# ══════════════════════════════════════════════════════
class Bomb:
    def __init__(self,x,y,fuse,radius,damage,owner):
        self.x=float(x);self.y=float(y);self.vy=0.0
        self.fuse=fuse;self.max_fuse=fuse;self.radius=radius
        self.damage=damage;self.owner=owner;self.alive=True;self.exploded=False
        self.on_ground=False
    def update(self,dt,platforms):
        if not self.on_ground:
            self.vy+=GRAVITY*dt;self.y+=self.vy*dt
            if self.y>=FLOOR_Y: self.y=float(FLOOR_Y);self.vy=0;self.on_ground=True
            else:
                if self.vy>=0:
                    for plat in platforms:
                        prev=self.y-self.vy*dt
                        if prev<=plat.top+1 and self.y>=plat.top-1 and plat.left<self.x<plat.right:
                            self.y=float(plat.top);self.vy=0;self.on_ground=True;break
        self.fuse-=dt
        if self.fuse<=0: self.exploded=True;self.alive=False
    def get_explode_rect(self): return pygame.Rect(self.x-self.radius,self.y-self.radius,self.radius*2,self.radius*2)
    def draw(self,surf):
        ratio=self.fuse/self.max_fuse
        # brightness increases as fuse depletes
        bright=int(80+175*(1-ratio))
        col=(bright,max(0,bright-80),0)
        pulse=1.0+0.3*math.sin(self.age_draw() * (4+8*(1-ratio)))
        r=max(6,int(16*pulse))
        gs=pygame.Surface((r*2+10,r*2+10),pygame.SRCALPHA)
        pygame.draw.circle(gs,(*col,160),(r+5,r+5),r);surf.blit(gs,(int(self.x)-r-5,int(self.y)-r-5))
        pygame.draw.circle(surf,col,(int(self.x),int(self.y)),max(4,r-2))
        pygame.draw.circle(surf,COLORS["white"],(int(self.x),int(self.y)-r-3),3)
        # fuse timer
        if self.fuse>0:
            txt=Fonts.r(14).render(f"{self.fuse:.1f}",True,COLORS["yellow"])
            surf.blit(txt,(int(self.x)-txt.get_width()//2,int(self.y)-r-20))
    def age_draw(self): return self.max_fuse-self.fuse

# ══════════════════════════════════════════════════════
#  REFLECT SHIELD
# ══════════════════════════════════════════════════════
class ReflectShield:
    """Circular reflect shield around caster. Projectiles bounce on contact with the shield."""
    LENIENCY_PX = 18   # extra px added to hit detection so fast projectiles don't slip through
    def __init__(self,x,y,facing,w,h,owner):
        self.x=float(x);self.y=float(y);self.facing=facing
        self.radius=max(w,h)//2  # circular shield
        self.owner=owner
        self.timer=3.0
        self.alive=True
    def update(self,dt): 
        self.timer-=dt
        self.alive=self.timer>0
    def contains(self,px,py):
        """Check if point is inside the circular shield (with leniency buffer)."""
        return math.hypot(px-self.x,py-self.y)<=(self.radius+self.LENIENCY_PX)
    def get_rect(self):
        """Return bounding rect for drawing (approx)."""
        r=self.radius+self.LENIENCY_PX
        return pygame.Rect(self.x-r,self.y-r,r*2,r*2)
    def draw(self,surf):
        ratio=max(0,self.timer/3.0)
        a=int(90*ratio)
        cx,cy=int(self.x),int(self.y)
        r=self.radius
        # glow circle (draw outer leniency ring faintly)
        gs=pygame.Surface((r*2+8+self.LENIENCY_PX*2,r*2+8+self.LENIENCY_PX*2),pygame.SRCALPHA)
        off=self.LENIENCY_PX
        pygame.draw.circle(gs,(*COLORS["reflect"],max(0,a-30)),(r+4+off,r+4+off),r+off+2,1)
        pygame.draw.circle(gs,(*COLORS["reflect"],a),(r+4+off,r+4+off),r+2)
        pygame.draw.circle(gs,(*COLORS["white"],min(255,a+80)),(r+4+off,r+4+off),r+2,3)
        surf.blit(gs,(cx-r-4-off,cy-r-4-off))

# ══════════════════════════════════════════════════════
#  THORN EFFECT
# ══════════════════════════════════════════════════════
class ThornEffect:
    """Visual + hitbox for a ground spike.
    - Origin y matches the owner player's floor y (platforms included).
    - Color matches owner (p1=blue, p2=red).
    - Rise speed is 1.6x faster (duration 0.25s instead of 0.4s).
    """
    def __init__(self,x,damage,owner,origin_y=None):
        self.x=float(x);self.damage=damage;self.owner=owner
        self.origin_y = float(origin_y) if origin_y is not None else float(FLOOR_Y)
        self.timer=0.0;self.duration=0.25;self.alive=True;self.hit=False
        self.rise_h=80
    @property
    def _col(self): return COLORS["p1"] if self.owner==0 else COLORS["p2"]
    def update(self,dt): self.timer+=dt;self.alive=self.timer<self.duration
    def get_rect(self):
        progress=min(1.0,self.timer/(self.duration*0.5))
        h=int(self.rise_h*math.sin(progress*math.pi))
        return pygame.Rect(int(self.x)-12,int(self.origin_y)-h,24,h+4)
    def draw(self,surf):
        progress=min(1.0,self.timer/(self.duration*0.5))
        h=int(self.rise_h*math.sin(progress*math.pi))
        if h<2: return
        x=int(self.x); base_y=int(self.origin_y); ty=base_y-h
        col=self._col;bright=tuple(min(255,c+80) for c in col)
        # main spike
        pts=[(x-8,base_y),(x,ty-6),(x+8,base_y)]
        pygame.draw.polygon(surf,col,pts)
        pygame.draw.polygon(surf,bright,pts,2)
        # glow
        gs=pygame.Surface((40,h+20),pygame.SRCALPHA)
        pygame.draw.polygon(gs,(*col,50),[(8,h+10),(20,0),(32,h+10)])
        surf.blit(gs,(x-20,ty-10))


# ══════════════════════════════════════════════════════
#  METEOR WARNING MARKER
# ══════════════════════════════════════════════════════
class MeteorWarning:
    """Shown 0.5s before a meteor lands."""
    def __init__(self, x, owner, size):
        self.x = float(x)
        self.owner = owner
        self.size = size
        self.life = 0.5
        self.alive = True
    def update(self, dt):
        self.life -= dt
        self.alive = self.life > 0
    def draw(self, surf):
        ratio = max(0.0, self.life / 0.5)
        col = COLORS["p1"] if self.owner == 0 else COLORS["p2"]
        a = int(200 * (1.0 - ratio) + 80)
        # pulsing cross
        cx = int(self.x); cy = FLOOR_Y - 4
        r = max(4, int((self.size + 10) * (0.7 + 0.3 * math.sin(self.life * 30))))
        s = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
        pygame.draw.circle(s, (*col, min(255,a)), (r+2,r+2), r, 2)
        pygame.draw.line(s, (*col, min(255,a)), (r+2-r//2, r+2), (r+2+r//2, r+2), 2)
        pygame.draw.line(s, (*col, min(255,a)), (r+2, r+2-r//2), (r+2, r+2+r//2), 2)
        surf.blit(s, (cx-r-2, cy-r-2))

# ══════════════════════════════════════════════════════
#  SLOW FIELD
# ══════════════════════════════════════════════════════
SLOW_FIELD_RADIUS = 450  # ~7 character widths (W=30 -> 7*30/2)

class SlowField:
    MAX_TIMER = 5.0
    EXPAND_TIME = 0.6   # seconds to reach full radius
    def __init__(self, x, y, owner):
        self.x = float(x); self.y = float(y)
        self.owner = owner
        self.timer = self.MAX_TIMER; self.alive = True
        self.max_radius = SLOW_FIELD_RADIUS
        self._pulse = 0.0
        self._expand = 0.0   # 0..1 expansion progress
    @property
    def radius(self):
        return int(self.max_radius * min(1.0, self._expand / self.EXPAND_TIME))
    @property
    def fully_expanded(self):
        return self._expand >= self.EXPAND_TIME
    def update(self, dt):
        self._expand = min(self.EXPAND_TIME, self._expand + dt)
        self.timer -= dt; self.alive = self.timer > 0
        self._pulse += dt * 2.5
    def contains(self, x, y):
        return math.hypot(x - self.x, y - self.y) <= self.radius
    def draw(self, surf):
        ratio = max(0.0, self.timer / self.MAX_TIMER)
        expand_ratio = min(1.0, self._expand / self.EXPAND_TIME)
        a = int(45 * ratio)
        pulse_r = int(self.radius + 6 * math.sin(self._pulse) * expand_ratio)
        pulse_r = max(1, pulse_r)
        s = pygame.Surface((pulse_r*2+4, pulse_r*2+4), pygame.SRCALPHA)
        # expanding ring wave effect
        for ring_frac in [1.0, 0.75, 0.5]:
            ring_r = int(pulse_r * ring_frac)
            if ring_r < 2: continue
            ring_a = int(a * (1.0 - ring_frac * 0.4))
            pygame.draw.circle(s, (180, 60, 255, ring_a), (pulse_r+2, pulse_r+2), ring_r)
        pygame.draw.circle(s, (220, 120, 255, min(255, int(a*2.5))), (pulse_r+2, pulse_r+2), pulse_r, 3)
        surf.blit(s, (int(self.x)-pulse_r-2, int(self.y)-pulse_r-2))
        # timer text
        txt = Fonts.r(13).render(f"{self.timer:.1f}s", True, (220, 120, 255))
        surf.blit(txt, (int(self.x)-txt.get_width()//2, int(self.y)-pulse_r-22))

# ══════════════════════════════════════════════════════
#  MINION (Base class for Clone, Dummy, Replica, Decoy)
# ══════════════════════════════════════════════════════
class Minion:
    W, H = 30, 50  # override in subclass
    def __init__(self, x, y, color, owner_id, owner_passive):
        self.x = float(x); self.y = float(y)
        self.color = tuple(min(255, c + 60) for c in color)
        self.owner = owner_id
        self.passive = owner_passive
        self.hp = 40.0; self.max_hp = 40.0
        self.alive = True
        self.facing = 1 if owner_id == 0 else -1
        self.vx = 0.0; self.vy = 0.0
        self.on_ground = False
        self.shoot_cd = random.uniform(0.2, 3.0)
        self.walk_phase = 0.0
        self.body_bounce = 0.0
        self.hurt_flash = 0.0
        self._move_timer = random.uniform(0.5, 1.5)
        self._move_dir = random.choice([-1, 0, 1])
        self._jump_timer = random.uniform(1.0, 4.0)

    def get_rect(self):
        return pygame.Rect(int(self.x - self.W//2), int(self.y - self.H), self.W, self.H)

    def update_common(self, dt, world, platforms, particles):
        self._move_timer -= dt
        if self._move_timer <= 0:
            self._move_timer = random.uniform(0.6, 1.8)
            self._move_dir = random.choice([-1, 0, 0, 1])
        enemy = world.enemy_of(self.owner)
        if enemy:
            self.facing = 1 if enemy.x > self.x else -1
        self.vx = self._move_dir * 220
        self._jump_timer -= dt
        if self._jump_timer <= 0 and self.on_ground:
            self._jump_timer = random.uniform(2.0, 4.5)
            self.vy = JUMP_VEL * 1.15
            self.on_ground = False
        slow_cl = (1.0/3.0) if world.in_slow_for(self.x, self.y, self.owner) else 1.0
        self.vy += GRAVITY * dt
        self.y += self.vy * dt
        self.x += self.vx * slow_cl * dt
        self.on_ground = False
        if self.vy >= 0:
            for plat in platforms:
                fp = self.y - self.vy * dt
                ix = plat.left - self.W//2+4 < self.x < plat.right + self.W//2-4
                cr = fp <= plat.top+1 and self.y >= plat.top-1
                if ix and cr:
                    self.y = float(plat.top); self.vy = 0.0; self.on_ground = True; break
        if self.y >= FLOOR_Y and not self.on_ground:
            self.y = float(FLOOR_Y); self.vy = 0.0; self.on_ground = True
        if self.y > SCREEN_H + 80: self.alive = False
        self.x = max(self.W//2, min(SCREEN_W - self.W//2, self.x))
        self.shoot_cd -= dt
        if abs(self.vx) > 10 and self.on_ground: self.walk_phase += 8.0 * dt
        else: self.walk_phase *= 0.88
        self.body_bounce = math.sin(self.walk_phase) * 3 if (abs(self.vx)>10 and self.on_ground) else 0
        if self.hurt_flash > 0: self.hurt_flash -= dt
        if self.hp <= 0: self.alive = False

    def take_damage(self, dmg, particles, dnums):
        self.hp -= dmg; self.hurt_flash = 0.2
        if dnums: dnums.append(DmgNum(self.x, self.y - self.H - 8, dmg, (255, 160, 80)))
        if particles:
            particles.burst(self.x, self.y - self.H//2, self.color, 8, 150, 4, 0.3, 200)
        if self.hp <= 0:
            if particles: particles.burst(self.x, self.y - self.H//2, self.color, 22, 260, 7, 0.6, 150)

    def draw_common(self, surf, label_text, label_color):
        cx = int(self.x); by = int(self.y + self.body_bounce); ty = by - self.H
        hurt = self.hurt_flash > 0
        a_val = 180
        bc = (255, 200, 200) if hurt else self.color
        dc = tuple(max(0, c-50) for c in self.color)
        hc = tuple(min(255, c+60) for c in self.color)
        sw = math.sin(self.walk_phase); bt = ty+14; bb = by
        hy = bb-4; fo = sw*18; ko = sw*10
        pygame.draw.line(surf, dc, (cx-8,hy), (cx-8+int(ko),hy+16), 4)
        pygame.draw.line(surf, dc, (cx-8+int(ko),hy+16), (cx-8+int(fo),hy+30), 4)
        pygame.draw.line(surf, dc, (cx+8,hy), (cx+8-int(ko),hy+16), 4)
        pygame.draw.line(surf, dc, (cx+8-int(ko),hy+16), (cx+8-int(fo),hy+30), 4)
        bs = pygame.Surface((24, bb-bt), pygame.SRCALPHA)
        r_col = (*bc, a_val)
        pygame.draw.rect(bs, r_col, (0,0,24,bb-bt), border_radius=5)
        surf.blit(bs, (cx-12, bt))
        pygame.draw.rect(surf, dc, (cx-12, bt, 24, bb-bt), 2, border_radius=5)
        hs = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(hs, (*hc, a_val), (16, 16), 14)
        surf.blit(hs, (cx-16, ty+8-16))
        pygame.draw.circle(surf, dc, (cx, ty+8), 14, 2)
        hp_r = max(0.0, self.hp / self.max_hp)
        bw = 36
        pygame.draw.rect(surf, (60,20,20), (cx-bw//2, ty-14, bw, 6), border_radius=3)
        if hp_r > 0:
            pygame.draw.rect(surf, (220,80,80), (cx-bw//2, ty-14, int(bw*hp_r), 6), border_radius=3)
        pygame.draw.rect(surf, COLORS["white"], (cx-bw//2, ty-14, bw, 6), 1, border_radius=3)
        lbl = Fonts.r(10).render(label_text, True, label_color)
        surf.blit(lbl, (cx - lbl.get_width()//2, ty - 26))

# ══════════════════════════════════════════════════════
#  CLONE
# ══════════════════════════════════════════════════════
class Clone(Minion):
    W, H = 30, 50
    def __init__(self, x, y, color, owner_id, owner_passive):
        super().__init__(x, y, color, owner_id, owner_passive)
        self.hp = 40.0; self.max_hp = 40.0
        self.shoot_cd = random.uniform(0.2, 3.0)
    def update(self, dt, world, platforms, particles):
        super().update_common(dt, world, platforms, particles)
        enemy = world.enemy_of(self.owner)
        if self.shoot_cd <= 0 and enemy:
            self.shoot_cd = random.uniform(1,6)
            dmg = 4 * self.passive["dmg_mult"]
            world.projectiles.append(Projectile(
                self.x + self.facing * 22, self.y - self.H//2,
                self.facing * 480, 0, 7, dmg, self.owner))
            particles.burst(self.x + self.facing*22, self.y - self.H//2,
                            self.color, 5, 100, 3, 0.2, 60)
    def draw(self, surf):
        self.draw_common(surf, "Clone", COLORS["yellow"])


# ══════════════════════════════════════════════════════
#  DUMMY
# ══════════════════════════════════════════════════════
class Dummy(Minion):
    W, H = 35, 55
    def __init__(self, x, y, color, owner_id, owner_passive):
        super().__init__(x, y, color, owner_id, owner_passive)
        self.hp = 55.0; self.max_hp = 55.0
        self.shoot_cd = random.uniform(1.4, 5.6)
    def update(self, dt, world, platforms, particles):
        super().update_common(dt, world, platforms, particles)
        enemy = world.enemy_of(self.owner)
        if self.shoot_cd <= 0 and enemy:
            self.shoot_cd = random.uniform(1.4, 6.0)
            dmg = 12 * self.passive["dmg_mult"]
            world.projectiles.append(Projectile(
                self.x + self.facing * 22, self.y - self.H//2,
                self.facing * 480, 0, 12, dmg, self.owner))
            particles.burst(self.x + self.facing*22, self.y - self.H//2,
                            self.color, 5, 100, 3, 0.2, 60)
    def draw(self, surf):
        self.draw_common(surf, "Dummy", COLORS["yellow"])


# ══════════════════════════════════════════════════════
#  ITEM
# ══════════════════════════════════════════════════════
ITEM_TYPES = ["apple", "banana", "pear"]
ITEM_COLORS = {"apple":(220,60,60), "banana":(240,220,40), "pear":(160,220,80)}
ITEM_LABELS = {"apple":"Apple +15HP", "banana":"Banana MP Regen", "pear":"Pear CD Reset"}

class Item:
    def __init__(self, x, kind):
        self.x = float(x); self.y = -30.0
        self.vy = 0.0; self.kind = kind
        self.alive = True; self.on_ground = False
        self.age = 0.0
    def update(self, dt, platforms):
        self.age += dt
        if not self.on_ground:
            self.vy += GRAVITY * 0.4 * dt
            self.y += self.vy * dt
            if self.y >= FLOOR_Y - 10:
                self.y = float(FLOOR_Y - 10); self.vy = 0; self.on_ground = True
            else:
                if self.vy >= 0:
                    for plat in platforms:
                        prev = self.y - self.vy * dt
                        if prev <= plat.top+1 and self.y >= plat.top-1 and plat.left < self.x < plat.right:
                            self.y = float(plat.top-10); self.vy = 0; self.on_ground = True; break
    def get_rect(self): return pygame.Rect(int(self.x)-12, int(self.y)-12, 24, 24)
    def draw(self, surf):
        col = ITEM_COLORS[self.kind]
        cx, cy = int(self.x), int(self.y)
        bounce = math.sin(self.age * 3) * 4
        cy += int(bounce)
        # glow
        gs = pygame.Surface((44, 44), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*col, 60), (22, 22), 22)
        surf.blit(gs, (cx-22, cy-22))
        # shape
        if self.kind == "apple":
            pygame.draw.circle(surf, col, (cx, cy), 10)
            pygame.draw.circle(surf, tuple(min(255,c+60) for c in col), (cx-3, cy-3), 4)
            pygame.draw.line(surf, (80,160,40), (cx, cy-10), (cx+4, cy-16), 2)
        elif self.kind == "banana":
            pts = [(cx-10,cy+4),(cx-4,cy-10),(cx+6,cy-8),(cx+10,cy+4),(cx,cy+10)]
            pygame.draw.polygon(surf, col, pts)
            pygame.draw.polygon(surf, tuple(min(255,c+60) for c in col), pts, 2)
        elif self.kind == "pear":
            pygame.draw.ellipse(surf, col, (cx-8, cy-4, 16, 18))
            pygame.draw.ellipse(surf, col, (cx-6, cy-14, 12, 14))
            pygame.draw.ellipse(surf, tuple(min(255,c+60) for c in col), (cx-8, cy-4, 16, 18), 2)
            pygame.draw.line(surf, (80,160,40), (cx, cy-14), (cx+3, cy-20), 2)
        # label
        lbl = Fonts.r(11).render(self.kind.capitalize(), True, COLORS["white"])
        surf.blit(lbl, (cx - lbl.get_width()//2, cy + 14))

# ══════════════════════════════════════════════════════
#  Replica
# ══════════════════════════════════════════════════════
class Replica(Minion):
    W, H = 30, 50
    def __init__(self, x, y, color, owner_id, owner_passive):
        super().__init__(x, y, color, owner_id, owner_passive)
        self.hp = 150.0; self.max_hp = 150.0
        self.shoot_cd = random.uniform(1,10)*0.3
    def update(self, dt, world, platforms, particles):
        super().update_common(dt, world, platforms, particles)
        enemy = world.enemy_of(self.owner)
        if self.shoot_cd <= 0 and enemy:
            self.shoot_cd = random.uniform(2.0,8.0)
            dmg = 23 * self.passive["dmg_mult"]
            world.projectiles.append(Projectile(
                self.x + self.facing * 22, self.y - self.H//2,
                self.facing * 480, 0, 23, dmg, self.owner))
            particles.burst(self.x + self.facing*22, self.y - self.H//2,
                            self.color, 5, 100, 3, 0.2, 60)
    def draw(self, surf):
        self.draw_common(surf, "Replica", COLORS["yellow"])



# ══════════════════════════════════════════════════════
#  DECOY (Fake Clone - No Attack)
# ══════════════════════════════════════════════════════
class Decoy(Minion):
    W, H = 30, 50
    def __init__(self, x, y, color, owner_id, owner_passive):
        super().__init__(x, y, color, owner_id, owner_passive)
        self.hp = 250.0; self.max_hp = 250.0
        self.timer = 8.0
        self._alpha = 150
    def update_decoy(self, dt, world, platforms, particles):
        self.timer -= dt
        if self.timer <= 0:
            self.alive = False
            return
        self._move_timer -= dt
        if self._move_timer <= 0:
            self._move_timer = random.uniform(0.6, 1.8)
            self._move_dir = random.choice([-1, 0, 0, 1])
        enemy = world.enemy_of(self.owner)
        if enemy:
            self.facing = 1 if enemy.x > self.x else -1
        self.vx = self._move_dir * 200
        self._jump_timer -= dt
        if self._jump_timer <= 0 and self.on_ground:
            self._jump_timer = random.uniform(2.0, 4.5)
            self.vy = JUMP_VEL * 1.1
            self.on_ground = False
        self.vy += GRAVITY * dt
        self.y += self.vy * dt
        self.x += self.vx * dt
        self.on_ground = False
        if self.vy >= 0:
            for plat in platforms:
                fp = self.y - self.vy * dt
                ix = plat.left - self.W//2+4 < self.x < plat.right + self.W//2-4
                cr = fp <= plat.top+1 and self.y >= plat.top-1
                if ix and cr:
                    self.y = float(plat.top); self.vy = 0.0; self.on_ground = True; break
        if self.y >= FLOOR_Y and not self.on_ground:
            self.y = float(FLOOR_Y); self.vy = 0.0; self.on_ground = True
        if self.y > SCREEN_H + 80: self.alive = False
        self.x = max(self.W//2, min(SCREEN_W - self.W//2, self.x))
        if abs(self.vx) > 10 and self.on_ground: self.walk_phase += 8.0 * dt
        else: self.walk_phase *= 0.88
        self.body_bounce = math.sin(self.walk_phase) * 3 if (abs(self.vx)>10 and self.on_ground) else 0
        if self.hurt_flash > 0: self.hurt_flash -= dt
        if self.hp <= 0: self.alive = False
    def draw(self, surf):
        cx = int(self.x); by = int(self.y + self.body_bounce); ty = by - self.H
        hurt = self.hurt_flash > 0
        bc = (255, 200, 200) if hurt else self.color
        dc = tuple(max(0, c-50) for c in self.color)
        hc = tuple(min(255, c+60) for c in self.color)
        sw = math.sin(self.walk_phase); bt = ty+14; bb = by
        hy = bb-4; fo = sw*18; ko = sw*10
        pygame.draw.line(surf, dc, (cx-8,hy), (cx-8+int(ko),hy+16), 4)
        pygame.draw.line(surf, dc, (cx-8+int(ko),hy+16), (cx-8+int(fo),hy+30), 4)
        pygame.draw.line(surf, dc, (cx+8,hy), (cx+8-int(ko),hy+16), 4)
        pygame.draw.line(surf, dc, (cx+8-int(ko),hy+16), (cx+8-int(fo),hy+30), 4)
        bs = pygame.Surface((24, bb-bt), pygame.SRCALPHA)
        r_col = (*bc, self._alpha)
        pygame.draw.rect(bs, r_col, (0,0,24,bb-bt), border_radius=5)
        surf.blit(bs, (cx-12, bt))
        pygame.draw.rect(surf, dc, (cx-12, bt, 24, bb-bt), 2, border_radius=5)
        hs = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(hs, (*hc, self._alpha), (16, 16), 14)
        surf.blit(hs, (cx-16, ty+8-16))
        pygame.draw.circle(surf, dc, (cx, ty+8), 14, 2)
        hp_r = max(0.0, self.hp / self.max_hp)
        bw = 36
        pygame.draw.rect(surf, (60,20,20), (cx-bw//2, ty-14, bw, 6), border_radius=3)
        if hp_r > 0:
            pygame.draw.rect(surf, (220,80,80), (cx-bw//2, ty-14, int(bw*hp_r), 6), border_radius=3)
        pygame.draw.rect(surf, COLORS["white"], (cx-bw//2, ty-14, bw, 6), 1, border_radius=3)
        lbl = Fonts.r(9).render("Decoy", True, COLORS["cyan"])
        surf.blit(lbl, (cx - lbl.get_width()//2, ty - 26))
        timer_txt = Fonts.r(9).render(f"{self.timer:.1f}s", True, COLORS["cyan"])
        surf.blit(timer_txt, (cx - timer_txt.get_width()//2, ty - 40))



# ══════════════════════════════════════════════════════
#  PLANET WARNING (bigger than MeteorWarning)
# ══════════════════════════════════════════════════════
class PlanetWarning:
    def __init__(self, x, owner, size):
        self.x=float(x); self.owner=owner; self.size=size
        self.life=1.5; self.alive=True
    def update(self,dt): self.life-=dt; self.alive=self.life>0
    def draw(self,surf):
        ratio=max(0.0,self.life/3.0)
        col=COLORS["p1"] if self.owner==0 else COLORS["p2"]
        a=int(80+160*(1-ratio))
        cx=int(self.x); r=self.size+8
        s=pygame.Surface((r*2+4,r*2+4),pygame.SRCALPHA)
        pulse=1.0+0.15*math.sin(self.life*20)
        pr=int(r*pulse)
        pygame.draw.circle(s,(*col,min(255,a)),(r+2,r+2),pr,3)
        pygame.draw.line(s,(*col,min(255,a)),(r+2-pr,r+2),(r+2+pr,r+2),2)
        surf.blit(s,(cx-r-2,FLOOR_Y-r-8))

# ══════════════════════════════════════════════════════
#  MEGA PLANET WARNING (bigger than MeteorWarning)
# ══════════════════════════════════════════════════════
class MegaPlanetWarning:
    def __init__(self, x, owner, size):
        self.x=float(x); self.owner=owner; self.size=size
        self.life=1.5; self.alive=True
    def update(self,dt): self.life-=dt; self.alive=self.life>0
    def draw(self,surf):
        ratio=max(0.0,self.life/3.0)
        col=COLORS["p1"] if self.owner==0 else COLORS["p2"]
        a=int(160+160*(1-ratio))
        cx=int(self.x); r=self.size+8
        s=pygame.Surface((r*2+4,r*2+4),pygame.SRCALPHA)
        pulse=1.0+0.15*math.sin(self.life*20)
        pr=int(r*pulse)
        pygame.draw.circle(s,(*col,min(255,a)),(r+2,r+2),pr,3)
        pygame.draw.line(s,(*col,min(255,a)),(r+2-pr,r+2),(r+2+pr,r+2),2)
        surf.blit(s,(cx-r-2,FLOOR_Y-r-8))



# ══════════════════════════════════════════════════════
#  SANCTUM FIELD
# ══════════════════════════════════════════════════════
class SanctumField:
    def __init__(self,x,y,owner,radius,duration,color):
        self.x=float(x);self.y=float(y)
        self.owner=owner;self.max_radius=radius;self.duration=duration
        self.timer=duration;self.alive=True;self.color=color
        self._expand=0.0;self._pulse=0.0
    @property
    def radius(self): return int(self.max_radius*min(1.0,self._expand/0.8))
    def update(self,dt):
        self._expand=min(0.8,self._expand+dt)
        self.timer-=dt;self.alive=self.timer>0
        self._pulse+=dt*1.5
    def contains(self,x,y): return math.hypot(x-self.x,y-self.y)<=self.radius
    def draw(self,surf):
        ratio=max(0.0,self.timer/self.duration)
        a=int(30*ratio)
        pr=int(self.radius+5*math.sin(self._pulse))
        if pr<2: return
        s=pygame.Surface((pr*2+4,pr*2+4),pygame.SRCALPHA)
        pygame.draw.circle(s,(*self.color,a),(pr+2,pr+2),pr)
        pygame.draw.circle(s,(*self.color,min(255,a*4)),(pr+2,pr+2),pr,3)
        surf.blit(s,(int(self.x)-pr-2,int(self.y)-pr-2))
        txt=Fonts.r(12).render(f"{self.timer:.1f}s",True,self.color)
        surf.blit(txt,(int(self.x)-txt.get_width()//2,int(self.y)-pr-20))

# ══════════════════════════════════════════════════════
#  HOMING PROJECTILE
# ══════════════════════════════════════════════════════
class HomingProjectile:
    """Tracks the enemy player (not clones). Gradual turn rate."""
    def __init__(self, x, y, vx, vy, size, damage, owner):
        self.x=float(x); self.y=float(y)
        self.vx=float(vx); self.vy=float(vy)
        self.size=size; self.damage=damage; self.owner=owner
        self.alive=True; self.age=0.0; self.trail_t=0.0
        self.speed=math.hypot(vx,vy)
        self.turn_rate=2.8   # radians/sec max turn
        self.duration=5.0    # disappear after 5 seconds
    def update(self, dt, particles, world):
        self.age+=dt
        # find target
        target=world.enemy_of(self.owner)
        if target and target.alive:
            tx=target.x; ty=target.y-target.H//2
            dx=tx-self.x; dy=ty-self.y
            dist=max(1,math.hypot(dx,dy))
            # desired angle
            desired_angle=math.atan2(dy,dx)
            current_angle=math.atan2(self.vy,self.vx)
            # compute shortest angle diff
            diff=desired_angle-current_angle
            while diff>math.pi: diff-=2*math.pi
            while diff<-math.pi: diff+=2*math.pi
            # clamp turn
            turn=max(-self.turn_rate*dt, min(self.turn_rate*dt, diff))
            new_angle=current_angle+turn
            # slow field affects homing too
            spd=self.speed
            if world.in_slow_for(self.x,self.y,self.owner):
                spd*=0.2
            self.vx=math.cos(new_angle)*spd
            self.vy=math.sin(new_angle)*spd
        self.x+=self.vx*dt; self.y+=self.vy*dt
        self.trail_t-=dt
        if self.trail_t<=0:
            self.trail_t=0.03
            col=COLORS["p1"] if self.owner==0 else COLORS["p2"]
            particles.trail(self.x, self.y, col, max(2,self.size-2))
        # expire after 4 seconds
        if self.age >= self.duration:
            self.alive=False
        if self.x<-150 or self.x>SCREEN_W+150 or self.y<-400 or self.y>SCREEN_H+150:
            self.alive=False
    def get_rect(self):
        return pygame.Rect(self.x-self.size,self.y-self.size,self.size*2,self.size*2)
    def draw(self, surf):
        col=COLORS["p1"] if self.owner==0 else COLORS["p2"]
        bright=tuple(min(255,c+100) for c in col)
        pulse=1.0+0.22*math.sin(self.age*18)
        # outer glow
        gr=int((self.size+7)*pulse)
        gs=pygame.Surface((gr*2,gr*2),pygame.SRCALPHA)
        pygame.draw.circle(gs,(*col,60),(gr,gr),gr); surf.blit(gs,(int(self.x)-gr,int(self.y)-gr))
        # core
        pygame.draw.circle(surf,bright,(int(self.x),int(self.y)),max(2,self.size))
        # direction indicator (small line showing heading)
        angle=math.atan2(self.vy,self.vx)
        ex=int(self.x+math.cos(angle)*(self.size+5))
        ey=int(self.y+math.sin(angle)*(self.size+5))
        pygame.draw.line(surf,COLORS["white"],(int(self.x),int(self.y)),(ex,ey),2)


# ══════════════════════════════════════════════════════
#  MELEE ATTACK  (overhead smash / thrust)
# ══════════════════════════════════════════════════════
class MeleeAttack:
    """Short-duration hitbox with a visual swing animation.
    style: 'smash' (overhead downswing) | 'thrust' (forward stab)
          'burst_step_blast' (radial explosion on landing)
          'quick_stab' (ultra-short jab, no knockback)
    """
    def __init__(self, x, y, facing, style, damage, owner, color):
        self.x=float(x); self.y=float(y)
        self.facing=facing; self.style=style
        self.damage=damage; self.owner=owner; self.color=color
        if   style=='smash':            self.duration=0.32
        elif style=='thrust':           self.duration=0.28
        elif style=='burst_step_blast': self.duration=0.30
        elif style=='quick_stab':       self.duration=0.18
        else:                           self.duration=0.28
        self.timer    = self.duration
        self.alive    = True
        self.hit_ids  = set()   # targets already hit this swing
        self._phase   = 0.0     # 0..1 animation progress

    def update(self, dt):
        self.timer -= dt
        self._phase = 1.0 - max(0.0, self.timer / self.duration)
        self.alive  = self.timer > 0

    def get_rect(self):
        """Active hitbox (follows owner, set each frame by GameState)."""
        if self.style == 'smash':
            # Wide downward arc in front, slightly above floor
            w, h = 60, 55
            rx = self.x + self.facing * 20
            ry = self.y - h + 10
        elif self.style == 'thrust':
            w, h = 72, 28
            rx = self.x + self.facing * 22
            ry = self.y - 30
        elif self.style == 'burst_step_blast':
            # Circular AoE centred on caster — radius 70px
            w, h = 140, 140
            rx = self.x
            ry = self.y - 70
        elif self.style == 'quick_stab':
            # Very short forward jab — narrow & close range
            w, h = 52, 22
            rx = self.x + self.facing * 18
            ry = self.y - 32
        else:
            w, h = 60, 40
            rx = self.x + self.facing * 20
            ry = self.y - h + 10
        return pygame.Rect(int(rx - w//2), int(ry), w, h)

    # ── blade geometry helpers ──────────────────────────────────────────
    @staticmethod
    def _draw_blade(surf, tip, base, col, light, width=4):
        """Draw a sharp sword blade: thick at base, tapers to a point."""
        dx = 1*(tip[0]-base[0]); dy = 1*(tip[1]-base[1])
        length = max(1, math.hypot(dx,dy))
        nx = -dy/length; ny = dx/length   # normal
        hw = width/2
        pts = [
            (base[0]+nx*hw*1.8, base[1]+ny*hw*1.8),   # base left
            (base[0]-nx*hw*1.8, base[1]-ny*hw*1.8),   # base right
            (tip[0],            tip[1]),               # sharp tip
        ]
        pygame.draw.polygon(surf, col, [(int(x),int(y)) for x,y in pts])
        # edge highlight (bright thin line along one face)
        pygame.draw.line(surf, light,
                         (int(base[0]+nx*hw), int(base[1]+ny*hw)),
                         (int(tip[0]),        int(tip[1])),  2)

    @staticmethod
    def _draw_blade_full(surf, tip, base, col, light, guard_col, width=5):
        """Full sword: blade + guard + grip."""
        dx = tip[0]-base[0]; dy = tip[1]-base[1]
        length = max(1, math.hypot(dx,dy))
        ux = dx/length; uy = dy/length   # unit toward tip
        nx = -uy;       ny =  ux         # normal
        hw = width/2
        # blade polygon (thin triangle)
        pts = [
            (base[0]+nx*hw*2.2, base[1]+ny*hw*2.2),
            (base[0]-nx*hw*2.2, base[1]-ny*hw*2.2),
            (tip[0],            tip[1]),
        ]
        pygame.draw.polygon(surf, col, [(int(x),int(y)) for x,y in pts])
        # fuller (central groove - slightly darker)
        mid_start = (base[0]+ux*6+nx*0.5, base[1]+uy*6+ny*0.5)
        mid_end   = (tip[0]-ux*8, tip[1]-uy*8)
        pygame.draw.line(surf, light,
                         (int(mid_start[0]),int(mid_start[1])),
                         (int(mid_end[0]),  int(mid_end[1])), 1)
        # guard (crossbar)
        gx = base[0]-ux*3; gy = base[1]-uy*3
        pygame.draw.line(surf, guard_col,
                         (int(gx+nx*10), int(gy+ny*10)),
                         (int(gx-nx*10), int(gy-ny*10)), 4)
        pygame.draw.circle(surf, guard_col, (int(gx),int(gy)), 4)
        # grip
        grip_end = (gx-ux*14, gy-uy*14)
        pygame.draw.line(surf, guard_col,
                         (int(gx),int(gy)),
                         (int(grip_end[0]),int(grip_end[1])), 3)
        pygame.draw.circle(surf, light, (int(grip_end[0]),int(grip_end[1])), 3)

    def draw(self, surf):
        # Dispatch new styles to dedicated helpers
        if self.style == 'burst_step_blast':
            self._draw_burst_blast(surf)
            return
        if self.style == 'quick_stab':
            self._draw_quick_stab(surf)
            return

        # ── color palette — P1=sky blue, P2=pink ─────────────────────
        if self.owner == 0:
            base   = (100, 200, 255)   # sky blue
            silver = (180, 230, 255)
        else:
            base   = (255, 130, 180)   # pink
            silver = (255, 200, 225)
        light  = tuple(min(255, c+80) for c in base)
        dark   = tuple(max(0,   c-90) for c in base)
        white  = (255, 255, 255)
        gold   = (255, 210,  60)

        p     = self._phase          # 0→1  swing progress
        fade  = max(0.0, 1.0 - p)   # opacity envelope
        f     = self.facing          # +1 or -1
        ox    = int(self.x)
        oy    = int(self.y) - 32     # roughly chest height

        # ─────────────────────────────────────────────────────────────
        #  Shared sword drawing helper
        # ─────────────────────────────────────────────────────────────
        def draw_sword(surface, grip, tip, alpha=255, width=6):
            """
            Draw a full longsword from grip to tip:
              - Blade (tapered triangle with fuller groove)
              - Guard (crossbar perpendicular at base of blade)
              - Grip (wrapped handle behind guard)
              - Pommel (round cap at grip end)
            alpha: 0-255 for trail transparency
            """
            gx, gy = grip; tx, ty = tip
            dx = tx - gx; dy = (ty - gy)
            ln = max(1.0, math.hypot(dx, dy))
            ux = dx/ln; uy = dy/ln         # unit toward tip
            nx = -uy;   ny =  ux           # perpendicular (normal)
            hw = width / 2.0

            # ── Blade (triangle: wide at guard, sharp at tip) ───────
            b_pts = [
                (gx + nx*hw*2.4,  gy + ny*hw*2.4),
                (gx - nx*hw*2.4,  gy - ny*hw*2.4),
                (tx,              ty),
            ]
            if alpha < 255:
                bs = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                pygame.draw.polygon(bs, (*silver, alpha),
                                    [(int(x),int(y)) for x,y in b_pts])
                surface.blit(bs, (0,0))
            else:
                pygame.draw.polygon(surface, silver,
                                    [(int(x),int(y)) for x,y in b_pts])

            # ── Fuller (central groove highlight) ────────────────────
            f_start = (gx + ux*8  + nx*0.4, gy + uy*8  + ny*0.4)
            f_end   = (tx - ux*12 + nx*0.4, ty - uy*12 + ny*0.4)
            la = min(255, int(alpha * 1.3))
            if alpha < 255:
                ls = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                pygame.draw.line(ls, (*white, la),
                                 (int(f_start[0]),int(f_start[1])),
                                 (int(f_end[0]),  int(f_end[1])), 1)
                surface.blit(ls,(0,0))
            else:
                pygame.draw.line(surface, white,
                                 (int(f_start[0]),int(f_start[1])),
                                 (int(f_end[0]),  int(f_end[1])), 1)

            # ── Guard (crossbar) ─────────────────────────────────────
            guard_len = hw * 4.5
            g_cx = gx - ux*2; g_cy = gy - uy*2
            g_a  = min(255, int(alpha*1.2))
            g_col = (*dark, g_a) if alpha < 255 else dark
            g_pts = [
                (g_cx + nx*guard_len - ux*2, g_cy + ny*guard_len - uy*2),
                (g_cx - nx*guard_len - ux*2, g_cy - ny*guard_len - uy*2),
                (g_cx - nx*guard_len + ux*3, g_cy - ny*guard_len + uy*3),
                (g_cx + nx*guard_len + ux*3, g_cy + ny*guard_len + uy*3),
            ]
            if alpha < 255:
                gs2 = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                pygame.draw.polygon(gs2, (*dark, g_a),
                                    [(int(x),int(y)) for x,y in g_pts])
                surface.blit(gs2,(0,0))
            else:
                pygame.draw.polygon(surface, dark,
                                    [(int(x),int(y)) for x,y in g_pts])

            # ── Grip (handle, 18px back from guard) ─────────────────
            grip_end = (g_cx - ux*18, g_cy - uy*18)
            if alpha < 255:
                hs = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                pygame.draw.line(hs, (*base, min(255,int(alpha*1.1))),
                                 (int(g_cx),int(g_cy)),
                                 (int(grip_end[0]),int(grip_end[1])), 4)
                surface.blit(hs,(0,0))
            else:
                pygame.draw.line(surface, base,
                                 (int(g_cx),int(g_cy)),
                                 (int(grip_end[0]),int(grip_end[1])), 4)
                # grip wrap lines
                for wrap in [4, 8, 12]:
                    wx = g_cx - ux*wrap; wy = g_cy - uy*wrap
                    pygame.draw.line(surface, dark,
                                     (int(wx-nx*3),int(wy-ny*3)),
                                     (int(wx+nx*3),int(wy+ny*3)), 1)

            # ── Pommel ───────────────────────────────────────────────
            pm = grip_end
            if alpha < 255:
                ps = pygame.Surface((16,16), pygame.SRCALPHA)
                pygame.draw.circle(ps, (*dark, min(255,int(alpha*1.1))), (8,8), 5)
                surface.blit(ps,(int(pm[0])-8,int(pm[1])-8))
            else:
                pygame.draw.circle(surface, dark,  (int(pm[0]),int(pm[1])), 5)
                pygame.draw.circle(surface, light, (int(pm[0]),int(pm[1])), 3)

        # ─────────────────────────────────────────────────────────────
        #  SMASH — diagonal overhead slash
        #  Grip travels upper-back → lower-front
        #  Blade sweeps: upper-forward → lower-forward (big arc)
        # ─────────────────────────────────────────────────────────────
        if self.style == 'smash':
            BLADE = 74

            # ease-out: fast start, decelerates at end
            ep = 1.0 - (1.0 - p) ** 2

            # ── All geometry in LOCAL space (facing=+1 = rightward) ──
            # Then mirror X by f for left-facing.
            # This guarantees identical motion shape regardless of direction.
            #   Grip: starts back(-18) and up(-26), ends forward(+20) and down(+18)
            #   Blade: sweeps from upper-forward(-65deg) to lower-forward(+82deg)
            #          X-component of local blade offset is always POSITIVE
            #          (tip is always in front of grip in local space) ✓
            loc_gx = -18 + 38 * ep          # grip local X: -18 → +20
            loc_gy = -26 + 44 * ep          # grip local Y: -26 → +18

            a_start = math.radians(-65)     # blade angle local: upper-fwd
            a_end   = math.radians( 82)     # blade angle local: lower-fwd
            a_cur   = a_start + (a_end - a_start) * ep

            # local tip offset (cos always >= 0 for this angle range)
            loc_tx = loc_gx + BLADE * math.cos(a_cur)   # always forward
            loc_ty = loc_gy + BLADE * math.sin(a_cur)

            # convert to screen (mirror X by facing)
            grip_x = ox + int(f * loc_gx)
            grip_y = oy + int(loc_gy)
            tip_x  = ox + int(f * loc_tx)
            tip_y  = oy + int(loc_ty)

            # ── SLASH TRAILS ──────────────────────────────────────────
            TRAIL = 9
            for i in range(TRAIL, 0, -1):
                t_ep  = max(0.0, ep - i * 0.07)
                t_a   = a_start + (a_end - a_start) * t_ep
                t_lgx = -18 + 38 * t_ep
                t_lgy = -26 + 44 * t_ep
                t_ltx = t_lgx + BLADE * math.cos(t_a)
                t_lty = t_lgy + BLADE * math.sin(t_a)
                t_gx  = ox + int(f * t_lgx); t_gy = oy + int(t_lgy)
                t_tx  = ox + int(f * t_ltx); t_ty = oy + int(t_lty)
                trail_a = int(110 * (1 - i/TRAIL) * fade)
                if trail_a < 8: continue
                draw_sword(surf, (t_gx, t_gy), (t_tx, t_ty),
                           alpha=trail_a, width=5)

            # ── MOTION ARC SPEED LINES ────────────────────────────────
            for i in range(6):
                t_ep2  = max(0.0, ep - i * 0.06)
                t_a2   = a_start + (a_end - a_start) * t_ep2
                t_lgx2 = -18 + 38 * t_ep2
                t_lgy2 = -26 + 44 * t_ep2
                t_ltx2 = t_lgx2 + (BLADE * 0.72) * math.cos(t_a2)
                t_lty2 = t_lgy2 + (BLADE * 0.72) * math.sin(t_a2)
                arc_tx = ox + int(f * t_ltx2)
                arc_ty = oy + int(t_lty2)
                aa = int(60 * (1 - i/6) * fade)
                if aa < 5: continue
                pygame.draw.line(surf, (*light, aa),
                    (arc_tx, arc_ty), (int(tip_x), int(tip_y)), 2)

            # ── MAIN BLADE ────────────────────────────────────────────
            draw_sword(surf, (grip_x, grip_y), (tip_x, tip_y), width=6)

            # ── IMPACT EFFECT ─────────────────────────────────────────
            if p > 0.70:
                ia = int(255 * (1 - (p - 0.70) / 0.30))
                ix, iy = int(tip_x), int(tip_y)
                # lines along local blade direction (mirrored)
                for dist in [14, 24]:
                    ex2 = ix + int(f * math.cos(a_cur) * dist)
                    ey2 = iy + int(    math.sin(a_cur) * dist)
                    pygame.draw.line(surf, (*white, ia), (ix, iy), (ex2, ey2), 2)
                    # perpendicular flash
                    px2 = ix + int(    math.sin(a_cur) * dist * 0.5)
                    py2 = iy - int(f * math.cos(a_cur) * dist * 0.5)
                    pygame.draw.line(surf, (*light, ia//2), (ix, iy), (px2, py2), 2)
                rs = pygame.Surface((40, 40), pygame.SRCALPHA)
                rr = int(4 + 18 * (p - 0.70) / 0.30)
                pygame.draw.circle(rs, (*light, ia//2), (20, 20), rr, 2)
                surf.blit(rs, (ix - 20, iy - 20))

        # ─────────────────────────────────────────────────────────────
        #  THRUST — two-step: cock back THEN lunge forward
        #  Phase 0..0.25: cock arm back (wind-up)
        #  Phase 0.25..0.55: FAST lunge forward (the thrust)
        #  Phase 0.55..1.0: retract
        # ─────────────────────────────────────────────────────────────
        else:
            BLADE = 72

            if p < 0.25:
                # Wind-up: pull back, blade horizontal (no Y angle flip)
                ep2    = p / 0.25
                grip_x = ox + f * int(-12 - 10*ep2)   # pull back
                grip_y = oy + int(-4 * ep2)             # slightly up
                tilt_y = -6 * ep2                       # blade tilts slightly up
                ext_m  = 0.72 + 0.08*ep2
                tip_x  = grip_x + f * int(BLADE * ext_m)
                tip_y  = grip_y + int(tilt_y * ext_m)

            elif p < 0.55:
                # LUNGE: fast forward, purely horizontal
                ep2    = ((p - 0.25) / 0.30) ** 2     # ease-in²
                grip_x = ox + f * int(-22 + 50*ep2)
                grip_y = oy + int(-4 + 4*ep2)
                tip_x  = grip_x + f * BLADE
                tip_y  = grip_y

                # ── SPEED LINES while lunging ─────────────────────────
                if ep2 < 0.85:
                    for dy_off in [-8, -4, 0, 4, 8]:
                        la2 = int(180*(1-ep2)*(1-abs(dy_off)/10))
                        if la2 < 8: continue
                        lx1 = int(ox + f * (-22 + 50*(ep2*0.4)))
                        lx2 = int(grip_x)
                        ly  = int(grip_y) + dy_off
                        pygame.draw.line(surf, (*light, la2),
                                         (lx1, ly), (lx2, ly), 2)

            else:
                # Retract
                ep2    = 1 - (1 - (p - 0.55)/0.45)**1.5
                grip_x = ox + f * int(28 - 40*ep2)
                grip_y = oy + int(2*ep2)
                tip_x  = grip_x + f * BLADE
                tip_y  = grip_y

            # ── THRUST TRAILS (only during lunge phase) ──────────────
            if 0.25 < p < 0.55:
                lunge_t = (p - 0.25) / 0.30
                TRAIL2  = 6
                for i in range(TRAIL2, 0, -1):
                    t_p2  = max(0.25, p - i*0.04)
                    t_ep3 = ((t_p2 - 0.25)/0.30)**2
                    t_gx  = ox + f*int(-22 + 50*t_ep3)
                    t_gy  = oy + int(-4 + 4*t_ep3)
                    t_tx  = t_gx + f*BLADE
                    t_ty  = t_gy
                    ta2   = int(100*(1-i/TRAIL2)*lunge_t)
                    if ta2 < 6: continue
                    draw_sword(surf,(t_gx,t_gy),(t_tx,t_ty),alpha=ta2,width=4)

            # ── MAIN BLADE ────────────────────────────────────────────
            draw_sword(surf, (grip_x, grip_y), (tip_x, tip_y), width=6)

            # ── IMPACT BURST at peak lunge ────────────────────────────
            if 0.38 < p < 0.56:
                ba2 = int(255*(1-abs(p-0.47)/0.09)); ba2=min(255,ba2)
                ix, iy = int(tip_x), int(tip_y)
                # Radial sparks forward + slight spread
                for i in range(6):
                    spread_a = (i - 2.5) * 0.28   # spread angle
                    dist2 = 8 + i*3
                    sx2 = ix + int(f * math.cos(spread_a) * dist2)
                    sy2 = iy + int(math.sin(spread_a) * dist2)
                    pygame.draw.line(surf, (*white, ba2),
                                     (ix, iy), (sx2, sy2), 2)
                # Diamond tip flash
                diamond = [
                    (ix + f*14,  iy),
                    (ix + f*4,   iy - 8),
                    (ix - f*2,   iy),
                    (ix + f*4,   iy + 8),
                ]
                ds = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                pygame.draw.polygon(ds, (*light, ba2), [(int(x),int(y)) for x,y in diamond])
                surf.blit(ds, (0,0))

    def height_offset(self):
        return 36

    def _draw_burst_blast(self, surf):
        """Expanding shockwave ring for burst_step landing explosion."""
        p    = self._phase
        col  = COLORS["p1"] if self.owner==0 else COLORS["p2"]
        bright = tuple(min(255,c+80) for c in col)
        cx, cy = int(self.x), int(self.y - 25)
        # ring expands outward, fades quickly
        r   = int(20 + 60 * p)
        a   = int(200 * (1.0 - p))
        if a < 5: return
        gs2 = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
        pygame.draw.circle(gs2, (*col, min(255,a)),        (r+2,r+2), r,    4)
        pygame.draw.circle(gs2, (*bright, min(255,a//2)),  (r+2,r+2), max(1,r-8))
        surf.blit(gs2, (cx-r-2, cy-r-2))
        # inner flash at start
        if p < 0.3:
            ir  = int(12 * (1-p/0.3))
            ifs = pygame.Surface((ir*2+2, ir*2+2), pygame.SRCALPHA)
            pygame.draw.circle(ifs, (255,255,255,int(180*(1-p/0.3))), (ir+1,ir+1), ir)
            surf.blit(ifs, (cx-ir-1, cy-ir-1))

    def _draw_quick_stab(self, surf):
        """Fast dagger jab: short spike in facing direction."""
        p   = self._phase
        col = COLORS["p1"] if self.owner==0 else COLORS["p2"]
        bright = tuple(min(255,c+100) for c in col)
        f   = self.facing
        ox, oy = int(self.x), int(self.y - 28)
        # spike tip: lunges out at p=0.4, retracts
        ext = math.sin(min(1.0,p/0.4)*math.pi) * 38
        tip_x = ox + int(f*(22 + ext))
        tip_y = oy
        base_x = ox + int(f*10)
        a   = max(0, int(255*(1-p)))
        if a < 5: return
        # blade
        s = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        pygame.draw.line(s, (*bright, a), (base_x, tip_y), (tip_x, tip_y), 4)
        pygame.draw.circle(s, (*bright, a), (tip_x, tip_y), 4)
        surf.blit(s, (0,0))

# ══════════════════════════════════════════════════════
#  SPREAD BULLET PROJECTILE
#  Travels forward; on player-hit OR max-dist → splits into N radial bullets
# ══════════════════════════════════════════════════════
class SpreadBulletProjectile:
    def __init__(self, x, y, vx, vy, size, damage, split_dmg, split_count, max_dist, owner):
        self.x=float(x); self.y=float(y)
        self.vx=float(vx); self.vy=float(vy)
        self.size=size; self.damage=damage
        self.split_dmg=split_dmg; self.split_count=split_count
        self.max_dist=max_dist; self.owner=owner
        self.alive=True; self.age=0.0; self.trail_t=0.0
        self.start_x=float(x); self.start_y=float(y)
        self.exploded=False; self.split_done=False; self.hit=False
    def update(self, dt, particles):
        self.age+=dt; self.x+=self.vx*dt; self.y+=self.vy*dt
        self.trail_t-=dt
        if self.trail_t<=0:
            self.trail_t=0.025
            col=COLORS["p1"] if self.owner==0 else COLORS["p2"]
            particles.trail(self.x, self.y, col, max(3,self.size-2))
        if math.hypot(self.x-self.start_x,self.y-self.start_y)>=self.max_dist and not self.exploded:
            self.explode(particles)
        if self.x<-200 or self.x>SCREEN_W+200 or self.y<-400 or self.y>SCREEN_H+200:
            self.explode(particles)
    def explode(self, particles):
        self.exploded=True; self.alive=False
        col=COLORS["p1"] if self.owner==0 else COLORS["p2"]
        particles.burst(self.x, self.y, col, 12, 180, 5, 0.4, 200)
    def get_rect(self):
        return pygame.Rect(self.x-self.size, self.y-self.size, self.size*2, self.size*2)
    def draw(self, surf):
        col=COLORS["p1"] if self.owner==0 else COLORS["p2"]
        bright=tuple(min(255,c+110) for c in col)
        pulse=1.0+0.2*math.sin(self.age*20)
        r=int((self.size+6)*pulse)
        gs=pygame.Surface((r*2,r*2),pygame.SRCALPHA)
        pygame.draw.circle(gs,(*col,60),(r,r),r); surf.blit(gs,(int(self.x)-r,int(self.y)-r))
        pygame.draw.circle(surf,bright,(int(self.x),int(self.y)),max(2,self.size))
        pygame.draw.circle(surf,COLORS["white"],(int(self.x),int(self.y)),max(1,self.size//3))

# ══════════════════════════════════════════════════════
#  SKILL  (runtime instance)
# ══════════════════════════════════════════════════════
class Skill:
    def __init__(self,sid):
        d=SKILL_MAP[sid]
        self.id=sid;self.name=d[1];self.tier=d[2];self.mp_cost=d[3];self.cooldown=d[4]
        self.stype=d[5];self.params=d[6]
        self.timer=0.0;self.just_used=0.0
    def is_ready(self): return self.timer<=0
    def update(self,dt):
        if self.timer>0: self.timer=max(0.0,self.timer-dt)
        if self.just_used>0: self.just_used=max(0.0,self.just_used-dt)
    def cd_ratio(self): return 1.0-(self.timer/self.cooldown) if self.cooldown>0 else 1.0

# ══════════════════════════════════════════════════════
#  PLAYER
# ══════════════════════════════════════════════════════
class Player:
    W,H=30,50

    def __init__(self,pid,x,y,color,skill_ids,passive):
        self.id=pid;self.color=color;self.passive=passive
        self.max_hp=max(10,BASE_HP+passive["hp_bonus"])
        self.hp=float(self.max_hp)
        self.max_mp=max(10,BASE_MP+passive["max_mp_bonus"])
        self.mp=float(self.max_mp)
        self.x=float(x);self.y=float(y);self.vx=self.vy=0.0
        self.facing=1 if pid==0 else -1
        self.on_ground=self.prev_on_ground=False;self.alive=True
        self.skills=[Skill(sid) for sid in skill_ids]
        self.walk_phase=self.attack_anim=self.hurt_flash=self.body_bounce=0.0
        self.is_moving=False
        self.dashing=False;self.dash_vx=0.0;self.dash_timer=0.0
        self.dash_dir=1;self.dash_ghost_t=0.0
        self.kb_vx=self.kb_vy=self.kb_timer=0.0
        self._pending=[]  # {delay,elapsed,fired, fn}  fn() spawns the effect
        self.giant_charging=False   # True while Giant Shot is charging
        self.giant_charge_t=0.0     # 0..0.5
        self.giant_charge_col=(255,255,255)
        # Bomb charge system
        self.bomb_charges=1         # start with 1 (max 5)
        self.bomb_charge_timer=3.0  # regen 1 charge per second
        # Reflect charge system
        self.reflect_charges=1         # start with 1 (max 3)
        self.reflect_charge_timer=15.0  # regen 1 charge per second
        # Confusion state
        # and charge system
        self.confusion_active=False
        self.confusion_timer=0.0
        self.confusion_teleport_timer=0.0
        self.confusion_teleport_interval=0.0
        self.confusion_charges=3
        self.confusion_charge_timer=15.0
        # Charge Shot state
        self.charge_shot_charging = False
        self.charge_shot_t        = 0.0    # 0..max_charge
        self.charge_shot_slot     = -1     # which skill slot is charging
        self._charge_shot_max     = 0.8    # seconds to full charge

    def get_rect(self): return pygame.Rect(int(self.x-self.W//2),int(self.y-self.H),self.W,self.H)

    def move(self,dx,dt):
        if self.kb_timer>0 or self.dashing: return
        self.vx=dx*MOVE_SPEED*self.passive["spd_mult"]
        self.facing=int(math.copysign(1,dx)) if dx!=0 else self.facing
        self.is_moving=dx!=0

    def jump(self):
        if self.on_ground and self.kb_timer<=0 and not self.dashing:
            self.vy=JUMP_VEL;self.on_ground=False

    # ── Skill dispatch ────────────────────────────────
    def use_skill(self,slot,world,particles,late_dmg_bonus=False):
        if slot>=len(self.skills): return
        sk=self.skills[slot]
        if not sk.is_ready() or self.mp<sk.mp_cost: return
        self.mp-=sk.mp_cost;sk.timer=sk.cooldown;sk.just_used=0.3
        self.attack_anim=0.3
        particles.burst(self.x+self.facing*22,self.y-self.H//2,self.color,6,120,4,0.22,80)
        p=sk.params; t=sk.stype

        def dmg_mod(base):
            d=base*self.passive["dmg_mult"]
            if late_dmg_bonus: d*=1.10
            return d

        if t=="projectile":
            is_giant = (sk.id==13)
            charge_delay = 0.8 if is_giant else 0.0
            if is_giant:
                self.giant_charging=True; self.giant_charge_t=0.0
                self.giant_charge_col=self.color
            def make_proj(facing=self.facing, dirs=p["dirs"], sz=p["size"],
                          spd=p["speed"], dmg=dmg_mod(p["damage"]),
                          burst=p["burst"], bd=p["burst_delay"], giant=is_giant, cdel=charge_delay):
                for i in range(burst):
                    delay=cdel+bd*i
                    def fire(facing=facing,dirs=dirs,sz=sz,spd=spd,dmg=dmg,g=giant):
                        if g: self.giant_charging=False
                        for dxf,dyf in dirs:
                            adx=dxf*facing
                            world.projectiles.append(Projectile(
                                self.x+adx*22,self.y-self.H//2,
                                adx*spd,dyf*spd,sz,dmg,self.id))
                    self._queue(delay,fire)
            make_proj()

        elif t=="dash":
            self._do_dash(p["dir"]*self.facing,particles,p.get("post"),
                          lambda dmg=dmg_mod(20): dmg, world, late_dmg_bonus)
            
        elif t=="super_dash":
            self._do_s_dash(p["dir"]*self.facing,particles,p.get("post"),
                          lambda dmg=dmg_mod(60): dmg, world, late_dmg_bonus)
                

        elif t=="thorn":
            dirs=p["dirs"]; count=p["count"]; spacing=p["spacing"]
            delay_e=p["delay_each"]; dmg=dmg_mod(p["damage"])
            for side in dirs:
                for i in range(count):
                    ox=side*self.facing*(60+spacing*i)
                    tx=self.x+ox
                    tx=max(20,min(SCREEN_W-20,tx))
                    player_y=self.y   # capture owner's current y
                    def spawn_thorn(tx=tx,dmg=dmg,oy=player_y):
                        world.thorns.append(ThornEffect(tx,dmg,self.id,origin_y=oy))
                    self._queue(delay_e*i*(1 if side==dirs[0] else 1.2),spawn_thorn)

        elif t=="charge_shot":
            # Begin charging — actual fire happens in release_charge_shot()
            self.charge_shot_charging = True
            self.charge_shot_t        = 0.0
            self.charge_shot_slot     = slot
            self._charge_shot_max     = p["max_charge"]
            # Refund MP & cooldown here; they'll be properly consumed on release
            self.mp += sk.mp_cost
            sk.timer = 0.0

        elif t=="burst_step":
            # Short forward dash that explodes on landing
            self.dashing    = True
            self.dash_vx    = self.facing * p["dash_speed"]
            self.dash_timer = p["dash_time"]
            self.dash_dir   = self.facing
            self.dash_ghost_t = 0.0
            blast_r   = p["blast_radius"]
            blast_dmg = dmg_mod(p["blast_damage"])
            owner_snap = self
            def do_blast(r=blast_r, d=blast_dmg, owner=owner_snap):
                # circular explosion around landing position
                world.melee_attacks.append(
                    MeleeAttack(owner.x, owner.y, owner.facing, "burst_step_blast", d, owner.id, owner.color))
            self._queue(p["dash_time"] + 0.02, do_blast)

        elif t=="arc_shot":
            facing = self.facing
            sz    = p["size"]; spd  = p["speed"]; dmg = dmg_mod(p["damage"])
            gs    = p["gravity_scale"]
            for x in range(0,5):
                arc_delay = x*0.15
                # 45° upward + forward velocity; gravity_scale stored on projectile via subclass trick
                vx_a  = facing * spd * 0.45 +0.15*x   # cos(63°)
                vy_a  = -spd * 0.89 +0.15*x          # sin(63°)
                def fire_arc(px=self.x+facing*22, py=self.y-self.H//2,
                                vx=vx_a, vy=vy_a, s=sz, d=dmg, g=gs):
                    proj = Projectile(px, py, vx, vy, s, d, self.id)
                    proj._arc_gravity = g   # consumed in ArcShot update path
                    proj._is_arc = True
                    world.projectiles.append(proj)
                self._queue(arc_delay, fire_arc)
        
        elif t=="arc_reverse":
            facing = self.facing
            sz    = p["size"]; spd  = p["speed"]; dmg = dmg_mod(p["damage"])
            gs    = p["gravity_scale"]
            for x in range(0,5):
                arc_delay = x*0.15
                # 45° upward + forward velocity; gravity_scale stored on projectile via subclass trick
                vx_a  = -1 * facing * spd * 0.45 +0.15*x   # cos(63°)
                vy_a  = -spd * 0.89 +0.15*x          # sin(63°)
                def fire_arc(px=self.x+facing*22, py=self.y-self.H//2,
                                vx=vx_a, vy=vy_a, s=sz, d=dmg, g=gs):
                    proj = Projectile(px, py, vx, vy, s, d, self.id)
                    proj._arc_gravity = g   # consumed in ArcShot update path
                    proj._is_arc = True
                    world.projectiles.append(proj)
                self._queue(arc_delay, fire_arc)
        
        elif t=="arc_burst":
            facing = self.facing
            sz    = p["size"]; spd  = p["speed"]; dmg = dmg_mod(p["damage"])
            gs    = p["gravity_scale"]
            arc_delay = 0
            for x in range(0,15):
                arc_delay += random.randint(5,25)*0.01
                # 45° upward + forward velocity; gravity_scale stored on projectile via subclass trick
                vx_a  = facing * spd * 0.40 +0.20*x   # cos(63°)
                vy_a  = -spd * 0.89 +0.15*x          # sin(63°)
                def fire_arc(px=self.x+facing*22, py=self.y-self.H//2,
                                vx=vx_a, vy=vy_a, s=sz, d=dmg, g=gs):
                    proj = Projectile(px, py, vx, vy, s, d, self.id)
                    proj._arc_gravity = g   # consumed in ArcShot update path
                    proj._is_arc = True
                    world.projectiles.append(proj)
                self._queue(arc_delay, fire_arc)
            arc_delay = 0
            for x in range(0,15):
                arc_delay += random.randint(5,25)*0.01
                # 45° upward + forward velocity; gravity_scale stored on projectile via subclass trick
                vx_a  = -1 * facing * spd * 0.45 +0.15*x   # cos(63°)
                vy_a  = -spd * 0.89 +0.15*x          # sin(63°)
                def fire_arc(px=self.x+facing*22, py=self.y-self.H//2,
                                vx=vx_a, vy=vy_a, s=sz, d=dmg, g=gs):
                    proj = Projectile(px, py, vx, vy, s, d, self.id)
                    proj._arc_gravity = g   # consumed in ArcShot update path
                    proj._is_arc = True
                    world.projectiles.append(proj)
                self._queue(arc_delay, fire_arc)

        elif t=="quick_stab":
            dmg   = dmg_mod(p["damage"])
            rng   = p["range"]
            owner_snap = self
            def do_stab(d=dmg, r=rng, owner=owner_snap):
                world.melee_attacks.append(
                    MeleeAttack(owner.x, owner.y, owner.facing, "quick_stab", d, owner.id, owner.color))
            self._queue(0, do_stab)

        elif t=="radial_thorn":
            # 12-direction radial burst fired SIMULTANEOUSLY from a safe offset.
            # SPAWN_OFFSET: projectiles start SPAWN_R px away from the caster center
            # so a player standing on top of the caster cannot be hit by every bullet.
            SPAWN_R = 55   # px — enough to clear both player hitboxes when overlapping
            rays       = p["rays"]        # 12
            per_ray    = p["per_ray"]     # 3
            spread_deg = p["spread_deg"]  # fan width per ray
            spd        = p["speed"]
            dmg        = dmg_mod(p["damage"])
            sz         = p["size"]
            base_angle_step = 360.0 / rays
            cx_snap, cy_snap = self.x, self.y - self.H // 2
            projs = []
            for ray_i in range(rays):
                base_deg = ray_i * base_angle_step
                for sub_i in range(per_ray):
                    if per_ray > 1:
                        fan_offset = -spread_deg/2 + spread_deg * sub_i / (per_ray - 1)
                    else:
                        fan_offset = 0.0
                    deg = base_deg + fan_offset
                    rad = math.radians(deg)
                    cos_r, sin_r = math.cos(rad), math.sin(rad)
                    vx_r = cos_r * spd
                    vy_r = sin_r * spd
                    # spawn position offset along the ray direction
                    px = cx_snap + cos_r * SPAWN_R
                    py = cy_snap + sin_r * SPAWN_R
                    projs.append((px, py, vx_r, vy_r))
            # fire ALL bullets in a single queued callback — truly simultaneous
            def fire_all(bullets=projs, d=dmg, s=sz):
                for px, py, vx, vy in bullets:
                    world.projectiles.append(Projectile(px, py, vx, vy, s, d, self.id))
            self._queue(0, fire_all)

        elif t=="bomb":
            # Use charge system
            if self.bomb_charges <= 0: return  # no charges, do nothing
            self.bomb_charges -= 1
            if self.bomb_charges < 5:
                self.bomb_charge_timer = min(self.bomb_charge_timer, 3.0)  # start regen if not already
            # Set actual cooldown based on remaining charges
            sk.timer = 0.1 if self.bomb_charges > 0 else 3.0
            self.mp += sk.mp_cost  # refund mp since we spent it above (charge is the limit)
            self.mp -= sk.mp_cost  # actually re-deduct
            def drop_bomb(fuse=p["fuse"],radius=p["radius"],dmg=dmg_mod(p["damage"])):
                world.bombs.append(Bomb(self.x,self.y-self.H,fuse,radius,dmg,self.id))
            self._queue(0,drop_bomb)

        elif t=="heal":
            amt=p["amount"]
            self.hp=min(self.max_hp,self.hp+amt)
            particles.heal_ring(self.x,self.y-self.H//2)

        elif t=="meteor":
            count=p["count"];bd=p["burst_delay"];sz=p["size"]
            spd=p["speed"];dmg=dmg_mod(p["damage"])
            enemy_ref=world.enemy_of(self.id)
            is_rain=(count>=10)   # Meteor Rain tracks live position

            for i in range(count):
                warn_delay=bd*i
                land_delay=warn_delay+0.5
                if is_rain:
                    def warn_rain(sz=sz,owner_id=self.id,eref=enemy_ref,spread=80):
                        tx=max(20,min(SCREEN_W-20, eref.x+random.uniform(-spread,spread)))
                        world.meteor_warnings.append(MeteorWarning(tx,owner_id,sz))
                    def fire_rain(sz=sz,spd=spd,dmg=dmg,eref=enemy_ref,spread=80):
                        tx=max(20,min(SCREEN_W-20, eref.x+random.uniform(-spread,spread)))
                        world.projectiles.append(Projectile(
                            tx,-80+random.uniform(-30,0),0,spd,sz,dmg,self.id))
                    self._queue(warn_delay,warn_rain)
                    self._queue(land_delay,fire_rain)
                else:
                    snap=enemy_ref.x+random.uniform(-30,30)*i
                    def warn_meteor(tx=snap,sz=sz,owner_id=self.id):
                        tx2=max(20,min(SCREEN_W-20,tx))
                        world.meteor_warnings.append(MeteorWarning(tx2+random.uniform(-18,18),owner_id,sz))
                    def fire_meteor(tx=snap,sz=sz,spd=spd,dmg=dmg):
                        tx2=max(20,min(SCREEN_W-20,tx))
                        world.projectiles.append(Projectile(
                            tx2+random.uniform(-18,18),-80+random.uniform(-30,0),
                            0,spd,sz,dmg,self.id))
                    self._queue(warn_delay,warn_meteor)
                    self._queue(land_delay,fire_meteor)

        elif t=="reflect":
            # Use charge system
            if self.reflect_charges <= 0: return  # no charges, do nothing
            self.reflect_charges -= 1
            if self.reflect_charges < 3:
                self.reflect_charge_timer = min(self.reflect_charge_timer, 15.0)  # start regen if not already
            # Set actual cooldown based on remaining charges
            sk.timer = 0.1 if self.reflect_charges > 0 else 15.0
            self.mp += sk.mp_cost  # refund mp since we spent it above (charge is the limit)
            self.mp -= sk.mp_cost  # actually re-deduct
            def spawn_reflect(dur=p["duration"],w2=p["w"],h2=p["h"]):
                world.shields.append(ReflectShield(self.x,self.y-self.H//2,self.facing,w2,h2,self.id))
            self._queue(0,spawn_reflect)

        elif t=="superjump":
            # Jump + 4-dir × 2 bullets (offset from center) at launch & land
            self.vy = JUMP_VEL * 1.2; self.on_ground=False
            particles.burst(self.x,self.y-self.H//2,self.color,10,120,4,0.3,60)
            def shoot4x2(owner=self,dmg=dmg_mod(4)):
                # 4 directions, 2 bullets each, offset 18px so they won't all hit at once
                for i in range(4):
                    a=2*math.pi*i/4
                    for spread in [-0.18, 0.18]:  # 2 bullets slightly spread
                        a2=a+spread
                        ox2=owner.x+math.cos(a)*18
                        oy2=owner.y-owner.H//2+math.sin(a)*18
                        world.superjump_projs.append(Projectile(
                            ox2, oy2,
                            math.cos(a2)*370, math.sin(a2)*370,
                            4, dmg, owner.id))
            self._queue(0,shoot4x2)  # on launch
            self._superjump_apex_done=False
            self._superjump_land_done=False
            self._superjump_active=True
            self._superjump_dmg=dmg_mod(4)

        elif t=="planet":
            sz=p["size"]; pdmg=dmg_mod(p["damage"]); sdmg=dmg_mod(p["split_dmg"])
            sc=p["split_count"]; delay=p["delay"]
            target=world.enemy_of(self.id)
            tx=target.x
            def warn_planet(tx=tx,sz=sz,owner_id=self.id):
                world.planet_warnings.append(PlanetWarning(tx,owner_id,sz))
            def fire_planet(tx=tx,sz=sz,spd=600.0,pdmg=pdmg,sdmg=sdmg,sc=sc):
                world.projectiles.append(Projectile(tx,-80,0,spd,sz,pdmg,self.id))
            self._queue(0,warn_planet)
            self._queue(delay,fire_planet)

        elif t=="mega_planet":
            sz=p["size"]; pdmg=dmg_mod(p["damage"]); sdmg=dmg_mod(p["split_dmg"])
            sc=p["split_count"]; delay=p["delay"]
            target=world.enemy_of(self.id)
            tx=target.x
            def warn_planet(tx=tx,sz=sz,owner_id=self.id):
                world.planet_warnings.append(MegaPlanetWarning(tx,owner_id,sz))
            def fire_planet(tx=tx,sz=sz,spd=600.0,pdmg=pdmg,sdmg=sdmg,sc=sc):
                world.projectiles.append(Projectile(tx,-80,0,spd,sz,pdmg,self.id))
            self._queue(0,warn_planet)
            self._queue(delay,fire_planet)

        elif t=="manaburst":
            dur=p["duration"]
            world.mana_burst[self.id]=dur
            particles.burst(self.x,self.y-self.H//2,self.color,24,220,7,0.6,60)

        elif t=="sanctum":
            scol=COLORS["p1"] if self.id==0 else COLORS["p2"]
            def spawn_sanctum(dur=p["duration"],rad=p["radius"]):
                world.sanctums.append(SanctumField(self.x,self.y-self.H//2,self.id,rad,dur,scol))
            self._queue(0,spawn_sanctum)
            particles.burst(self.x,self.y-self.H//2,scol,16,180,6,0.5,40)

        elif t=="spreadbullet":
            sz=p["size"]; spd=p["speed"]; dmg=dmg_mod(p["damage"])
            sdmg=dmg_mod(p["split_dmg"]); sc=p["split_count"]; md=p["max_dist"]
            facing=self.facing
            def launch_sb(sz=sz,spd=spd,dmg=dmg,sdmg=sdmg,sc=sc,md=md,facing=facing):
                world.spread_bullets.append(SpreadBulletProjectile(
                    self.x+facing*22, self.y-self.H//2,
                    facing*spd, 0, sz, dmg, sdmg, sc, md, self.id))
            self._queue(0, launch_sb)

        elif t=="homing":
            sz=p["size"]; spd=p["speed"]; dmg=dmg_mod(p["damage"])
            facing=self.facing
            def launch_homing(sz=sz,spd=spd,dmg=dmg,facing=facing):
                vx=facing*spd; vy=0.0
                world.homing_projs.append(HomingProjectile(
                    self.x+facing*22, self.y-self.H//2, vx, vy, sz, dmg, self.id))
            self._queue(0, launch_homing)
        
        elif t=="homing_burst":
            for i in range(3):    
                sz=p["size"]; spd=p["speed"]; dmg=dmg_mod(p["damage"])
                facing=self.facing
                def launch_homing(sz=sz,spd=spd,dmg=dmg,facing=facing):
                    vx=facing*spd; vy=0.0
                    world.homing_projs.append(HomingProjectile(
                        self.x+facing*22, self.y-self.H//2, vx, vy, sz, dmg, self.id))
                self._queue(1.0*i, launch_homing)

        elif t=="melee":
            style=p["style"]; dmg=dmg_mod(p["damage"])
            owner_snap=self
            def launch_melee(style=style,dmg=dmg,owner=owner_snap):
                world.melee_attacks.append(MeleeAttack(
                    owner.x, owner.y, owner.facing, style, dmg, owner.id, owner.color))
            self._queue(0, launch_melee)

        elif t=="slowfield":
            def spawn_sf(dur=p["duration"]):
                world.slow_fields.append(SlowField(self.x, self.y-self.H//2, self.id))
            self._queue(0, spawn_sf)
            particles.burst(self.x, self.y-self.H//2, (180,60,255), 20, 120, 6, 0.6, 50)

        elif t=="clone":
            for _ in range(p["count"]):
                ox = random.choice([-60, 60])
                cx2 = max(self.W, min(SCREEN_W-self.W, self.x+ox))
                world.clones.append(Clone(cx2, self.y, self.color, self.id, self.passive))
            particles.burst(self.x, self.y-self.H//2, self.color, 20, 200, 7, 0.5, 100)
        
        elif t=="dummy":
            for _ in range(p["count"]):
                ox = random.choice([-60, 60])
                cx2 = max(self.W, min(SCREEN_W-self.W, self.x+ox))
                world.clones.append(Dummy(cx2, self.y, self.color, self.id, self.passive))
            particles.burst(self.x, self.y-self.H//2, self.color, 20, 200, 7, 0.5, 100)
        
        elif t=="replica":
            for _ in range(p["count"]):
                ox = random.choice([-60, 60])
                cx2 = max(self.W, min(SCREEN_W-self.W, self.x+ox))
                world.clones.append(Replica(cx2, self.y, self.color, self.id, self.passive))
            particles.burst(self.x, self.y-self.H//2, self.color, 20, 200, 7, 0.5, 100)

        elif t=="army":
            for _ in range(6):
                ox = random.choice([-60, 60])
                cx2 = max(self.W, min(SCREEN_W-self.W, self.x+ox))
                world.clones.append(Clone(cx2, self.y, self.color, self.id, self.passive))
            particles.burst(self.x, self.y-self.H//2, self.color, 20, 200, 7, 0.5, 100)
            for _ in range(3):
                ox = random.choice([-60, 60])
                cx2 = max(self.W, min(SCREEN_W-self.W, self.x+ox))
                world.clones.append(Dummy(cx2, self.y, self.color, self.id, self.passive))
            particles.burst(self.x, self.y-self.H//2, self.color, 20, 200, 7, 0.5, 100)
            for _ in range(1):
                ox = random.choice([-60, 60])
                cx2 = max(self.W, min(SCREEN_W-self.W, self.x+ox))
                world.clones.append(Replica(cx2, self.y, self.color, self.id, self.passive))
            particles.burst(self.x, self.y-self.H//2, self.color, 20, 200, 7, 0.5, 100)

        elif t=="boomerang":
            sz=p["size"]; spd=p["speed"]; dmg=dmg_mod(p["damage"])
            owner_self=self
            def launch_boom(facing=self.facing, sz=sz, spd=spd, dmg=dmg, owner=owner_self):
                bm=BoomerangProjectile(
                    owner.x+facing*22, owner.y-owner.H//2, facing, spd, sz, dmg, owner.id)
                bm._owner_ref=owner   # follow owner's live position on return
                world.boomerangs.append(bm)
            self._queue(0, launch_boom)

        elif t=="doublejump":
            self.vy = JUMP_VEL * 0.9
            self.on_ground = False
            particles.burst(self.x, self.y-self.H//2, self.color, 8, 100, 4, 0.25, -50)

        elif t=="spike":
            sz=p["size"]; spd=p["speed"]; dmg=dmg_mod(p["damage"])
            sdmg=dmg_mod(p["split_dmg"]); sc=p["split_count"]; md=p["max_dist"]
            def launch_spike(facing=self.facing, sz=sz, spd=spd, dmg=dmg, sdmg=sdmg, sc=sc, md=md):
                world.spike_projs.append(SpikeProjectile(
                    self.x+facing*22, self.y-self.H//2, facing, spd, sz, dmg, sdmg, sc, md, self.id))
            self._queue(0, launch_spike)

        elif t=="spread":
            cnt=p["count"]; dmg=dmg_mod(p["damage"]); spd=p["speed"]
            md=p["max_dist"]; ang=p["spread_angle"]
            facing=self.facing
            def launch_spread(facing=facing, cnt=cnt, dmg=dmg, spd=spd, md=md, ang=ang):
                base_angle = 0.0 if facing>0 else math.pi
                for i in range(cnt):
                    a = base_angle + ang*(i/(cnt-1) - 0.5)
                    vx2 = math.cos(a)*spd; vy2 = math.sin(a)*spd
                    world.spread_projs.append(SpreadProjectile(
                        self.x+facing*18, self.y-self.H//2, vx2, vy2, 5, dmg, md, self.id))
            self._queue(0, launch_spread)

        elif t=="decoy":
            # Spawn 1 decoy at player position
            world.clones.append(Decoy(self.x, self.y, self.color, self.id, self.passive))
            particles.burst(self.x, self.y-self.H//2, self.color, 12, 150, 5, 0.35, 80)

        elif t=="bomb_rain":
            # Rain 18 bombs from sky at random X positions
            count = p["count"]
            bd = p["burst_delay"]
            fuse = p["fuse"]
            radius = p["radius"]
            dmg = dmg_mod(p["damage"])
            for i in range(count):
                delay = bd * i
                def drop_bomb_rain(fuse=fuse, radius=radius, dmg=dmg):
                    tx = random.uniform(80, SCREEN_W-80)
                    world.bombs.append(Bomb(tx, -50, fuse, radius, dmg, self.id))
                self._queue(delay, drop_bomb_rain)

        elif t=="confusion":
            if self.confusion_charges <= 0: return  # no charges, do nothing
            self.confusion_charges -= 1
            if self.confusion_charges < 3:
                self.confusion_charge_timer = min(self.confusion_charge_timer, 15.0)  # start regen if not already
            # Set actual cooldown based on remaining charges
            sk.timer = 0.1 if self.confusion_charges > 0 else 15.0
            self.mp += sk.mp_cost  # refund mp since we spent it above (charge is the limit)
            self.mp -= sk.mp_cost  # actually re-deduct
            # Start confusion state: teleport every 2s for 20s, leaving decoy at old position
            self.confusion_active = True
            self.confusion_timer = p["duration"]  # 20 seconds
            self.confusion_teleport_interval = p["teleport_interval"]  # 2 seconds
            self.confusion_teleport_timer = 0.0
            particles.burst(self.x, self.y-self.H//2, (180,80,255), 16, 200, 6, 0.5, 100)
            

    def _queue(self,delay,fn):
        self._pending.append({"delay":delay,"elapsed":0.0,"fired":False,"fn":fn})

    def release_charge_shot(self, world, particles, late_dmg_bonus=False):
        """Called on key-up. If a charge_shot was being held, fire it now."""
        if not self.charge_shot_charging:
            return
        self.charge_shot_charging = False
        slot = self.charge_shot_slot
        if slot < 0 or slot >= len(self.skills):
            return
        sk = self.skills[slot]
        if sk.stype != "charge_shot":
            return
        # Check MP & cooldown (consume now)
        if self.mp < sk.mp_cost or not sk.is_ready():
            self.charge_shot_charging = False
            return
        self.mp -= sk.mp_cost
        sk.timer = sk.cooldown
        sk.just_used = 0.3
        self.attack_anim = 0.3

        p   = sk.params
        t   = self.charge_shot_t
        mx  = self._charge_shot_max
        ratio = min(1.0, t / mx)   # 0.0 (instant tap) → 1.0 (full charge)

        min_d = p["min_damage"]; max_d = p["max_damage"]
        min_s = p["min_size"];   max_s = p["max_size"]
        spd   = p["speed"]

        dmg  = min_d + (max_d - min_d) * ratio
        sz   = int(min_s + (max_s - min_s) * ratio)
        if late_dmg_bonus: dmg *= 1.10
        dmg = dmg * self.passive["dmg_mult"]

        facing = self.facing
        px = self.x + facing * 22
        py = self.y - self.H // 2

        particles.burst(px, py, self.color, int(6 + 12*ratio), int(100+140*ratio), sz, 0.25+0.2*ratio, 80)

        def fire_cs(px=px, py=py, vx=facing*spd, vy=0.0, d=dmg, s=sz):
            world.projectiles.append(Projectile(px, py, vx, vy, s, d, self.id))
        self._queue(0, fire_cs)

    def _do_dash(self,dir_sign,particles,post,dmg_fn,world,late_dmg):
        self.dashing=True;self.dash_vx=dir_sign*750;self.dash_timer=0.20
        self.dash_dir=dir_sign;self.dash_ghost_t=0.0
        if post=="thorn3bk":
            facing=self.facing
            dmg=dmg_fn()
            for i in range(3):
                ox=-facing*(60+130*i);tx=self.x+ox;tx=max(20,min(SCREEN_W-20,tx))
                owner_y_snap=self.y
                def sp(tx=tx,dmg=dmg,oy=owner_y_snap): world.thorns.append(ThornEffect(tx,dmg,self.id,origin_y=oy))
                self._queue(0.22+0.18*i,sp)
        elif post=="shot3fwd":
            facing=self.facing;dmg=12 #dmg_fn()
            for i in range(3):
                def sp(facing=facing,dmg=dmg):
                    world.projectiles.append(Projectile(self.x+facing*22,self.y-self.H//2,facing*560,0,7,dmg,self.id))
                self._queue(0.22+0.12*i,sp)

    def _do_s_dash(self,dir_sign,particles,post,dmg_fn,world,late_dmg):
        self.dashing=True;self.dash_vx=dir_sign*1500;self.dash_timer=0.30
        self.dash_dir=dir_sign;self.dash_ghost_t=0.0
        if post=="thorn3bk":
            facing=self.facing
            dmg=dmg_fn()
            for i in range(3):
                ox=-facing*(60+130*i);tx=self.x+ox;tx=max(20,min(SCREEN_W-20,tx))
                owner_y_snap=self.y
                def sp(tx=tx,dmg=dmg,oy=owner_y_snap): world.thorns.append(ThornEffect(tx,dmg,self.id,origin_y=oy))
                self._queue(0.22+0.18*i,sp)
        elif post=="shot3fwd":
            facing=self.facing;dmg=12 #dmg_fn()
            for i in range(3):
                def sp(facing=facing,dmg=dmg):
                    world.projectiles.append(Projectile(self.x+facing*22,self.y-self.H//2,facing*560,0,7,dmg,self.id))
                self._queue(0.22+0.12*i,sp)


    def update(self,dt,world,particles,platforms,hp_regen_on,dmg_bonus):
        # pending queue
        new_p=[]
        for pb in self._pending:
            pb["elapsed"]+=dt
            if pb["elapsed"]>=pb["delay"] and not pb["fired"]:
                pb["fired"]=True;pb["fn"]()
            elif not pb["fired"]: new_p.append(pb)
        self._pending=new_p

        # Confusion state: periodic teleportation
        if self.confusion_active:
            self.confusion_timer -= dt
            self.confusion_teleport_timer -= dt
            if self.confusion_teleport_timer <= 0:
                self.x = random.uniform(100, SCREEN_W-100)
                self.y = random.uniform(150, 500)
                particles.burst(self.x, self.y-self.H//2, (180,80,255), 8, 120, 4, 0.3, 50)
                self.confusion_teleport_timer = self.confusion_teleport_interval
            if self.confusion_timer <= 0:
                self.confusion_active = False
                particles.burst(self.x, self.y-self.H//2, (180,80,255), 12, 150, 5, 0.4, 80)

        for sk in self.skills: sk.update(dt)
        # Sanctum: extra CD drain (4x on top of normal = 5x total = 80% reduction)
        if any(sc.owner==self.id and sc.contains(self.x,self.y-self.H//2)
               for sc in world.sanctums):
            for sk in self.skills:
                if sk.timer>0: sk.timer=max(0.0, sk.timer-dt*4.0)

        # knockback
        if self.kb_timer>0:
            self.kb_timer-=dt*2
            self.x+=self.kb_vx*dt
            self.y+=self.kb_vy*dt
            self.kb_vx*=0.80
            self.kb_vy*=0.80

        # dash ghost
        if self.dashing:
            self.dash_ghost_t-=dt
            if self.dash_ghost_t<=0:
                self.dash_ghost_t=0.035;particles.trail(self.x,self.y-self.H//2,self.color,14)
                for _ in range(3):
                    particles.add(Particle(self.x+random.uniform(-12,12),
                                           self.y-random.uniform(0,self.H),
                                           -self.dash_dir*random.uniform(30,100),
                                           random.uniform(-40,40),
                                           random.uniform(0.12,0.28),self.color,random.randint(3,7),0))
            self.dash_timer-=dt;self.x+=self.dash_vx*dt
            if self.dash_timer<=0:
                self.dashing=False;self.dash_vx=0
                particles.burst(self.x,self.y-self.H//2,self.color,10,100,5,0.3,200)

        if not self.dashing:
            slow_m=(1.0/3.0) if world.in_slow_for(self.x,self.y,self.id) else 1.0
            # Mana burst skill CD reduction (75%)
            if world.mana_burst.get(self.id,0)>0:
                for sk in self.skills:
                    if sk.timer>0: sk.timer=max(0,sk.timer-dt*0.75)
            charge_lock=1.0 if not (self.giant_charging or self.charge_shot_charging) else 0.0
            self.vy+=GRAVITY*dt;self.y+=self.vy*dt;self.x+=self.vx*slow_m*charge_lock*dt

        # Charge Shot: accumulate charge time
        if self.charge_shot_charging:
            self.charge_shot_t = min(self._charge_shot_max, self.charge_shot_t + dt)
            # visual: emit small sparks
            if random.random() < 0.4:
                particles.add(Particle(
                    self.x + self.facing*18 + random.uniform(-8,8),
                    self.y - self.H//2 + random.uniform(-10,10),
                    self.facing*random.uniform(40,100), random.uniform(-60,60),
                    random.uniform(0.1,0.25), self.color, random.randint(3,6), 0))

        # platform collision
        self.on_ground=False
        if self.vy>=0:
            for plat in platforms:
                fty=self.y; fp=fty-self.vy*dt
                ix=plat.left-self.W//2+4<self.x<plat.right+self.W//2-4
                cr=fp<=plat.top+1 and fty>=plat.top-1
                if ix and cr:
                    self.y=float(plat.top);self.vy=0.0;self.on_ground=True
                    if not self.prev_on_ground: particles.land_dust(self.x,self.y,self.color)
                    break
        if self.y>=FLOOR_Y and not self.on_ground:
            self.y=float(FLOOR_Y);self.vy=0.0;self.on_ground=True
            if not self.prev_on_ground: particles.land_dust(self.x,self.y,self.color)
        self.prev_on_ground=self.on_ground

        if self.y>SCREEN_H+80: self.hp=0
        self.x=max(self.W//2,min(SCREEN_W-self.W//2,self.x))

        mp_regen=MP_REGEN*self.passive["mp_regen_mult"]
        if hasattr(self,'_banana_timer') and self._banana_timer>0:
            self._banana_timer-=dt; mp_regen=50.0
        # Mana burst bonus
        if world.mana_burst.get(self.id,0)>0:
            mp_regen*=1.75
        # Sanctum bonus (check if inside own sanctum)
        _in_sanctum=any(sc.owner==self.id and sc.contains(self.x,self.y-self.H//2)
                        for sc in world.sanctums)
        if _in_sanctum:
            mp_regen*=1.2  # +20% mp regen inside sanctum
        self.mp=min(self.max_mp,self.mp+mp_regen*dt)
        if hp_regen_on:
            self.hp=min(self.max_hp,self.hp+HP_REGEN*dt)
        # Bomb charge regen
        if self.bomb_charges < 5:
            self.bomb_charge_timer -= dt
            if self.bomb_charge_timer <= 0:
                self.bomb_charges = min(5, self.bomb_charges + 1)
                self.bomb_charge_timer = 3.0

        # Reflect charge regen
        if self.reflect_charges < 3:
            self.reflect_charge_timer -= dt
            if self.reflect_charge_timer <= 0:
                self.reflect_charges = min(3, self.reflect_charges + 1)
                self.reflect_charge_timer = 15.0

        # Confusion charge regen
        if self.confusion_charges < 3:
            self.confusion_charge_timer -= dt
            if self.confusion_charge_timer <= 0:
                self.confusion_charges = min(3, self.confusion_charges + 1)
                self.confusion_charge_timer = 15.0

        # Giant Shot charge timer
        if self.giant_charging:
            self.giant_charge_t=min(0.5, self.giant_charge_t+dt)
        if self.is_moving and self.on_ground: self.walk_phase+=8.0*dt
        else: self.walk_phase*=0.88
        if self.attack_anim>0: self.attack_anim-=dt
        if self.hurt_flash>0: self.hurt_flash-=dt
        self.body_bounce=math.sin(self.walk_phase)*3 if (self.is_moving and self.on_ground) else 0
        if self.hp<=0: self.alive=False

    def take_damage(self,dmg,kb_dir=0,particles=None,dnums=None,world=None):
        actual=dmg*self.passive.get("def_mult",1.0)
        self.hp-=actual;self.hurt_flash=0.2
        if kb_dir!=0: self.kb_vx=kb_dir*350;self.kb_vy=-230;self.kb_timer=0.28
        if particles:
            particles.sparks(self.x,self.y-self.H//2,self.color,kb_dir,10,260)
            particles.burst(self.x,self.y-self.H//2,(255,240,100),5,80,4,0.3,400)
        if dnums is not None:
            dnums.append(DmgNum(self.x+random.uniform(-18,18),self.y-self.H-8,actual,(255,80,80)))
        # Curse passive: counter-meteor
        if self.passive.get("curse") and world is not None:
            enemy=world.enemy_of(self.id)
            ex=enemy.x;ey=enemy.y
            world.projectiles.append(Projectile(ex+2*random.uniform(-10,10),-60,0,560,8,2,self.id))
            world.projectiles.append(Projectile(ex+2*random.uniform(-100,100),-60,0,540,8,2,self.id))
            world.projectiles.append(Projectile(ex+2*random.uniform(-200,200),-60,0,520,8,2,self.id))
            world.projectiles.append(Projectile(ex+2*random.uniform(-10,10),-60,0,480,8,2,self.id))
            world.projectiles.append(Projectile(ex+2*random.uniform(-100,100),-60,0,460,8,2,self.id))
            world.projectiles.append(Projectile(ex+2*random.uniform(-200,200),-60,0,440,8,2,self.id))

    def draw(self,surf):
        cx=int(self.x);by=int(self.y+self.body_bounce);ty=by-self.H
        hurt=self.hurt_flash>0
        bc=(255,150,150) if hurt else self.color
        dc=tuple(max(0,c-65) for c in self.color)
        hc=(255,210,210) if hurt else tuple(min(255,c+55) for c in self.color)
        sw=math.sin(self.walk_phase);cw=math.cos(self.walk_phase)
        ae=max(0,self.attack_anim/0.3);bt=ty+14;bb=by
        # shadow
        sh=pygame.Surface((52,14),pygame.SRCALPHA);pygame.draw.ellipse(sh,(0,0,0,55),(0,0,52,14))
        surf.blit(sh,(cx-26,int(self.y)-7))
        # legs
        hy=bb-4;fo=sw*18;ko=sw*10
        lh=(cx-8,hy);lk=(cx-8+int(ko),hy+16);lf=(cx-8+int(fo),hy+30)
        pygame.draw.line(surf,dc,lh,lk,5);pygame.draw.line(surf,dc,lk,lf,5);pygame.draw.circle(surf,dc,lk,4)
        rh=(cx+8,hy);rk=(cx+8-int(ko),hy+16);rf=(cx+8-int(fo),hy+30)
        pygame.draw.line(surf,dc,rh,rk,5);pygame.draw.line(surf,dc,rk,rf,5);pygame.draw.circle(surf,dc,rk,4)
        # body
        br=pygame.Rect(cx-13,bt,26,bb-bt);pygame.draw.rect(surf,bc,br,border_radius=6)
        hi=tuple(min(255,c+80) for c in bc);pygame.draw.rect(surf,hi,pygame.Rect(cx-10,bt+3,8,8),border_radius=3)
        pygame.draw.rect(surf,dc,br,2,border_radius=6)
        # arms
        sy2=bt+6;arm_s=cw*20;ar=self.facing*34*ae
        if ae>0.2:
            ags=pygame.Surface((50,50),pygame.SRCALPHA);pygame.draw.circle(ags,(*self.color,int(100*ae)),(25,25),25)
            surf.blit(ags,(cx-25+int(ar*0.5),sy2-10))
        ls=(cx-12,sy2)
        if ae>0.1: le=(cx-12-int(ar*0.5),sy2+10);lhand=(cx-12-int(ar),sy2+4)
        else: le=(cx-12-6,sy2+12+int(arm_s*0.5));lhand=(cx-12,sy2+22+int(arm_s))
        pygame.draw.line(surf,dc,ls,le,4);pygame.draw.line(surf,dc,le,lhand,4);pygame.draw.circle(surf,dc,le,3)
        rs=(cx+12,sy2)
        if ae>0.1: re=(cx+12+int(ar*0.5),sy2+10);rhand=(cx+12+int(ar),sy2+4)
        else: re=(cx+12+6,sy2+12-int(arm_s*0.5));rhand=(cx+12,sy2+22-int(arm_s))
        pygame.draw.line(surf,dc,rs,re,4);pygame.draw.line(surf,dc,re,rhand,4);pygame.draw.circle(surf,dc,re,3)
        # head
        hcy=ty+8;pygame.draw.circle(surf,hc,(cx,hcy),14);pygame.draw.circle(surf,dc,(cx,hcy),14,2)
        ex2=cx+self.facing*5;pygame.draw.circle(surf,COLORS["white"],(ex2,hcy-2),4)
        pygame.draw.circle(surf,COLORS["black"],(ex2+self.facing,hcy-2),2)
        if hurt: pygame.draw.circle(surf,(255,50,50),(ex2,hcy-2),5,2)
        # Giant Shot charge visual
        if self.giant_charging and self.giant_charge_t > 0:
            ratio = self.giant_charge_t / 0.5
            charge_r = int(8 + 34 * ratio)
            charge_a = int(80 + 120 * ratio)
            cs = pygame.Surface((charge_r*2+4, charge_r*2+4), pygame.SRCALPHA)
            pulse_r = charge_r + int(4*math.sin(self.giant_charge_t*30))
            pygame.draw.circle(cs, (*self.color, charge_a), (charge_r+2, charge_r+2), max(2,pulse_r))
            pygame.draw.circle(cs, (255,255,255, min(255,charge_a+60)), (charge_r+2, charge_r+2), max(1,pulse_r//3))
            surf.blit(cs, (cx+self.facing*10-charge_r-2, hcy-charge_r-2))
        # Charge Shot visual (grows from small spark to glowing orb)
        if self.charge_shot_charging and self.charge_shot_t > 0:
            ratio   = min(1.0, self.charge_shot_t / self._charge_shot_max)
            cr      = int(4 + 22 * ratio)
            ca      = int(60 + 140 * ratio)
            pulse_r = cr + int(3 * math.sin(self.charge_shot_t * 40))
            # white-hot core → player-color glow
            cs2 = pygame.Surface((pulse_r*2+8, pulse_r*2+8), pygame.SRCALPHA)
            pygame.draw.circle(cs2, (*self.color, ca),      (pulse_r+4,pulse_r+4), max(2,pulse_r))
            pygame.draw.circle(cs2, (255,255,200, min(255,ca+60)), (pulse_r+4,pulse_r+4), max(1,pulse_r//2))
            surf.blit(cs2, (cx + self.facing*20 - pulse_r - 4, hcy - pulse_r - 4))
        # badge
        badge=Fonts.r(11).render(self.passive["name"],True,COLORS["yellow"])
        surf.blit(badge,(cx-badge.get_width()//2,ty-24))


# ══════════════════════════════════════════════════════
#  SPECIAL PROJECTILES
# ══════════════════════════════════════════════════════
class BoomerangProjectile:
    """L-shaped rotating boomerang that returns to owner's current position.
    Go-phase: can hit enemy once. Return-phase: can hit enemy once more (separate hit).
    """
    def __init__(self, x, y, facing, speed, size, damage, owner):
        self.x = float(x); self.y = float(y)
        self.facing = facing
        self.speed = speed; self.size = size; self.damage = damage; self.owner = owner
        self.alive = True; self.age = 0.0
        self.vx = float(facing * speed); self.vy = 0.0
        self.max_dist = 520; self.start_x = float(x)
        self.returning = False
        self.hit_set_go = set()      # ids hit during outward travel (no repeat per target)
        self.hit_set_return = set()  # ids hit during return travel (no repeat per target)
        self.angle = 0.0
        self._owner_ref = None   # set externally by GameState
    def update(self, dt, particles):
        self.age += dt; self.angle += dt * 12 * self.facing
        if not self.returning:
            dist = abs(self.x - self.start_x)
            if dist >= self.max_dist:
                self.returning = True
                self.vx = -self.vx * 0.85
            # wall bounce → immediately start returning
            if self.x <= self.size and self.vx < 0:
                self.returning = True; self.vx = abs(self.vx)
            elif self.x >= SCREEN_W - self.size and self.vx > 0:
                self.returning = True; self.vx = -abs(self.vx)
        else:
            # return toward owner's CURRENT x AND y position
            if self._owner_ref is not None:
                owner_x = self._owner_ref.x
                owner_y = self._owner_ref.y - self._owner_ref.H // 2
            else:
                owner_x = self.start_x; owner_y = self.y
            dx = owner_x - self.x
            dy = owner_y - self.y
            dist2d = max(1.0, math.hypot(dx, dy))
            spd = min(self.speed * 1.3, math.hypot(self.vx, self.vy) + 400*dt)
            self.vx = dx / dist2d * spd
            self.vy = dy / dist2d * spd
            if dist2d < 30:
                self.alive = False
        self.x += self.vx * dt; self.y += self.vy * dt
        particles.trail(self.x, self.y,
                        COLORS["p1"] if self.owner==0 else COLORS["p2"], max(2, self.size-3))
        # out-of-bounds kill (only if not returning, returning boomerangs follow owner)
        if not self.returning and (self.y < -400 or self.y > SCREEN_H+200):
            self.alive = False
    def can_hit_go(self, target_id):    return not self.returning and target_id not in self.hit_set_go
    def can_hit_return(self, target_id): return self.returning and target_id not in self.hit_set_return
    def get_rect(self): return pygame.Rect(self.x-self.size, self.y-self.size, self.size*2, self.size*2)
    def draw(self, surf):
        col = COLORS["p1"] if self.owner==0 else COLORS["p2"]
        bright = tuple(min(255,c+100) for c in col)
        cx, cy = int(self.x), int(self.y)
        a = self.angle
        # L-shape: two arms
        arm1 = [(math.cos(a)*r - math.sin(a)*0, math.sin(a)*r + math.cos(a)*0) for r in [0,self.size*1.4]]
        arm2 = [(math.cos(a+math.pi/2)*r, math.sin(a+math.pi/2)*r) for r in [0,self.size]]
        def pt(v): return (cx+int(v[0]), cy+int(v[1]))
        pygame.draw.line(surf, bright, pt(arm1[0]), pt(arm1[1]), 4)
        pygame.draw.line(surf, col,    pt(arm2[0]), pt(arm2[1]), 4)
        # glow center
        gs = pygame.Surface((self.size*2+8, self.size*2+8), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*col, 80), (self.size+4, self.size+4), self.size+2)
        surf.blit(gs, (cx-self.size-4, cy-self.size-4))

class SpikeProjectile:
    """Travels forward, then explodes into spread of small projectiles.
    explode() sets exploded=True and alive=False.
    split_done prevents double-spawning split projectiles.
    """
    def __init__(self, x, y, facing, speed, size, damage, split_dmg, split_count, max_dist, owner):
        self.x=float(x); self.y=float(y); self.facing=facing
        self.vx=float(facing*speed); self.vy=0.0
        self.size=size; self.damage=damage; self.split_dmg=split_dmg
        self.split_count=split_count; self.max_dist=max_dist; self.owner=owner
        self.alive=True; self.age=0.0; self.start_x=float(x)
        self.exploded=False; self.hit=False; self.split_done=False; self.trail_t=0.0
    def update(self, dt, particles):
        self.age+=dt; self.x+=self.vx*dt; self.y+=self.vy*dt
        self.trail_t-=dt
        if self.trail_t<=0:
            self.trail_t=0.02
            col=COLORS["p1"] if self.owner==0 else COLORS["p2"]
            particles.trail(self.x, self.y, col, max(3,self.size-2))
        if abs(self.x-self.start_x)>=self.max_dist and not self.exploded:
            self.explode(particles)
        if self.x<-200 or self.x>SCREEN_W+200 or self.y<-400 or self.y>SCREEN_H+200:
            self.alive=False
    def explode(self, particles):
        self.exploded=True; self.alive=False
        col=COLORS["p1"] if self.owner==0 else COLORS["p2"]
        particles.burst(self.x, self.y, col, 14, 180, 5, 0.4, 200)
    def get_rect(self): return pygame.Rect(self.x-self.size, self.y-self.size, self.size*2, self.size*2)
    def draw(self, surf):
        col=COLORS["p1"] if self.owner==0 else COLORS["p2"]
        bright=tuple(min(255,c+110) for c in col)
        pulse=1.0+0.2*math.sin(self.age*18)
        r=int((self.size+6)*pulse)
        gs=pygame.Surface((r*2,r*2),pygame.SRCALPHA)
        pygame.draw.circle(gs,(*col,70),(r,r),r); surf.blit(gs,(int(self.x)-r,int(self.y)-r))
        pygame.draw.circle(surf, bright, (int(self.x),int(self.y)), max(2,self.size))
        pygame.draw.circle(surf, COLORS["white"], (int(self.x),int(self.y)), max(1,self.size//3))

class SpreadProjectile:
    """Fan of projectiles that disappear after max_dist."""
    def __init__(self, x, y, vx, vy, size, damage, max_dist, owner):
        self.x=float(x); self.y=float(y)
        self.vx=vx; self.vy=vy
        self.size=size; self.damage=damage; self.owner=owner
        self.alive=True; self.age=0.0
        self.start_x=float(x); self.start_y=float(y)
        self.max_dist=max_dist; self.trail_t=0.0
    def update(self, dt, particles):
        self.age+=dt; self.x+=self.vx*dt; self.y+=self.vy*dt
        self.trail_t-=dt
        if self.trail_t<=0:
            self.trail_t=0.03
            col=COLORS["p1"] if self.owner==0 else COLORS["p2"]
            particles.trail(self.x, self.y, col, max(1,self.size))
        dist=math.hypot(self.x-self.start_x, self.y-self.start_y)
        if dist>=self.max_dist: self.alive=False
        if self.x<-200 or self.x>SCREEN_W+200 or self.y<-400 or self.y>SCREEN_H+200: self.alive=False
    def get_rect(self): return pygame.Rect(self.x-self.size, self.y-self.size, self.size*2, self.size*2)
    def draw(self, surf):
        col=COLORS["p1"] if self.owner==0 else COLORS["p2"]
        bright=tuple(min(255,c+100) for c in col)
        dist=math.hypot(self.x-self.start_x,self.y-self.start_y)
        alpha=int(255*(1.0-dist/self.max_dist))
        r=max(1,self.size)
        s=pygame.Surface((r*2+4,r*2+4),pygame.SRCALPHA)
        pygame.draw.circle(s,(*bright,alpha),(r+2,r+2),r); surf.blit(s,(int(self.x)-r-2,int(self.y)-r-2))

# ══════════════════════════════════════════════════════
#  WORLD  (shared game objects, passed to Player)
# ══════════════════════════════════════════════════════
class World:
    def __init__(self,p1,p2):
        self.p1=p1;self.p2=p2
        self.projectiles:list[Projectile]=[]
        self.boomerangs:list[BoomerangProjectile]=[]
        self.spike_projs:list[SpikeProjectile]=[]
        self.spread_projs:list[SpreadProjectile]=[]
        self.thorns:list[ThornEffect]=[]
        self.bombs:list[Bomb]=[]
        self.shields:list[ReflectShield]=[]
        self.slow_fields:list[SlowField]=[]
        self.clones:list[Clone]=[]
        self.items:list[Item]=[]
        self.meteor_warnings:list[MeteorWarning]=[]
        self.planet_warnings:list[PlanetWarning]=[]
        self.mega_planet_warnings:list[MegaPlanetWarning]=[]
        self.sanctums:list[SanctumField]=[]
        self.mana_burst:dict={0:0.0,1:0.0}   # pid -> remaining time
        self.superjump_projs:list[Projectile]=[]
        self.homing_projs:list=[]  # HomingProjectile
        self.spread_bullets:list=[]  # SpreadBulletProjectile
        self.melee_attacks:list=[]  # MeleeAttack
    def enemy_of(self,pid): return self.p2 if pid==0 else self.p1
    def in_slow_for(self, x, y, owner_id):
        """Returns True if position is inside a slow field owned by the OPPONENT."""
        for sf in self.slow_fields:
            if sf.owner == owner_id: continue   # caster is immune
            if sf.contains(x, y): return True
        return False
    def in_slow(self, x, y):
        """Legacy: any slow field (used for neutral checks)."""
        for sf in self.slow_fields:
            if sf.contains(x, y): return True
        return False

# ══════════════════════════════════════════════════════
#  MAP
# ══════════════════════════════════════════════════════
class Map:
    @staticmethod
    def _gen_platforms():
        """Generate 6-8 platforms at random non-overlapping positions."""
        count = random.randint(6, 8)
        plats = []
        # Y tiers: low(420-470), mid(330-380), high(240-290)
        y_tiers = [random.randint(450,490), random.randint(330,380), random.randint(240,290),
                   random.randint(450,490), random.randint(330,380), random.randint(240,290),
                   random.randint(240,490), random.randint(220,330)]
        random.shuffle(y_tiers)
        attempts = 0
        while len(plats) < count and attempts < 60:
            attempts += 1
            w = random.randint(50, 220)
            x = random.randint(80, SCREEN_W - 80 - w)
            y = y_tiers[len(plats) % len(y_tiers)] + random.randint(-20,20)
            r = pygame.Rect(x, y, w, 16)
            # ensure no overlap with existing platforms (x-axis)
            overlap = any(abs(r.centerx - p.centerx) < (r.width//2 + p.width//2 + 60)
                          and abs(r.y - p.y) < 60 for p in plats)
            # keep away from spawn zones
            near_spawn = (x < 180 and y > 400) or (x + w > SCREEN_W-180 and y > 400)
            if not overlap and not near_spawn:
                plats.append(r)
        # guarantee at least 3
        if len(plats) < 3:
            plats = [pygame.Rect(290,450,170,16), pygame.Rect(820,450,170,16), pygame.Rect(545,355,190,16)]
        return plats

    def __init__(self):
        self.platforms = self._gen_platforms()
        self.bg_stars=[(random.randint(0,SCREEN_W),random.randint(0,SCREEN_H),random.random(),random.uniform(0.5,3.0)) for _ in range(130)]
        self.nebulas=[(random.randint(120,SCREEN_W-120),random.randint(40,350),random.randint(70,170),
                       random.choice([COLORS["p1"],COLORS["p2"],COLORS["purple"],COLORS["cyan"]]),
                       random.uniform(0,math.tau)) for _ in range(7)]
        self.t=0.0;self.pp=0.0
    def update(self,dt): self.t+=dt;self.pp+=dt*1.8
    def draw(self,surf):
        surf.fill(COLORS["bg"])
        for nx,ny,nr,nc,nph in self.nebulas:
            pulse=0.6+0.4*math.sin(self.t*0.35+nph);r=int(nr*pulse)
            ns=pygame.Surface((r*2,r*2),pygame.SRCALPHA)
            for ri in range(r,0,max(1,r//7)): pygame.draw.circle(ns,(*nc,int(16*(1-ri/r))),(r,r),ri)
            surf.blit(ns,(nx-r,ny-r))
        for sx,sy,b,ts in self.bg_stars:
            a=max(20,min(255,int(70+b*100+55*math.sin(self.t*ts+b*10))))
            pygame.draw.circle(surf,(a,a,min(255,a+25)),(sx,sy),1 if b<0.5 else 2)
        for i in range(10): cv=max(0,52-i*5);pygame.draw.rect(surf,(cv,cv,cv+28),(0,FLOOR_Y+i*5,SCREEN_W,5))
        pygame.draw.rect(surf,COLORS["floor"],(0,FLOOR_Y,SCREEN_W,SCREEN_H-FLOOR_Y))
        ga=int(110+70*math.sin(self.t*1.4));fgs=pygame.Surface((SCREEN_W,5),pygame.SRCALPHA)
        pygame.draw.rect(fgs,(*COLORS["cyan"],ga),(0,0,SCREEN_W,3));surf.blit(fgs,(0,FLOOR_Y-1))
        for gx in range(0,SCREEN_W,80):
            la=int(18+10*math.sin(self.t+gx*0.05));ls=pygame.Surface((2,SCREEN_H-FLOOR_Y),pygame.SRCALPHA)
            ls.fill((90,110,170,la));surf.blit(ls,(gx,FLOOR_Y))
        for i,plat in enumerate(self.platforms):
            pga=int(150+70*math.sin(self.pp+i*1.3))
            ps=pygame.Surface((plat.width,plat.height),pygame.SRCALPHA)
            pygame.draw.rect(ps,(*COLORS["floor"],230),(0,0,plat.width,plat.height),border_radius=5)
            pygame.draw.rect(ps,(110,130,190,90),(2,2,plat.width-4,4),border_radius=3);surf.blit(ps,plat.topleft)
            tgs=pygame.Surface((plat.width,4),pygame.SRCALPHA)
            pygame.draw.rect(tgs,(*COLORS["cyan"],pga),(0,0,plat.width,3),border_radius=2);surf.blit(tgs,(plat.x,plat.y-1))
            uw=int(plat.width*0.7);ug=pygame.Surface((uw*2,22),pygame.SRCALPHA)
            pygame.draw.ellipse(ug,(*COLORS["cyan"],int(pga*0.28)),(0,0,uw*2,22));surf.blit(ug,(plat.x+plat.width//2-uw,plat.bottom))

# ══════════════════════════════════════════════════════
#  UI
# ══════════════════════════════════════════════════════
class UI:
    def __init__(self): self.t=0.0
    def update(self,dt): self.t+=dt

    def draw_bar(self,surf,x,y,w,h,ratio,fg,bg,label=""):
        pygame.draw.rect(surf,bg,(x,y,w,h),border_radius=5)
        if ratio>0:
            fw=int(w*ratio);pygame.draw.rect(surf,fg,(x,y,fw,h),border_radius=5)
            hs=pygame.Surface((fw,h//2),pygame.SRCALPHA);hs.fill((255,255,255,45));surf.blit(hs,(x,y))
        pygame.draw.rect(surf,COLORS["white"],(x,y,w,h),1,border_radius=5)
        if label:
            txt=Fonts.r(11).render(label,True,COLORS["white"])
            surf.blit(txt,(x+w//2-txt.get_width()//2,y+h//2-txt.get_height()//2+1))

    def draw_player_ui(self,surf,player,base_x):
        bar_w=280
        panel=pygame.Surface((bar_w+10,170),pygame.SRCALPHA);panel.fill((0,0,0,115));surf.blit(panel,(base_x-5,5))
        hp_r=max(0.0,player.hp/player.max_hp)
        hp_c=COLORS["hp_fg"] if hp_r>0.5 else (COLORS["orange"] if hp_r>0.25 else (255,40,40))
        self.draw_bar(surf,base_x,12,bar_w,22,hp_r,hp_c,COLORS["hp_bg"],f"HP {int(player.hp)}/{player.max_hp}")
        mp_r=max(0.0,player.mp/player.max_mp)
        self.draw_bar(surf,base_x,38,bar_w,16,mp_r,COLORS["mp_fg"],COLORS["mp_bg"],f"MP {int(player.mp)}/{int(player.max_mp)}")
        bt=Fonts.r(11).render(f"[{player.passive['name']}]",True,COLORS["yellow"])
        surf.blit(bt,(base_x+bar_w-bt.get_width(),58))
        for i,sk in enumerate(player.skills):
            self._draw_slot(surf,base_x+i*72,78,66,sk,i+1,player)

    def _draw_slot(self,surf,x,y,size,sk,num,player=None):
        ratio=max(0.0,min(1.0,sk.cd_ratio()))
        bg=pygame.Surface((size,size),pygame.SRCALPHA);bg.fill((20,20,40,215));surf.blit(bg,(x,y))
        if ratio<1.0:
            fh=int(size*ratio)
            if fh>0:
                fs=pygame.Surface((size,fh),pygame.SRCALPHA);fs.fill((55,80,160,150))
                surf.blit(fs,(x,y+size-fh))
        if sk.just_used>0:
            fa=int(200*sk.just_used/0.3);fls=pygame.Surface((size,size),pygame.SRCALPHA)
            fls.fill((255,255,200,fa));surf.blit(fls,(x,y))
        # tier colour
        tier_col={"atk":COLORS["cyan"],"uty":COLORS["green"],"high":COLORS["orange"],"ult":COLORS["purple"]}.get(sk.tier,COLORS["gray"])
        border=tier_col if ratio>=1.0 else COLORS["gray"]
        pygame.draw.rect(surf,border,(x,y,size,size),2,border_radius=5)
        # name
        nm=sk.name.replace("[ULT] ","")[:8]
        txt=Fonts.r(10).render(nm,True,COLORS["white"])
        if txt.get_width()>size-4: txt=pygame.transform.scale(txt,(size-4,txt.get_height()))
        surf.blit(txt,(x+size//2-txt.get_width()//2,y+5))
        # tier badge
        if sk.tier=="ult":
            ub=Fonts.r(9).render("ULT",True,COLORS["purple"]);surf.blit(ub,(x+2,y+size-26))
        # mp cost
        mt=Fonts.r(9).render(f"MP:{sk.mp_cost}",True,COLORS["cyan"]);surf.blit(mt,(x+2,y+size-16))
        # cd
        if sk.timer>0:
            ct=Fonts.r(10).render(f"{sk.timer:.1f}",True,COLORS["yellow"]);surf.blit(ct,(x+size//2-ct.get_width()//2,y+size-28))
        # key
        kt=Fonts.r(13).render(str(num),True,COLORS["yellow"]);surf.blit(kt,(x+size-15,y+2))
        # bomb charge indicator
        if sk.stype=="bomb" and player is not None and hasattr(player,"bomb_charges"):
            chg=player.bomb_charges
            for ci in range(5):
                cx2=x+4+ci*7; cy2=y+size-8
                col=(255,160,40) if ci<chg else (60,60,60)
                pygame.draw.circle(surf,col,(cx2,cy2),3)
        # reflect charge indicator
        if sk.stype=="reflect" and player is not None and hasattr(player,"reflect_charges"):
            chg=player.reflect_charges
            for ci in range(3):
                cx2=x+4+ci*7; cy2=y+size-8
                col=(255,160,40) if ci<chg else (60,60,60)
                pygame.draw.circle(surf,col,(cx2,cy2),3)
        # confusion charge indicator
        if sk.stype=="confusion" and player is not None and hasattr(player,"confusion_charges"):
            chg=player.confusion_charges
            for ci in range(3):
                cx2=x+4+ci*7; cy2=y+size-8
                col=(255,160,40) if ci<chg else (60,60,60)
                pygame.draw.circle(surf,col,(cx2,cy2),3)
        # charge_shot: "HOLD" label + live charge bar while player is charging
        if sk.stype=="charge_shot" and player is not None:
            ht=Fonts.r(9).render("HOLD",True,(255,200,80))
            surf.blit(ht,(x+2,y+size-26))
            is_charging = (getattr(player,"charge_shot_charging",False) and
                           getattr(player,"charge_shot_slot",-1) == player.skills.index(sk)
                           if sk in player.skills else False)
            if is_charging:
                cr  = min(1.0, player.charge_shot_t / player._charge_shot_max)
                bw2 = size-4
                pygame.draw.rect(surf,(40,40,40),(x+2,y+size-6,bw2,4),border_radius=2)
                if cr>0:
                    fc=(int(80+175*cr),int(200-120*cr),40)
                    pygame.draw.rect(surf,fc,(x+2,y+size-6,int(bw2*cr),4),border_radius=2)

    def draw_timer(self,surf,seconds,phase):
        s=int(seconds);urgent=s<=30
        pulse=1.0+(0.15*math.sin(self.t*8) if urgent else 0)
        col=(255,int(70+50*math.sin(self.t*8)),30) if urgent else COLORS["yellow"]
        txt=Fonts.r(30).render(f"{s//60:02d}:{s%60:02d}",True,col)
        w,h=int(txt.get_width()*pulse),int(txt.get_height()*pulse)
        surf.blit(pygame.transform.scale(txt,(w,h)),(SCREEN_W//2-w//2,10))
        # phase indicator
        if phase==1:
            ph=Fonts.r(14).render("!! DMG +10% !!",True,(255,180,60))
            surf.blit(ph,(SCREEN_W//2-ph.get_width()//2,46))
        elif phase==2:
            ph=Fonts.r(14).render("!! DMG +10%  |  NO REGEN !!",True,(255,80,80))
            surf.blit(ph,(SCREEN_W//2-ph.get_width()//2,46))

# ══════════════════════════════════════════════════════
#  STATE MACHINE
# ══════════════════════════════════════════════════════
class State(ABC):
    def __init__(self,mgr): self.manager=mgr
    @abstractmethod
    def handle_event(self,e): pass
    @abstractmethod
    def update(self,dt): pass
    @abstractmethod
    def draw(self,surf): pass

class StateManager:
    def __init__(self): self.current=None
    def change(self,s): self.current=s
    def handle_event(self,e):
        if self.current: self.current.handle_event(e)
    def update(self,dt):
        if self.current: self.current.update(dt)
    def draw(self,surf):
        if self.current: self.current.draw(surf)

# ══════════════════════════════════════════════════════
#  MAIN MENU
# ══════════════════════════════════════════════════════
class MainMenuState(State):
    def __init__(self,mgr):
        super().__init__(mgr);self.t=0.0
        self.particles=ParticleSystem();self.sp_t=0.0
    def handle_event(self,e):
        if e.type==pygame.KEYDOWN and e.key==pygame.K_RETURN:
            self.manager.change(CharacterSelectState(self.manager))
    def update(self,dt):
        self.t+=dt;self.particles.update(dt);self.sp_t-=dt
        if self.sp_t<=0:
            self.sp_t=0.04;a=random.uniform(0,math.tau);sp=random.uniform(50,180)
            col=random.choice([COLORS["p1"],COLORS["p2"],COLORS["cyan"],COLORS["yellow"]])
            self.particles.add(Particle(SCREEN_W//2+random.uniform(-320,320),SCREEN_H//2+random.uniform(-120,120),
                                        math.cos(a)*sp,math.sin(a)*sp-30,random.uniform(0.8,2.2),col,random.randint(2,6),-15))
    def draw(self,surf):
        surf.fill(COLORS["bg"]);self.particles.draw(surf)
        for i in range(4):
            r=200+i*55;a=int(18+14*math.sin(self.t*0.7+i));s=pygame.Surface((r*2,r*2),pygame.SRCALPHA)
            c=COLORS["p1"] if i%2==0 else COLORS["p2"];pygame.draw.circle(s,(*c,a),(r,r),r);surf.blit(s,(SCREEN_W//2-r,110-r))
        title=Fonts.r(64).render("TANG BI KEVIN",True,COLORS["white"])
        shad=Fonts.r(64).render("TANG BI KEVIN",True,(0,0,0))
        surf.blit(shad,(SCREEN_W//2-title.get_width()//2+3,133));surf.blit(title,(SCREEN_W//2-title.get_width()//2,130))
        sub=Fonts.r(22).render("2 Player Fighting Game",True,COLORS["gray"])
        surf.blit(sub,(SCREEN_W//2-sub.get_width()//2,210))
        c3=tuple(int(80+175*(0.5+0.5*math.sin(self.t*3+ci))) for ci in range(3))
        start=Fonts.r(22).render("Press ENTER to Start",True,c3)
        surf.blit(start,(SCREEN_W//2-start.get_width()//2,272))
        for i,(nm,keys,col) in enumerate([
            ("Player 1","A/D Move  W Jump  1/2/3/4 Skill",COLORS["p1"]),
            ("Player 2","L/R Move  Up Jump  M/,/./Slash Skill",COLORS["p2"]),
        ]):
            bx,by=80+i*610,360
            ps=pygame.Surface((490,90),pygame.SRCALPHA);ps.fill((*COLORS["darkgray"],210))
            pygame.draw.rect(ps,col,(0,0,490,90),2,border_radius=8);surf.blit(ps,(bx-10,by-10))
            surf.blit(Fonts.r(18).render(nm,True,col),(bx,by))
            surf.blit(Fonts.r(14).render(keys,True,COLORS["white"]),(bx,by+32))
        # skill tier legend
        leg_y=480
        legend=[("atk",COLORS["cyan"],"Normal Atk"),("uty",COLORS["green"],"Utiliy"),
                ("high",COLORS["orange"],"High Atk"),("ult",COLORS["purple"],"[ULT]")]
        for i,(tier,col,lbl) in enumerate(legend):
            bx=SCREEN_W//2-220+i*115
            pygame.draw.rect(surf,col,(bx,leg_y,14,14),2,border_radius=3)
            surf.blit(Fonts.r(13).render(lbl,True,col),(bx+18,leg_y))


# ══════════════════════════════════════════════════════
#  CHARACTER SELECT STATE
# ══════════════════════════════════════════════════════
class CharacterSelectState(State):
    """
    50-character select, 5 pages × 10 per page.
    P1 picks first, then P2.
    P key toggles hidden-pick (no colour border visible to opponent).
    Duplicate characters allowed.
    Left/Right arrows navigate pages.
    """
    PER_PAGE = 10

    def __init__(self, mgr):
        super().__init__(mgr)
        self.p1_char   = None
        self.p2_char   = None
        self.t         = 0.0
        self.page      = 0          # 0-based page index
        self.hidden    = False      # P key: hide current picker's choice
        self.particles = ParticleSystem()
        self._sp_t     = 0.0
        # How many pages we actually need (ceil)
        self._total_pages = max(1, (len(CHARACTERS) + self.PER_PAGE - 1) // self.PER_PAGE)

    @property
    def picking_p1(self): return self.p1_char is None
    @property
    def picking_p2(self): return self.p1_char is not None and self.p2_char is None

    def _page_chars(self):
        """Return (global_idx, name, skill_ids, pass_idx) for the current page."""
        start = self.page * self.PER_PAGE
        end   = min(start + self.PER_PAGE, len(CHARACTERS))
        return [(i, *CHARACTERS[i]) for i in range(start, end)]

    def handle_event(self, e):
        if e.type != pygame.KEYDOWN: return
        key = e.key

        # Page navigation (left / right arrows)
        if key == pygame.K_LEFT:
            self.page = (self.page - 1) % self._total_pages
            return
        if key == pygame.K_RIGHT:
            self.page = (self.page + 1) % self._total_pages
            return

        # Hidden-pick toggle (P key)
        if key == pygame.K_p:
            self.hidden = not self.hidden
            return

        # ESC → main menu
        if key == pygame.K_ESCAPE:
            self.manager.change(MainMenuState(self.manager))
            return

        # Backspace: P2 → let P1 re-pick  /  P1 → undo pick (clear p1)
        if key == pygame.K_BACKSPACE:
            if self.picking_p2:
                self.p1_char = None
            return

        # Number keys 0-9: pick slot on current page
        num_map = {
            pygame.K_0:0, pygame.K_1:1, pygame.K_2:2, pygame.K_3:3, pygame.K_4:4,
            pygame.K_5:5, pygame.K_6:6, pygame.K_7:7, pygame.K_8:8, pygame.K_9:9,
        }
        if key in num_map:
            slot = num_map[key]
            global_idx = self.page * self.PER_PAGE + slot
            if global_idx >= len(CHARACTERS):
                return  # slot is empty
            if self.picking_p1:
                self.p1_char = global_idx
            elif self.picking_p2:
                # duplicates allowed
                self.p2_char = global_idx
                self._launch()

    def _launch(self):
        gs = GameState(self.manager, p1_char=self.p1_char, p2_char=self.p2_char)
        self.manager.change(PreviewState(self.manager, gs))

    def update(self, dt):
        self.t += dt
        self.particles.update(dt)
        self._sp_t -= dt
        if self._sp_t <= 0:
            self._sp_t = 0.05
            col = random.choice([COLORS["p1"], COLORS["p2"], COLORS["yellow"], COLORS["cyan"]])
            self.particles.add(Particle(
                random.uniform(0, SCREEN_W), random.uniform(0, SCREEN_H),
                random.uniform(-60,60), random.uniform(-60,60),
                random.uniform(0.6,1.8), col, random.randint(1,4), 0))

    def draw(self, surf):
        surf.fill(COLORS["bg"])
        self.particles.draw(surf)

        picker_col  = COLORS["p1"] if self.picking_p1 else COLORS["p2"]
        picker_name = "PLAYER 1"   if self.picking_p1 else "PLAYER 2"

        # ── Title ──────────────────────────────────────────────────────
        title = Fonts.r(34).render("CHARACTER SELECT", True, COLORS["white"])
        surf.blit(title, (SCREEN_W//2 - title.get_width()//2, 12))

        # ── Picker label ───────────────────────────────────────────────
        hint_str = f"{picker_name}  —  0~9: pick  |  ◄►: page  |  P: hide  |  BSP: back  |  ESC: menu"
        ht = Fonts.r(16).render(hint_str, True, picker_col)
        surf.blit(ht, (SCREEN_W//2 - ht.get_width()//2, 52))

        # ── Hidden / locked status line ────────────────────────────────
        status_parts = []
        if self.picking_p2:
            # Show P1 selection (unless hidden was active WHEN P1 picked — we can't
            # retroactively hide it; we just hide during picking phase)
            p1_name = CHARACTERS[self.p1_char][0]
            #status_parts.append(f"P1 locked: {p1_name}")
        if self.hidden:
            status_parts.append("[HIDDEN MODE ON]")
        if status_parts:
            sl = Fonts.r(14).render("  |  ".join(status_parts), True, COLORS["yellow"])
            surf.blit(sl, (SCREEN_W//2 - sl.get_width()//2, 76))

        # ── Page indicator ─────────────────────────────────────────────
        page_txt = Fonts.r(14).render(
            f"Page {self.page+1} / {self._total_pages}   "
            f"(chars {self.page*self.PER_PAGE+1}~"
            f"{min((self.page+1)*self.PER_PAGE, len(CHARACTERS))})",
            True, COLORS["gray"])
        surf.blit(page_txt, (SCREEN_W//2 - page_txt.get_width()//2, 96))

        # ── Cards ──────────────────────────────────────────────────────
        CARD_W, CARD_H = 220, 258
        COLS = 5
        GAP  = 14
        total_w = COLS*CARD_W + (COLS-1)*GAP
        start_x = SCREEN_W//2 - total_w//2
        start_y = 116

        page_chars = self._page_chars()

        for slot, (global_i, cname, skill_ids, pass_idx) in enumerate(page_chars):
            col_i = slot % COLS
            row_i = slot // COLS
            cx = start_x + col_i*(CARD_W+GAP)
            cy = start_y + row_i*(CARD_H+GAP)

            # ── Border logic ──────────────────────────────────────────
            is_p1 = (global_i == self.p1_char)
            is_p2 = (global_i == self.p2_char)

            # Hidden mode: if current picker has hidden on, don't show
            # their pending selection highlight.  Locked (already picked)
            # choices are always shown.
            show_p1_border = is_p1 and not (self.picking_p2 and self.hidden)
            show_p2_border = is_p2  # P2 has already picked when this is drawn

            if show_p1_border and show_p2_border:
                border, bw = COLORS["yellow"], 4   # same char → gold border
            elif show_p1_border:
                border, bw = COLORS["p1"], 4
            elif show_p2_border:
                border, bw = COLORS["p2"], 4
            else:
                border, bw = COLORS["gray"], 2

            # ── Card background ───────────────────────────────────────
            card_s = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
            card_s.fill((20,20,45,210))
            pygame.draw.rect(card_s, border, (0,0,CARD_W,CARD_H), bw, border_radius=8)
            surf.blit(card_s, (cx, cy))

            # ── Slot key badge ─────────────────────────────────────────
            num_badge = Fonts.r(22).render(str(slot), True, COLORS["yellow"])
            surf.blit(num_badge, (cx+8, cy+5))

            # ── Global index (small) ───────────────────────────────────
            gi_t = Fonts.r(10).render(f"#{global_i}", True, COLORS["gray"])
            surf.blit(gi_t, (cx+CARD_W-gi_t.get_width()-6, cy+8))

            # ── Character name ─────────────────────────────────────────
            cn_txt = Fonts.r(15).render(cname, True, COLORS["white"])
            surf.blit(cn_txt, (cx+CARD_W//2-cn_txt.get_width()//2, cy+30))

            # ── Passive ────────────────────────────────────────────────
            passive = PASSIVE_DATA[pass_idx]
            pt = Fonts.r(10).render(f"[{passive['name']}]", True, COLORS["yellow"])
            surf.blit(pt, (cx+CARD_W//2-pt.get_width()//2, cy+50))

            # ── 4 skill mini-slots ────────────────────────────────────
            slot_sz  = 42; slot_gap = 6
            slot_tot = 4*slot_sz + 3*slot_gap
            sx0 = cx + (CARD_W-slot_tot)//2
            sy0 = cy + 68
            for si, sid in enumerate(skill_ids):
                if sid not in SKILL_MAP: continue
                sk_data = SKILL_MAP[sid]
                sk_tier = sk_data[2]; sk_type = sk_data[5]
                sx = sx0 + si*(slot_sz+slot_gap); sy = sy0
                tier_col = {"low":COLORS["cyan"],"mid":COLORS["green"],
                            "atk":COLORS["cyan"],
                            "high":COLORS["orange"],"ult":COLORS["purple"],
                            "uty":COLORS["green"]}.get(sk_tier, COLORS["gray"])
                ss = pygame.Surface((slot_sz,slot_sz), pygame.SRCALPHA)
                ss.fill((15,15,35,220))
                pygame.draw.rect(ss, tier_col, (0,0,slot_sz,slot_sz), 2, border_radius=5)
                surf.blit(ss,(sx,sy))
                icon_s = pygame.Surface((slot_sz,slot_sz), pygame.SRCALPHA)
                draw_skill_icon(icon_s, 0, 0, slot_sz, sk_type, tier_col)
                surf.blit(icon_s, (sx,sy))
                sn_t = Fonts.r(9).render(str(si+1), True, COLORS["yellow"])
                surf.blit(sn_t, (sx+slot_sz-11, sy+2))

            # ── Skill names stacked ────────────────────────────────────
            name_y = sy0 + slot_sz + 5
            for si, sid in enumerate(skill_ids):
                if sid not in SKILL_MAP: continue
                sk_name = SKILL_MAP[sid][1].replace("[ULT] ","★")
                nt = Fonts.r(9).render(sk_name[:15], True, COLORS["white"])
                surf.blit(nt, (cx+5, name_y + si*13))

            # ── P1/P2 lock overlay ────────────────────────────────────
            # P1 overlay: only show if not hidden
            if is_p1 and not (self.picking_p2 and self.hidden):
                ov = pygame.Surface((CARD_W,CARD_H), pygame.SRCALPHA)
                ov.fill((*COLORS["p1"], 28))
                surf.blit(ov,(cx,cy))
                lk = Fonts.r(13).render("P1", True, COLORS["p1"])
                surf.blit(lk,(cx+CARD_W-28,cy+5))
            if is_p2:
                ov = pygame.Surface((CARD_W,CARD_H), pygame.SRCALPHA)
                ov.fill((*COLORS["p2"], 28))
                surf.blit(ov,(cx,cy))
                lk = Fonts.r(13).render("P2", True, COLORS["p2"])
                surf.blit(lk,(cx+CARD_W-28,cy+5))

        # ── Arrow page indicators ──────────────────────────────────────
        arr_y = start_y + CARD_H//2 + (CARD_H+GAP)//2
        if self.page > 0:
            la = Fonts.r(28).render("◄", True, COLORS["cyan"])
            surf.blit(la, (14, arr_y - la.get_height()//2))
        if self.page < self._total_pages - 1:
            ra = Fonts.r(28).render("►", True, COLORS["cyan"])
            surf.blit(ra, (SCREEN_W - 14 - ra.get_width(), arr_y - ra.get_height()//2))

        # ── Hidden mode indicator ──────────────────────────────────────
        if self.hidden:
            hd = Fonts.r(13).render("HIDDEN  [P to toggle]", True, (180, 80, 255))
            surf.blit(hd, (SCREEN_W - hd.get_width() - 10, SCREEN_H - 20))

# ══════════════════════════════════════════════════════
#  GAME STATE
# ══════════════════════════════════════════════════════
class GameState(State):
    def __init__(self,mgr,p1_char=None,p2_char=None):
        super().__init__(mgr)
        # Use character roster if provided, else random fallback
        if p1_char is not None:
            sk1=get_character_skills(p1_char); p1_pass=get_character_passive(p1_char)
        else:
            sk1=pick_skills(); p1_pass=random.choice(PASSIVE_DATA)
        if p2_char is not None:
            sk2=get_character_skills(p2_char); p2_pass=get_character_passive(p2_char)
        else:
            sk2=pick_skills(); p2_pass=random.choice(PASSIVE_DATA)
        self.player1=Player(0,250,FLOOR_Y,COLORS["p1"],sk1,p1_pass)
        self.player2=Player(1,1030,FLOOR_Y,COLORS["p2"],sk2,p2_pass)
        self.world=World(self.player1,self.player2)
        self.game_map=Map();self.ui=UI()
        self.particles=ParticleSystem();self.screen_fx=ScreenFX()
        self.dnums:list[DmgNum]=[]
        self.time_left=float(GAME_TIME);self.keys=set()
        self.gsurf=pygame.Surface((SCREEN_W,SCREEN_H))
        self.flash_enabled=True   # P key toggles screen flash
        self._item_timer=random.uniform(15,25)  # first item after ~15-25s
        self._item_spawned=False

    def _game_phase(self):
        if self.time_left<=LATE_NOHEAL_TIME: return 2
        if self.time_left<=LATE_DMG_BONUS_TIME: return 1
        return 0

    def handle_event(self,e):
        if e.type==pygame.KEYDOWN:
            self.keys.add(e.key)
            if e.key==pygame.K_p:
                self.flash_enabled = not getattr(self,'flash_enabled',True)
            lb=self._game_phase()>=1  # late dmg bonus
            # P1 skills: 1 2 3 4
            if   e.key==pygame.K_x: self.player1.use_skill(0,self.world,self.particles,lb)
            elif e.key==pygame.K_c: self.player1.use_skill(1,self.world,self.particles,lb)
            elif e.key==pygame.K_v: self.player1.use_skill(2,self.world,self.particles,lb)
            elif e.key==pygame.K_b: self.player1.use_skill(3,self.world,self.particles,lb)
            # P2 skills: m , . /
            elif e.key==pygame.K_m:      self.player2.use_skill(0,self.world,self.particles,lb)
            elif e.key==pygame.K_COMMA:  self.player2.use_skill(1,self.world,self.particles,lb)
            elif e.key==pygame.K_PERIOD: self.player2.use_skill(2,self.world,self.particles,lb)
            elif e.key==pygame.K_SLASH:  self.player2.use_skill(3,self.world,self.particles,lb)
            elif e.key==pygame.K_w:  self.player1.jump()
            elif e.key==pygame.K_UP: self.player2.jump()
        if e.type==pygame.KEYUP:
            self.keys.discard(e.key)
            # Charge Shot release: fire when key released
            lb = (self._game_phase() >= 1)
            if e.key == pygame.K_x:
                self.player1.release_charge_shot(self.world, self.particles, lb)
            elif e.key == pygame.K_c:
                self.player1.release_charge_shot(self.world, self.particles, lb)
            elif e.key == pygame.K_v:
                self.player1.release_charge_shot(self.world, self.particles, lb)
            elif e.key == pygame.K_b:
                self.player1.release_charge_shot(self.world, self.particles, lb)
            elif e.key == pygame.K_m:
                self.player2.release_charge_shot(self.world, self.particles, lb)
            elif e.key == pygame.K_COMMA:
                self.player2.release_charge_shot(self.world, self.particles, lb)
            elif e.key == pygame.K_PERIOD:
                self.player2.release_charge_shot(self.world, self.particles, lb)
            elif e.key == pygame.K_SLASH:
                self.player2.release_charge_shot(self.world, self.particles, lb)

    def _move(self):
        dx1=int(pygame.K_d in self.keys)-int(pygame.K_a in self.keys)
        self.player1.move(dx1,1/FPS)
        dx2=int(pygame.K_RIGHT in self.keys)-int(pygame.K_LEFT in self.keys)
        self.player2.move(dx2,1/FPS)

    def update(self,dt):
        if not self.player1.alive or not self.player2.alive:
            w=1 if not self.player2.alive else 2
            if not self.player1.alive and not self.player2.alive: w=0
            self.manager.change(GameOverState(self.manager,w,self.player1,self.player2)); return
        self.time_left-=dt
        if self.time_left<=0:
            w=1 if self.player1.hp>self.player2.hp else (2 if self.player2.hp>self.player1.hp else 0)
            self.manager.change(GameOverState(self.manager,w,self.player1,self.player2)); return

        phase=self._game_phase()
        hp_regen_on=(phase<2)
        lb=(phase>=1)

        self._move()
        plats=self.game_map.platforms
        self.player1.update(dt,self.world,self.particles,plats,hp_regen_on,lb)
        self.player2.update(dt,self.world,self.particles,plats,hp_regen_on,lb)

        for p in self.world.projectiles: p.update(dt,self.particles)
        for t in self.world.thorns: t.update(dt)
        for b in self.world.bombs: b.update(dt,plats)
        for s in self.world.shields: s.update(dt)

        clone_targets = [(cl, cl.get_rect()) for cl in self.world.clones if cl.alive]
        self._collide(lb, clone_targets)
        self.world.projectiles=[p for p in self.world.projectiles if p.alive]
        self.world.thorns=[t for t in self.world.thorns if t.alive]
        self.world.shields=[s for s in self.world.shields if s.alive]
        # bomb explosions
        for b in self.world.bombs:
            if b.exploded:
                self._explode_bomb(b,lb)
        self.world.bombs=[b for b in self.world.bombs if not b.exploded]

        # New objects update
        for b in self.world.boomerangs: b.update(dt,self.particles)
        for s in self.world.spike_projs: s.update(dt,self.particles)
        for s in self.world.spread_projs: s.update(dt,self.particles)
        for sf in self.world.slow_fields: sf.update(dt)
        for cl in self.world.clones: cl.update(dt,self.world,self.game_map.platforms,self.particles)
        for it in self.world.items: it.update(dt,self.game_map.platforms)
        for mw in self.world.meteor_warnings: mw.update(dt)
        for pw in self.world.planet_warnings: pw.update(dt)
        for sc in self.world.sanctums: sc.update(dt)
        for sj in self.world.superjump_projs: sj.update(dt,self.particles)
        for sb in self.world.spread_bullets: sb.update(dt,self.particles)
        for hm in self.world.homing_projs: hm.update(dt,self.particles,self.world)
        for sb in self.world.spread_bullets: sb.update(dt,self.particles)
        # update melee attacks (move hitbox to follow owner)
        for ma in self.world.melee_attacks:
            # sync position to owner
            owner_pl = self.player1 if ma.owner==0 else self.player2
            ma.x = owner_pl.x; ma.y = owner_pl.y
            ma.update(dt)
        # mana burst countdown
        for pid in [0,1]:
            if self.world.mana_burst[pid]>0:
                self.world.mana_burst[pid]=max(0,self.world.mana_burst[pid]-dt)
        # Super jump apex/land detection
        for pl in [self.player1,self.player2]:
            if not getattr(pl,'_superjump_active',False): continue
            dmg=getattr(pl,'_superjump_dmg',1)
            # apex: when vy crosses 0 (going from up to down)
            if not pl._superjump_apex_done and pl.vy>=0:
                pl._superjump_apex_done=True
                # no mid-air burst (only launch + land)
                self.particles.burst(pl.x,pl.y-pl.H//2,pl.color,6,80,3,0.2,40)
            # land: when on_ground after apex → 4×2 burst
            if pl._superjump_apex_done and not pl._superjump_land_done and pl.on_ground:
                pl._superjump_land_done=True; pl._superjump_active=False
                for i in range(4):
                    a=2*math.pi*i/4
                    for spread in [-0.18, 0.18]:
                        a2=a+spread
                        ox2=pl.x+math.cos(a)*18
                        oy2=pl.y-pl.H//2+math.sin(a)*18
                        self.world.superjump_projs.append(Projectile(
                            ox2,oy2,math.cos(a2)*370,math.sin(a2)*370,4,dmg,pl.id))
                self.particles.burst(pl.x,pl.y-pl.H//2,pl.color,12,130,4,0.35,80)
        # ── Slow Field: owner-immune, non-accumulating, restore on exit/expire ──
        # Strategy: each projectile stores _orig_spd and _slowed.
        # When entering a hostile field → set speed to 1/5 of _orig_spd.
        # When exiting (no longer in any hostile field) → restore to _orig_spd.
        # When field expires, all its projectiles that are still _slowed get restored.
        def _apply_slow_to_projs(proj_list, is_2d=True):
            for proj in proj_list:
                if not getattr(proj, 'alive', True): continue
                if not hasattr(proj, '_orig_spd'):
                    proj._orig_spd = math.hypot(proj.vx, proj.vy) if is_2d else abs(proj.vx)
                in_sf = self.world.in_slow_for(proj.x, proj.y, proj.owner)
                was_slowed = getattr(proj, '_slowed', False)
                if in_sf and not was_slowed:
                    if is_2d:
                        mag = math.hypot(proj.vx, proj.vy)
                        if mag > 0:
                            proj.vx = proj.vx/mag*(proj._orig_spd*0.2)
                            proj.vy = proj.vy/mag*(proj._orig_spd*0.2)
                    else:
                        proj.vx = math.copysign(proj._orig_spd*0.2, proj.vx)
                    proj._slowed = True
                elif not in_sf and was_slowed:
                    if is_2d:
                        mag = math.hypot(proj.vx, proj.vy)
                        if mag > 0:
                            proj.vx = proj.vx/mag*proj._orig_spd
                            proj.vy = proj.vy/mag*proj._orig_spd
                    else:
                        proj.vx = math.copysign(proj._orig_spd, proj.vx)
                    proj._slowed = False

        if len(self.world.slow_fields) > 0:
            proj_lists = [
                (self.world.projectiles, True),
                (self.world.boomerangs, True),
                (self.world.spread_projs, True),
                (self.world.spike_projs, False),
                (self.world.homing_projs, True),
                (self.world.spread_bullets, True)
            ]
            for plist, is_2d in proj_lists:
                _apply_slow_to_projs(plist, is_2d=is_2d)
        else:
            for plist in [self.world.projectiles, self.world.boomerangs,
                          self.world.spread_projs, self.world.spike_projs,
                          self.world.homing_projs, self.world.spread_bullets]:
                for proj in plist:
                    if getattr(proj, '_slowed', False) and hasattr(proj, '_orig_spd'):
                        if isinstance(proj, (SpreadProjectile,)) or hasattr(proj, 'vy'):
                            mag = math.hypot(proj.vx, getattr(proj,'vy',0))
                            if mag > 0:
                                proj.vx = proj.vx/mag*proj._orig_spd
                                if hasattr(proj,'vy'): proj.vy = proj.vy/mag*proj._orig_spd
                        proj._slowed = False

        # cleanup
        self.world.boomerangs=[b for b in self.world.boomerangs if b.alive]
        self.world.spike_projs=[s for s in self.world.spike_projs if s.alive]
        self.world.spread_projs=[s for s in self.world.spread_projs if s.alive]
        self.world.slow_fields=[sf for sf in self.world.slow_fields if sf.alive]
        self.world.clones=[cl for cl in self.world.clones if cl.alive]
        self.world.items=[it for it in self.world.items if it.alive]
        self.world.meteor_warnings=[mw for mw in self.world.meteor_warnings if mw.alive]
        self.world.planet_warnings=[pw for pw in self.world.planet_warnings if pw.alive]
        self.world.sanctums=[sc for sc in self.world.sanctums if sc.alive]
        self.world.superjump_projs=[sj for sj in self.world.superjump_projs if sj.alive]
        self.world.spread_bullets=[sb for sb in self.world.spread_bullets if sb.alive]
        self.world.homing_projs=[hm for hm in self.world.homing_projs if hm.alive]
        self.world.spread_bullets=[sb for sb in self.world.spread_bullets if sb.alive]
        self.world.melee_attacks=[ma for ma in self.world.melee_attacks if ma.alive]

        self._collide_special(lb, clone_targets)
        self._collide_new(lb, clone_targets)
        self._item_pickup()

        # item spawn logic
        self._item_timer-=dt
        if self._item_timer<=0:
            self.world.items.append(Item(random.uniform(80,SCREEN_W-80),random.choice(ITEM_TYPES)))
            interval = random.uniform(5,12) if self.time_left<60 else random.uniform(10,18)
            self._item_timer=interval

        self.particles.update(dt);self.screen_fx.update(dt)
        self.ui.update(dt);self.game_map.update(dt)
        self.dnums=[d for d in self.dnums if d.life>0]
        for d in self.dnums: d.update(dt)

    def _explode_bomb(self,b,lb):
        self.particles.burst(b.x,b.y,COLORS["bomb"],30,300,8,0.6,200)
        self.particles.burst(b.x,b.y,COLORS["yellow"],12,200,5,0.4,100)
        self.screen_fx.shake(12,0.25);self.screen_fx.flash_if(getattr(self,"flash_enabled",True),COLORS["orange"],0.1)
        er=b.get_explode_rect()
        dmg_base=b.damage*(1.1 if lb else 1.0)
        for pl in [self.player1,self.player2]:
            if pl.id!=b.owner and er.colliderect(pl.get_rect()):
                kd=1 if pl.x>b.x else -1
                pl.take_damage(dmg_base,kd,self.particles,self.dnums,self.world)
        # bomb also damages opponent clones
        for cl in self.world.clones:
            if cl.alive and cl.owner!=b.owner and er.colliderect(cl.get_rect()):
                cl.take_damage(dmg_base,self.particles,self.dnums)

    def _collide(self, lb, clone_targets):
        p1r=self.player1.get_rect();p2r=self.player2.get_rect()
        all_targets=[(self.player1,p1r),(self.player2,p2r)]
        # helper: check reflect shield contact for a projectile
        def try_reflect(proj, target_id):
            for sh in self.world.shields:
                if sh.owner==target_id and sh.contains(proj.x, proj.y):
                    proj.vx=-proj.vx; proj.vy=-proj.vy; proj.owner=target_id
                    self.particles.burst(proj.x,proj.y,COLORS["reflect"],10,150,5,0.3,100)
                    return True
            return False

        # projectile vs player (includes superjump_projs via unified list check)
        all_projs = self.world.projectiles + self.world.superjump_projs
        for proj in all_projs:
            if not proj.alive: continue
            for pl,(pr) in [(self.player1,p1r),(self.player2,p2r)]:
                if proj.owner!=pl.id and pr.colliderect(proj.get_rect()):
                    reflected=False
                    if not proj.is_thorn:
                        reflected=try_reflect(proj,pl.id)
                    if not reflected:
                        kd=1 if proj.vx>=0 else -1
                        dmg=proj.damage*(1.1 if lb else 1.0)
                        pl.take_damage(dmg,kd,self.particles,self.dnums,self.world)
                        proj.alive=False
                        hc=COLORS["p1"] if proj.owner==0 else COLORS["p2"]
                        self.particles.burst(proj.x,proj.y,hc,16,200,5,0.45,300)
                        self.particles.burst(proj.x,proj.y,COLORS["white"],5,100,3,0.2,100)
                        self.screen_fx.shake(4+proj.size*0.3,0.10)
                        self.screen_fx.flash_if(getattr(self,"flash_enabled",True),hc,0.05)
                    break

        # thorn vs player + reflect check
        for th in self.world.thorns:
            if th.hit: continue
            tr=th.get_rect()
            for pl in [self.player1,self.player2]:
                if pl.id!=th.owner and tr.colliderect(pl.get_rect()):
                    th.hit=True
                    dmg=th.damage*(1.1 if lb else 1.0)
                    pl.take_damage(dmg,0,self.particles,self.dnums,self.world)
                    self.screen_fx.shake(3,0.08)

        # superjump projs vs players (with reflect)
        for sj in self.world.superjump_projs:
            if not sj.alive: continue
            for pl,(pr) in [(self.player1,p1r),(self.player2,p2r)]:
                if sj.owner!=pl.id and pr.colliderect(sj.get_rect()):
                    if try_reflect(sj, pl.id):
                        break
                    kd=1 if sj.vx>=0 else -1
                    dmg=sj.damage*(1.1 if lb else 1.0)
                    pl.take_damage(dmg,kd,self.particles,self.dnums,self.world)
                    sj.alive=False
                    self.screen_fx.shake(2,0.06)
                    break

        # dash collision
        for pl,ot,otr in [(self.player1,self.player2,p2r),(self.player2,self.player1,p1r)]:
            if pl.dashing and pl.get_rect().colliderect(otr):
                dmg=22**pl.passive["dmg_mult"]*(1.1 if lb else 1.0)
                if abs(pl.dash_vx) == 1500:
                    ot.take_damage(dmg,pl.dash_dir,self.particles,self.dnums,self.world)
                    pl.dashing=False
                    self.particles.burst(pl.x,pl.y-pl.H//2,pl.color,20,260,7,0.5,200)
                    self.screen_fx.shake(9,0.18);self.screen_fx.flash_if(getattr(self,"flash_enabled",True),pl.color,0.08)

    def _collide_special(self, lb, clone_targets):
        p1r=self.player1.get_rect(); p2r=self.player2.get_rect()
        players=[(self.player1,p1r),(self.player2,p2r)]

        # ── reflect helper ────────────────────────────────────────────────
        def try_reflect_special(obj, target_id, reverse_fn):
            """Try to reflect obj off target_id's shields. reverse_fn reverses obj motion."""
            for sh in self.world.shields:
                if sh.owner==target_id and sh.contains(obj.x, obj.y):
                    reverse_fn()
                    self.particles.burst(obj.x,obj.y,COLORS["reflect"],10,150,5,0.3,100)
                    return True
            return False

        # ── BOOMERANG: multi-hit (each target once per phase) ──────────
        for bm in self.world.boomerangs:
            if not bm.alive: continue
            r=bm.get_rect()
            bm_col=COLORS["p1"] if bm.owner==0 else COLORS["p2"]
            # check players
            for pl,pr in players:
                if pl.id==bm.owner: continue
                def bm_reverse(b=bm, new_owner=pl.id):
                    # Reflect: boomerang changes owner, returns to new owner
                    b.owner=new_owner
                    b._owner_ref=pl   # follow new owner back
                    b.returning=True
                    # reverse direction toward new owner
                    dx=pl.x-b.x; dy=(pl.y-pl.H//2)-b.y
                    dist=max(1,math.hypot(dx,dy))
                    spd=math.hypot(b.vx,b.vy) or b.speed
                    b.vx=dx/dist*spd; b.vy=dy/dist*spd
                    # reset hit sets so new owner's targets can be hit
                    b.hit_set_go=set(); b.hit_set_return=set()
                reflected=try_reflect_special(bm,pl.id,bm_reverse)
                if reflected: continue
                if bm.can_hit_go(pl.id) and pr.colliderect(r):
                    bm.hit_set_go.add(pl.id)
                    dmg=bm.damage*(1.1 if lb else 1.0)
                    pl.take_damage(dmg,bm.facing,self.particles,self.dnums,self.world)
                    self.screen_fx.shake(4,0.1); self.screen_fx.flash_if(getattr(self,"flash_enabled",True),bm_col,0.04)
                elif bm.can_hit_return(pl.id) and pr.colliderect(r):
                    bm.hit_set_return.add(pl.id)
                    dmg=bm.damage*(1.1 if lb else 1.0)
                    pl.take_damage(dmg,bm.facing,self.particles,self.dnums,self.world)
                    self.screen_fx.shake(4,0.1); self.screen_fx.flash_if(getattr(self,"flash_enabled",True),bm_col,0.04)
            # boomerang vs clones (also multi-hit per clone per phase)
            for cl,cr in clone_targets:
                if cl.owner==bm.owner: continue
                cid=id(cl)
                if bm.can_hit_go(cid) and cr.colliderect(r):
                    bm.hit_set_go.add(cid)
                    cl.take_damage(bm.damage,self.particles,self.dnums)
                elif bm.can_hit_return(cid) and cr.colliderect(r):
                    bm.hit_set_return.add(cid)
                    cl.take_damage(bm.damage,self.particles,self.dnums)

        # ── SPIKE vs players + clones ─────────────────────────────────────
        for sp in self.world.spike_projs:
            if sp.split_done: continue  # already split, skip
            r=sp.get_rect()
            hit_target=False
            if sp.alive and not sp.hit:
                # vs players
                for pl,pr in players:
                    if pl.id!=sp.owner and pr.colliderect(r):
                        # reflect?
                        def sp_reverse(s=sp): s.vx=-s.vx
                        if try_reflect_special(sp,pl.id,sp_reverse): break
                        sp.hit=True; hit_target=True
                        dmg=sp.damage*(1.1 if lb else 1.0)
                        pl.take_damage(dmg,sp.facing,self.particles,self.dnums,self.world)
                        sp.explode(self.particles)
                        self.screen_fx.shake(5,0.12)
                        break
                # vs clones
                if not sp.hit:
                    for cl,cr in clone_targets:
                        if cl.owner!=sp.owner and cr.colliderect(r):
                            sp.hit=True; hit_target=True
                            cl.take_damage(sp.damage,self.particles,self.dnums)
                            sp.explode(self.particles)
                            break
            # spawn split projectiles once (on hit or distance-explode)
            if sp.exploded and not sp.split_done:
                sp.split_done=True
                for i in range(sp.split_count):
                    angle=2*math.pi*i/sp.split_count
                    vx2=math.cos(angle)*220; vy2=math.sin(angle)*220
                    sdmg=sp.split_dmg*(1.1 if lb else 1.0)
                    self.world.projectiles.append(Projectile(sp.x,sp.y,vx2,vy2,5,sdmg,sp.owner))

        # ── SPREAD vs players + clones ───────────────────────────────────
        for sp in self.world.spread_projs:
            if not sp.alive: continue
            r=sp.get_rect()
            for pl,pr in players:
                if pl.id!=sp.owner and pr.colliderect(r):
                    def spr_rev(s=sp): s.vx=-s.vx; s.vy=-s.vy
                    if try_reflect_special(sp,pl.id,spr_rev): break
                    sp.alive=False
                    dmg=sp.damage*(1.1 if lb else 1.0)
                    pl.take_damage(dmg,0,self.particles,self.dnums,self.world)
                    self.screen_fx.shake(2,0.06)
                    break
            if not sp.alive: continue
            for cl,cr in clone_targets:
                if cl.owner!=sp.owner and cr.colliderect(r):
                    sp.alive=False
                    cl.take_damage(sp.damage,self.particles,self.dnums)
                    break

        # ── HOMING vs players + clones ──────────────────────────────────
        for hm in self.world.homing_projs:
            if not hm.alive: continue
            hr=hm.get_rect()
            for pl,pr in players:
                if pl.id==hm.owner: continue
                def hm_rev(h=hm): h.vx=-h.vx; h.vy=-h.vy; h.owner=pl.id
                if try_reflect_special(hm, pl.id, hm_rev): break
                if pr.colliderect(hr):
                    hm.alive=False
                    dmg=hm.damage*(1.1 if lb else 1.0)
                    kd=1 if hm.vx>=0 else -1
                    pl.take_damage(dmg,kd,self.particles,self.dnums,self.world)
                    hc=COLORS["p1"] if hm.owner==0 else COLORS["p2"]
                    self.particles.burst(hm.x,hm.y,hc,10,160,4,0.35,200)
                    self.screen_fx.shake(3,0.08)
                    break
            if not hm.alive: continue
            for cl,cr in clone_targets:
                if cl.owner!=hm.owner and cr.colliderect(hr):
                    hm.alive=False
                    cl.take_damage(hm.damage,self.particles,self.dnums); break

                # ── MELEE ATTACKS vs players + clones + golems ──────────────────
        for ma in self.world.melee_attacks:
            if not ma.alive: continue
            mr = ma.get_rect()
            for pl, pr in players:
                if pl.id == ma.owner: continue
                tid = ('player', pl.id)
                if tid not in ma.hit_ids and pr.colliderect(mr):
                    ma.hit_ids.add(tid)
                    dmg = ma.damage * (1.1 if lb else 1.0)
                    # quick_stab has no knockback — allows consecutive hits
                    kd  = 0 if ma.style == 'quick_stab' else ma.facing
                    pl.take_damage(dmg, kd, self.particles, self.dnums, self.world)
                    self.particles.sparks(ma.x, ma.y - 30, ma.color, ma.facing, 8, 200)
                    self.screen_fx.shake(4, 0.10)
            for cl, cr in clone_targets:
                if cl.owner == ma.owner: continue
                cid = ('clone', id(cl))
                if cid not in ma.hit_ids and cr.colliderect(mr):
                    ma.hit_ids.add(cid)
                    cl.take_damage(ma.damage, self.particles, self.dnums)

        # ── SPREAD BULLET vs players + clones ───────────────────────────
        for sb in self.world.spread_bullets:
            if not sb.alive: continue
            r=sb.get_rect()
            hit=False
            for pl,pr in players:
                if pl.id==sb.owner: continue
                def sb_rev(s=sb): s.vx=-s.vx; s.vy=-s.vy
                if try_reflect_special(sb,pl.id,sb_rev): hit=True; break
                if pr.colliderect(r):
                    hit=True; sb.hit=True
                    dmg=sb.damage*(1.1 if lb else 1.0)
                    kd=1 if sb.vx>=0 else -1
                    pl.take_damage(dmg,kd,self.particles,self.dnums,self.world)
                    sb.explode(self.particles); break
            if not hit:
                for cl,cr in clone_targets:
                    if cl.owner!=sb.owner and cr.colliderect(r):
                        hit=True; sb.hit=True
                        cl.take_damage(sb.damage,self.particles,self.dnums)
                        sb.explode(self.particles); break
            # spawn splits once exploded
            if sb.exploded and not sb.split_done:
                sb.split_done=True
                for i in range(sb.split_count):
                    a=2*math.pi*i/sb.split_count
                    sdmg=sb.split_dmg*(1.1 if lb else 1.0)
                    self.world.projectiles.append(
                        Projectile(sb.x,sb.y,math.cos(a)*220,math.sin(a)*220,
                                   5,sdmg,sb.owner))

        # ── BOMB explosion vs clones ──────────────────────────────────────
        # (players handled in _explode_bomb; clones checked here live)
        # Note: bombs that already exploded are removed before this runs.
        # We add clone damage in _explode_bomb instead — done below.

        # ── PROJECTILES (world.projectiles) vs clones ────────────────────
        for proj in self.world.projectiles:
            if not proj.alive: continue
            for cl,cr in clone_targets:
                if cl.owner==proj.owner: continue
                if cr.colliderect(proj.get_rect()):
                    proj.alive=False
                    cl.take_damage(proj.damage,self.particles,self.dnums)
                    self.screen_fx.shake(2,0.06)
                    break

        # ── THORNS vs clones ─────────────────────────────────────────────
        for th in self.world.thorns:
            if th.hit: continue
            tr=th.get_rect()
            for cl,cr in clone_targets:
                if cl.owner!=th.owner and cr.colliderect(tr):
                    cl.take_damage(0.35*th.damage,self.particles,self.dnums)
                    # thorn can hit clone AND player (don't set th.hit here)

    def _collide_new(self, lb, clone_targets):
        """Collisions for golem, sanctum effects, superjump projs, planet split."""
        p1r=self.player1.get_rect(); p2r=self.player2.get_rect()
        players=[(self.player1,p1r),(self.player2,p2r)]

        # super jump projs vs players+clones+golems
        for sj in self.world.superjump_projs:
            if not sj.alive: continue
            r=sj.get_rect()
            for pl,pr in players:
                if pl.id!=sj.owner and pr.colliderect(r):
                    sj.alive=False
                    dmg=sj.damage*(1.1 if lb else 1.0)
                    pl.take_damage(dmg,0,self.particles,self.dnums,self.world); break
            if not sj.alive: continue
            for cl,cr in clone_targets:
                if cl.owner!=sj.owner and cr.colliderect(r):
                    sj.alive=False
                    cl.take_damage(sj.damage,self.particles,self.dnums); break

        # ── CLONE vs CLONE combat (projectiles already handled above) ─
        # Clones' bullets go into world.projectiles and hit via projectile vs clone loop

        # bomb explosion vs golems (handled in _explode_bomb, just need golem list there)
        # ── PLANET multi-tier split system ──────────────────────────────
        p1r=self.player1.get_rect(); p2r=self.player2.get_rect()
        players_list=[(self.player1,p1r),(self.player2,p2r)]
        clone_t2=[(cl,cl.get_rect()) for cl in self.world.clones if cl.alive]

        def spawn_tier2(px,py,owner):
            """12 size-6 projectiles in a ring."""
            for i in range(12):
                a=2*math.pi*i/12
                p=Projectile(px,py,math.cos(a)*240,math.sin(a)*240,6,6,owner)
                p.planet_tier=2
                self.world.projectiles.append(p)

        def spawn_tier1(px,py,owner):
            """12 size-14 projectiles in a ring."""
            for i in range(12):
                a=2*math.pi*i/12
                p=Projectile(px,py,math.cos(a)*260,math.sin(a)*260,14,getattr(self,'_planet_t1_dmg',6),owner)
                p.planet_tier=1
                self.world.projectiles.append(p)

        new_projs=[]
        for proj in list(self.world.projectiles):
            if not proj.alive: continue
            tier=getattr(proj,'planet_tier',0)

            # ── TIER 0 (original 52-size planet) ──────────────────────
            if tier==0 and proj.size>=50:
                # hit player?
                hit=False
                for pl,pr in players_list:
                    if proj.owner!=pl.id and pr.colliderect(proj.get_rect()):
                        hit=True
                        dmg=proj.damage*(1.1 if lb else 1.0)
                        pl.take_damage(dmg,0,self.particles,self.dnums,self.world)
                        break
                # hit floor?
                if not hit and proj.y>=FLOOR_Y-proj.size:
                    hit=True
                if hit:
                    proj.alive=False
                    col=COLORS["p1"] if proj.owner==0 else COLORS["p2"]
                    self.particles.burst(proj.x,proj.y,col,24,300,8,0.6,200)
                    self.screen_fx.shake(14,0.3)
                    self.screen_fx.flash_if(getattr(self,"flash_enabled",True),COLORS["yellow"],0.08)
                    self._planet_t1_dmg=6
                    spawn_tier1(proj.x,proj.y,proj.owner)

            # ── TIER 1 (size-14 fragments) ────────────────────────────
            elif tier==1:
                hit=False
                for pl,pr in players_list:
                    if proj.owner!=pl.id and pr.colliderect(proj.get_rect()):
                        hit=True
                        dmg=proj.damage*(1.1 if lb else 1.0)
                        pl.take_damage(dmg,0,self.particles,self.dnums,self.world)
                        break
                if not hit:
                    for cl,cr in clone_t2:
                        if cl.owner!=proj.owner and cr.colliderect(proj.get_rect()):
                            hit=True; cl.take_damage(proj.damage,self.particles,self.dnums); break
                # wall/floor terrain
                if not hit and (proj.x<=proj.size or proj.x>=SCREEN_W-proj.size
                                or proj.y>=FLOOR_Y-proj.size or proj.y<=-proj.size):
                    hit=True
                if hit and proj.alive:
                    proj.alive=False
                    col=COLORS["p1"] if proj.owner==0 else COLORS["p2"]
                    self.particles.burst(proj.x,proj.y,col,10,180,4,0.35,150)
                    spawn_tier2(proj.x,proj.y,proj.owner)

            # ── TIER 2 (size-6 final fragments, no further split) ─────
            elif tier==2:
                for pl,pr in players_list:
                    if proj.owner!=pl.id and pr.colliderect(proj.get_rect()):
                        proj.alive=False
                        dmg=6*(1.1 if lb else 1.0)
                        pl.take_damage(dmg,0,self.particles,self.dnums,self.world)
                        break
                if proj.alive:
                    for cl,cr in clone_t2:
                        if cl.owner!=proj.owner and cr.colliderect(proj.get_rect()):
                            proj.alive=False; cl.take_damage(6,self.particles,self.dnums); break

    def _item_pickup(self):
        p1r=self.player1.get_rect(); p2r=self.player2.get_rect()
        for it in self.world.items:
            if not it.alive: continue
            ir=it.get_rect()
            for pl,pr in [(self.player1,p1r),(self.player2,p2r)]:
                if pr.colliderect(ir):
                    it.alive=False
                    self.particles.burst(it.x,it.y,ITEM_COLORS[it.kind],16,180,6,0.5,100)
                    self.screen_fx.flash_if(getattr(self,"flash_enabled",True),ITEM_COLORS[it.kind],0.08)
                    lbl=ITEM_LABELS[it.kind]
                    self.dnums.append(DmgNum(pl.x,pl.y-pl.H-10,-99,ITEM_COLORS[it.kind]))
                    self.dnums[-1].val=0  # override draw
                    # custom display
                    if it.kind=="apple":
                        pl.hp=min(pl.max_hp,pl.hp+15)
                        self.dnums.append(DmgNum(pl.x,pl.y-pl.H-10,-20,COLORS["green"]))
                    elif it.kind=="banana":
                        pl.mp=min(pl.max_mp,pl.mp+40)
                        self.dnums.append(DmgNum(pl.x,pl.y-pl.H-10,-50,COLORS["mp_fg"]))
                    elif it.kind=="pear":
                        for sk in pl.skills:
                            sk.timer=max(0.0,sk.timer-10.0)
                    break

    def draw(self,surf):
        gs=self.gsurf
        self.game_map.draw(gs)
        # draw thorns below particles
        for t in self.world.thorns: t.draw(gs)
        self.particles.draw(gs)
        # shields
        for s in self.world.shields: s.draw(gs)
        self.player1.draw(gs);self.player2.draw(gs)
        for sf in self.world.slow_fields: sf.draw(gs)
        for sc in self.world.sanctums: sc.draw(gs)
        for pw in self.world.planet_warnings: pw.draw(gs)
        for mw in self.world.meteor_warnings: mw.draw(gs)
        for it in self.world.items: it.draw(gs)
        for p in self.world.projectiles: p.draw(gs)
        for sj in self.world.superjump_projs: sj.draw(gs)
        for sb in self.world.spread_bullets: sb.draw(gs)
        for hm in self.world.homing_projs: hm.draw(gs)
        for ma in self.world.melee_attacks: ma.draw(gs)
        for b in self.world.bombs: b.draw(gs)
        for bm in self.world.boomerangs: bm.draw(gs)
        for sp in self.world.spike_projs: sp.draw(gs)
        for sp in self.world.spread_projs: sp.draw(gs)
        for cl in self.world.clones: cl.draw(gs)
        for d in self.dnums: d.draw(gs)
        self.ui.draw_player_ui(gs,self.player1,20)
        self.ui.draw_player_ui(gs,self.player2,SCREEN_W-20-290)
        self.ui.draw_timer(gs,self.time_left,self._game_phase())
        hl=Fonts.r(12).render("P1: A/D  W  1/2/3/4",True,COLORS["gray"])
        hr=Fonts.r(12).render("P2: L/R  Up  M/,/./Slash",True,COLORS["gray"])
        gs.blit(hl,(10,SCREEN_H-18));gs.blit(hr,(SCREEN_W-hr.get_width()-10,SCREEN_H-18))
        flash_lbl=Fonts.r(11).render(f"Flash: {'ON' if self.flash_enabled else 'OFF'} [P]",
                                      True,COLORS["yellow"] if self.flash_enabled else COLORS["gray"])
        gs.blit(flash_lbl,(SCREEN_W//2-flash_lbl.get_width()//2,SCREEN_H-18))
        ox,oy=self.screen_fx.offset;surf.blit(gs,(ox,oy))
        self.screen_fx.draw_flash(surf)

# ══════════════════════════════════════════════════════
#  PRE-GAME SKILL PREVIEW (3 seconds)
# ══════════════════════════════════════════════════════
SKILL_ICONS = {
    "projectile": [(0,0),(8,0)],
    "dash":        "dash",
    "thorn":       "thorn",
    "radial_thorn":"radial_thorn",
    "bomb":        "bomb",
    "heal":        "heal",
    "meteor":      "meteor",
    "reflect":     "reflect",
    "slowfield":   "slow",
    "clone":       "clone",
    "boomerang":   "boom",
    "doublejump":  "jump",
    "spike":       "spike",
    "spread":      "spread",
    "superjump":   "sjump",
    "planet":      "planet",
    "manaburst":   "mburst",
    "sanctum":     "sanctum",
    "charge_shot": "charge_shot",
    "burst_step":  "burst_step",
    "arc_shot":    "arc_shot",
    "quick_stab":  "quick_stab",
}

def draw_skill_icon(surf, x, y, size, sk_type, col):
    """Draw a simple geometric icon representing the skill type."""
    cx,cy = x+size//2, y+size//2
    c = col; dc = tuple(min(255,v+60) for v in col)
    if sk_type == "projectile":
        pygame.draw.circle(surf, c, (cx,cy), size//4)
        pygame.draw.line(surf, dc, (cx-size//3,cy), (cx+size//3,cy), 3)
    elif sk_type == "dash":
        for i,ox in enumerate([-8,-2,4]):
            pygame.draw.line(surf, c, (cx+ox,cy-6),(cx+ox+6,cy),2)
            pygame.draw.line(surf, c, (cx+ox+6,cy),(cx+ox,cy+6),2)
    elif sk_type == "thorn":
        for ox in [-8,0,8]:
            pygame.draw.line(surf, c, (cx+ox,cy+8),(cx+ox,cy-10),3)
            pts=[(cx+ox-4,cy-4),(cx+ox,cy-14),(cx+ox+4,cy-4)]
            pygame.draw.polygon(surf, c, pts)
    elif sk_type == "radial_thorn":
        # starburst: 12 lines radiating from center
        r_inner, r_outer = size//6, size//2-2
        for i in range(12):
            a = math.radians(i * 30)
            pygame.draw.line(surf, c,
                (cx + int(math.cos(a)*r_inner), cy + int(math.sin(a)*r_inner)),
                (cx + int(math.cos(a)*r_outer), cy + int(math.sin(a)*r_outer)), 2)
        pygame.draw.circle(surf, dc, (cx, cy), r_inner+1)
    elif sk_type == "bomb":
        pygame.draw.circle(surf, c, (cx,cy+2), size//4+1)
        pygame.draw.line(surf, dc, (cx,cy-size//4+2),(cx+4,cy-size//3-2),2)
        pygame.draw.circle(surf, (255,220,80), (cx+5,cy-size//3-3), 3)
    elif sk_type == "heal":
        hw=4
        pygame.draw.rect(surf, (80,220,100), (cx-hw,cy-hw*3,hw*2,hw*6), border_radius=2)
        pygame.draw.rect(surf, (80,220,100), (cx-hw*3,cy-hw,hw*6,hw*2), border_radius=2)
    elif sk_type == "meteor":
        for i in range(3):
            ox=random.choice([-8,0,8]); oy=-12+i*6
            pygame.draw.circle(surf, c, (cx+ox,cy+oy), 4)
            pygame.draw.line(surf, dc,(cx+ox,cy+oy),(cx+ox,cy+oy-6),2)
        # deterministic version:
        for ox,sy in [(-8,-6),(0,-10),(8,-4)]:
            pygame.draw.circle(surf, c, (cx+ox,cy+sy), 4)
            pygame.draw.line(surf, dc,(cx+ox,cy+sy),(cx+ox,cy+sy-8),2)
    elif sk_type == "reflect":
        pygame.draw.line(surf, dc,(cx,cy-12),(cx,cy+12),4)
        pygame.draw.line(surf, c,(cx-8,cy-6),(cx,cy),2)
        pygame.draw.line(surf, c,(cx-8,cy+6),(cx,cy),2)
    elif sk_type in ("slowfield","sanctum"):
        pygame.draw.circle(surf, c, (cx,cy), size//3, 2)
        for a in range(0,360,45):
            r=math.radians(a)
            pygame.draw.circle(surf, dc,(cx+int(math.cos(r)*size//4),cy+int(math.sin(r)*size//4)),2)
    elif sk_type == "clone":
        for ox in [-9,0,9]:
            pygame.draw.circle(surf, c,(cx+ox,cy-6),5)
            pygame.draw.rect(surf, c, (cx+ox-4,cy-1,8,10),border_radius=2)
    elif sk_type == "boomerang":
        pts=[(cx-12,cy+4),(cx-4,cy-10),(cx+8,cy-6),(cx+12,cy+4)]
        pygame.draw.lines(surf, c, False, pts, 3)
    elif sk_type == "doublejump":
        pygame.draw.line(surf, c,(cx-8,cy+8),(cx,cy-10),3)
        pygame.draw.line(surf, c,(cx,cy-10),(cx+8,cy+8),3)
        pygame.draw.line(surf, c,(cx-4,cy+2),(cx+4,cy+2),2)
    elif sk_type == "spike":
        pygame.draw.circle(surf, c,(cx,cy),size//4+2)
        for a in range(0,360,60):
            r=math.radians(a)
            pygame.draw.line(surf,dc,(cx+int(math.cos(r)*8),cy+int(math.sin(r)*8)),
                             (cx+int(math.cos(r)*16),cy+int(math.sin(r)*16)),3)
    elif sk_type == "spread":
        base=math.pi
        for i in range(5):
            a=base-math.pi/3+i*math.pi/6
            pygame.draw.line(surf,c,(cx,cy),(cx+int(math.cos(a)*18),cy+int(math.sin(a)*18)),2)
    elif sk_type == "superjump":
        pygame.draw.polygon(surf,c,[(cx,cy-14),(cx-8,cy+4),(cx+8,cy+4)])
        for i in range(4):
            a=math.pi/2+i*math.pi/2
            pygame.draw.line(surf,dc,(cx,cy),(cx+int(math.cos(a)*10),cy+int(math.sin(a)*10)),2)
    elif sk_type == "planet":
        pygame.draw.circle(surf,c,(cx,cy),size//4+3)
        pygame.draw.ellipse(surf,dc,(cx-size//3,cy-4,size*2//3,8),2)
    elif sk_type == "mega_planet":
        pygame.draw.circle(surf,c,(cx,cy),size//4+3)
        pygame.draw.ellipse(surf,dc,(cx-size//3,cy-4,size*2//3,8),2)
    elif sk_type == "manaburst":
        for i in range(8):
            a=math.pi/4*i
            pygame.draw.line(surf,(80,160,255),(cx,cy),(cx+int(math.cos(a)*14),cy+int(math.sin(a)*14)),2)
        pygame.draw.circle(surf,(120,200,255),(cx,cy),5)
    elif sk_type == "homing":
        for i in range(6):
            a = i * math.pi / 3
            r1 = size//5 + i*2; r2 = r1 + 4
            pygame.draw.line(surf, c,
                (cx+int(math.cos(a)*r1), cy+int(math.sin(a)*r1)),
                (cx+int(math.cos(a+0.5)*r2), cy+int(math.sin(a+0.5)*r2)), 2)
        pygame.draw.circle(surf, dc, (cx,cy), 4)
    elif sk_type == "melee":
        # Staff icon  — vertical rod with tip
        rod_top = (cx, cy - size//2 + 4)
        rod_bot = (cx + size//4, cy + size//4 - 4)
        pygame.draw.line(surf, c,   rod_top, rod_bot, 4)
        pygame.draw.line(surf, dc,  rod_top, rod_bot, 2)
        tip_pts = [(cx-4, cy-size//2+2),(cx+4,cy-size//2+2),(cx,cy-size//2-7)]
        pygame.draw.polygon(surf, dc, tip_pts)
        # small impact lines for thrust / arc for smash
        for ia in [-25, 25]:
            ar = math.radians(ia)
            pygame.draw.line(surf, dc,
                (cx + int(math.cos(ar)*6),  cy + int(math.sin(ar)*6)),
                (cx + int(math.cos(ar)*14), cy + int(math.sin(ar)*14)), 2)
    elif sk_type == "charge_shot":
        # Concentric rings suggesting charge build-up — drawn on SRCALPHA surface for proper alpha
        icon_s = pygame.Surface((size, size), pygame.SRCALPHA)
        icx, icy = size//2, size//2
        for r2, a2 in [(size//2-2, 180), (size//3, 120), (size//5, 80)]:
            pygame.draw.circle(icon_s, (*c, a2), (icx, icy), max(2, r2), 2)
        pygame.draw.circle(icon_s, (*dc, 255), (icx, icy), size//8+1)
        surf.blit(icon_s, (x, y))
    elif sk_type == "burst_step":
        # Footstep + shockwave ring
        r3 = size//3
        pygame.draw.circle(surf, c, (cx,cy), r3, 2)
        pygame.draw.line(surf, dc, (cx-r3,cy+r3//2),(cx+r3,cy+r3//2), 2)
        for a3 in [0, 60, 120, 180, 240, 300]:
            ra3 = math.radians(a3)
            pygame.draw.line(surf, dc,
                (cx+int(math.cos(ra3)*r3), cy+int(math.sin(ra3)*r3)),
                (cx+int(math.cos(ra3)*(r3+5)), cy+int(math.sin(ra3)*(r3+5))), 2)
    elif sk_type == "arc_shot":
        # Parabolic curve
        pts2 = []
        for i in range(9):
            t2 = i / 8.0
            ax2 = cx - size//2 + int(size*t2)
            ay2 = cy + int(size//3 * math.sin(t2*math.pi) * -1) - 2
            pts2.append((ax2, ay2))
        if len(pts2) > 1:
            pygame.draw.lines(surf, c, False, pts2, 2)
        pygame.draw.circle(surf, dc, pts2[-1], 4)
    elif sk_type == "quick_stab":
        # Short sharp dagger
        tip3 = (cx + size//2 - 2, cy)
        base3 = (cx - size//4, cy)
        pygame.draw.line(surf, dc, base3, tip3, 4)
        pygame.draw.circle(surf, dc, tip3, 3)
        pygame.draw.line(surf, c, (cx, cy-5),(cx, cy+5), 2)  # guard
    else:
        pygame.draw.circle(surf,c,(cx,cy),size//4)

class PreviewState(State):
    """Shows both players' skills for 3 seconds before the game starts."""
    def __init__(self, mgr, game_state):
        super().__init__(mgr)
        self.gs = game_state
        self.timer = 3.0
        self.t = 0.0

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.timer = 0.0  # skip

    def update(self, dt):
        self.timer -= dt
        self.t += dt
        if self.timer <= 0:
            self.manager.change(self.gs)

    def draw(self, surf):
        surf.fill(COLORS["bg"])
        # draw map in bg lightly
        self.gs.game_map.draw(surf)
        # dim overlay
        dim = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        dim.fill((0,0,0,160))
        surf.blit(dim,(0,0))

        # Title
        title = Fonts.r(32).render("SKILL PREVIEW", True, COLORS["yellow"])
        surf.blit(title, (SCREEN_W//2-title.get_width()//2, 18))

        # Countdown
        cnt = Fonts.r(22).render(f"Starting in {max(0,self.timer):.1f}s  [ENTER to skip]",
                                  True, COLORS["gray"])
        surf.blit(cnt, (SCREEN_W//2-cnt.get_width()//2, 58))

        SLOT_W = 270; SLOT_H = 180; GAP = 20
        ICON_SIZE = 54
        players_info = [
            (self.gs.player1, COLORS["p1"], 60,  "Player 1"),
            (self.gs.player2, COLORS["p2"], SCREEN_W//2+40, "Player 2"),
        ]

        for player, pcol, base_x, plabel in players_info:
            # player header
            ph = Fonts.r(20).render(plabel, True, pcol)
            surf.blit(ph, (base_x, 90))
            pname = Fonts.r(13).render(f"Passive: [{player.passive['name']}]", True, COLORS["yellow"])
            surf.blit(pname, (base_x, 116))

            for slot_i, sk in enumerate(player.skills):
                sx = base_x + (slot_i % 2) * (SLOT_W//2 + GAP//2)
                sy = 148 + (slot_i // 2) * (SLOT_H + GAP)

                # slot background
                panel = pygame.Surface((SLOT_W//2 - 4, SLOT_H), pygame.SRCALPHA)
                panel.fill((20, 20, 45, 200))
                tier_col = {"atk":COLORS["cyan"],"uty":COLORS["green"],
                            "high":COLORS["orange"],"ult":COLORS["purple"]}.get(sk.tier, COLORS["gray"])
                pygame.draw.rect(panel, tier_col, (0,0,SLOT_W//2-4,SLOT_H), 2, border_radius=6)
                surf.blit(panel, (sx, sy))

                # icon
                icon_surf = pygame.Surface((ICON_SIZE, ICON_SIZE), pygame.SRCALPHA)
                draw_skill_icon(icon_surf, 0, 0, ICON_SIZE, sk.stype, tier_col)
                surf.blit(icon_surf, (sx+6, sy+8))

                # slot key
                keys_p1 = ["1","2","3","4"]; keys_p2 = ["M",",",".","Slash"]
                key_str = keys_p1[slot_i] if player.id==0 else keys_p2[slot_i]
                kt = Fonts.r(13).render(f"[{key_str}]", True, COLORS["yellow"])
                surf.blit(kt, (sx+ICON_SIZE+10, sy+6))

                # skill name (multi-line wrap at 16 chars)
                full_name = sk.name
                name_w = SLOT_W//2 - ICON_SIZE - 20
                name_lines = []
                word = full_name
                while len(word) > 0:
                    # try to fit as much as possible
                    fit = word
                    for cut in range(len(word), 0, -1):
                        t2 = Fonts.r(12).render(word[:cut], True, COLORS["white"])
                        if t2.get_width() <= name_w:
                            fit = word[:cut]; word = word[cut:]; break
                    else:
                        fit = word; word = ""
                    name_lines.append(fit)
                    if len(name_lines) >= 3: break
                for li, line in enumerate(name_lines):
                    lt = Fonts.r(12).render(line, True, COLORS["white"])
                    surf.blit(lt, (sx+ICON_SIZE+10, sy+24+li*14))

                # stats
                stats = [
                    f"MP: {sk.mp_cost}",
                    f"CD: {sk.cooldown:.1f}s",
                ]
                for si, st in enumerate(stats):
                    st2 = Fonts.r(11).render(st, True, COLORS["cyan"])
                    surf.blit(st2, (sx+ICON_SIZE+10, sy+SLOT_H-36+si*14))

                # tier badge
                if sk.tier == "ult":
                    ub = Fonts.r(9).render("★ULT", True, COLORS["purple"])
                    surf.blit(ub, (sx+4, sy+SLOT_H-16))

# ══════════════════════════════════════════════════════
#  GAME OVER
# ══════════════════════════════════════════════════════
class GameOverState(State):
    def __init__(self,mgr,winner,p1,p2):
        super().__init__(mgr);self.winner=winner;self.p1_hp=p1.hp;self.p2_hp=p2.hp
        self.t=0.0;self.particles=ParticleSystem()
    def handle_event(self,e):
        if e.type==pygame.KEYDOWN:
            if e.key==pygame.K_RETURN:
                self.manager.change(CharacterSelectState(self.manager))
            elif e.key==pygame.K_ESCAPE: self.manager.change(MainMenuState(self.manager))
    def update(self,dt):
        self.t+=dt;self.particles.update(dt)
        wc=COLORS["p1"] if self.winner==1 else COLORS["p2"] if self.winner==2 else COLORS["gray"]
        for _ in range(4):
            self.particles.add(Particle(random.randint(180,SCREEN_W-180),random.randint(80,420),
                                        random.uniform(-110,110),random.uniform(-220,-60),random.uniform(0.9,2.2),
                                        random.choice([wc,COLORS["yellow"],COLORS["white"]]),random.randint(3,9),160))
    def draw(self,surf):
        surf.fill(COLORS["bg"]);self.particles.draw(surf)
        wc=COLORS["p1"] if self.winner==1 else COLORS["p2"] if self.winner==2 else COLORS["gray"]
        for i in range(5):
            r=90+i*58;a=int(28+22*math.sin(self.t*2.5+i));s=pygame.Surface((r*2,r*2),pygame.SRCALPHA)
            pygame.draw.circle(s,(*wc,a),(r,r),r);surf.blit(s,(SCREEN_W//2-r,260-r))
        msg="DRAW!" if self.winner==0 else f"PLAYER {self.winner} WINS!"
        shad=Fonts.r(72).render(msg,True,(0,0,0));title=Fonts.r(72).render(msg,True,wc)
        surf.blit(shad,(SCREEN_W//2-shad.get_width()//2+4,194));surf.blit(title,(SCREEN_W//2-title.get_width()//2,190))
        hp1=Fonts.r(30).render(f"Player 1  HP: {int(self.p1_hp)}",True,COLORS["p1"])
        hp2=Fonts.r(30).render(f"Player 2  HP: {int(self.p2_hp)}",True,COLORS["p2"])
        surf.blit(hp1,(SCREEN_W//2-hp1.get_width()-20,320));surf.blit(hp2,(SCREEN_W//2+20,320))
        s1=Fonts.r(22).render("ENTER  ->  Rematch",True,COLORS["yellow"])
        s2=Fonts.r(22).render("ESC  ->  Main Menu",True,COLORS["gray"])
        surf.blit(s1,(SCREEN_W//2-s1.get_width()//2,400));surf.blit(s2,(SCREEN_W//2-s2.get_width()//2,436))

# ══════════════════════════════════════════════════════
#  GAME
# ══════════════════════════════════════════════════════
class Game:
    def __init__(self):
        pygame.init()
        self.screen=pygame.display.set_mode((SCREEN_W,SCREEN_H))
        pygame.display.set_caption("Tangbi Kevin — 2 Player Game")
        self.clock=pygame.time.Clock()
        self.manager=StateManager()
        self.manager.change(MainMenuState(self.manager))
    def run(self):
        while True:
            dt=min(self.clock.tick(FPS)/1000.0,0.05)
            for e in pygame.event.get():
                if e.type==pygame.QUIT: pygame.quit();sys.exit()
                self.manager.handle_event(e)
            self.manager.update(dt);self.manager.draw(self.screen);pygame.display.flip()

if __name__=="__main__":
    Game().run()
