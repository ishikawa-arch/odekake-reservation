#!/usr/bin/env python3
"""
WordPress自動セットアップスクリプト
==========================================

o-dekake.com に「オデカケ予約」を組み込むための初期セットアップを実行します。

【何をやるか】
1. 固定ページ「オデカケ予約」（slug: reservation）を作成（既にあれば更新）
2. 既存のメニュー一覧を表示し、「オデカケ予約」親 + 子3つを追加
3. メニューの並び順は最後に手動で確認（既存の並び順を壊さないため）

【事前準備】
1. WordPressにログイン → ユーザー > プロフィール画面で
   「アプリケーションパスワード」を発行（名前: claude-code）
2. プロジェクトルートに .env を作成し、以下を記入:
   WP_BASE_URL=https://o-dekake.com
   WP_USERNAME=石川さんのユーザー名
   WP_APP_PASSWORD=発行されたアプリケーションパスワード（半角スペース込みでOK）
   GH_PAGES_URL=https://ishikawa-arch.github.io/odekake-reservation/
3. requirements: pip install requests python-dotenv

【実行】
   python scripts/wp_setup.py --dry-run     # 動作確認（書き込まない）
   python scripts/wp_setup.py               # 実行
"""

import argparse
import os
import sys
from pathlib import Path

try:
    import requests
    from dotenv import load_dotenv
except ImportError:
    print("requirements不足: pip install requests python-dotenv --break-system-packages")
    sys.exit(1)


# ============================================================
# 設定
# ============================================================

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

WP_BASE_URL = os.getenv("WP_BASE_URL", "").rstrip("/")
WP_USERNAME = os.getenv("WP_USERNAME", "")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD", "")
GH_PAGES_URL = os.getenv("GH_PAGES_URL", "https://ishikawa-arch.github.io/odekake-reservation/")

PAGE_SLUG = "reservation"
PAGE_TITLE = "オデカケ予約"

PAGE_CONTENT = f"""<!-- wp:html -->
<div style="margin: -20px -20px 0;">
<iframe id="odekake-reservation-frame" src="{GH_PAGES_URL}?type=club" style="width:100%; height:1900px; border:0; display:block;" title="オデカケ予約"></iframe>
<script>
(function() {{
  var valid = ['club', 'order', 'gathered'];
  var params = new URLSearchParams(window.location.search);
  var type = params.get('type');
  if (!valid.includes(type)) return;
  var url = '{GH_PAGES_URL}?type=' + type;
  var f = document.getElementById('odekake-reservation-frame');
  if (!f) return;
  f.src = url;
  if (f.dataset) f.dataset.src = url;
}})();
</script>
</div>
<!-- /wp:html -->
"""

# WordPressメニューに追加する親+子の構成
MENU_ITEMS = [
    {
        "title": "オデカケ予約",
        "description": "Reservation",
        "url": f"{WP_BASE_URL}/{PAGE_SLUG}/" if WP_BASE_URL else f"/{PAGE_SLUG}/",
        "type": "custom",  # 直接URLを指定
        "children": [
            {"title": "オデカケ倶楽部", "url": f"/{PAGE_SLUG}/?type=club"},
            {"title": "オーダーメイド", "url": f"/{PAGE_SLUG}/?type=order"},
            {"title": "集まったら開催", "url": f"/{PAGE_SLUG}/?type=gathered"},
        ],
    },
]


# ============================================================
# WordPress REST API クライアント
# ============================================================

class WPClient:
    def __init__(self, base_url, username, app_password):
        self.base = base_url.rstrip("/")
        self.auth = (username, app_password)
        self.api = f"{self.base}/wp-json/wp/v2"

    def _req(self, method, path, **kwargs):
        url = path if path.startswith("http") else f"{self.api}/{path}"
        r = requests.request(method, url, auth=self.auth, timeout=30, **kwargs)
        if r.status_code >= 400:
            print(f"  ⚠ {method} {url} -> {r.status_code}")
            print(f"    {r.text[:300]}")
            r.raise_for_status()
        return r.json() if r.text else None

    # --- Pages ---
    def find_page_by_slug(self, slug):
        results = self._req("GET", "pages", params={"slug": slug, "status": "publish,draft"})
        return results[0] if results else None

    def create_page(self, title, content, slug, status="publish"):
        return self._req("POST", "pages", json={
            "title": title, "content": content, "slug": slug, "status": status
        })

    def update_page(self, page_id, content):
        return self._req("POST", f"pages/{page_id}", json={"content": content})

    # --- Menus ---
    def list_menus(self):
        return self._req("GET", "menus")

    def list_menu_items(self, menu_id):
        return self._req("GET", "menu-items", params={"menus": menu_id, "per_page": 100})

    def create_menu_item(self, menu_id, title, url, parent=0, menu_order=999, item_type="custom", description=""):
        payload = {
            "title": title,
            "menus": menu_id,
            "parent": parent,
            "menu_order": menu_order,
            "type": item_type,
            "url": url,
            "status": "publish",
        }
        if description:
            payload["description"] = description
        return self._req("POST", "menu-items", json=payload)


# ============================================================
# メイン処理
# ============================================================

def check_env():
    missing = []
    if not WP_BASE_URL: missing.append("WP_BASE_URL")
    if not WP_USERNAME: missing.append("WP_USERNAME")
    if not WP_APP_PASSWORD: missing.append("WP_APP_PASSWORD")
    if missing:
        print(f"❌ .envに以下の設定が不足: {', '.join(missing)}")
        print(f"   .env.example をコピーして .env を作成してください。")
        sys.exit(1)


