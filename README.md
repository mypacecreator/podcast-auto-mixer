# podcast-auto-mixer (`podmix`)

`podmix` は、ポッドキャストの voice 音源に BGM とアウトロを自動でミックスする Python 製の CLI ツールです。これまで Adobe Audition で手作業していたエピソードのミキシング工程を 1 コマンドで再現することを目的としています。

MVP では voice の有無に応じて BGM を自動で減衰させる **auto-ducking は実装しません**。BGM は `--bgm-gain` で指定した一定の相対音量で voice と並走します。

## 主な機能

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
│   └── ep001.wav        ← ここに収録音声を置く
├── bgm/
│   └── lofi.mp3         ← ここに BGM を置く
└── outro/
    └── outro.wav        ← ここにアウトロを置く
```

## 使い方

### クイックスタート

```bash
# 1. 音源を配置したら、ミックスを実行
podmix \
  --voice  audio/voice/ep001.wav \
  --bgm    audio/bgm/lofi.mp3 \
  --outro  audio/outro/outro.wav \
  --output output/ep001.mp3

# 2. output/ep001.mp3 が生成されます
```

出力ファイルは `output/` フォルダに自動作成されます。

### コマンドオプション

主なオプション:

| オプション | 単位 | デフォルト | 説明 |
|---|---|---|---|
| `--voice-start` | 秒 (float) | 1.5 | BGM 開始から voice 開始までの先行時間 |
| `--outro-tail` | 秒 (float) | 3.0 | voice 終了後、アウトロ単独で流れる長さ |
| `--bgm-outro-crossfade` | 秒 (float) | 2.0 | BGM ↔ アウトロのクロスフェード長 |
| `--bgm-gain` | dB | -12.0 | BGM の相対音量 (voice 基準、負の値が通常) |
| `--bitrate` | 文字列 | `192k` | MP3 出力ビットレート (例: `128k` / `192k` / `256k`) |
| `--config` | パス | (なし) | デフォルト値を上書きする TOML 設定ファイル |

入出力は拡張子 (`.wav` / `.mp3`) で自動判別されます。

## 設定ファイル

リポジトリ同梱の `config/default.toml` でデフォルト値をまとめて変更できます。

```toml
# config/default.toml
voice_start_ms        = 1500   # BGM 先行時間 (ミリ秒)
outro_tail_ms         = 3000   # voice 後のアウトロ余韻 (ミリ秒)
bgm_outro_crossfade_ms = 2000  # BGM↔アウトロ クロスフェード (ミリ秒)
bgm_gain_db           = -12.0  # BGM 音量 (dB、負の値で減衰)
sample_rate           = 48000  # 出力サンプリングレート (Hz)
channels              = 2      # 出力チャンネル数 (1=モノラル / 2=ステレオ)
output_bitrate        = "192k" # MP3 出力ビットレート
```

設定ファイルを使って実行する場合:

```bash
podmix \
  --voice  audio/voice/ep001.wav \
  --bgm    audio/bgm/lofi.mp3 \
  --outro  audio/outro/outro.wav \
  --output output/ep001.mp3 \
  --config config/default.toml
```

CLI オプションは設定ファイルより優先されます (CLI > TOML > 組み込みデフォルト)。

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

詳細仕様 (時間軸の編集フロー、パラメータの内部単位、CLI 設計の背景など) は [`CLAUDE.md`](./CLAUDE.md) を、フェーズ別の実装ロードマップとモジュール設計の詳細は [`PLAN.md`](./PLAN.md) を参照してください。

## ライセンス

TBD
