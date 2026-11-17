#!/usr/bin/env python3
"""저장소 쪽(믿지 않는) 검사기 사본 — 문지기는 이 파일을 실행하지 않는다."""
import sys
text = open(sys.argv[1], encoding='utf-8').read()
bad = [w for w in ('[확인필요]',) if w in text]
print('fail: ' + ', '.join(bad) if bad else 'ok')
sys.exit(1 if bad else 0)