def setup_page(wp, dry_run=False):
    """固定ページの作成または更新"""
    print("─" * 60)
    print("▶ 固定ページのセットアップ")
    existing = wp.find_page_by_slug(PAGE_SLUG)
    if existing:
        print(f"  既存ページ発見: ID={existing['id']}, URL={existing['link']}")
        if dry_run:
            print(f"  [dry-run] 内容を更新する予定")
        else:
            wp.update_page(existing["id"], PAGE_CONTENT)
            print(f"  ✓ ページ内容を更新しました")
        return existing
    else:
        print(f"  新規作成: title='{PAGE_TITLE}', slug='{PAGE_SLUG}'")
        if dry_run:
            print(f"  [dry-run] 作成する予定")
            return None
        page = wp.create_page(PAGE_TITLE, PAGE_CONTENT, PAGE_SLUG)
        print(f"  ✓ 作成完了: ID={page['id']}, URL={page['link']}")
        return page


def setup_menu(wp, menu_ids=None, dry_run=False):
    """メニュー追加（複数メニュー対応）

    menu_ids: 対象メニューIDのリスト。未指定の場合はエラー終了する。
    """
    print("─" * 60)
    print("▶ メニューのセットアップ")
    menus = wp.list_menus()
    if not menus:
        print("  ⚠ メニューが見つかりません。先にWP管理画面でメニューを作成してください。")
        return

    print(f"  検出したメニュー（{len(menus)}件）:")
    for m in menus:
        print(f"    - id={m['id']}, name={m.get('name')}, slug={m.get('slug')}")

    if not menu_ids:
        print()
        print("❌ --menu-ids が未指定です。対象メニューIDをカンマ区切りで指定してください。")
        print(f"   例: --menu-ids 4,6")
        sys.exit(1)

    menus_by_id = {m["id"]: m for m in menus}
    invalid = [mid for mid in menu_ids if mid not in menus_by_id]
    if invalid:
        print(f"❌ 存在しないメニューID: {invalid}")
        sys.exit(1)

    targets = [menus_by_id[mid] for mid in menu_ids]
    print(f"\n  対象メニュー（{len(targets)}件）:")
    for t in targets:
        print(f"    - '{t.get('name')}' (id={t['id']})")

    for target in targets:
        print()
        print(f"━ メニュー '{target.get('name')}' (id={target['id']}) への追加 ━")
        existing_items = wp.list_menu_items(target["id"])
        existing_titles = {i.get("title", {}).get("rendered", "") if isinstance(i.get("title"), dict) else i.get("title", "") for i in existing_items}

        for parent_def in MENU_ITEMS:
            parent_title = parent_def["title"]
            if any(parent_title in t for t in existing_titles):
                print(f"  ◦ '{parent_title}' は既に追加済み（スキップ）")
                continue
            if dry_run:
                print(f"  [dry-run] 親メニュー '{parent_title}' を追加する予定")
                for c in parent_def["children"]:
                    print(f"    [dry-run] └─ '{c['title']}' (URL: {c['url']})")
                continue
            parent_item = wp.create_menu_item(
                menu_id=target["id"],
                title=parent_title,
                url=parent_def["url"],
                menu_order=999,
                description=parent_def.get("description", ""),
            )
            parent_id = parent_item["id"]
            print(f"  ✓ 親メニュー追加: '{parent_title}' (id={parent_id})")
            for i, c in enumerate(parent_def["children"], 1):
                child = wp.create_menu_item(
                    menu_id=target["id"],
                    title=c["title"],
                    url=c["url"],
                    parent=parent_id,
                    menu_order=i,
                    description=c.get("description", ""),
                )
                print(f"    └─ '{c['title']}' 追加 (id={child['id']})")

    print()
    print("  ⚠ 並び順について")
    print("    新規追加した項目はメニューの最後に配置されます。")
    print("    WP管理画面（外観 > メニュー）で「サービス」と「オデカケ記録」の間に")
    print("    手動でドラッグ移動してください（既存配置を壊さないため自動化しません）。")


def main():
    parser = argparse.ArgumentParser(description="WordPress オデカケ予約 セットアップ")
    parser.add_argument("--dry-run", action="store_true", help="書き込まずに動作確認のみ")
    parser.add_argument("--skip-menu", action="store_true", help="メニュー処理をスキップ")
    parser.add_argument("--skip-page", action="store_true", help="固定ページ処理をスキップ")
    parser.add_argument("--menu-ids", help="対象メニューIDをカンマ区切りで指定（例: 4,6）")
    args = parser.parse_args()

    check_env()

    menu_ids = None
    if args.menu_ids:
        try:
            menu_ids = [int(x.strip()) for x in args.menu_ids.split(",") if x.strip()]
        except ValueError:
            print(f"❌ --menu-ids の形式エラー: {args.menu_ids}（数値をカンマ区切りで指定）")
            sys.exit(1)

    print("=" * 60)
    print(f"  WordPress: {WP_BASE_URL}")
    print(f"  ユーザー: {WP_USERNAME}")
    print(f"  GitHub Pages URL: {GH_PAGES_URL}")
    print(f"  モード: {'dry-run（書き込みなし）' if args.dry_run else '本番実行'}")
    print("=" * 60)

    wp = WPClient(WP_BASE_URL, WP_USERNAME, WP_APP_PASSWORD)

    if not args.skip_page:
        setup_page(wp, dry_run=args.dry_run)
    if not args.skip_menu:
        setup_menu(wp, menu_ids=menu_ids, dry_run=args.dry_run)

    print("─" * 60)
    print("✓ 完了。WP管理画面で最終確認してください。")
    print(f"  確認URL: {WP_BASE_URL}/{PAGE_SLUG}/")


if __name__ == "__main__":
    main()
