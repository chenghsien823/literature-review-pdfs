# 文獻搜尋與全文下載 Skill

這是一個可安裝到 Codex 的研究型 skill，協助你完成從 PubMed 檢索、AI 輔助初篩、人工確認、文獻整理，到合法取得全文 PDF 的流程。

它的核心原則很簡單：系統負責搜尋、整理與稽核；是否納入研究、如何解讀結果與怎麼下結論，仍由研究者判斷。

## 可以做什麼？

1. 以 PubMed 建立可追溯的文獻搜尋紀錄。
2. 以 JSONL 建立可稽核的 title/abstract 篩選佇列；AI 可產生初篩草稿，人工負責最終確認。
3. 產出設計導向的證據表與介入措施－結果的研究缺口地圖。
4. 在篩選完成後，主動詢問是否要下載已納入研究的全文。
5. 只嘗試取得合法公開的 PDF，並建立下載與驗證紀錄。

## 學生快速安裝（建議）

不需要安裝 Git。

1. 在 GitHub 頁面按 **Code → Download ZIP**，並解壓縮。
2. 在 Codex／ChatGPT Desktop 開啟 **Plugins → Skills → Create → Upload**，上傳解壓縮後的 skill 資料夾（或介面接受的壓縮檔）。
3. 確認根目錄有 `SKILL.md`，完成安裝後開啟新的 task。
4. 在 skill 資料夾中執行 `check_setup.cmd`（Windows）或 `python scripts/check_setup.py`（macOS／Linux），依畫面提示完成設定。

若學校使用 ChatGPT Edu 或 Business，建議由教師／工作區管理者上傳 skill 並分享至工作區；學生只需在「Shared by workspace」選擇安裝。若看不到 Skills 或 Upload，請洽詢工作區管理者確認權限與帳號方案。

## 使用前準備

你需要：

- Python 3.10 或以上版本
- 一個可聯絡的 NCBI email

先在 skill 資料夾內安裝所需套件：

~~~powershell
# Windows（建議）
py -3 -m pip install -r requirements.txt
~~~

~~~bash
# macOS 或 Linux
python3 -m pip install -r requirements.txt
~~~

Windows 若顯示找不到 `py`，請先安裝 Python 3.10 以上版本並在安裝畫面勾選「Add Python to PATH」，再重新開啟終端機。

接著設定 NCBI_EMAIL。NCBI_API_KEY 是選用項目，可提高允許的查詢速度。

Windows PowerShell：

~~~powershell
$env:NCBI_EMAIL = "you@example.org"
~~~

macOS 或 Linux：

~~~bash
export NCBI_EMAIL="you@example.org"
~~~

請將 email 與 API key 保留在環境變數或你自行指定的本機 env 檔中；不要把它們寫入此 repository 或提交到 Git。

設定完成後，Windows 執行：

~~~powershell
.\check_setup.cmd
~~~

這個檢查不會連線到 PubMed，也不會傳送你的 email 或 API key。

## 最短成功路徑

1. 將 `examples/query.scoping.example.json` 複製為 `query.json`，把族群、介入措施與結果詞換成自己的研究主題。
2. 請 Codex 協助檢查檢索式，再執行 `run_pipeline.cmd query.json outdir --auto` 建立搜尋紀錄、`records.json` 與 **DRAFT** 草稿。
3. 執行 `create_screening_queue.py`，填妥納入／排除標準後重跑一次，建立 AI 初篩與人工覆核佇列。
4. AI 可先提出 DRAFT 決策；人工確認納入與需全文項目後，再完成 `extraction.json`。只有人工確認且標示 `verified: true` 的納入研究才會進入全文下載清單。
5. 當 Codex 詢問是否下載全文時，確認後才下載合法公開 PDF。

## 基本流程

### 1. 建立搜尋與識別紀錄

準備 query.json 與已人工審核的 extraction.json，然後執行：

~~~text
python scripts/run_pipeline.py query.json outdir --extraction extraction.json
~~~

完成後會保留下列檔案：

- 01_search_log.xlsx：客觀的 PubMed 搜尋與識別紀錄
- records.json：供篩選佇列使用的機器可讀原始記錄
- 02_evidence_table.xlsx：經研究者審核的證據整理表
- 03_gap_map.xlsx：協助發現研究缺口的整理地圖

