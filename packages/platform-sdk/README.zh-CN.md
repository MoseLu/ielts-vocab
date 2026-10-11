# Platform SDK

面向微服务转型的共享 Python 工具集。

当前模块:

- `platform_sdk.storage.aliyun_oss`: 共享的阿里云 OSS 客户端、元数据、签名 URL 以及对象生命周期辅助函数
- `platform_sdk.service_app`: 极简的 FastAPI 服务工厂,内置 `/health`、`/ready`、`/version`

本包有意复用现有的 `AXI_ALIYUN_OSS_*` 环境变量与当前的私有桶签名 URL 策略。
