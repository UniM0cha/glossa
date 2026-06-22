"""SRT를 일정 간격으로 샘플링해 타임라인 개요를 출력 — 설교/찬양/기도 구간 식별용.

usage: python srt_outline.py <file.srt> [interval_sec=90]
"""
import re
import sys


def parse_srt(path):
    blocks = re.split(r"\n\n+", open(path, encoding="utf-8").read().strip())
    out = []
    for b in blocks:
        lines = b.splitlines()
        if len(lines) >= 2 and "-->" in lines[1]:
            start = lines[1].split("-->")[0].strip().replace(",", ".")
            h, m, s = start.split(":")
            sec = int(h) * 3600 + int(m) * 60 + float(s)
            out.append((sec, " ".join(lines[2:]).strip()))
    return out


def main():
    path = sys.argv[1]
    interval = float(sys.argv[2]) if len(sys.argv) > 2 else 120.0
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 220
    entries = parse_srt(path)
    total = entries[-1][0] if entries else 0
    print(f"# {path}  (segments={len(entries)}, end={int(total//60)}:{int(total%60):02d})")

    cur = 0.0
    buf = []

    def flush(t):
        if buf:
            mm, ss = int(t // 60), int(t % 60)
            print(f"{mm:>3d}:{ss:02d}  {' '.join(buf)[:width]}")

    for sec, text in entries:
        if sec >= cur + interval:
            flush(cur)
            while sec >= cur + interval:
                cur += interval
            buf = []
        buf.append(text)
    flush(cur)


if __name__ == "__main__":
    main()
