# CLAUDE.md

このファイルは Claude Code が本リポジトリで作業する際に参照する記憶用ドキュメントです。
プロジェクトの不変仕様 (憲法) のみを記載しています。

## Gitとブランチ操作

- **メインブランチへの直接反映の禁止:** ローカル作業時は、新規ブランチを切り、作業を開始してください。メインブランチへの適用時は、プルリクエストの作成を必須とします。
- **状態の確認:** 作業を開始する前やコミットする前は、現在のブランチの状態（`git status`, `git diff`）を必ず確認してください。

## プロジェクト概要

`podmix` は、ポッドキャスト音源 (voice) に BGM とアウトロをミックスする Python CLI ツールです。現状ユーザーが Adobe Audition で手作業しているミキシング工程を自動化し、エピソードごとの作業時間を短縮することを目的とします。

## 実際の編集フロー

アウトロは単純に末尾に append するのではなく、voice の末尾に重ねて配置します:

- BGM を voice より先に開始 (デフォルト 1.5 秒先行)
- BGM ループを voice と並走させる
- アウトロ音源 (固定長) を voice の末尾に重ねて配置
- voice 終了後、アウトロが `outro_tail_ms` 分だけ単独で残響的に流れる
- BGM ループは voice と並走し、outro 開始位置でクロスフェードして outro に引き継ぐ

時間軸:

```
時刻:        0    voice_start             outro_start    voice_end          end
bgm    : ████████████████████████████████████\(xfade)
voice  :          ████████████████████████████████████████████████|
outro  :                                  (xfade)/████████████████████████████|
                                             |←──── T_outro ────→|
                                             ↑                   ↑           ↑
                                       outro_start          voice ends    outro ends
```

導出式:

- voice 配置位置 = `voice_start_ms` (BGM が先行する時間、デフォルト 1500ms)
- voice 終了時刻 = `voice_start_ms + T_voice`
- 出力全長 = `voice_start_ms + T_voice + outro_tail_ms`
- `outro_start_ms = voice_start_ms + T_voice + outro_tail_ms - T_outro`
- BGM は 0 から始まり、`outro_start_ms + bgm_outro_crossfade_ms` まで継続

## MVP 機能 (auto-ducking はスコープ外)

1. BGM を voice より先に開始 (デフォルト 1.5 秒先行、パラメータで変更可)
2. BGM ループを voice と並走させ、適切な位置で outro にクロスフェード
3. outro を voice 末尾に重ねて配置 (outro_tail_ms 分だけ余韻が残る)
4. BGM↔outro 間にクロスフェードを適用 (デフォルト 2 秒、パラメータで変更可)

auto-ducking (voice 検出による BGM 自動減衰) は将来拡張とし、本 MVP では実装しません。

## 対応フォーマット

- **入力**: WAV / MP3 (voice / bgm / outro いずれも両対応)
- **出力**: MP3 (デフォルト 192kbps) または WAV
- pydub は内部で ffmpeg を呼ぶため、拡張子で自動判別 (`AudioSegment.from_file`)

## 技術スタック

- Python 3.11+ (`tomllib` 標準ライブラリ利用のため)
- [pydub](https://github.com/jiaaro/pydub) — `AudioSegment` の `overlay` / `*` / `fade_in/fade_out` がそのまま要件に対応
- [audioop-lts](https://pypi.org/project/audioop-lts/) — Python 3.13+ 向け `audioop` バックポート (pydub の内部依存)
- ffmpeg — pydub のバックエンド (システムにインストール必須)
- argparse — CLI 引数解析 (標準ライブラリ)
- pytest — テスト

## ディレクトリ構造

パス表記はリポジトリルートを `<repo-root>` と置く相対構成です。

```
<repo-root>/
├── README.md
├── CLAUDE.md
├── PLAN.md
├── pyproject.toml
├── .gitignore
├── config/default.toml
├── src/podmix/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── mixer.py
│   ├── audio_io.py
│   └── config.py
├── tests/
│   ├── __init__.py
│   ├── fixtures/.gitkeep
│   ├── test_audio_io.py
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_e2e_real_audio.py
│   └── test_mixer.py
├── audio/{voice,bgm,outro}/.gitkeep
└── output/.gitkeep
```

## パラメータ仕様

| パラメータ | デフォルト | 説明 |
|---|---|---|
| `voice_start_ms` | 1500 | BGM 開始から voice 開始までの遅延 (BGM 先行時間) |
| `outro_tail_ms` | 3000 | voice 終了後、outro 単独で流れる時間 |
| `bgm_outro_crossfade_ms` | 2000 | BGM↔outro クロスフェード長 |
| `bgm_gain_db` | -12.0 | BGM の音量減衰 (voice に対する相対値) |
| `sample_rate` | 48000 | 出力サンプリングレート |
| `channels` | 2 | 出力チャンネル数 |
| `output_bitrate` | "192k" | MP3 出力ビットレート (例: "128k" / "192k" / "256k") |

すべて `config/default.toml` と CLI 引数 (`--voice-start`, `--outro-tail`, `--bgm-outro-crossfade`, `--bgm-gain`, `--bitrate` 等) の両方で上書き可能です。

**単位の規約**: 内部パラメータ (`MixConfig` 及び表中の `_ms` 接尾辞) は整数の **ミリ秒** で保持します。CLI 引数 `--voice-start` / `--outro-tail` / `--bgm-outro-crossfade` は人間が扱いやすい **秒 (float)** で受け取り、`cli.main` の冒頭で `int(round(value * 1000))` により ms へ変換して `MixConfig` に渡します。`--bgm-gain` は dB、`--bitrate` は文字列 (例: `"192k"`) でそのまま渡します。

## CLI 仕様

```
podmix \
  --voice  audio/voice/ep001.wav      # WAV or MP3
  --bgm    audio/bgm/lofi.mp3         # WAV or MP3
  --outro  audio/outro/standard.wav   # WAV or MP3
  --output output/ep001.mp3           # MP3 (推奨), WAV も可
  [--voice-start 1.5] \               # 秒 (BGM が voice より先行する時間)
  [--outro-tail 3.0] \                # 秒 (voice 終了後 outro 単独で流れる長さ)
  [--bgm-outro-crossfade 2.0] \       # 秒 (BGM↔outro クロスフェード長)
  [--bgm-gain -12] \                  # dB (BGM の相対減衰量)
  [--bitrate 192k] \                  # MP3 出力ビットレート
  [--config config/default.toml]
```

数値引数の単位は明示します。`--voice-start` / `--outro-tail` / `--bgm-outro-crossfade` は **秒 (float)**、`--bgm-gain` は **dB**、`--bitrate` は **文字列**。argparse のヘルプ文にも単位を併記します。

## 開発コマンド

```bash
# 1. ffmpeg のインストール
# Linux:
sudo apt update && sudo apt install -y ffmpeg
# macOS:
brew install ffmpeg
# Windows:
choco install ffmpeg

# 2. Python venv の作成と依存インストール
cd "$(git rev-parse --show-toplevel)"
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 3. 動作確認
podmix --help

# 4. テスト実行
pytest
```

## 設計メモ

- アウトロは単純 append ではなく **overlay** で voice 末尾に重ねる (Audition での手作業を再現)
- BGM↔outro クロスフェード長は将来調整しやすいよう独立パラメータ化 (`bgm_outro_crossfade_ms`)
- auto-ducking は MVP スコープ外。将来 `pedalboard` / `numpy` への部分置換も検討可能な構造とする
