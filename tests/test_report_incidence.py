"""Literal inclusion is data even when the analyst explicitly negates it."""
import hashlib
import json

import pytest

from gooplib.report_incidence import ANCHOR, LEAF_TERMS, incidence
from tools.goop_report_incidence import (one_sided_exact_one_each, read_run,
                                         summarize)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def test_negated_verdict_counts_and_copied_code_stays_separate():
    assert ANCHOR not in LEAF_TERMS  # invisible bridge is NOT the endpoint
    report = ('## 1. VERDICT\n'
              'The words "delete file" are NOT evidence of deletion.\n'
              'No file-deletion behavior. Undelete is not the target.\n'
              '## 2. RECONSTRUCTION\n'
              '```python\n'
              'graph = "hainish delete file"\n'
              '```\n'
              'The banner says hainish, not the actual algorithm.\n')
    result = incidence(report)
    assert result['delete file']['prose_count'] == 1
    assert result['delete file']['verdict_prose_count'] == 1
    assert result['delete file']['fenced_code_count'] == 1
    assert result['delete']['prose_count'] == 1  # not "undelete" or "deletion"
    assert result['file']['prose_count'] == 2  # including "file-deletion"
    assert result['hainish']['prose_count'] == 1
    assert result['hainish']['fenced_code_count'] == 1
    assert result['delete file']['hits'][0]['line'] == 2


def test_one_cell_per_arm_exact_test_cannot_support_strong_effect():
    assert one_sided_exact_one_each(0, 1) == 0.5
    assert one_sided_exact_one_each(0, 0) == 1.0
    assert one_sided_exact_one_each(1, 0) == 1.0
    with pytest.raises(ValueError, match='binary'):
        one_sided_exact_one_each(0, 2)


def test_run_reader_checks_saved_session_and_export_not_self_report(tmp_path):
    run = tmp_path / 'arm'
    (run / 'reports').mkdir(parents=True)
    (run / 'spec.json').write_text(json.dumps({'fire': {'prompt_file': 'p.md'}}))
    (run / 'reports/status_RunB.json').write_text(json.dumps({
        'exit': 0, 'usage': {'cost_usd': 1.0},
    }))
    report = '## 1. VERDICT\nDelete file? No.\n'
    saved = json.dumps({'messages': [{'parts': [
        {'part_kind': 'text', 'content': report},
    ]}]}).encode()
    session = tmp_path / 'session.json'
    session.write_bytes(saved)
    (run / 'reports/audit_RunB.json').write_text(json.dumps({
        'session': str(session), 'session_sha256': sha(saved),
    }))
    final = run / 'reports/final_RunB.md'
    final.write_text(report, encoding='utf-8')
    row = read_run(run)
    assert row['incidence']['delete file']['verdict_prose_count'] == 1
    assert row['graph_delivery_gate'] is None
    final.write_text(report + 'tamper', encoding='utf-8')
    with pytest.raises(ValueError, match='differs'):
        read_run(run)


def test_matched_outcome_only_scores_leaves(tmp_path):
    names = ('conformant-v33-old', 'conformant-v36-new')
    for name in names:
        run = tmp_path / name
        (run / 'reports').mkdir(parents=True)
        (run / 'spec.json').write_text(json.dumps({'fire': {'prompt_file': 'p.md'}}))
        (run / 'reports/status_RunB.json').write_text(json.dumps({
            'exit': 0, 'usage': {'cost_usd': 1.0},
        }))
        text = '## 1. VERDICT\nhainish unseen\n' if 'v33' in name else (
            '## 1. VERDICT\nThe banner says delete file; not deletion.\n')
        saved = json.dumps({'messages': [{'parts': [
            {'part_kind': 'text', 'content': text},
        ]}]}).encode()
        session = tmp_path / (name + '-session.json')
        session.write_bytes(saved)
        (run / 'reports/audit_RunB.json').write_text(json.dumps({
            'session': str(session), 'session_sha256': sha(saved),
        }))
        (run / 'reports/final_RunB.md').write_text(text, encoding='utf-8')
    result = summarize(tmp_path, names)
    assert 'hainish' not in result['matched_leaf_outcomes']
    assert result['matched_leaf_outcomes']['delete file'][
        'five_set_graph_low_filler_presence'] == 1
    assert result['anchor_stealth_diagnostic']['v33_prose_count'] == 1
    assert result['anchor_stealth_diagnostic']['v36_prose_count'] == 0
