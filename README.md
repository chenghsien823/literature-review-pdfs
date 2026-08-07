# 文獻搜尋與全文下載 Skill

這是一個可安裝到 Codex 的研究型 skill，協助你完成從 PubMed 檢索、文獻整理，到合法取得全文 PDF 的流程。

它的核心原則很簡單：系統負責搜尋、整理與稽核；是否納入研究、如何解讀結果與怎麼下結論，仍由研究者判斷。

## 可以做什麼？

1. 以 PubMed 建立可追溯的文獻搜尋紀錄。
2. 產出設計導向的證據表與介入措施－結果的研究缺口地圖。
3. 在篩選完成後，主動詢問是否要下載已納入研究的全文。
4. 只嘗試取得合法公開的 PDF，並建立下載與驗證紀錄。

## 安裝方式

將此 repository 下載到 Codex 的 skills 資料夾。

使用 Git：

~~~text
git clone https://github.com/chenghsien823/literature-review-pdfs.git ~/.codex/skills/literature-review-pdfs
~~~

或直接下載 ZIP，解壓縮後放到：

~~~text
~/.codex/skills/literature-review-pdfs
~~~

確認資料夾根目錄中有 SKILL.md，然後重新啟動 Codex 或開啟新的 task，讓 Codex 重新偵測 skill。

## 使用前準備

你需要：

- Python 3.10 或以上版本
- 一個可聯絡的 NCBI email

先在 skill 資料夾內安裝所需套件：

~~~text
python -m pip install -r requirements.txt
~~~

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

## 基本流程

### 1. 建立搜尋與證據整理檔案

準備 query.json 與已人工審核的 extraction.json，然後執行：

~~~text
python scripts/run_pipeline.py query.json outdir --extraction extraction.json
~~~

完成後會得到三份檔案：

- 01_search_log.xlsx：客觀的 PubMed 搜尋與識別紀錄
- 02_evidence_table.xlsx：經研究者審核的證據整理表
- 03_gap_map.xlsx：協助發現研究缺口的整理地圖

如果使用 --auto，系統只會建立 DRAFT 草稿。草稿不能視為已驗證證據，也不應直接用於研究結論。

### 2. 選出要下載全文的研究

完成篩選、確認納入研究，且 extraction.json 中的研究已標記為 verified:true 後，執行：

~~~text
python scripts/prepare_fulltext_input.py outdir/records.json extraction.json outdir/included_records.json
~~~

工具會優先使用 DOI、再使用 PMID 對照原始搜尋結果，只保留已驗證且確定納入的研究。

### 3. 先檢查合法全文來源

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

## 授權

本 project 採用 MIT License，詳見 LICENSE。
