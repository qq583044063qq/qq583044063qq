# GitHub Profile 完整修复及 WakaTime SVG 改版

适用仓库：https://github.com/qq583044063qq/qq583044063qq，分支 `main`。

## 安装

解压 ZIP，将目录下的 `README.md`、`scripts/`、`.github/workflows/` **按原目录结构覆盖仓库同名文件**。文件包**不包含**原有 `assets/stats/github-stats.svg` 等文件，避免重新覆盖已经生成的真实数据。

上传后在 GitHub Actions 中**手动先运行一次 `Waka Readme`**；这是新 WakaTime 两张 SVG 首次生成的必要步骤。随后运行 `Generate Profile Statistics`，两套工作流都会每天自动更新。

> **WakaTime Token：** 工作流优先从 `secrets.WAKATIME_OAUTH_TOKEN` 读取，没有时才从 `secrets.WAKATIME_API_KEY` 读取。用户如果已将个人 OAuth Token 配置在其中一个 Secret，不需要再改名。不要把令牌写到 README 或脚本中。WakaTime 个人 Token 需要 `read_stats` 范围，编辑器插件 API Key 不能用于此统计接口。

## 新 WakaTime 卡片

- `assets/stats/wakatime-overview.svg`：每周编码时长、每日平均、历史累计时长。
- `assets/stats/wakatime-breakdown.svg`：前 5 名语言、前 3 名编辑器、前 2 名系统，各自时长及占比。
- 与现有 GitHub Stats SVG 使用同一深色蓝粉视觉设计。
- 每天 UTC 18:30（北京时间/新加坡时间次日 02:30）定时执行，同时可手动触发。
- 每次更新 README 的 `?v=` 图片版本以尽量绕过旧的 Pending 图片缓存。
- 访问 WakaTime 失败时，生成器会报错退出，不会把旧的有效 SVG 覆盖成占位图。
- 仅显示聚合统计；不包括私有项目名称、目录或 Token。
- 此方案替代 `anmol098/waka-readme-stats` 的长文本区块及旧 Action；原来的 AI 细节统计不再展示，避免在没有可核实的对应 API 字段时显示过时数据。

## GitHub Stats 原有修复

`profile-stats.yml` 已改为 checkout@v5/setup-python@v6、自动更新 README 图片版本并与 WakaTime 共用并发队列；`generate_profile_stats.py` 支持选择性加入私有仓库语言统计。

可选开启私有语言统计：

1. 创建属于 `qq583044063qq` 的 GitHub fine-grained PAT，允许读取要统计的私有仓库（只读 Metadata 权限）。
2. 在本仓库 Secrets 新增 `PROFILE_STATS_TOKEN`，值为该 PAT。
3. 在 Actions Variables 中新增 `PROFILE_INCLUDE_PRIVATE=true`。默认不统计私有仓库。
4. 手动运行 `Generate Profile Statistics`。生成的是公开可见的聚合比例，**不会暴露私有仓库名字或代码**。

## 结果检查

1. `Actions → Waka Readme → Run workflow`，确保 `Generate WakaTime dashboard` 和 `Commit WakaTime SVG and README` 都是绿色。
2. 打开 `/assets/stats/wakatime-overview.svg` 与 `wakatime-breakdown.svg`，再强制刷新主页 Ctrl+Shift+R。
3. 若遇到 401/403，检查 Token 确实是 WakaTime *个人 OAuth Token*，而不是插件 API Key，且有 `read_stats` 权限。
4. 若 Actions 推送失败，检查仓库 `Settings → Actions → General → Workflow permissions`，开启读写权限，并检查分支保护策略。

**状态说明**：新脚本已通过离线 SVG 生成、XML 解析和模拟数据渲染测试；无法从本地测试你放在 GitHub Secrets 中的真实 Token，必须由首次 Actions 运行完成联网验证。
