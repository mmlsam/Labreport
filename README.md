# Labreport 平台

该示例提供了一个可部署在 openEuler 24.03 服务器上的简易「实验报告批改」系统，包含 FastAPI 后端与纯 HTML 前端：

- 支持批量导入学生信息并设置默认密码。
- 学生登陆后上传 Word (`.docx`) 实验报告。
- 自动调用 DeepSeek 大模型（或在无密钥时使用内置示例）生成 100 分制成绩与中文评语。
- 将红色文本框评语写入报告封面页并生成可下载的批注版。
- 返回评分统计报表。

## 目录结构

```
backend/           # FastAPI 服务
frontend/          # 简单的浏览器端页面
labreport.db       # SQLite 数据库（运行后生成）
data/reports/     # 上传/批注后的报告存储目录
```

## 快速运行

1. 安装依赖（建议在虚拟环境中）：
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. 启动后端服务（默认 8000 端口）：
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

3. 打开前端：将 `frontend/index.html` 放置到可访问的 Web 目录（或直接用浏览器打开文件），默认向当前域名的后端接口发起请求。

4. 可选：设置 DeepSeek API Key（若不设置则使用示例反馈与 92 分）：
   ```bash
   export DEEPSEEK_API_KEY=your_key
   ```

## 功能演示

- **批量导入**：在前端输入 JSON 学生列表与默认密码，点击「导入学生」。
- **登陆**：使用学号+默认密码登陆，获取令牌。
- **上传批改**：上传 `.docx` 报告后自动调用模型生成反馈并将红色文本框写入封面，返回成绩与报告 ID。
- **下载批注版**：通过 `/api/reports/{id}/download?token=xxx` 获取批注后的文件。
- **统计报表**：点击「刷新统计」查看提交数量、平均成绩及明细。

> 说明：会话令牌保存在内存，重启服务后需要重新登陆；数据库使用 SQLite，适合示例与小规模使用，可根据需求替换为其他引擎。
