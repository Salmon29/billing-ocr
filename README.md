# ローカルAI-OCR・データ構造化システム — 開発仕様書

## 1. プロジェクト概要
外部クラウドサービス（Google Document AI 等）を使わず、ローカル環境（Python + GPU）ですべて完結するドキュメント解析パイプラインを構築する。画像（請求書、仕様書、手書き帳票 等）から AI を使って「構造化データ（JSON/CSV）」を抽出し、データベースへ永続化することを目的とする。

## 2. システム構成とロードマップ
ハードウェアリソースに応じて段階的にアーキテクチャを進化させる。

- Phase 1: MVP / プロトタイプ（現行）
    - 環境: NVIDIA GeForce GTX 1660Ti (VRAM 6GB)
    - 方式: Coordinate-Aware OCR Pipeline
    - 方針: VRAM 制約のため VLM を使わず、軽量 OCR と軽量 LLM を組み合わせる
    - 核心: OCR の座標情報を LLM に渡し、レイアウト（行・列の関係）を推論させる
    - 目的: パイプライン確立、データ整形ロジックの実証

- Phase 2: Production / 商用想定（将来）
    - 環境: High-End GPU（例: RTX 5090, VRAM 24GB+）
    - 方式: Hybrid Grounding Architecture（VLM + OCR）
    - 核心: VLM による画像理解と OCR の文字認識精度を組み合わせ、精度向上を図る

## 3. 技術スタック（Phase 1）
- 言語: Python 3.10+
- OCR: PaddleOCR (v4) — 日本語精度・座標検出が優れる
- LLM 実行環境: llama.cpp（python バインディング） — VRAM 6GB 前提で量子化・オフロードを利用
- 推論モデル: Qwen2.5-7B-Instruct (Int4) — 日本語性能・長文対応
- データ操作: pandas, SQLite

## 4. アーキテクチャ詳細設計

### 4.1 処理フロー（Data Pipeline）
1. Image Input: 画像読み込み  
2. OCR Processing (PaddleOCR): テキストとバウンディングボックス（座標）を抽出  
3. 前処理: 座標に基づき、人間が読む順（左上→右下）でソート  
4. Coordinate Injection (Prompt Engineering):  
     - テキスト単体ではなく "(y:100, x:50) 請求書" の形式で LLM に渡す  
     - LLM は Y 座標の近さで「同行」、X 座標の揃いで「同列」を推論可能  
5. LLM Inference (Structuring): プロンプト指示に従い、非構造化テキストを JSON に変換  
6. Post Processing: JSON 検証、欠損値処理  
7. Storage: SQLite に「生データ」と「整形済みデータ」を保存、必要に応じて CSV エクスポート

### 4.2 データベース設計（SQLite）
中間データも含めて全て保存し、将来の再学習や修正を容易にする。

