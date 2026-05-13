# PLAN.md

このファイルは podmix の実装状況と将来拡張の記録です。
プロジェクトの不変仕様 (時間軸の編集フロー、パラメータ、CLI、対応フォーマット等) は `CLAUDE.md` を参照してください。

## MVP 完了

podmix の MVP は完了済みです。全テストがパスしています。現在のコードベースは voice/BGM/outro の 3 トラックミキシング、BGM↔outro クロスフェード、outro オーバーレイ、パラメータ調整 (CLI / TOML)、WAV/MP3 入出力、個別音量調整 (voice_gain_db / bgm_gain_db / outro_gain_db)、デフォルトパス・自動出力ファイル名・config 自動読み込みのすべてに対応しています。実装の詳細はソースコード (`src/podmix/`) を参照してください。

BGM の音量は最初から最後まで一定です。voice の有無に応じて BGM を自動で減衰させる auto-ducking 機能は、運用上不要なため実装していません。
