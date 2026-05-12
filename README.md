# podcast-auto-mixer (`podmix`)

`podmix` は、ポッドキャストの voice 音源に BGM とアウトロを自動でミックスする Python 製の CLI ツールです。これまで Adobe Audition で手作業していたエピソードのミキシング工程を 1 コマンドで再現することを目的としています。

MVP では voice の有無に応じて BGM を自動で減衰させる **auto-ducking は実装しません**。BGM は `--bgm-gain` で指定した一定の相対音量で voice と並走します。

## 主な機能

- BGM を voice より先に開始 (デフォルト 1.5 秒先行)
- BGM ループを voice と並走させ、voice の末尾でアウトロにクロスフェード
- アウトロ音源を voice 末尾に **オーバーレイ** (単純な append ではなく、voice 終了後にアウトロ末尾の余韻 `outro_tail_ms` だけが単独で残る)
- 入力 WAV / MP3 両対応、出力は MP3 (デフォルト 192kbps) または WAV

## 必要環境

- Python 3.11 以上
- [ffmpeg](https://ffmpeg.org/) (pydub のバックエンド)

## インストール

```bash
# 1. ffmpeg (Linux)
sudo apt update && sudo apt install -y ffmpeg

# 2. リポジトリ取得 & 仮想環境
git clone <this-repo-url>
cd podcast-auto-mixer
python3 -m venv .venv
source .venv/bin/activate

# 3. パッケージを editable インストール
pip install -e ".[dev]"
```

インストール後、`podmix --help` でヘルプが表示されることを確認してください (Phase 3 以降で動作)。

## 使い方

```bash
podmix \
  --voice  audio/voice/ep001.wav \
  --bgm    audio/bgm/lofi.mp3 \
  --outro  audio/outro/standard.wav \
  --output output/ep001.mp3
```

主なオプション:

| オプション | 単位 | デフォルト | 説明 |
|---|---|---|---|
| `--voice-start` | 秒 (float) | 1.5 | BGM 開始から voice 開始までの先行時間 |
| `--outro-tail` | 秒 (float) | 3.0 | voice 終了後、アウトロ単独で流れる長さ |
| `--bgm-outro-crossfade` | 秒 (float) | 2.0 | BGM ↔ アウトロのクロスフェード長 |
| `--bgm-gain` | dB | -12.0 | BGM の相対音量 (voice 基準) |
| `--bitrate` | 文字列 | `192k` | MP3 出力ビットレート (例: `128k` / `192k` / `256k`) |
| `--config` | パス | (なし) | デフォルト値を上書きする TOML 設定ファイル |

入出力は拡張子 (`.wav` / `.mp3`) で自動判別されます。

## 設定ファイル

CLI 引数で個別に上書きする代わりに、`config/default.toml` 形式の TOML ファイルでデフォルト値をまとめて変更できます。リポジトリ同梱の [`config/default.toml`](./config/default.toml) を参考にしてください。

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
