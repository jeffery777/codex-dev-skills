# GPT-6 cost routing

此文件記錄 Issue #292 的 GPT-6 日常 baseline 遷移與 2026-09-23 的價格觀測。它是
規劃與評估輔助，不是 router 輸入、資格證明、使用者設定或全域啟用指令。
`policies/model-selection-policy.md` 與已安裝的 routing reference 仍只依工作
類別、tier、sandbox、目前 runtime 與 qualification 選路。

## Everyday baselines

下列具名 profiles 是日常 baseline；它們仍要求當前 installed bytes 與 runtime
support。source 變更不會安裝 profile、修改個人設定或啟用 user qualification store：

| Baseline role | Model / effort | Use boundary |
| --- | --- | --- |
| mechanical reader | `gpt-6-luna` / low | Mechanical extraction/summarization. |
| explorer | `gpt-6-luna` / high | Evidence-led exploration. |
| balanced worker | `gpt-6-sol` / medium | Bounded routine implementation/docs. |
| senior worker | `gpt-6-sol` / high | Complex bounded implementation. |
| advanced worker | `gpt-6-sol` / medium | Multi-trigger advanced work. |
| routine reviewer | `gpt-6-sol` / high | Read-only everyday review only. |

`routine_reviewer` 不得用於 deep/security review。deep、security 與 exceptional
baseline 維持 Astra-xhigh；三個 Astra candidates 仍是 default-off，必須有 exact
scope、runtime、profile digest、current loaded bytes 與 quality evidence。既有歷史
receipts 維持 frozen；其 old digest 不能用於新 dispatch。

保留 Astra 高風險 baselines 的理由是既有 class/tier、唯讀／sandbox 邊界與已採用
設定仍適用，並非由本次比較推論 Astra 品質較佳。Sol-medium／Sol-high 的分工是
依日常與 senior tier 的明確 workload scope。一般 reviewer 選 Sol-high，是本次
high 在相同一般審查案例具有完整可見證據、盲審 control 查核較完整的保守採用。
medium/Astra 的部分 provenance 因公開 event 缺口仍 unknown；不以缺 event 判定
模型虛構，不宣稱單例證明模型或 effort 普遍較佳。

若需 rollback，依當時已核准的 source change 與 release 流程選回先前 profile
mapping，並重新驗證 installed bytes、runtime 與新 dispatch；不可把歷史 receipt、
舊 digest 或本文件當成安裝、設定變更或 runtime rollback 的授權。

## Selection and evaluation

官方 [Models](https://learn.chatgpt.com/docs/models) 說明 GPT-5.5 的 ChatGPT
sign-in 將於 2026-10-14 退役（API 不在此範圍），並將 GPT-6 Sol 定位於較複雜
agentic 工作、GPT-6 Luna 定位於集中且重複的工作。官方也描述 GPT-6 Sol 相對
GPT-5.6 Sol 的事實可靠性與溝通改善；這不是本 repository 的量測結論。官方
skills 指引支持按需載入指令，而不是為每個模型建立完整提示詞矩陣。

先固定模型、effort、案例、來源、工具與權限，A/B 評估提示詞變更；再固定提示詞，
比較模型或 effort。記錄完成率、false completion、權限邊界、漏報、重複驗證、
修正輪數、wall time 與實際用量。文件或契約回歸測試只能驗證載入與邊界文字，
不能證明模型品質或實際成本改善。Issue #292 的六個固定 CLI packet 各有五個
acceptance points；parent 以固定 developer prompt、model、effort 與 sandbox
執行，並明示 CLI explicit config，非 native custom role。結果及失敗紀錄見
[Issue #292 verification](loops/issue-292/verification.md)；不宣稱 Desktop quality
qualification 或 ME01/ME02/ME03 全部完成。環境、資料或
權限問題應先診斷/recovery，不能藉由提高模型或 effort 解決。

參考：[Models](https://learn.chatgpt.com/docs/models)、[Choosing models and reasoning](https://learn.chatgpt.com/docs/agent-configuration/subagents#choosing-models-and-reasoning)、[Skills overview](https://learn.chatgpt.com/docs/customization/overview#skills)、[Latest model guide](https://developers.openai.com/api/docs/guides/latest-model)。

## Point-in-time Codex Standard rate context

下表是依官方 [Codex pricing: tokens and credits](https://learn.chatgpt.com/docs/pricing#what-are-tokens-and-credits)
於 2026-09-23 查閱時，每 1M tokens 所需的 input / cached input / output credits。
它不是 subscription bucket 的換算公式，也不是 routing 的價格函數。Codex Fast GPT-6
為所列 Standard GPT-6 credits 的 2.5 倍。

| Model | Input | Cached input | Output |
| --- | ---: | ---: | ---: |
| GPT-6 Sol | 50 | 5 | 250 |
| GPT-6 Luna | 2.5 | 0.25 | 12.5 |
| GPT-6 Astra | 250 | 25 | 1250 |
| GPT-5.6 Sol | 100 | 10 | 500 |
| GPT-5.6 Terra | 50 | 5 | 300 |
| GPT-5.6 Luna | 5 | 0.5 | 30 |
| GPT-5.5 | 125 | 12.5 | 750 |

這不是 API 美元報價。API 的美元費率、短 context（<=272k tokens）與 cache/cache-write
條件以官方 [API pricing](https://developers.openai.com/api/docs/pricing) 為準；API Fast
為 API Standard 的 2 倍，與 Codex Fast 的 2.5 倍 credits 規則不同。本文件不重製
API 價格表，也不以任一費率推論品質、實測結果或實際帳戶支出。以這個 native
credits 表比較，GPT-6 Sol 相對 GPT-5.6 Sol 的三欄都是 -50%；相對 Terra，input
相同、output -16.7%。GPT-6 Luna 相對 GPT-5.6 Luna 的 input -50%、output -58.3%。
這些是費率差異，不是任務實際成本或節省保證。

實際帳戶可用模型、速率與用量 bucket 必須於當次 runtime/帳戶介面重新查核。
