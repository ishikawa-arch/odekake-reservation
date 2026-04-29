# オデカケ予約 (Odekake Reservation)

ODEKAKE（おもちまん株式会社）のお出かけ予約ページ。WordPress（o-dekake.com）に iframe で埋め込み、本体は GitHub Pages で公開する構成。

## 全体構成

```
[ o-dekake.com (WordPress) ]
   │ メニュー: オデカケ予約 ▼
   │   ├─ オデカケ倶楽部     → /reservation/?type=club
   │   ├─ オーダーメイド      → /reservation/?type=order
   │   └─ 集まったら開催      → /reservation/?type=gathered
   │
   └─ 固定ページ /reservation/ には iframe を埋め込み
        │
        ▼
[ ishikawa-arch.github.io/odekake-reservation/ ]   ← このリポジトリ
   ├─ index.html
   ├─ data/events.json   ← ここを編集すると即時反映
   └─ images/            ← お出かけの写真
```

## ディレクトリ構成

```
odekake-reservation/
├── index.html               予約ページ本体（タブUI）
├── data/
│   └── events.json          予定データ（編集対象）
├── images/                  お出かけの写真
├── scripts/
│   ├── wp_setup.py          WordPress固定ページ＋メニュー自動セットアップ
│   └── add_event.py         予定追加CLI（Claude Codeから呼ぶ）
├── .env.example             環境変数のテンプレ
├── .gitignore
└── README.md
```

## 初回セットアップ

### 1. このリポジトリを公開

```bash
gh repo create ishikawa-arch/odekake-reservation --public --source=. --push
```

GitHub Pages を有効化（Settings > Pages > Source: `main` / `/(root)`）。

### 2. WordPress側の設定

#### (a) アプリケーションパスワードの発行（1回だけ手動）

1. WordPress管理画面にログイン
2. ユーザー > プロフィール画面の下部 → 「新しいアプリケーションパスワード名」に `claude-code` と入力
3. 「新しいアプリケーションパスワードを追加」をクリック
4. 表示されたパスワード（半角スペース込み）をコピー

#### (b) `.env` を作成

```bash
cp .env.example .env
# .env を編集して以下を記入
# WP_BASE_URL=https://o-dekake.com
# WP_USERNAME=（管理者ユーザー名）
# WP_APP_PASSWORD=（さっきコピーしたパスワード）
# GH_PAGES_URL=https://ishikawa-arch.github.io/odekake-reservation/
```

#### (c) セットアップスクリプトの実行

```bash
pip install requests python-dotenv --break-system-packages

# 動作確認（書き込まない）
python scripts/wp_setup.py --dry-run

# 本番実行
python scripts/wp_setup.py
```

これにより以下が自動で行われます：
- 固定ページ「オデカケ予約」（slug: `reservation`）を作成、iframe を埋め込み
- メニューに「オデカケ予約」親 + 子3つを追加

#### (d) メニュー並び順の調整（手動）

新規追加項目はメニューの最後に配置されます。WordPress管理画面（外観 > メニュー）で「サービス」と「オデカケ記録」の間にドラッグして移動してください。

## 日常運用：予定の追加

### Claude Code に頼む場合

> 「5月25日のオデカケ倶楽部に犬山城下町ツアーを追加して。定員6名、参加費8,200円〜、写真は ~/Downloads/inuyama.jpg」

Claude Code は以下を実行：
1. 画像を `images/club-2026-05-03.jpg` にコピー
2. `python scripts/add_event.py --type club --title "..." --date 2026-05-25 ...` で events.json に追記
3. `git add -A && git commit -m "..." && git push`

### 手動の場合

```bash
# 対話モード
python scripts/add_event.py

# 引数モード
python scripts/add_event.py \
  --type club \
  --title "春の桜と老舗うなぎの旅" \
  --date 2026-05-25 \
  --deadline 2026-05-18 \
  --capacity 6 \
  --fee "8,200円〜" \
  --location "犬山市" \
  --image images/club-2026-05-03.jpg \
  --description "犬山城下町を散策し、老舗のうなぎを"
```

`type` は `club` または `gathered`。`gathered` のときは `--current 0` で現在の申込人数を指定。

## 申込フォームの差し替え

`index.html` の冒頭のスクリプト内に下記の変数があります：

```javascript
const APPLY_FORM_URL = ""; // 後で申込フォームURLを入れる
```

ここに Googleフォーム等のURLを入れると、各カードの「申し込む」ボタンが `URL + イベントID` に飛ぶようになります（イベント特定用にIDが付与される）。空のままだと「お問い合わせから申込」（既存のcontactページ）にフォールバックします。

## 主な仕様

- **タブ初期化**: URLクエリ `?type=club|order|gathered` で初期表示タブを指定
- **月別フィルタ**: クラブタブのみ。`events.json` 内のデータから自動生成
- **進捗バー**: gathered（集まったら開催）でのみ表示。`current / capacity` から自動計算
- **画像**: `images/xxx.jpg` の相対パス、または外部URL（既存のWordPressメディアURL等）どちらもOK
