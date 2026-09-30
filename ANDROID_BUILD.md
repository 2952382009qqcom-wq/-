# 明鉴 Android 测试版

Android 工程位于 `android-app/`，使用原生 WebView 加载当前公网服务。
当前最低支持 Android 7.0（API 24），目标版本为 Android 16（API 36）。
当前测试包版本为 `1.3.0-debug`（versionCode 4），启动地址为
`http://39.96.14.33/`，打开后使用与网页端相同的“明鉴法律智能体”聊天首屏。

## 已实现

- 保持网页登录状态和 Cookie
- 支持网页中的拍照、相册及文档上传
- 相册和文档支持多选；再次拍照会追加附件而不会替换上一张；发送前可预览、删除和调整顺序
- 智能问答、文书分析和合同审查均支持一次合并分析最多 10 个附件，总大小不超过 15 MB
- 相机照片通过临时 `content://` URI 返回网页，不申请存储权限
- 支持将网页生成的 PDF、Word 文书保存到系统“下载/明鉴”目录
- Android 返回键优先返回网页上一页
- 官方数据库等外部链接交给系统浏览器
- 网络失败时显示重试页面
- 仅暴露受限的文书下载桥接接口，并限制文件名与 Base64 文件大小

## 构建

在项目根目录执行：

```powershell
cd android-app
.\gradlew.bat assembleDebug lintDebug
```

测试 APK 输出在 `android-app/app/build/outputs/apk/debug/`。正式发布需要单独生成并妥善保管 release 签名密钥。

本次可交付测试包另复制到 `outputs/MingJian-Legal-Agent-1.3.0-debug.apk`。

## 当前限制

当前后端地址是 HTTP IP，因此测试工程临时允许明文网络。此配置只适合内测；正式参赛发布前应配置域名和 HTTPS，然后把 `network_security_config.xml` 改为禁止明文流量。
# Optional FCM push configuration

The Android app compiles without a committed Firebase configuration. To enable
offline push notifications, download `google-services.json` from the project's
Firebase console and place it at `android-app/app/google-services.json`. This
file is secret deployment configuration and is intentionally ignored by Git.
The server registers the FCM token through the authenticated WebView session;
notification taps route back to the relative page supplied by the server.
