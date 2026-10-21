# 工具参数 JSON Schema 首次演示

日期：2026-10-21。学习者已独立通过 15 项参数校验与工具测试，并明确请求学习如何用 JSON Schema 向模型描述工具。

AI 保存参数描述到 experiment_agent/tools/read_text_file.schema.json，并创建 labs/l05_tool_schema.py。参数字段为 relative_path；规则包括 object、properties、required、string、minLength、pattern 和 additionalProperties。

本次使用内部工具描述格式，外层 name / description / parameters 并不作为所有模型 API 的统一格式承诺。接入真实模型服务时须按其字段和 Schema 支持范围适配。

AI 在 agent-study 环境实际执行 `python -X utf8 -m labs.l05_tool_schema`，成功解析并显示说明。手工正常请求返回 success；额外 project_root 请求经已有 Python 校验返回 invalid_arguments。进程退出码为 0。

本次未改动运行时或参数校验器，也未安装 JSON Schema 验证库；json.loads 仅解析 JSON，不能据此声称自动执行了通用 Schema 校验。没有调用模型 API。15 项测试通过的证据来自学习者刚提供的运行，本次未无必要地重复。

参数规则参考 2026-10-21 已访问的 JSON Schema 官方对象和字符串文档，链接见 lessons/06-tool-json-schema.md。文件存在、实际路径归属和权限仍由本地工具核验。

学习者已提供独立运行 Schema 演示的输出；正确判断全空白字符串不会被 minLength:1 拒绝，经过讲解后正确判断 "   a   " 满足 minLength 和 pattern。关于 strip，已补充它只去两端空白且返回新字符串，不原地修改输入。进入模拟模型驱动的工具闭环。
