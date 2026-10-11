# 多项目域名路由

`axiomaticworld.com` 是 AxiomaticWorld 的父域名，不属于 IELTS Vocab 的永久产品入口。

## 当前兼容状态

- 当前生产站仍通过 `axiomaticworld.com` / `www.axiomaticworld.com` 提供服务。
- `IELTS_PUBLIC_HOST` 未配置时，部署脚本继续使用 `axiomaticworld.com`，保证旧环境可回滚。
- `PROD_SMOKE_HOST` 未配置时跟随 `IELTS_PUBLIC_HOST`。

## 多项目目标状态

为 IELTS Vocab 配置独立主机，例如：

```text
ielts.axiomaticworld.com
```

在 DNS、证书和 Nginx 就绪后，生产环境设置：

```bash
IELTS_PUBLIC_HOST=ielts.axiomaticworld.com
PROD_SMOKE_HOST=ielts.axiomaticworld.com
PROD_PUBLIC_URL=https://ielts.axiomaticworld.com
PUBLIC_WEB_ORIGINS=https://ielts.axiomaticworld.com
IELTS_MOBILE_PROD_BASE_URL=https://ielts.axiomaticworld.com
```

Web 端继续使用同源 `/api` 和 `/socket.io`，移动端通过同一个项目主机访问 API。其他项目使用自己的子域名，不修改 IELTS 的运行时配置。

## 切换顺序

1. 为项目子域名添加 A/CNAME 记录并等待 DNS 生效。
2. 为项目子域名签发覆盖该主机的 HTTPS 证书。
3. 设置上述主机、Smoke 和 CORS 变量。
4. 渲染或更新 Nginx `server_name`，再执行生产部署和真实域名 Smoke。
5. 确认子域名稳定后，再评估是否下线根域名的旧 IELTS 路由。

不要在第 5 步之前删除根域名或 `www` 记录；它们当前仍承载可用的 IELTS 生产站。
