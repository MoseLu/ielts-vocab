# Platform SDK

Shared Python utilities for the microservice transition.

Current modules:

- `platform_sdk.storage.aliyun_oss`: shared Aliyun OSS client, metadata, signed URL, and object lifecycle helpers
- `platform_sdk.service_app`: minimal FastAPI service factory with `/health`, `/ready`, and `/version`

This package intentionally reuses the existing `AXI_ALIYUN_OSS_*` environment variables and the current private-bucket signed-URL strategy.
