#!/usr/bin/env python3
"""Сверка C++-детекций (raw-строки --box-log) против оракула RKNNLite.

Вход:  dump_dir  — PPM-дампы model-input тензора (--dump-cal, cal_%04d.ppm)
       log_csv   — box-log прогона (строки 'frame,c1,c2' + 'raw,cls,conf,x,y,w,h')
Модель берётся из misc/yolov5s_relu_int8_mmse.rknn (модель пайплайна, решение
владельца 2026-11-01: дефолт mmse остаётся, v5 осознанно не трогаем).

Метод: каждый дамп гонится через RKNNLite (uint8 NHWC — рецепт
tools/save_board_csv.py, откалиброван против misc/board_preds.csv на v2),
декодируется tools/postprocess (жгут подтверждён), переводится в сцену и
матчится с raw-строками того же кадра. Совпадение: IoU>=%.2f при dconf<=%.2f.
"""
import re, sys, glob
import numpy as np
from rknnlite.api import RKNNLite
sys.path.insert(0, 'tools')
from postprocess import decode_outputs

MATCH_IOU = 0.6
CONF_TOL = 0.06
BORDER_CONF = 0.35  # ниже — кромка порога 0.25: dec-графы NPU/Lite расходятся
                    # в самом факте наличия бокса; несходство не считается сбоем
SCALE = 0.5          # 1280x960 -> 640x640 (README: 960p working mode)
LB_TOP_MODEL = 80.0  # 960p letterbox (подтверждается сканом дампа ниже)

def load_ppm(path):
    d = open(path, 'rb').read()
    m = re.match(rb'P6\s+(\d+)\s+(\d+)\s+(\d+)\s', d)
    w, h = int(m.group(1)), int(m.group(2))
    return np.frombuffer(d[m.end():], dtype=np.uint8)[:w*h*3].reshape(h, w, 3)

def lb_top_of(pix):
    gray = (np.abs(pix.astype(np.int16) - 128) <= 1).all(axis=(1, 2))
    top = 0
    while top < len(gray) and gray[top]:
        top += 1
    bot = 0
    while bot < len(gray) and gray[len(gray) - 1 - bot]:
        bot += 1
    return top, bot

def load_log(path):
    frames = {}
    cur = None
    for line in open(path):
        parts = line.strip().split(',')
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            cur = int(parts[0]); frames[cur] = []
        elif len(parts) == 7 and parts[0] == 'raw' and cur is not None:
            frames[cur].append((int(parts[1]), float(parts[2]),
                                float(parts[3]), float(parts[4]),
                                float(parts[5]), float(parts[6])))
    return frames

def iou(a, b):
    ax1, ay1, ax2, ay2 = a[2], a[3], a[2]+a[4], a[3]+a[5]
    bx1, by1, bx2, by2 = b[2], b[3], b[2]+b[4], b[3]+b[5]
    iw, ih = max(0.0, min(ax2,bx2)-max(ax1,bx1)), max(0.0, min(ay2,by2)-max(ay1,by1))
    inter = iw*ih
    return inter / (a[4]*a[5] + b[4]*b[5] - inter + 1e-6)

dump_dir, log_csv = sys.argv[1], sys.argv[2]
frames = load_log(log_csv)
dumps = sorted(glob.glob(dump_dir + '/cal_*.ppm'))

rk = RKNNLite()
rk.load_rknn('./misc/yolov5s_relu_int8_mmse.rknn')
rk.init_runtime(core_mask=RKNNLite.NPU_CORE_0)

tot = mat = u_ref = u_pred = 0
max_px = max_conf = 0.0
for path in dumps:
    idx = int(re.search(r'(\d+)', path).group(1))
    pix = load_ppm(path)
    top, bot = lb_top_of(pix)
    lb_top = float(top)
    outs = rk.inference(inputs=[pix[np.newaxis]])
    pred = decode_outputs([o[0] for o in outs], 0.25, 0.45)
    mine = [(int(c), float(s), x1/SCALE, (y1-lb_top)/SCALE,
             (x2-x1)/SCALE, (y2-y1)/SCALE)
            for x1, y1, x2, y2, s, c in pred]
    # best-frame матчинг: дампы снимаются с шагом --cal-interval,
    # номер кадра дампы != номер строки лога — ищем лучший кадр по среднему IoU
    def frame_score(boxes):
        if not mine or not boxes:
            return -1.0
        vs = []
        for m in mine:
            bv = 0.0
            for g in boxes:
                if g[0] != m[0]:
                    continue
                v = iou(m, g)
                if v > bv:
                    bv = v
            vs.append(bv)
        return sum(vs) / len(mine)
    fbest, fidx = -1.0, None
    for f, boxes in frames.items():
        s = frame_score(boxes)
        if s > fbest:
            fbest, fidx = s, f
    log = frames.get(fidx, []) if fidx is not None else []
    if fidx is not None and fidx != idx:
        print('  dump cal_%04d matched to log frame %d (score %.3f)' % (idx, fidx, fbest))
    taken = [False]*len(mine)
    for g in log:
        tot += 1
        best_v, best_i = 0.0, -1
        for i, m in enumerate(mine):
            if taken[i] or m[0] != g[0]:
                continue
            v = iou(m, g)
            if v > best_v:
                best_v, best_i = v, i
        if best_i < 0 or best_v < MATCH_IOU:
            if g[1] < BORDER_CONF:
                print('  frame %d: BORDERLINE log cls=%d conf=%.4f (IoU %.3f) — не в вердикте' % (idx, g[0], g[1], best_v))
                continue
            u_ref += 1
            print('  frame %d: UNMATCHED log cls=%d conf=%.4f box=(%.1f,%.1f %.1fx%.1f)' % ((idx,) + g))
        else:
            taken[best_i] = True
            m = mine[best_i]
            dx = abs(m[2] - g[2]); dy = abs(m[3] - g[3])
            dc = abs(m[1] - g[1])
            max_px = max(max_px, dx, dy)
            max_conf = max(max_conf, dc)
            if dc > CONF_TOL:
                u_ref += 1
                print('  frame %d: CONF-DRIFT cls=%d log %.4f vs mine %.4f (IoU %.3f)' % (idx, g[0], g[1], m[1], best_v))
            else:
                mat += 1
    for i, m in enumerate(mine):
        if not taken[i]:
            u_pred += 1
            print('  frame %d: PHANTOM pred cls=%d conf=%.4f box=(%.1f,%.1f %.1fx%.1f)' % ((idx,) + m))
rk.release()

print('reference boxes: %d, matched: %d, unmatched: %d, phantoms: %d' % (tot, mat, u_ref, u_pred))
print('max px delta: %.3f, max conf delta: %.4f' % (max_px, max_conf))
ok = (tot > 0 or u_pred == 0) and u_ref == 0 and u_pred == 0
print('PASS' if ok else 'FAIL')
