# 实验报告管理平台

该项目提供一个面向 C 语言课程实验的在线实验报告管理系统，支持以下功能：

- 学生通过学号登录提交 Word (`.docx`) 实验报告。
- 管理员通过 Excel 导入学生名单、创建实验、查看提交情况并导出成绩统计。
- 系统模拟调用大模型，根据实验报告内容自动生成成绩与评语。
- 自动将红色字体的成绩与评语添加到 Word 报告首页，并提供下载。

## 快速开始

### 1. 创建并激活虚拟环境（可选）

```bash
python -m venv .venv
source .venv/bin/activate  # Windows 使用 .venv\\Scripts\\activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动开发服务器

```bash
flask --app app:create_app run --debug
```

访问 <http://127.0.0.1:5000> 即可体验系统。首次运行时系统会自动创建默认管理员账号 `admin`/`admin123`。

## 功能说明

### 管理员

- 使用默认管理员账号登录后，可在控制台上传 Excel 学生名单（需包含 `student_number`、`name`、`password` 三列）。
- 可创建 8 次实验（或更多），查看各实验的提交情况，下载带评语的报告。
- 支持导出单次实验的成绩统计为 Excel 文件。

### 学生

- 使用学号与初始密码登录后，可查看所有实验并上传 Word 报告。
- 每次提交后系统会自动生成成绩与评语，并在文档首页插入红色字体标注。
- 学生可下载带评语的报告或重新提交覆盖之前的结果。

## 评分与评语逻辑

项目通过 `app/services.py` 中的 `evaluate_report` 函数模拟大模型打分：

- 根据文档中是否包含“实验目的”、“实验原理”等关键字奖励得分。
- 在基础分 60 上进行浮动，最高不超过 100 分。
- 生成结构化的中文评语，并传递给 `annotate_report` 函数写入 Word 首页面。

如需接入真实大模型，可在 `evaluate_report` 中调用实际的 API，并保持返回 `(score, feedback)` 的结构即可。

## 文件存储

- 原始文件存储在 `uploads/` 目录，带评语的文件存储在 `processed/` 目录。
- 目录位置可通过环境变量 `UPLOAD_FOLDER`、`PROCESSED_FOLDER` 配置。

## 开源协议

MIT License
