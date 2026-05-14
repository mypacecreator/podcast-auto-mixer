# CLAUDE.md

このファイルは Claude Code が本リポジトリで作業する際に参照する記憶用ドキュメントです。
プロジェクトの不変仕様（憲法）のみを記載しています。

## Gitとブランチ操作

- **メインブランチへの直接反映の禁止:** ローカル作業時は、新規ブランチを切り、作業を開始してください。メインブランチへの適用時は、プルリクエストの作成を必須とします。
- **状態の確認:** 作業を開始する前やコミットする前は、現在のブランチの状態（`git status`, `git diff`）を必ず確認してください。

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

## パラメータ仕様と単位規約

### 組み込みデフォルト値（config.py 定義）

| パラメータ | デフォルト | 説明 |
|---|---|---|
| `voice_start_ms` | 1500 | BGM 開始から voice 開始までの遅延 (BGM 先行時間) |
| `outro_tail_ms` | 3000 | voice 終了後、outro 単独で流れる時間 |
| `bgm_outro_crossfade_ms` | 2000 | BGM↔outro クロスフェード長 |
| `voice_gain_db` | 0.0 | Voice の音量調整 |
| `bgm_gain_db` | -18.0 | BGM の音量調整 |
| `outro_gain_db` | -6.0 | Outro の音量調整 |
| `sample_rate` | 48000 | 出力サンプリングレート |
| `channels` | 2 | 出力チャンネル数 |
| `output_bitrate` | "192k" | MP3 出力ビットレート (例: "128k" / "192k" / "256k") |

すべて `config/default.toml` と CLI 引数で上書き可能です。

### 単位の規約

- **内部パラメータ** (`MixConfig` 及び表中の `_ms` 接尾辞): 整数の **ミリ秒**
- **CLI 引数** (`--voice-start` / `--outro-tail` / `--bgm-outro-crossfade`): **秒 (float)** で受け取り、`cli.main` の冒頭で `int(round(value * 1000))` により ms へ変換して `MixConfig` に渡す
- **gain 系** (`--voice-gain` / `--bgm-gain` / `--outro-gain`): **dB (float)**
- **bitrate** (`--bitrate`): **文字列** (例: `"192k"`)

## 設計メモ

- アウトロは単純 append ではなく **overlay** で voice 末尾に重ねる (Audition での手作業を再現)
- BGM↔outro クロスフェード長は将来調整しやすいよう独立パラメータ化 (`bgm_outro_crossfade_ms`)
- auto-ducking は MVP スコープ外。将来 `pedalboard` / `numpy` への部分置換も検討可能な構造とする
