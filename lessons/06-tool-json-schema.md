# 第 6 次动手：用 JSON Schema 描述工具参数

## 本课目标

学习者已独立复跑参数校验，提供额外 project_root 被拒绝的输出和 15 项测试通过的结果。接下来把参数规则写成可序列化的描述，为模型接入准备输入接口。

先区分三个东西：工具说明、调用请求、执行结果。Schema 是工具说明里描述输入参数结构的部分；不会读取文件，也不会自己调用 Python 函数。

## 一份工具说明包含什么

本课使用本项目内部描述格式：

```json
{
  "name": "read_text_file",
  "description": "读取项目内的 UTF-8 文本文件，用于查看代码、配置或日志。",
  "parameters": {
    "type": "object",
    "properties": {
      "relative_path": {
        "type": "string",
        "description": "相对于项目根目录的文件路径。",
        "minLength": 1,
        "pattern": "\\S"
      }
    },
    "required": ["relative_path"],
    "additionalProperties": false
  }
}
```

name 帮助选择工具，description 说明什么时候使用，parameters 内的 JSON Schema 说明怎样填写参数。具体模型 API 的外层字段和支持的 Schema 子集可能不同，接入时按该提供方文档适配，本课尚未选择服务商。

## 关键字逐个对应到已有 Python 检查

| Schema | 规则 | 已有程序检查 |
| --- | --- | --- |
| type: object | 参数是 JSON 对象 | isinstance(arguments, dict) |
| properties | 声明已知字段及字段规则 | 本工具接受 relative_path |
| required: [relative_path] | 必须提供该字段 | 检查字段存在 |
| 字段 type: string | 值必须是字符串 | isinstance(value, str) |
| minLength: 1 | 字符串长度至少为 1 | 拒绝空字符串 |
| pattern: \\S | 至少包含一个非空白字符 | 本项目的非空白输入规则 |
| additionalProperties: false | 禁止 properties 之外的字段 | 拒绝额外 project_root 等字段 |

properties 默认不代表必填，需要 required；额外字段默认允许，需要 additionalProperties: false 禁止。参考 [JSON Schema 官方对象文档](https://json-schema.org/understanding-json-schema/reference/object)。

minLength 计算字符串长度，空格也计入；pattern 的正则表达式可匹配字符串任意位置，因此 \\S 表示至少有一个非空白字符。JSON 中反斜杠需要转义，所以源码写成 "\\S"。参考 [官方字符串文档](https://json-schema.org/understanding-json-schema/reference/string)。

本项目仍以 Python 校验与路径检查作为实际执行判据；不同模型服务和验证器的正则/Unicode 细节在实际接入时测试，不宣称跨实现的所有 Unicode 空白语义完全相同。

## Schema 和真实世界状态的边界

`{"relative_path": "labs/fixtures/missing.txt"}` 在结构上符合规则，但文件读取仍会返回 file_not_found。

`{"relative_path": "../outside-demo.txt"}` 也可能符合这个参数 Schema；实际解析后的目录归属由文件工具检查，返回 path_outside_project。description 中写“项目内”是使用说明，不等于自动完成文件权限校验。

project_root 不列为模型参数，由程序配置并绑定到注册表。模型生成调用请求后，程序仍检查名称、参数和文件范围，再执行工具。

## 文件和运行

参数 Schema：experiment_agent/tools/read_text_file.schema.json。

演示：labs/l05_tool_schema.py。

```bat
python -X utf8 -m labs.l05_tool_schema
```

演示先打印准备提供给模型的工具说明，再把两条手工请求交给当前运行时：正常读取成功、额外 project_root 返回 invalid_arguments。

本课仍使用标准库。json.loads 确认 JSON 能被解析，不是通用 JSON Schema 验证器；运行中的校验仍由已有 validate_read_text_arguments 执行。没有调用模型 API，也没有让模型实际选择工具。

## 本轮练习

只考虑 Schema 规则：如果删除 pattern，只保留 minLength: 1，值 "   " 会不会被拒绝？为什么？先口头判断，不修改已有文件。

回答后，把工具说明与模拟模型、工具请求、观察结果接成第一个小循环。
