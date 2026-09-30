# 受限本機 storage 資格

`mg1-local-operation/v1` 僅處理本機 Darwin、單專案、同 UID 可信 operator、固定
SQL、256 MiB main ceiling。容量不足安全拒絕；不保證滿庫 stop，不要求實體
滿庫實驗，不宣稱完整 G1/MG1、power-loss、RSS、swap 或 deadline 資格。

## 可追溯 build

固定 Python 3.12.9 與 SQLite 3.53.4 官方 source，SQLite 靜態連結進 CPython
`_sqlite3`；不能使用 Apple vendor build、注入 library、任意 VFS 或 extension。
同 UID 與 operator 已審查的 build 程序是 TCB；source ID、flags、雜湊或 JSON
自洽不證明抵抗同帳號惡意程式的二進位偽造。

| 來源 | 雜湊 |
| --- | --- |
| [SQLite archive](https://www.sqlite.org/2026/sqlite-amalgamation-3530400.zip) | 官方 [download metadata](https://www.sqlite.org/download.html) SHA3-256 `628a44cfe82c66aed1ccbbe85a562d2e33ebe64b3288981ed76285612227934e` |
| archive member `sqlite3.c` | SHA-256 `b1dd5d74ec7f29055a6684fa06fb3c2f6821c87dd38f9a458dfd2e8a1db28189` |
| [Python archive](https://www.python.org/ftp/python/3.12.9/Python-3.12.9.tar.xz) | 本次官方 HTTPS 下載觀察 SHA-256 `7220835d9f90b37c006e9842a8dff4580aaca4318674f947302b8d28f3f81112`；不是另外驗證過的簽章 |

SQLite source ID：
`2026-07-24 19:02:57 bf7c7f30031888f4e796e429ab3978879485813aaca6f641c7b33e4e09459bcc`。
固定編譯選項：`SQLITE_TEMP_STORE=3`、`SQLITE_OMIT_LOAD_EXTENSION`、
`SQLITE_THREADSAFE=1`、`SQLITE_MAX_MMAP_SIZE=0`、`SQLITE_MAX_WORKER_THREADS=0`、
`SQLITE_ENABLE_LOCKING_STYLE=0`。另外啟用 `SQLITE_ENABLE_FTS5` 供 repo 既有驗證使用；
本五操作固定 schema 不使用 FTS5。禁止 CODEC、OS_OTHER、DEFAULT_UNIX_VFS、
OMIT_DISKIO、OMIT_MEMORYDB、自訂 VFS／初始化 extension。

在已核對的獨立空 build 目錄解壓兩個 archive 後，用固定 compiler 建 sqlite3.c：

```sh
cc -O2 -fPIC -DSQLITE_TEMP_STORE=3 -DSQLITE_OMIT_LOAD_EXTENSION \
  -DSQLITE_THREADSAFE=1 -DSQLITE_MAX_MMAP_SIZE=0 -DSQLITE_MAX_WORKER_THREADS=0 \
  -DSQLITE_ENABLE_LOCKING_STYLE=0 -DSQLITE_ENABLE_FTS5 \
  -c sqlite-amalgamation-3530400/sqlite3.c -o sqlite3-posix.o
ar rcs libsqlite3-posix.a sqlite3-posix.o
```

CPython configure 用該目錄的絕對路徑，設定
`LIBSQLITE3_CFLAGS=-I<build>/sqlite-amalgamation-3530400` 與
`LIBSQLITE3_LIBS=<build>/libsqlite3-posix.a`，`--prefix=<new-isolated-runtime>`、
`--without-ensurepip`，再 `make`／`make altinstall`。不替換系統 Python，不改
個人 Codex 設定。檢查 actual `_sqlite3.__file__`、source ID、compile options，
以及 `otool -L` 未依賴 Apple libsqlite3。本次 Darwin build 已做以上核對。
不同 build 必須重新核對，不能因版本號相同採用未知 library。

## Exact source 推導

以下行號皆對應上述 archive 的 `sqlite3.c`；獨立唯讀 reviewer 已核對 archive
hash、member bytes 與 call sites。`P=4096`、`M` 是當次 main bytes、`N=M/P`、
`D=268435456`。Writer 與 initialize 實際設定並讀回 DELETE、NORMAL、
cache_spill OFF、MEMORY temp、EXTRA sync、secure_delete ON 與 page ceiling。

| 邊界 | Exact source 行號與理由 |
| --- | --- |
| sector ceiling | 60050、62392–62442：最大 65536 bytes |
| journal header／padding | 61001–61204、64015–64020、65563–65570：保守保留兩個 sector |
| spill 關閉 | 145714–145732、63334–63337、64317–64322：不追加 spill header；66293 的 commit `newHdr=0` |
| records | 65672–65717、65770–65779：每既有頁最多一次 P+8；以 bit vector 及 dbOrigSize 限制 |
| main growth | 105393–105405、65272–65280、64145–64164：page ceiling 超限回 SQLITE_FULL，寫入 pgno 不超過 dbSize |
| POSIX VFS | 40263–40268、48699–48704：Darwin 必須固定 locking style 0；避免 autolock 的 proxy／dot-file sidecars |
| 沒有 chunk 擴張 | 46819、44246–44307：unixFile 初始 szChunk=0，固定 SQL 不設定 chunk size |
| statement journal | 190075–190090、76942、65603–65608、64201–64211、109975、110129–110160：TEMP_STORE=3，subjournal nSpill=-1，純 memory |
| reader temp／sorter | 75774–75783、107484–107561、108368–108384、109151–109160：ephemeral B-tree／sorter 留在 memory |
| 限制 | 66944–66960 的 relocation 錯誤可能重複 journal；77443 的 INCREMENTAL 分支跳過 commit relocation。固定五操作不執行 DDL、DROP、vacuum、ATTACH 或同交易錯誤後續作 |

```text
J = N*(4096+8) + 2*65536
Tdisk = 0
G = D-M
R = ceil((J+Tdisk+G)/4096)*4096
```

R 最大 269090816 bytes，小於既有 maintenance envelope 335544320 bytes。
G 覆蓋全部 main 成長，包含 history/index/proof，沒有以平均成長取代上界。
每次 preview 與接受後 execute 重新量測，要求完整 coverage、page_count 與實際
檔案大小一致、零 bytes lock／journal、可用 bytes ≥R。這是准入檢查，不是實體
空間 reservation；其他程序仍可能消耗空間，寫入錯誤必須獨立讀回分類。

初始化在第一個可能寫入的 pragma 前設定 64-page ceiling／spill／locking，
涵蓋前置 pragma 與 schema 子交易：Jinit=393728、Ginit=262144、Tinit=0、
Rinit=659456 bytes；建立前與每次等待後重新檢查容量、parent/root/source 身分及
雙時鐘。核心之後的 writer 才重新設定 D ceiling；已有或 partial root 拒絕。

## 錯誤行為

低容量 preview 回 not-applied，不呼叫 execute。收到 `SQLITE_FULL`／ENOSPC／
OOM／I/O error 不代表 rollback：由新 reader/read-only connection 判定 applied、
not-applied 或 unknown。讀回未知、輸出失敗、程序中斷均不重播、不自動修復或
清理。測試使用受控 errorcode／交易階段注入；不把它描述為實體 FULL 實驗。
新增 SQL、VFS、build、容量 profile 或 workload 必須重做受影響的資格推導。