SQL:
```sql
CREATE TABLE documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT NOT NULL,
        ocr_raw_json TEXT,
        llm_parsed_json TEXT,
        human_corrected_json TEXT,
        status TEXT DEFAULT 'processed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 5. 開発タスクリスト（TODO）

## 🛠️ AI-OCRシステム 開発タスクリスト

### 1. Setup: 環境構築

* [ ] **Python 仮想環境の作成**（Python 3.10+ 推奨）。
* [ ] **CUDA Toolkit / cuDNN のセットアップ**（GPU利用のため）。
* [ ] **PaddleOCR のインストール & 動作確認**（`paddlepaddle-gpu` 推奨、日本語モデル動作確認）。
* [ ] **llama-cpp-python のインストール**（**GPU有効化ビルド**が必須）。

### 2. Logic 1: OCR 実装（The "Eye"）

* [ ] **OCR 実行関数の作成**：画像パスからテキスト、座標、信頼度を抽出。
* [ ] **座標整形ロジックの実装（最重要）**：
    * OCR結果をY座標・X座標でソートし、読む順序に並べ替え。
    * テキストを `f"(y:{y}, x:{x}) {text}"` 形式に変換し、LLMに渡す。
    * 低信頼度テキストは削除または置換（ノイズ除去）。

### 3. Logic 2: LLM 実装（The "Brain"）

* [ ] **モデルのダウンロード**：**4-bit量子化**された `.gguf` 形式モデル（例: Qwen2.5-7B-Instruct）を選定。
* [ ] **推論クラスの実装**：`llama_cpp.Llama` を使用し、`n_gpu_layers=-1` でGPUを最大活用。
* [ ] **プロンプトテンプレートの作成**：座標付きテキストを解析させ、`response_format={"type": "json_object"}` でJSON出力を強制。
* [ ] **マッピング定義**：JSONとして抽出するキー（日付、金額、明細など）を明確化。

### 4. Logic 3: データ保存（Persistence）

* [ ] **DB 接続クラスの実装**：SQLiteを使用し、**OCR生データとLLM整形済みデータ**を格納。
* [ ] **CSV 出力機能の実装**：Pandasを使用し、ネスト構造（明細）を適切にフラット化する仕様を決定。

### 5. Verification: 検証

* [ ] **単一レシートでの疎通確認**：全パイプライン（OCR→LLM→DB/CSV）の正常動作確認。
* [ ] **複雑レイアウトでの検証**：表組みやズレを含む画像で、座標ロジックの有効性を確認。
* [ ] **エラーハンドリングの実装**：LLMが出力異常を起こした場合の再試行またはログ記録ロジックを実装。

## 6. Phase 2（高性能 GPU 導入時）への移行計画
- LLM 部分を VLM（例: Qwen2-VL-72B）に差し替え、Grounding（根拠付け）アプローチを採用する。
- 入力: 画像そのもの + PaddleOCR のテキストリスト  
- 指示: 「画像の視覚情報でレイアウトを理解し、値の書き起こしには OCR リストのテキストを使用せよ」  
- 期待効果: 座標ズレやハルシネーションを抑えた高精度な抽出により、手書き図面や特殊帳票にも対応可能となる。


# テスト実装

- APIサーバー：LM Studio
- GPU:NVIDIA GeForce GTX 1660Ti (VRAM 6GB)
- 利用モデル：google/gemma-3-12b 12b→12億パラメーター
- プログラム：Python 3.12.6

プロジェクト内の請求書読み取りを実行

github\billing-ocr\請求書サンプル.png

読み取り結果

```json
{
  "件名": "サンプルプロジェクト",
  "支払金額": "154,000円（税込）",
  "請求日": "2022/4/30",
  "請求金額合計": "154,000",
  "明細": [
    {
      "適用": "サンプル1",
      "数量": 1,
      "単位": "式",
      "単価": 10000,
      "金額": 10000
    },
    {
      "適用": "サンプル2",
      "数量": 1,
      "単位": "式",
      "単価": 10000,
      "金額": 10000
    },
    {
      "適用": "サンプル3",
      "数量": 1,
      "単位": "式",
      "単価": 10000,
      "金額": 10000
    },
    {
      "適用": "サンプル4",
      "数量": 1,
      "単位": "式",
      "単価": 10000,
      "金額": 10000
    },
    {
      "適用": "サンプル5",
      "数量": 1,
      "単位": "式",
      "単価": 10000,
      "金額": 10000
    },
    {
      "適用": "サンプル6",
      "数量": 1,
      "単位": "式",
      "単価": 10000,
      "金額": 10000
    },
    {
      "適用": "サンプル7",
      "数量": 1,
      "単位": "式",
      "単価": 10000,
      "金額": 10000
    },
    {
      "適用": "サンプル8",
      "数量": 1,
      "単位": "式",
      "単価": 10000,
      "金額": 10000
    },
    {
      "適用": "サンプル9",
      "数量": 1,
      "単位": "式",
      "単価": 10000,
      "金額": 10000
    },
    {
      "適用": "サンプル10",
      "数量": 1,
      "単位": "式",
      "単価": 10000,
      "金額": 10000
    }
  ]
}
```

Document Created: 2025-11-25  
Architecture Decision: Hybrid AI-OCR Strategy