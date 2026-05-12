# CLAUDE.md

このファイルは Claude Code が本リポジトリで作業する際に参照する記憶用ドキュメントです。

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
- ffmpeg — pydub のバックエンド (システムにインストール必須)
- argparse — CLI 引数解析 (標準ライブラリ)
- pytest — テスト

## ディレクトリ構造 (予定)

```
/home/user/podcast-auto-mixer/
├── README.md
├── CLAUDE.md
├── pyproject.toml            # 次セッションで作成
├── .gitignore                # 次セッションで作成
├── config/default.toml       # 次セッションで作成
├── src/podmix/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                # Phase 3
│   ├── mixer.py              # Phase 2 (コア)
│   ├── audio_io.py           # Phase 1
│   └── config.py             # Phase 3
├── tests/
│   ├── __init__.py
│   └── fixtures/.gitkeep
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

## CLI 仕様

```
podmix \
  --voice  audio/voice/ep001.wav      # WAV or MP3
  --bgm    audio/bgm/lofi.mp3         # WAV or MP3
  --outro  audio/outro/standard.wav   # WAV or MP3
  --output output/ep001.mp3           # MP3 (推奨), WAV も可
  [--voice-start 1.5] \
  [--outro-tail 3.0] \
  [--bgm-outro-crossfade 2.0] \
  [--bgm-gain -12] \
  [--bitrate 192k] \
  [--config config/default.toml]
```

## 開発コマンド

```bash
# 1. ffmpeg のインストール (Linux)
sudo apt update && sudo apt install -y ffmpeg

# 2. Python venv の作成と依存インストール
cd /home/user/podcast-auto-mixer
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 3. 動作確認
podmix --help

# 4. テスト実行
pytest
```

## タスクロードマップ (MVP)

- **Phase 0**: scaffolding (`pyproject.toml`, `.gitignore`, `config/default.toml`, 空モジュール群)
- **Phase 1**: `audio_io.load_audio` / `export_audio` / `normalize_format`
- **Phase 2**: `mixer.loop_to_length` / `mixer.build_episode` (BGM↔outro クロスフェード + outro オーバーレイ込み)
- **Phase 3**: `cli.main` (argparse) + `config.load_config`
- **Phase 4**: 実音源で end-to-end 検証、Audition 出力と聴感比較

## モジュール設計メモ

### `src/podmix/audio_io.py`

- `load_audio(path: Path) -> AudioSegment` — 拡張子から `.wav` / `.mp3` を自動判別し `AudioSegment.from_file(path, format=...)` を呼ぶ。未対応拡張子はエラー。
- `export_audio(seg, path, *, bitrate="192k", sample_rate=48000) -> None` — 出力拡張子から format を決定。MP3 の場合は `bitrate` を指定。
- `normalize_format(seg, sample_rate, channels) -> AudioSegment` — `.set_frame_rate().set_channels().set_sample_width(2)` で全素材を揃える。

### `src/podmix/mixer.py`

- `loop_to_length(track, target_ms, fade_ms=50)` — `track * n` で繰り返し、端数 `track[:r]`、継ぎ目に微小フェードでクリック音回避。
- `build_episode(voice, bgm, outro, *, voice_start_ms=1500, outro_tail_ms=3000, bgm_outro_crossfade_ms=2000, bgm_gain_db=-12.0) -> AudioSegment` — コア関数:
  1. `total_ms = voice_start_ms + len(voice) + outro_tail_ms`
  2. `outro_start_ms = total_ms - len(outro)`
  3. ガード: `outro_start_ms < voice_start_ms + bgm_outro_crossfade_ms` なら警告
  4. BGM を `outro_start_ms + bgm_outro_crossfade_ms` の長さまで `loop_to_length` で伸ばす
  5. BGM の末尾 `bgm_outro_crossfade_ms` に `fade_out`、outro の冒頭 `bgm_outro_crossfade_ms` に `fade_in` を適用
  6. 空キャンバス (長さ = `total_ms`) を作り `bgm + bgm_gain_db` を 0 / `voice` を `voice_start_ms` / `outro` を `outro_start_ms` に overlay

### `src/podmix/cli.py`

- `main(argv=None) -> int` — argparse で引数を受け、`audio_io.load_audio` → `mixer.build_episode` → `audio_io.export_audio`。

### `src/podmix/config.py`

- `@dataclass(frozen=True) class MixConfig` — 全パラメータをデフォルト値付きで保持。
- `load_config(path: Path | None) -> MixConfig` — `tomllib` で読み込み (Python 3.11 標準)。

## 設計メモ

- アウトロは単純 append ではなく **overlay** で voice 末尾に重ねる (Audition での手作業を再現)
- BGM↔outro クロスフェード長は将来調整しやすいよう独立パラメータ化 (`bgm_outro_crossfade_ms`)
- auto-ducking は MVP スコープ外。将来 `pedalboard` / `numpy` への部分置換も検討可能な構造とする
