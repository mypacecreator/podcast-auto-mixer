# PLAN.md

このファイルは podmix の **実装ロードマップとモジュール設計詳細** をまとめたものです。
プロジェクトの不変仕様 (時間軸の編集フロー、パラメータ、CLI、対応フォーマット等) は `CLAUDE.md` を参照してください。

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
- `build_episode(voice, bgm, outro, *, voice_start_ms=1500, outro_tail_ms=3000, bgm_outro_crossfade_ms=2000, bgm_gain_db=-12.0) -> AudioSegment` — コア関数。
  - **前提条件**: `len(outro) > outro_tail_ms`。Audition 運用では outro は固定長 (10〜20 秒) で常に満たします。違反時は `ValueError("outro must be longer than outro_tail_ms")` を送出して即座に異常終了します (これにより `outro_start_ms >= voice_end` となるケース、すなわち outro が voice 末尾に重ならず append 同然になる状態を排除します)。
  - 処理ステップ:
    1. `total_ms = voice_start_ms + len(voice) + outro_tail_ms`
    2. `outro_start_ms = total_ms - len(outro)`
    3. ガード: `outro_start_ms < voice_start_ms + bgm_outro_crossfade_ms` なら警告 (voice が極端に短いケース)
    4. BGM を `outro_start_ms + bgm_outro_crossfade_ms` の長さまで `loop_to_length` で伸ばす
    5. BGM の末尾 `bgm_outro_crossfade_ms` に `fade_out`、outro の冒頭 `bgm_outro_crossfade_ms` に `fade_in` を適用
    6. 空キャンバス (長さ = `total_ms`) を作り `bgm + bgm_gain_db` を 0 / `voice` を `voice_start_ms` / `outro` を `outro_start_ms` に overlay

### `src/podmix/cli.py`

- `main(argv=None) -> int` — argparse で引数を受け、`audio_io.load_audio` → `mixer.build_episode` → `audio_io.export_audio`。秒指定の引数 (`--voice-start` / `--outro-tail` / `--bgm-outro-crossfade`) は `int(round(value * 1000))` で ms に変換してから `MixConfig` に渡す。

### `src/podmix/config.py`

- `@dataclass(frozen=True) class MixConfig` — 全パラメータをデフォルト値付きで保持。
- `load_config(path: Path | None) -> MixConfig` — `tomllib` で読み込み (Python 3.11 標準)。
