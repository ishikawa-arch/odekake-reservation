#!/usr/bin/env python3
"""
オデカケ予定の追加CLI
==========================================

data/events.json に新しい予定を追加します。
Claude Code から「5月25日に〇〇ツアーを追加」のような指示で呼び出される想定。

【使い方】
# 対話モード
python scripts/add_event.py

# 引数モード（Claude Codeが直接呼ぶ）
python scripts/add_event.py \\
  --type club \\
  --title "春の桜と老舗うなぎの旅" \\
  --date 2026-05-25 \\
  --deadline 2026-05-18 \\
  --capacity 6 \\
  --fee "8,200円〜" \\
  --location "犬山市" \\
  --image images/club-2026-05-03.jpg \\
  --description "犬山城下町を散策し、老舗のうなぎを"

# gathered（集まったら開催）の場合は --current 0 も指定
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
EVENTS_PATH = ROOT / "data" / "events.json"


def load_events():
    with open(EVENTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_events(data):
    with open(EVENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def generate_id(events, ev_type, date_str):
    """既存IDと衝突しないIDを生成"""
    if ev_type == "club":
        # club-YYYY-MM-NN
        yyyy_mm = date_str[:7]  # 2026-05
        existing_nums = [
            int(e["id"].split("-")[-1])
            for e in events if e["id"].startswith(f"club-{yyyy_mm}")
        ]
        next_num = (max(existing_nums) + 1) if existing_nums else 1
        return f"club-{yyyy_mm}-{next_num:02d}"
    else:
        # gathered-YYYY-NNN
        year = date_str[:4]
        existing_nums = [
            int(e["id"].split("-")[-1])
            for e in events if e["id"].startswith(f"gathered-{year}")
        ]
        next_num = (max(existing_nums) + 1) if existing_nums else 1
        return f"gathered-{year}-{next_num:03d}"


def validate_date(s):
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except ValueError:
        raise argparse.ArgumentTypeError(f"日付形式エラー: {s}（YYYY-MM-DD で指定）")


def prompt_interactive():
    """対話入力"""
    print("=" * 50)
    print("  オデカケ予定の追加")
    print("=" * 50)
    print("種別を選択：")
    print("  1) club     オデカケ倶楽部（毎月企画）")
    print("  2) gathered 集まったら開催")
    choice = input("選択 [1-2] > ").strip()
    ev_type = "club" if choice == "1" else "gathered"

    title = input("ツアー名 > ").strip()
    date = input("開催日 (YYYY-MM-DD) > ").strip()
    deadline = input("締切日 (YYYY-MM-DD) > ").strip()
    capacity = int(input("定員 > ").strip())
    current = 0
    if ev_type == "gathered":
        current = int(input("現在の申込人数（通常は0） > ").strip() or "0")
    fee = input("参加費 (例: 5,500円〜) > ").strip()
    location = input("行き先 > ").strip()
    image = input("画像URL or images/xxx.jpg > ").strip()
    description = input("説明文 > ").strip()

    return {
        "type": ev_type, "title": title, "date": date, "deadline": deadline,
        "capacity": capacity, "current": current, "fee": fee, "location": location,
        "image": image, "description": description
    }


def main():
    parser = argparse.ArgumentParser(description="オデカケ予定を追加")
    parser.add_argument("--type", choices=["club", "gathered"], help="種別")
    parser.add_argument("--title", help="ツアー名")
    parser.add_argument("--date", type=validate_date, help="開催日 YYYY-MM-DD")
    parser.add_argument("--deadline", type=validate_date, help="締切日 YYYY-MM-DD")
    parser.add_argument("--capacity", type=int, help="定員")
    parser.add_argument("--current", type=int, default=0, help="現在の申込人数（gatheredのみ）")
    parser.add_argument("--fee", help="参加費")
    parser.add_argument("--location", help="行き先")
    parser.add_argument("--image", help="画像URL or images/xxx.jpg")
    parser.add_argument("--description", help="説明")
    parser.add_argument("--id", help="ID（指定しない場合は自動生成）")
    args = parser.parse_args()

    # 引数が一つもなければ対話モード
    if not args.title:
        params = prompt_interactive()
    else:
        required = ["type", "title", "date", "deadline", "capacity", "fee", "location", "image", "description"]
        missing = [k for k in required if not getattr(args, k)]
        if missing:
            print(f"❌ 不足引数: {', '.join('--' + k for k in missing)}")
            sys.exit(1)
        params = {
            "type": args.type, "title": args.title, "date": args.date,
            "deadline": args.deadline, "capacity": args.capacity,
            "current": args.current, "fee": args.fee, "location": args.location,
            "image": args.image, "description": args.description
        }

    data = load_events()
    events = data.get("events", [])

    # ID生成
    new_id = args.id if args.id else generate_id(events, params["type"], params["date"])

    new_event = {
        "id": new_id,
        "type": params["type"],
        "title": params["title"],
        "date": params["date"],
        "deadline": params["deadline"],
        "capacity": params["capacity"],
        "fee": params["fee"],
        "location": params["location"],
        "image": params["image"],
        "description": params["description"],
    }
    if params["type"] == "gathered":
        new_event["current"] = params.get("current", 0)

    events.append(new_event)
    data["events"] = events
    save_events(data)

    print()
    print(f"✓ 追加完了: {new_id}")
    print(f"  {params['title']} / {params['date']} / 定員{params['capacity']}名")
    print()
    print("次のステップ:")
    print(f"  1. 画像を images/ に配置（{params['image']}）")
    print(f"  2. git add -A && git commit -m 'add event {new_id}' && git push")
    print(f"  3. 数十秒で本番反映")


if __name__ == "__main__":
    main()
