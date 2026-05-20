# HSI-Core Error Knowledge Base

This file is updated automatically whenever the app records a system, camera, stage, scan, upload, or UI error.

| Time | Module | Severity | Type/Code | Message | Likely Action |
| --- | --- | --- | --- | --- | --- |
| 2026-05-19T10:27:06.001+05:30 | SYSTEM_EVENT | ERROR | HARDWARE_LOCKED | Another backend process owns the hardware lock; using mock fallback | Inspect logs/hardware_log.jsonl and repeat the operation after correcting the cause. |
| 2026-05-19 10:27:06 | SYSTEM_ERROR | ERROR | RuntimeError | Another backend process owns the hardware lock; using mock fallback | Inspect logs/hardware_log.jsonl and repeat the operation after correcting the cause. |
| 2026-05-19T10:27:06.002+05:30 | STAGE_EVENT | ERROR | STAGE_FALLBACK | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:27:06 | STAGE_ERROR | ERROR | RuntimeError | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:27:06.004+05:30 | CAMERA_EVENT | ERROR | CAMERA_FALLBACK | Camera switched to mock fallback | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19 10:27:06 | CAMERA_ERROR | ERROR | RuntimeError | Camera switched to mock fallback | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19T10:27:06.005+05:30 | STAGE_EVENT | INFO | EVENT | Stage velocity profile applied | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:27:17.629+05:30 | SYSTEM_EVENT | ERROR | HARDWARE_LOCKED | Another backend process owns the hardware lock; using mock fallback | Inspect logs/hardware_log.jsonl and repeat the operation after correcting the cause. |
| 2026-05-19 10:27:17 | SYSTEM_ERROR | ERROR | RuntimeError | Another backend process owns the hardware lock; using mock fallback | Inspect logs/hardware_log.jsonl and repeat the operation after correcting the cause. |
| 2026-05-19T10:27:17.630+05:30 | STAGE_EVENT | ERROR | STAGE_FALLBACK | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:27:17 | STAGE_ERROR | ERROR | RuntimeError | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:27:17.631+05:30 | CAMERA_EVENT | ERROR | CAMERA_FALLBACK | Camera switched to mock fallback | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19 10:27:17 | CAMERA_ERROR | ERROR | RuntimeError | Camera switched to mock fallback | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19T10:27:17.632+05:30 | STAGE_EVENT | INFO | EVENT | Stage velocity profile applied | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:27:48.952+05:30 | SYSTEM_EVENT | ERROR | HARDWARE_LOCKED | Another backend process owns the hardware lock; using mock fallback | Inspect logs/hardware_log.jsonl and repeat the operation after correcting the cause. |
| 2026-05-19 10:27:48 | SYSTEM_ERROR | ERROR | RuntimeError | Another backend process owns the hardware lock; using mock fallback | Inspect logs/hardware_log.jsonl and repeat the operation after correcting the cause. |
| 2026-05-19T10:27:48.953+05:30 | STAGE_EVENT | ERROR | STAGE_FALLBACK | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:27:48 | STAGE_ERROR | ERROR | RuntimeError | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:27:48.955+05:30 | CAMERA_EVENT | ERROR | CAMERA_FALLBACK | Camera switched to mock fallback | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19 10:27:48 | CAMERA_ERROR | ERROR | RuntimeError | Camera switched to mock fallback | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19T10:27:48.956+05:30 | STAGE_EVENT | INFO | EVENT | Stage velocity profile applied | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:27:49 | STAGE_ERROR | ERROR | RuntimeError | Startup stage health check is using fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:27:49 | CAMERA_ERROR | ERROR | RuntimeError | Startup camera health check is using fallback | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19T10:28:05.438+05:30 | STAGE_EVENT | INFO | EVENT | Stage velocity profile applied | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:29:46.072+05:30 | STAGE_EVENT | INFO | EVENT | Stage home confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:29:46.753+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:48:16.510+05:30 | STAGE_EVENT | INFO | EVENT | Stage connected and health check passed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:48:17.456+05:30 | CAMERA_EVENT | INFO | EVENT | Camera connected and frame grab health check passed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19T10:48:17.483+05:30 | STAGE_EVENT | INFO | EVENT | Stage velocity profile applied | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:21.356+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:21 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:21.711+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:21 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:22.063+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:22 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:22.416+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:22 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:22.772+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:22 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:23.125+05:30 | STAGE_EVENT | ERROR | STAGE_FALLBACK | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:23 | STAGE_ERROR | ERROR | RuntimeError | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:23.898+05:30 | CAMERA_EVENT | INFO | EVENT | Camera connected and frame grab health check passed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19T10:53:23.898+05:30 | STAGE_EVENT | INFO | EVENT | Stage velocity profile applied | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:24 | STAGE_ERROR | ERROR | RuntimeError | Startup stage health check is using fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:28.912+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:28 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:29.268+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:29 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:29.621+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:29 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:29.977+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:29 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:30.332+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:30 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:30.687+05:30 | STAGE_EVENT | ERROR | STAGE_FALLBACK | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:30 | STAGE_ERROR | ERROR | RuntimeError | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:35.692+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:35 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:36.045+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:36 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:36.398+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:36 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:36.750+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:36 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:37.103+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:37 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:37.455+05:30 | STAGE_EVENT | ERROR | STAGE_FALLBACK | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:37 | STAGE_ERROR | ERROR | RuntimeError | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:37.465+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:38.531+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:39.638+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:40.676+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:41.608+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:42.459+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:42 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:42.814+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:42 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:43.170+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:43 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:43.526+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:43 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:43.882+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:43 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:44.236+05:30 | STAGE_EVENT | ERROR | STAGE_FALLBACK | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:44 | STAGE_ERROR | ERROR | RuntimeError | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:44.246+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:46.146+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:46.626+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:47.253+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:47.498+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:47.710+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:48.423+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:48.883+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:49.238+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:49 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:49.592+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:49 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:49.945+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:49 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:50.065+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:50.300+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:50 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:50.653+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:50 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:51.007+05:30 | STAGE_EVENT | ERROR | STAGE_FALLBACK | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:51 | STAGE_ERROR | ERROR | RuntimeError | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:52.005+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:56.014+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:56 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:56.372+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:56 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:56.725+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:56 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:57.079+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:57 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:57.433+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:57 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:53:57.786+05:30 | STAGE_EVENT | ERROR | STAGE_FALLBACK | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:53:57 | STAGE_ERROR | ERROR | RuntimeError | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:01.452+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:02.027+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:02.791+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:02 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:02.921+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:03.146+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:03 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:03.500+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:03 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:03.518+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:03.754+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:03.854+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:03 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:04.062+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:04.209+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:04 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:04.293+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:04.563+05:30 | STAGE_EVENT | ERROR | STAGE_FALLBACK | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:04 | STAGE_ERROR | ERROR | RuntimeError | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:04.691+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:04.973+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:09.568+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:09 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:09.923+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:09 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:10.279+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:10 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:10.634+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:10 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:10.988+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:10 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:11.342+05:30 | STAGE_EVENT | ERROR | STAGE_FALLBACK | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:11 | STAGE_ERROR | ERROR | RuntimeError | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:16.346+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:16 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:16.699+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:16 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:17.051+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:17 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:17.403+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:17 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:17.758+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:17 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:18.110+05:30 | STAGE_EVENT | ERROR | STAGE_FALLBACK | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:18 | STAGE_ERROR | ERROR | RuntimeError | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:23.113+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:23 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:23.469+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:23 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:23.824+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:23 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:24.177+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:24 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:24.529+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:24 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:24.882+05:30 | STAGE_EVENT | ERROR | STAGE_FALLBACK | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:24 | STAGE_ERROR | ERROR | RuntimeError | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:29.887+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:29 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:30.242+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:30 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:30.596+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:30 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:30.951+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:30 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:31.308+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:31 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:31.662+05:30 | STAGE_EVENT | ERROR | STAGE_FALLBACK | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:31 | STAGE_ERROR | ERROR | RuntimeError | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:36.665+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:36 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:37.020+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:37 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:37.374+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:37 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:37.726+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:37 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:38.078+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:38 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:38.431+05:30 | STAGE_EVENT | ERROR | STAGE_FALLBACK | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:38 | STAGE_ERROR | ERROR | RuntimeError | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:43.434+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:43 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:43.787+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:43 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:44.140+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:44 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:44.494+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:44 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:44.847+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:44 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:45.200+05:30 | STAGE_EVENT | ERROR | STAGE_FALLBACK | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:45 | STAGE_ERROR | ERROR | RuntimeError | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:50.202+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:50 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:50.557+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:50 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:50.913+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:50 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:51.266+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:51 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:51.621+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:51 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:51.973+05:30 | STAGE_EVENT | ERROR | STAGE_FALLBACK | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:51 | STAGE_ERROR | ERROR | RuntimeError | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:56.981+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:56 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 1/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:57.337+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:57 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 2/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:57.691+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:57 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 3/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:58.045+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:58 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 4/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:58.399+05:30 | STAGE_EVENT | ERROR | STAGE_CONNECT_FAILED | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:58 | STAGE_ERROR | ERROR | RuntimeError | Stage connect attempt 5/5 failed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:54:58.754+05:30 | STAGE_EVENT | ERROR | STAGE_FALLBACK | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19 10:54:58 | STAGE_ERROR | ERROR | RuntimeError | Stage switched to mock fallback | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:55:04.341+05:30 | STAGE_EVENT | INFO | EVENT | Stage connected and health check passed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:57:27.426+05:30 | STAGE_EVENT | INFO | EVENT | Stage home confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:57:31.908+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:57:34.357+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:57:36.406+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:57:39.191+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:57:41.560+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:57:45.692+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:57:52.559+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:57:58.224+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:57:58.848+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:57:59.456+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:58:03.250+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:58:05.587+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:58:10.549+05:30 | STAGE_EVENT | INFO | EVENT | Stage home confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:58:27.900+05:30 | STAGE_EVENT | INFO | EVENT | Stage home confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:41.837+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:42.573+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:43.325+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:44.061+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:44.798+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:45.534+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:46.271+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:47.039+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:47.807+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:48.544+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:49.296+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:50.031+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:50.768+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:51.520+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:52.256+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:52.993+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:53.730+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:54.465+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:55.218+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:55.954+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:56.707+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:57.459+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:58.196+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:58.947+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T10:59:59.684+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T11:07:08.702+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T11:07:11.535+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T11:07:49.424+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T11:07:53.857+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T11:07:55.890+05:30 | STAGE_EVENT | INFO | EVENT | Stage move confirmed | Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage. |
| 2026-05-19T11:14:27.263+05:30 | CAMERA_EVENT | ERROR | CAMERA_FALLBACK | Camera switched to mock fallback | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19 11:14:27 | CAMERA_ERROR | ERROR | RuntimeError | Camera switched to mock fallback | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19 11:14:27 | SYSTEM_ERROR | ERROR | AccessException | Node is not readable. : AccessException thrown in node 'DeviceTemperature' while calling 'DeviceTemperature.GetValue()' (file 'FloatT.h', line 296) | Inspect logs/hardware_log.jsonl and repeat the operation after correcting the cause. |
| 2026-05-19T11:14:29.758+05:30 | CAMERA_EVENT | ERROR | CAMERA_CONNECT_FAILED | Camera connect attempt 1/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19 11:14:29 | CAMERA_ERROR | ERROR | RuntimeError | Camera connect attempt 1/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19T11:14:30.364+05:30 | CAMERA_EVENT | ERROR | CAMERA_CONNECT_FAILED | Camera connect attempt 2/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19 11:14:30 | CAMERA_ERROR | ERROR | RuntimeError | Camera connect attempt 2/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19T11:14:30.977+05:30 | CAMERA_EVENT | ERROR | CAMERA_CONNECT_FAILED | Camera connect attempt 3/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19 11:14:30 | CAMERA_ERROR | ERROR | RuntimeError | Camera connect attempt 3/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19T11:14:31.587+05:30 | CAMERA_EVENT | ERROR | CAMERA_CONNECT_FAILED | Camera connect attempt 4/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19 11:14:31 | CAMERA_ERROR | ERROR | RuntimeError | Camera connect attempt 4/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19T11:14:32.194+05:30 | CAMERA_EVENT | ERROR | CAMERA_CONNECT_FAILED | Camera connect attempt 5/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19 11:14:32 | CAMERA_ERROR | ERROR | RuntimeError | Camera connect attempt 5/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19T11:14:32.546+05:30 | CAMERA_EVENT | ERROR | CAMERA_FALLBACK | Camera switched to mock fallback | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19 11:14:32 | CAMERA_ERROR | ERROR | RuntimeError | Camera switched to mock fallback | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19T14:07:29.692+05:30 | CAMERA_EVENT | ERROR | CAMERA_CONNECT_FAILED | Camera connect attempt 1/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19 14:07:29 | CAMERA_ERROR | ERROR | RuntimeError | Camera connect attempt 1/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19T14:07:30.046+05:30 | CAMERA_EVENT | ERROR | CAMERA_CONNECT_FAILED | Camera connect attempt 2/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19 14:07:30 | CAMERA_ERROR | ERROR | RuntimeError | Camera connect attempt 2/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19T14:07:30.400+05:30 | CAMERA_EVENT | ERROR | CAMERA_CONNECT_FAILED | Camera connect attempt 3/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19 14:07:30 | CAMERA_ERROR | ERROR | RuntimeError | Camera connect attempt 3/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19T14:07:30.754+05:30 | CAMERA_EVENT | ERROR | CAMERA_CONNECT_FAILED | Camera connect attempt 4/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19 14:07:30 | CAMERA_ERROR | ERROR | RuntimeError | Camera connect attempt 4/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19T14:07:31.107+05:30 | CAMERA_EVENT | ERROR | CAMERA_CONNECT_FAILED | Camera connect attempt 5/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19 14:07:31 | CAMERA_ERROR | ERROR | RuntimeError | Camera connect attempt 5/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19T14:07:31.462+05:30 | CAMERA_EVENT | ERROR | CAMERA_FALLBACK | Camera switched to mock fallback | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19 14:07:31 | CAMERA_ERROR | ERROR | RuntimeError | Camera switched to mock fallback | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19T14:07:36.718+05:30 | CAMERA_EVENT | ERROR | CAMERA_CONNECT_FAILED | Camera connect attempt 1/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19 14:07:36 | CAMERA_ERROR | ERROR | RuntimeError | Camera connect attempt 1/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19T14:07:37.329+05:30 | CAMERA_EVENT | ERROR | CAMERA_CONNECT_FAILED | Camera connect attempt 2/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19 14:07:37 | CAMERA_ERROR | ERROR | RuntimeError | Camera connect attempt 2/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19T14:07:37.941+05:30 | CAMERA_EVENT | ERROR | CAMERA_CONNECT_FAILED | Camera connect attempt 3/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19 14:07:37 | CAMERA_ERROR | ERROR | RuntimeError | Camera connect attempt 3/5 failed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
| 2026-05-19T14:07:39.330+05:30 | CAMERA_EVENT | INFO | EVENT | Camera connected and frame grab health check passed | Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware. |
