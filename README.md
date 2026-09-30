# Joule Heating Literature Monitor

一个可部署到 GitHub Pages 的公共文献监测网站。它通过 OpenAlex 和 Crossref 查询文献，按 DOI/标题去重，生成静态网页，并由 GitHub Actions 定期更新。

## 功能

- 监测 Joule heating、flash Joule heating、rapid/ultrafast Joule heating 等主题
- 覆盖材料合成、碳材料、高熵合金、催化剂、电池、废物资源化等方向
- 自动查询 OpenAlex 和 Crossref 公共接口
- 按 DOI 或标准化标题去重
- 保存历史结果，避免每次覆盖旧文献
- 生成可公开访问的静态 HTML 页面
- GitHub Actions 每周自动更新

## 快速部署

1. 在 GitHub 创建一个公开仓库。
2. 把本目录中的所有文件上传到仓库根目录。
3. 进入仓库的 **Settings → Pages**，选择 **GitHub Actions** 部署来源。
4. 手动运行一次 **Actions → Update literature monitor → Run workflow**。
5. 部署完成后，访问：

   `https://你的用户名.github.io/仓库名/`

工作流默认每周一 UTC 01:00 运行。你可以修改 `.github/workflows/update.yml` 中的 cron。

## 本地运行

需要 Python 3.10 或更高版本。无需第三方依赖：

```bash
python scripts/update_literature.py
```

生成文件：

- `docs/index.html`
- `docs/data.json`
- `data/literature.json`

## 修改检索主题

编辑 `config/topics.json`：

- `queries`：OpenAlex/Crossref 查询词
- `concepts`：页面显示的主题标签
- `from_year`：起始年份
- `max_results_per_query`：每个查询最多获取的结果数

## 注意事项

- OpenAlex 和 Crossref 结果不等于 Web of Science、Scopus、CNKI 等订阅数据库的完整覆盖。
- 页面会标注来源和检索日期，不会伪造全文可得性或引用次数。
- GitHub Actions 的公共 API 请求应保持低频；不要把 cron 改成高频轮询。
- 这个包默认只做文献发现和元数据整理，不自动下载受版权保护的全文。
