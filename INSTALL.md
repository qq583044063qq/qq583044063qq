# Top Languages: 默认统计公开 + 私有仓库

仅需用本包的两个文件覆盖仓库同名文件：
- `.github/workflows/profile-stats.yml`
- `scripts/generate_profile_stats.py`

## 必须配置的 GitHub Secret

1. GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token。
2. Resource owner 选 `qq583044063qq`，Repository access 选 **All repositories**，Repository permissions 保留 **Metadata: Read-only**。此权限足以读取仓库语言统计；不要赋予 Contents: write。
3. 打开个人主页仓库 `qq583044063qq/qq583044063qq` → Settings → Secrets and variables → Actions → Secrets，新增 `PROFILE_STATS_TOKEN`，填入创建的 PAT。
4. 可选：Actions → Variables → `PROFILE_INCLUDE_PRIVATE = false` 关闭私有仓库统计。没有配置此变量时，默认 `true`。如果之前已建了值为 `false` 的同名变量，请将其改为 `true` 或删除，否则会覆盖默认值。
5. 运行 Actions → Generate Profile Statistics → Run workflow。

生成结果：仅在 `assets/stats/top-langs.svg` 中公开语言名称和汇总比例，**不公开仓库名称**。原脚本规则会排除 Fork 和已归档仓库；“全部”是指可访问的自有、非 Fork、非归档仓库。授权范围仅覆盖选中的仓库时，只能统计这些获授权私有仓库，并不能识别遗漏的未授权仓库。若没有 Secret，工作流会显式失败，不会把公开仓库数据误标为全部仓库。

**注意**：公开的语言占比可能间接暴露技术栈信息。不要将 PAT 写入 README、工作流代码或公开仓库文件中。
