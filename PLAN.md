# PLAN.md

このファイルは podmix の実装状況と将来拡張の記録です。
プロジェクトの不変仕様 (時間軸の編集フロー、パラメータ、CLI、対応フォーマット等) は `CLAUDE.md` を参照してください。

## MVP 完了 (Phase 0–4)

podmix の MVP は完了済みです。Phase 0 (scaffolding) から Phase 4 (実音源での E2E 検証) までがすべて main にマージ済みで、テスト 59 本が全てパスしています。現在のコードベースは voice/BGM/outro の 3 トラックミキシング、BGM↔outro クロスフェード、outro オーバーレイ、パラメータ調整 (CLI / TOML)、WAV/MP3 入出力のすべてに対応しています。実装の詳細はソースコード (`src/podmix/`) を参照してください。

## 将来拡張の候補

### auto-ducking (voice 検出による BGM 自動減衰)

現在は BGM を一定の gain で減衰していますが、将来的に voice 区間を検出して BGM を自動で ducking (一時的な減衰) させることで、より自然なミックスが可能になります。この機能は以下の技術スタックが前提となります:

- **pedalboard** または **numpy** — 音声信号処理による voice 区間検出 (音量エンベロープ解析)
- pydub の高レベル API では実装困難なため、wav データを直接操作する必要がある

実装時は既存の `mixer.build_episode` とは独立した関数として設計し、CLI で `--auto-duck` フラグで選択可能にする想定です。
