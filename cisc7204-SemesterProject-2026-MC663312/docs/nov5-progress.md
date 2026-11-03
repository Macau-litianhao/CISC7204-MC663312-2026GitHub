# 11 月 5 日提交 — 进度核实（截至 2026-11-03 16:00）

> 三项交付，每项都要「发论坛帖 + 上传文件」两处提交，且**六人各自提交**。
> 截止：**2026-11-05（周四）23:00**（是 23:00，不是 23:59）。

---

## 一、任务总清单

| # | 任务 | 状态 | 说明 |
|---|---|---|---|
| 1 | Team Project Proposal（PDF） | ✅ 完成 | 10 页 ≤ 15 页；9 部分齐全；≥7 条 APA 参考文献；封面字段齐全；PDF 已从 docx 重新导出 |
| 2 | 1st Meeting Minutes（PDF） | ✅ 完成 | 4 页；官方模板 **12** 个部分齐全（与模板逐节对齐） |
| 3 | 介绍视频脚本 | ✅ 完成 | `docs/video/video_script.md`，16 段旁白 ≈550 词 |
| 4 | 介绍视频 PPT | ✅ 完成 | `docs/video/deck/deck.pptx`，16 页，含合照/姓名学号/标题/课程信息 |
| 5 | 介绍视频（mp4） | ✅ 完成 | `docs/video/Team01_IntroVideo.mp4`，**4:52**，1920×1080，官方音色 + 字幕已烧录 |
| 6 | 提案论坛发帖 | ⚠️ 待发 | 文案已备：`docs/forum/project-proposal-post.md`（标题 `Our Team Project Proposal`）|
| 7 | 纪要论坛发帖 | ⚠️ 待发 | 文案已备：`docs/forum/first-meeting-minutes-post.md`（标题 `Team 01 - Our First Team Meeting Minutes`）|
| 8 | 上传提案 PDF | ⚠️ 待上传 | `docs/proposal/CISC7204-Team01-ProjectProposal.pdf` |
| 9 | 上传纪要 PDF | ⚠️ 待上传 | `docs/meeting-minutes/01_Team01_Meeting_Minutes.pdf` |
| 10 | 上传视频 mp4 | ⚠️ 待上传 | `docs/video/Team01_IntroVideo.mp4` |
| 11 | 六人各自提交 | ⚠️ 待执行 | 每人须亲自点提交，否则该成员不计分 |

---

## 二、已就绪的文件清单

| 文件 | 路径 | 状态 |
|---|---|---|
| 提案 PDF（10 页） | `docs/proposal/CISC7204-Team01-ProjectProposal.pdf` | ✅ |
| 提案 DOCX | `docs/proposal/CISC7204-Team01-ProjectProposal.docx` | ✅ |
| 纪要 PDF（4 页） | `docs/meeting-minutes/01_Team01_Meeting_Minutes.pdf` | ✅ |
| 纪要 DOCX | `docs/meeting-minutes/01_Team01_Meeting_Minutes.docx` | ✅ |
| 提案论坛文案 | `docs/forum/project-proposal-post.md` | ✅ |
| 纪要论坛文案 | `docs/forum/first-meeting-minutes-post.md` | ✅ |
| 视频成片（4:52） | `docs/video/Team01_IntroVideo.mp4` | ✅ |
| 视频字幕 | `docs/video/Team01_IntroVideo.srt` | ✅ |
| 视频脚本 | `docs/video/video_script.md` | ✅ |
| 视频 PPT（16 页） | `docs/video/deck/deck.pptx` | ✅ |
| 视频 PPT 预览 | `docs/video/deck/deck.pdf` · `deck/png/`（16 帧） | ✅ |
| 视频制作方案 | `docs/video/video-production-plan.md` | ✅ |
| 一键重建脚本 | `docs/video/_build_official_video.py` | ✅ |
| 测试回归 | `53 passed`（pytest） | ✅ |

---

## 三、接下来的动作（按顺序）

1. **发 2 篇论坛帖**：粘贴对应文案全文（团队名义，正确板块）。
2. **上传 3 个文件**：提案 PDF、纪要 PDF、视频 mp4（各提交链接）。
3. **六人各自提交**：每人在各自账号确认三项都提交完成。
4. **终检（留 60 分钟）**：回下每个文件能否打开；确认 PDF 页数；确认视频浏览器可播；截图留证；打 `submission-v1` tag。

> 视频如后续要换「克隆音色」或「真人录制」，把 16 段音频替换进
> `docs/video/assets/narration/official/01..16.mp3` 后重跑 `_build_official_video.py` 即可，画面与字幕会自动对齐。
