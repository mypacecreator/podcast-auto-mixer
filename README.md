# podcast-auto-mixer (`podmix`)

`podmix` は、ポッドキャストの voice 音源に BGM とアウトロを自動でミックスする Python 製の CLI ツールです。これまで Adobe Audition で手作業していたエピソードのミキシング工程を 1 コマンドで再現することを目的としています。

**注:** BGM の音量は最初から最後まで一定です。voice の有無に応じて BGM を自動で減衰させる auto-ducking 機能は実装していません。

## 主な機能

- **シングルファイル処理**: 個別のエピソードを指定してミックス
- **バッチ処理**: `audio/voice/` 内の全 WAV/MP3 ファイルを一括処理
- BGM を voice より先に開始 (デフォルト 1.5 秒先行)
- BGM ループを voice と並走させ、voice の末尾でアウトロにクロスフェード
- アウトロ音源を voice 末尾に **オーバーレイ** (単純な append ではなく、voice 終了後にアウトロ末尾の余韻 `outro_tail_ms` だけが単独で残る)
- 入力 WAV / MP3 両対応、出力は MP3 (デフォルト 192kbps) または WAV

## 必要環境

- Python 3.11 以上 (3.13 / 3.14 も対応済み — `audioop-lts` が自動インストールされます)
- [ffmpeg](https://ffmpeg.org/) (pydub のバックエンド)

## インストール

```bash
# 1. ffmpeg をインストール
#    Linux (apt)
sudo apt update && sudo apt install -y ffmpeg
#    macOS (Homebrew)
brew install ffmpeg
#    Windows (Chocolatey)
choco install ffmpeg

# 2. リポジトリ取得 & 仮想環境
git clone <this-repo-url>
cd podcast-auto-mixer
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. パッケージを editable インストール
pip install -e ".[dev]"
```

インストール後、`podmix --help` でヘルプが表示されることを確認してください。

### トラブルシューティング: `podmix: command not found`

`podmix` は `pip install -e ".[dev]"` で作成される CLI エントリポイントです。
このエラーは多くの場合、**仮想環境 (`.venv`) が有効化されていない**か、**シェルの `PATH` が上書きされている**ことが原因です。

確認:

```bash
echo $SHELL
which -a podmix
python3 -m pip show podmix
```

復旧 (推奨):

```bash
cd /path/to/podcast-auto-mixer
source .venv/bin/activate
podmix --help
```

`.venv` が未作成・破損している場合:

```bash
cd /path/to/podcast-auto-mixer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
podmix --help
```

補足:

- `.zshrc` で `export PATH="..."` と書くと既存 `PATH` を潰すことがあります。通常は `export PATH="/some/path:$PATH"` のように追記してください。
- 一時的な回避としては `python -m podmix --help` でも実行できます。

## 音源の準備

3 種類の音源を用意し、リポジトリ内の対応フォルダに配置します。

| 役割 | 配置フォルダ | 内容 | 制約 |
|---|---|---|---|
| voice | `audio/voice/` | 収録済みのエピソード音声 | なし |
| bgm | `audio/bgm/` | BGM ループ素材 | なし (短くても自動でループ) |
| outro | `audio/outro/` | エンディングジングル | ファイル長 > `outro_tail` (デフォルト 3 秒) かつ > `bgm_outro_crossfade` (デフォルト 2 秒) |

対応フォーマット: WAV / MP3 いずれも可。ファイル名は任意です。

```
audio/
├── voice/
│   ├── ep001.wav        ← ここに収録音声を置く
│   ├── ep002.wav        ← 複数ファイルを置くとバッチ処理可能
│   └── ep003.mp3        ← WAV と MP3 混在も可
├── bgm/
│   └── lofi.mp3         ← ここに BGM を置く
└── outro/
    └── outro.wav        ← ここにアウトロを置く
```

## 使い方

### クイックスタート

**シングルファイル処理** (個別のエピソードを処理):

```bash
# デフォルトの BGM/outro を使う場合 (最もシンプル)
podmix --voice audio/voice/ep001.wav

# 出力は output/ep001_mixed.mp3 として自動生成されます
```

**バッチ処理** (`audio/voice/` 内の全ファイルを一括処理):

```bash
# --voice を省略すると、audio/voice/ 内の全 WAV/MP3 を自動処理
podmix --bgm audio/bgm/lofi.mp3 --outro audio/outro/outro.wav

# 各ファイルは output/{ファイル名}_mixed.mp3 として出力されます
# 例: ep001.wav → output/ep001_mixed.mp3
#     ep002.mp3 → output/ep002_mixed.mp3
```

`--bgm` / `--outro` / `--output` は省略可能です:
- `--bgm` を省略 → `config/default.toml` の `default_bgm` を使用 (デフォルト: `audio/bgm/bgm_main.wav`)
- `--outro` を省略 → `config/default.toml` の `default_outro` を使用 (デフォルト: `audio/outro/bgm_end.wav`)
- `--output` を省略 → `output/{voice_stem}_mixed.mp3` として自動生成 (バッチモードでは無視されます)

別の BGM やアウトロを使う場合:

```bash
podmix \
  --voice  audio/voice/ep001.wav \
  --bgm    audio/bgm/special.mp3 \
  --outro  audio/outro/special.wav \
  --output output/ep001_special.mp3
```

### コマンドオプション

主なオプション:

| オプション | 単位 | デフォルト | 説明 |
|---|---|---|---|
| `--voice` | パス | (任意) | Voice 音源ファイル (WAV/MP3)。省略時は `audio/voice/` 内の全ファイルをバッチ処理 |
| `--bgm` | パス | `audio/bgm/bgm_main.wav` | BGM 音源ファイル (WAV/MP3) |
| `--outro` | パス | `audio/outro/bgm_end.wav` | Outro 音源ファイル (WAV/MP3) |
| `--output` | パス | `output/{voice_stem}_mixed.mp3` | 出力ファイル (WAV/MP3) |
| `--voice-start` | 秒 (float) | 1.5 | BGM 開始から voice 開始までの先行時間 |
| `--outro-tail` | 秒 (float) | 3.0 | voice 終了後、アウトロ単独で流れる長さ |
| `--bgm-outro-crossfade` | 秒 (float) | 2.0 | BGM ↔ アウトロのクロスフェード長 |
| `--voice-gain` | dB | 0.0 | Voice の音量調整 |
| `--bgm-gain` | dB | -18.0 | BGM の音量調整 |
| `--outro-gain` | dB | -6.0 | Outro の音量調整 |
| `--bitrate` | 文字列 | `192k` | MP3 出力ビットレート (例: `128k` / `192k` / `256k`) |
| `--config` | パス | (自動) | デフォルト値を上書きする TOML 設定ファイル |

入出力は拡張子 (`.wav` / `.mp3`) で自動判別されます。

## 音量調整ガイド

各音源の音量は dB (デシベル) 単位で調整できます:

- **`0 dB`**: 原音のまま (変更なし)
- **`-6 dB`**: 音量が約半分に
- **`-12 dB`**: 音量が約 1/4 に
- **`+6 dB`**: 音量が約 2 倍に

### 調整例

**BGM が大きすぎる場合:**
```bash
podmix --voice audio/voice/ep001.wav --bgm-gain -24
```

**voice が小さすぎる場合:**
```bash
podmix --voice audio/voice/ep001.wav --voice-gain 3
```

**全体のバランスを調整:**
```bash
podmix \
  --voice audio/voice/ep001.wav \
  --voice-gain 2 \
  --bgm-gain -20 \
  --outro-gain -8
```

デフォルト値 (voice: 0 dB / BGM: -18 dB / outro: -6 dB) は `config/default.toml` で変更できます。

## 設定ファイル

リポジトリ同梱の `config/default.toml` でデフォルト値をまとめて変更できます。

```toml
# config/default.toml
[paths]
# デフォルトの音源ファイルパス (CLI で省略時に使用)
default_bgm = "audio/bgm/bgm_main.wav"
default_outro = "audio/outro/bgm_end.wav"

[mix]
# ミックスパラメータ (ミリ秒)
voice_start_ms = 1500          # BGM 先行時間
outro_tail_ms = 3000           # voice 後のアウトロ余韻
bgm_outro_crossfade_ms = 2000  # BGM↔アウトロ クロスフェード

# 音量調整 (dB): 0 = 原音、負 = 減衰、正 = 増幅
voice_gain_db = 0.0
bgm_gain_db = -18.0
outro_gain_db = -6.0

[output]
# 出力パラメータ
sample_rate = 48000     # 出力サンプリングレート (Hz)
channels = 2            # 出力チャンネル数 (1=モノラル / 2=ステレオ)
output_bitrate = "192k" # MP3 出力ビットレート
```

設定ファイルを使って実行する場合:

```bash
podmix --voice audio/voice/ep001.wav --config config/default.toml
```

### config 読み込みの優先順位

優先順位: **CLI > TOML > 組み込みデフォルト**

`--config` を省略した場合、カレントディレクトリから見た `./config/default.toml` が存在すれば自動的に読み込まれます。ファイルが存在しない場合は組み込みデフォルト値が使用されます。

> **注意**: 自動読み込みで参照されるのは、実行時のカレントディレクトリ基準の `./config/default.toml` です。たとえばリポジトリのサブディレクトリから実行した場合、その場所に `./config/default.toml` が存在しなければ見つからず、組み込みデフォルトが適用されます。逆に、リポジトリルート以外でも同じ相対パスにファイルがあれば自動読み込みされます。

## 開発

```bash
# テスト実行
pytest
```

リポジトリの構成:

```
src/podmix/   ライブラリ本体 (audio_io / mixer / cli / config)
tests/        pytest テストとフィクスチャ
audio/        入力音源置き場 (voice / bgm / outro)
output/       生成された MP3 / WAV の出力先
config/       デフォルト設定 TOML
```

## 技術スタック

- **Python 3.11+** (`tomllib` 標準ライブラリ利用のため)
- **pydub** — `AudioSegment` の `overlay` / `*` / `fade_in/fade_out` で要件実装
- **audioop-lts** — Python 3.13+ 向け `audioop` バックポート (pydub の内部依存)
- **ffmpeg** — pydub のバックエンド (システムにインストール必須)
- **pytest** — テストフレームワーク

詳細な設計背景や時間軸の導出式は [`CLAUDE.md`](./CLAUDE.md) を、実装状況と将来拡張の記録は [`PLAN.md`](./PLAN.md) を参照してください。

## ライセンス

TBD
