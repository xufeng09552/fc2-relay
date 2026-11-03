# FC2 Relay

只放行 `fc2.com` 的极简单用途抓取中转，供内网 NAS 刮削 FC2 影片元数据时取网页用。
不是公开代理：只允许 fc2.com 及其子域，必须带 access key。

- Python 标准库，无任何依赖
- 监听 `$PORT`（默认 8000）
- 接口：`GET /health`、`GET /fetch?url=<fc2 网页>&key=<ACCESS_KEY>`
