---
name: ec2-deploy
description: EC2 部署最佳實踐與常見坑。涵蓋記憶體吃緊時的 deploy-local 策略、Elastic IP 設定、Ghost CMS headless 架構的 proxy/routes.yaml 陷阱。Use when: 部署 Next.js 或 Ghost 到 EC2、遇到 OOM/IP 變更/Docker 部署問題。
---

# EC2 部署最佳實踐

## 核心原則

**EC2 記憶體吃緊（≤1GB RAM）時，永遠用 `deploy-local`，而非在 EC2 上 build。**

---

## 常見陷阱與解法

### 1. OOM（Out of Memory）

- **症狀**：`make deploy-frontend` 在 EC2 上執行 `next build` 時 OOM 崩潰
- **根本原因**：Next.js production build 極度消耗記憶體，t2.micro/t3.micro 通常不夠
- **解法**：改用 `make deploy-local`——在本機 build Docker image，再 `rsync` / `docker save | ssh ... docker load` 傳到 EC2，只在 EC2 跑容器

```bash
# 本機 build + 傳 image
make deploy-local   # 通常等同於：
# docker build -t myapp . && docker save myapp | ssh ec2-user@<ip> docker load
# ssh ec2-user@<ip> "sudo docker compose up -d"
```

---

### 2. EC2 重啟後 IP 變更

- **症狀**：stop → start 後 public IP 變化，DNS 失效，部署腳本 SSH 失敗
- **根本解法**：設定 AWS Elastic IP（免費，只要綁定運行中的 instance）

```bash
# AWS Console → EC2 → Elastic IPs → Allocate → Associate to instance
# 或 AWS CLI：
aws ec2 allocate-address --domain vpc
aws ec2 associate-address --instance-id i-xxx --allocation-id eipalloc-xxx
```

---

### 3. Ghost CMS headless 架構

#### routes.yaml 必須手動上傳
- **症狀**：新文章 404；routes.yaml 修改後 GitHub Actions 沒效果
- **原因**：routes.yaml 不走 Git 部署，必須透過 Ghost Admin 上傳
- **解法**：`Ghost Admin → Labs → Routes → Upload routes.yaml`
- **常見錯誤**：只有自訂 collection（如 `/insights/`），缺 default collection

```yaml
# routes.yaml 正確格式
routes:
  /insights/:
    controller: channel
    filter: tag:insights

collections:
  /insights/:
    permalink: /insights/{slug}/
    filter: tag:insights
  /:  # ← 必須有 default collection
    permalink: /{slug}/
```

#### Ghost 內部 HTTP 請求需告知協定
- **症狀**：Ghost API 回傳 301 redirect，導致 fetch 循環
- **原因**：Ghost 在收到非 HTTPS 請求時自動 301 to HTTPS
- **解法**：在 server-side fetch 加 `X-Forwarded-Proto: https` header

```typescript
const response = await fetch(`http://localhost:2368/ghost/api/...`, {
  headers: {
    Authorization: `Ghost ${token}`,
    'X-Forwarded-Proto': 'https',  // ← 關鍵
  }
})
```

#### Deploy 腳本永遠排除 .env
```bash
# rsync 排除 .env
rsync -avz --exclude='.env' --exclude='node_modules' . ec2-user@<ip>:/app/
```

---

### 4. 跨機器部署（SSH key 在不同機器）

- **情境**：程式碼修改在 Mac mini，EC2 SSH key 在 MacBook Pro
- **解法**：feature branch + git push → MacBook Pro pull + deploy

```bash
# Mac mini（修改）
git checkout -b fix/og-meta
git push origin fix/og-meta

# MacBook Pro（有 SSH key）
git pull
git checkout fix/og-meta
make deploy-local
```

---

### 5. Next.js OG/Meta 陷阱

- **症狀**：`og:url` 缺失，社交平台抓不到正確預覽
- **原因**：`layout.tsx` 缺 `metadataBase`
- **解法**：

```typescript
// app/layout.tsx
export const metadata: Metadata = {
  metadataBase: new URL('https://yourdomain.com'),  // ← 必須設定
  // ...
}
```

- 修改後需到 Facebook Sharing Debugger → Scrape Again 強制刷新 cache

---

## 來源

- 2026-04-10 觀察：Ghost Blog OG 修復與部署流程
- 2026-04-12 觀察：Ghost Blog 訂閱功能實作
- 驗證場景：Ghost headless blog 部署到 t3.micro EC2
