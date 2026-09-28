# Evidence: Tally on GenLayer StudioNet

Every row below was read back from the chain by `scripts/evidence.mjs`: the
sender, the status and the outcome come from the node's answer for each hash,
not from the deployment record. Every outcome on chain matches the record.

- **Contract:** [`0xd8083238c9b62e06A793cc7a0d663E34d77B8639`](https://explorer-studio.genlayer.com/address/0xd8083238c9b62e06A793cc7a0d663E34d77B8639)
- **Deploy transaction:** [`0xf794fd38…1b2e`](https://explorer-studio.genlayer.com/tx/0xf794fd389d116676378edde3628749d76bdbf9df659ebf35bc58466e9aa71b2e)
- **Source sha256:** `eb9a6595ba5b9a50e067ce4eb34bfc834a8d2715e3f5633d2b32d86c8e172a25`
- **Transactions:** 17, from 3 different wallets
- **Generated:** 2026-09-28 02:00 UTC

## Wallets

Each wallet was made in memory for this run, and its key was never written
anywhere. Click an address to see every transaction it sent.

| Role | Address | Transactions sent |
|---|---|---|
| buyer | [`0x93178850cf85a9DBEBfb365f50B1Df700B310FF8`](https://explorer-studio.genlayer.com/address/0x93178850cf85a9DBEBfb365f50B1Df700B310FF8) | 6 |
| stranger | [`0xd1E351F9C0a055670b8946F05C4688e2De854bc1`](https://explorer-studio.genlayer.com/address/0xd1E351F9C0a055670b8946F05C4688e2De854bc1) | 4 |
| supplier | [`0xB71D89724C164a3A68517Ae0Bfb6774C4612A9e2`](https://explorer-studio.genlayer.com/address/0xB71D89724C164a3A68517Ae0Bfb6774C4612A9e2) | 7 |

## Transactions, in order

"refused" is a transaction the contract was meant to refuse: the committee
agreed on the refusal, and the sentence is the contract's own.

| # | Step | Sent by | Method | On chain | Outcome | Tx |
|---|---|---|---|---|---|---|
| 0 | deploy | buyer [`0x9317…0FF8`](https://explorer-studio.genlayer.com/address/0x93178850cf85a9DBEBfb365f50B1Df700B310FF8) | `deploy` | FINALIZED · MAJORITY_AGREE | executed | [`0xf794fd38…1b2e`](https://explorer-studio.genlayer.com/tx/0xf794fd389d116676378edde3628749d76bdbf9df659ebf35bc58466e9aa71b2e) |
| 1 | order 0 opened: office supplies, three lines | buyer [`0x9317…0FF8`](https://explorer-studio.genlayer.com/address/0x93178850cf85a9DBEBfb365f50B1Df700B310FF8) | `open` | FINALIZED · MAJORITY_AGREE | executed | [`0x2c7289e4…ac57`](https://explorer-studio.genlayer.com/tx/0x2c7289e460bd06f99e8c6a865c96283258112cfbc331e8d80a82ceb94571ac57) |
| 2 | order 1 opened: runs five minutes | buyer [`0x9317…0FF8`](https://explorer-studio.genlayer.com/address/0x93178850cf85a9DBEBfb365f50B1Df700B310FF8) | `open` | FINALIZED · MAJORITY_AGREE | executed | [`0x1b460f3e…fe8b`](https://explorer-studio.genlayer.com/tx/0x1b460f3e6018886c07bcee0cfd7cbc8d3c14c9e4efb5e74846b0631ccdc7fe8b) |
| 3 | order 1 closed before it ends | stranger [`0xd1E3…4bc1`](https://explorer-studio.genlayer.com/address/0xd1E351F9C0a055670b8946F05C4688e2De854bc1) | `close` | FINALIZED · MAJORITY_AGREE | refused: the order runs until 2026-09-28T01:52:59Z | [`0xfe6b986c…0ece`](https://explorer-studio.genlayer.com/tx/0xfe6b986c2db0a8b03c37acaa59a0ded63f97afd8a6b5d6dc9d953bac3ab30ece) |
| 4 | order 2 opened: spare toner | buyer [`0x9317…0FF8`](https://explorer-studio.genlayer.com/address/0x93178850cf85a9DBEBfb365f50B1Df700B310FF8) | `open` | FINALIZED · MAJORITY_AGREE | executed | [`0x6deed466…2e21`](https://explorer-studio.genlayer.com/tx/0x6deed466d5b494385d6f5775eaf3bcd686b5d0a94829460406bb0d7bef0d2e21) |
| 5 | a stranger invoices order 0 | stranger [`0xd1E3…4bc1`](https://explorer-studio.genlayer.com/address/0xd1E351F9C0a055670b8946F05C4688e2De854bc1) | `invoice` | FINALIZED · MAJORITY_AGREE | refused: only the supplier may invoice this order | [`0x67e14aa2…233c`](https://explorer-studio.genlayer.com/tx/0x67e14aa2bce717d7fe42992f4ae892d13c60f1becc1d157f9dd533fd6892233c) |
| 6 | invoice 1: paper, toner and a desk lamp | supplier [`0xB71D…A9e2`](https://explorer-studio.genlayer.com/address/0xB71D89724C164a3A68517Ae0Bfb6774C4612A9e2) | `invoice` | FINALIZED · MAJORITY_AGREE | executed | [`0x76646096…9a25`](https://explorer-studio.genlayer.com/tx/0x766460965508af9fb83b53b5723f5ef3cd76ae0f2920ea748de60e2dc04f9a25) |
| 7 | a second invoice while one waits | supplier [`0xB71D…A9e2`](https://explorer-studio.genlayer.com/address/0xB71D89724C164a3A68517Ae0Bfb6774C4612A9e2) | `invoice` | FINALIZED · MAJORITY_AGREE | refused: an invoice is waiting to be matched; either party may ask for it | [`0xf7a34208…9a7a`](https://explorer-studio.genlayer.com/tx/0xf7a34208683f23b8d0c04a1e9ed2b5a0309e6e8ddd32a578d376f1557ba29a7a) |
| 8 | a stranger asks for the match | stranger [`0xd1E3…4bc1`](https://explorer-studio.genlayer.com/address/0xd1E351F9C0a055670b8946F05C4688e2De854bc1) | `match` | FINALIZED · MAJORITY_AGREE | refused: only the buyer or the supplier may ask for a match | [`0xb16e9628…a20a`](https://explorer-studio.genlayer.com/tx/0xb16e96284fbb6a04031feb85b8cd629549bdc65863b3c91ea734dde2aedca20a) |
| 9 | matched: paper and toner paid, the lamp was never ordered | buyer [`0x9317…0FF8`](https://explorer-studio.genlayer.com/address/0x93178850cf85a9DBEBfb365f50B1Df700B310FF8) | `match` | FINALIZED · MAJORITY_AGREE | executed | [`0x0b579264…df59`](https://explorer-studio.genlayer.com/tx/0x0b57926409c3a61324a11cc3284f3152210e857dcc3a1047bbec77574e00df59) |
| 10 | the same invoice again | supplier [`0xB71D…A9e2`](https://explorer-studio.genlayer.com/address/0xB71D89724C164a3A68517Ae0Bfb6774C4612A9e2) | `invoice` | FINALIZED · MAJORITY_AGREE | refused: this invoice was already matched as invoice 1; change it to invoice what is still open | [`0x61fbde1e…ea8f`](https://explorer-studio.genlayer.com/tx/0x61fbde1e0236140372459cb57b7ad6ad462daf04f0f9bd55a45ebff64efaea8f) |
| 11 | invoice 2: too much paper, stapler above price | supplier [`0xB71D…A9e2`](https://explorer-studio.genlayer.com/address/0xB71D89724C164a3A68517Ae0Bfb6774C4612A9e2) | `invoice` | FINALIZED · MAJORITY_AGREE | executed | [`0xea60781b…6646`](https://explorer-studio.genlayer.com/tx/0xea60781b87ee7c5bac4323161ae6fa347405a98b068ee70001e1936cab226646) |
| 12 | matched: both lines refused by the arithmetic | supplier [`0xB71D…A9e2`](https://explorer-studio.genlayer.com/address/0xB71D89724C164a3A68517Ae0Bfb6774C4612A9e2) | `match` | FINALIZED · MAJORITY_AGREE | executed | [`0x12aca38f…6ae8`](https://explorer-studio.genlayer.com/tx/0x12aca38f3ef0437c5784c332b3a9447d7a03db8598ab26246fadac4fdebf6ae8) |
| 13 | invoice 3: the rest, stapler below price | supplier [`0xB71D…A9e2`](https://explorer-studio.genlayer.com/address/0xB71D89724C164a3A68517Ae0Bfb6774C4612A9e2) | `invoice` | FINALIZED · MAJORITY_AGREE | executed | [`0x2ad3401f…6499`](https://explorer-studio.genlayer.com/tx/0x2ad3401fe0cf99d87eb74c2171746db86b2877491c817aa0107a2849ea186499) |
| 14 | matched: order 0 fulfilled, the difference back | buyer [`0x9317…0FF8`](https://explorer-studio.genlayer.com/address/0x93178850cf85a9DBEBfb365f50B1Df700B310FF8) | `match` | FINALIZED · MAJORITY_AGREE | executed | [`0x9209ca46…1cee`](https://explorer-studio.genlayer.com/tx/0x9209ca46230c69fc15481254d46ee15a12ec1f163f7671b16fd07f3d94de1cee) |
| 15 | order 2 released by the supplier | supplier [`0xB71D…A9e2`](https://explorer-studio.genlayer.com/address/0xB71D89724C164a3A68517Ae0Bfb6774C4612A9e2) | `release` | FINALIZED · MAJORITY_AGREE | executed | [`0xe207bded…3d5c`](https://explorer-studio.genlayer.com/tx/0xe207bdedbfe27eebce1cf50039ce9fab4900a9299cd1416e6cb33e930b243d5c) |
| 16 | order 1 closed after it ended | stranger [`0xd1E3…4bc1`](https://explorer-studio.genlayer.com/address/0xd1E351F9C0a055670b8946F05C4688e2De854bc1) | `close` | FINALIZED · MAJORITY_AGREE | executed | [`0x12ff7f7f…3365`](https://explorer-studio.genlayer.com/tx/0x12ff7f7fbe498c86dbcd7e912aa91a34d45517b7dd90440b589cbde2a0593365) |