如果使用 --auto，系統只會建立 DRAFT 草稿。草稿不能視為已驗證證據，也不應直接用於研究結論或跳過篩選。

### 2. 建立 AI 初篩與人工覆核佇列

不要用 Excel 當篩選決策資料庫。搜尋完成後，使用 `records.json` 建立本機 JSONL 佇列：

~~~text
python scripts/create_screening_queue.py outdir/records.json outdir/02_screening
~~~

第一次執行會建立 `outdir/02_screening/screening_criteria.json` 後停止。請填寫研究問題、納入條件與預先定義的排除理由，再執行一次相同指令。

第二次執行會建立：

- `screening_candidates.jsonl`：不可直接覆寫的候選文獻資料
- `agent_screening_instructions.md`：AI 初篩決策格式
- `review_queue.html`：本機人工審核頁，可匯出 `reviewer_decisions.jsonl`
- `screening_manifest.json`：來源、筆數與建立時間的稽核紀錄

請 AI 將初篩決策另存為 `ai_screening_draft.jsonl`，不要修改候選文獻檔。每筆需保留納入／排除／需全文決策、標準依據、排除理由（如適用）、信心度與時間戳。完成後驗證格式：

~~~text
python scripts/validate_screening_decisions.py outdir/02_screening/screening_candidates.jsonl outdir/02_screening/ai_screening_draft.jsonl
~~~

AI 決策一律是 DRAFT。人工必須確認每一筆 AI 建議納入或需全文的文獻，並按研究計畫抽查 AI 排除項目。系統性回顧或統合分析仍須執行獨立人工雙人篩選與衝突裁決。

### 3. 完成人工確認、資料萃取與全文準備

完成題名／摘要篩選、需要時的全文資格確認與資料萃取後，才在 `extraction.json` 將確定納入研究標記為 `verified: true`，再執行：

~~~text
python scripts/prepare_fulltext_input.py outdir/records.json extraction.json outdir/included_records.json
~~~

工具會優先使用 DOI、再使用 PMID 對照原始搜尋結果，只保留已驗證且確定納入的研究。

### 4. 先檢查合法全文來源

先以 dry-run 查看可能取得的全文：

~~~text
python scripts/retrieve_fulltext.py --input outdir/included_records.json --output-dir outdir/fulltext --filename-style first-author-country-year --dry-run
~~~

確認要下載後，移除 --dry-run 再執行一次。

下載完成後，請查看 retrieval_manifest.csv。只有狀態為 retrieved 的項目，才表示已成功取得並驗證 PDF。

## 全文下載與研究倫理

此 skill 只會使用 PMC、Europe PMC 與 Unpaywall 提供的合法公開來源。它會檢查 PDF 檔頭、記錄 SHA-256，並在可行時記錄頁數。

它不會繞過付費牆、CAPTCHA、Cloudflare、cookies、帳號登入或任何存取限制。若文章需要機構授權，skill 只會提供安全的人工交接，不會嘗試代為登入或取得未授權內容。

PDF 預設會命名為「第一作者 國家 年份.pdf」。如果無法可靠判斷第一作者國家，檔名會使用 UnknownCountry，並在 manifest 中標示需要人工確認。

## 常見問題

| 情況 | 處理方式 |
| --- | --- |
| 看不到 Skills 或 Upload | 先確認帳號方案、地區與學校工作區是否開放 Skills；Edu／Business 使用者可請管理者開啟上傳與安裝權限。 |
| Windows 找不到 `py` 或 `python` | 安裝 Python 3.10 以上版本，勾選加入 PATH，重新開啟終端機後再執行 `check_setup.cmd`。 |
| 顯示 `NCBI_EMAIL` 未設定 | 依上方 PowerShell 指令設定可聯絡的 email，再重新執行檢查。 |
| 找不到全文 PDF | 這通常代表沒有合法公開版本或需要機構訂閱；請透過學校圖書館或自己已登入的瀏覽器取得，不要嘗試繞過限制。 |
| AI 初篩是否可直接作為納入結果？ | 不可以。AI 僅產生 DRAFT；人工必須確認納入與需全文項目，系統性回顧還需要獨立人工審查與衝突裁決。 |
| `--auto` 已產出 Excel，是否可直接交作業？ | 不可以。它僅是 DRAFT；研究納入、結果解讀與研究缺口都必須人工確認。 |

## 授權

本 project 採用 MIT License，詳見 LICENSE。
