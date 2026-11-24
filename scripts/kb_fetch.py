#!/usr/bin/env python3
"""Fetch the risk-control knowledge-base child docs into markdown draft files.

One-off helper: reads the index of docs mounted in the "风控领域知识库" doc,
fetches each via lark-cli (user identity) as markdown, and writes them under
skillbot/knowledge_base_draft/<category>/ with sanitized filenames.
"""
import json
import re
import subprocess
from pathlib import Path

DRAFT = Path(__file__).resolve().parent.parent / "knowledge_base_draft"

# (category_dir, doc_id_or_token, title, source_type)
DOCS = [
    ("01_风控总览", "SOBvwqWBwiUhSBkEmdZc8PECnVr", "国际支付账号体系介绍 GP Account System Introduction（2024.06）", "wiki"),
    ("01_风控总览", "EaSEd2RBHo5m4RxTHuIlVkgjgEb", "3DS2.0分享", "docx"),
    ("01_风控总览", "OKFhwkFROiiPEzkjw0Hc12tUnWg", "PIPO 支付风控核心指标口径 One Pager", "wiki"),
    ("01_风控总览", "NCnrwffXLiuObhkXU3jcw5oln2e", "CheckPoint列表", "wiki"),
    ("02_业务场景", "BS4owO25UicSLEk8vc6cEKk6n5f", "GPP-电商业务线分享 E-commerce Introduction", "wiki"),
    ("02_业务场景", "ACYSwba3RiKyahkkcrAcxVx1nLb", "GPP-TikTok Live业务线分享", "wiki"),
    ("02_业务场景", "XRxwwwQA2ifnSgkc6qrc2rZanzd", "GPP- TikTok Local Service Sharing", "wiki"),
    ("03_风险类型", "QqrWd4vmxo6orhxJsMWlpXHsgzb", "[TTS][ROW]电商Payin黑标", "docx"),
    ("03_风险类型", "NoxLdl168odBR1xzDLElYbtZgyc", "TTS ROW交易黑标V3", "docx"),
    ("03_风险类型", "D1xBdCDDnoq2lyxLXnjmpPycyvV", "直播黑白标签定义(D1xBdC-裸链接)", "docx"),
    ("03_风险类型", "EW59dcy88osQ3vxud6mlbJCfg1z", "直播黑白标签定义和False Positive分析 TTLive Bad Tagging Definition and False Positive Analysis", "docx"),
    ("03_风险类型", "FPe7wZWupi25jNkWrWuchKLYnUf", "黑白标优化", "wiki"),
    ("04_规则与策略", "PJnEd8NvqooFXYxDWE8lrlzBgoh", "智能规则优化", "docx"),
]


def sanitize(name: str) -> str:
    name = re.sub(r"[/\\|\[\]<>:*?\"]", "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:120]


def fetch(doc_id: str) -> dict:
    cmd = (
        "LARKSUITE_CLI_NO_UPDATE_NOTIFIER=1 LARKSUITE_CLI_NO_SKILLS_NOTIFIER=1 "
        f'lark-cli docs +fetch --doc "{doc_id}" --as user --doc-format markdown'
    )
    out = subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True)
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": {"message": (out.stderr or out.stdout)[:300]}}


def main():
    results = []
    for category, doc_id, title, stype in DOCS:
        res = fetch(doc_id)
        ok = res.get("ok")
        if ok:
            content = res["data"]["document"]["content"]
            fname = f"{sanitize(title)}.md"
            path = DRAFT / category / fname
            header = (
                f"<!-- source_type: {stype} | doc_id: {doc_id} | "
                f"title: {title} -->\n\n"
            )
            path.write_text(header + content, encoding="utf-8")
            results.append((category, title, "OK", len(content), str(path.relative_to(DRAFT.parent))))
        else:
            err = json.dumps(res.get("error", {}), ensure_ascii=False)[:200]
            results.append((category, title, f"FAIL: {err}", 0, ""))

    print(f"{'STATUS':<8} {'LEN':>7}  CATEGORY / TITLE")
    print("-" * 80)
    for cat, title, status, length, path in results:
        print(f"{('OK' if status=='OK' else 'FAIL'):<8} {length:>7}  {cat} / {title[:50]}")
        if status != "OK":
            print(f"         -> {status}")
    ok_n = sum(1 for r in results if r[2] == "OK")
    print("-" * 80)
    print(f"Fetched OK: {ok_n}/{len(results)}")


if __name__ == "__main__":
    main()
