# 可选证据检查器

当任务需要保存正式检查记录或防止引用过期文件时，可使用 `review`。普通制作、局部修改、看图判断都不要求运行它，也不要求创建 quality.yml。检查方式、范围和投入由用户要求与模型判断决定。

`review <record.yml> --out <dir>` 只检查调用者列出的事项和文件 hash；不自动判断设计、审美或规范合规。它不会补入建筑检查项，也不要求四个固定维度。

## 输入接口（仅调用此工具时使用）

```yaml
schema_version: 1
task: 本次需要留档的检查
criteria:
  - id: requested-labels
    dimension: translation  # 可选自由分类；也可省略
    requirement: 图例采用用户指定的英文名称
    basis: 用户提供的译名表
    status: pass
    observation: 实际复核后的具体发现
    evidence:
      - file: figure.svg
        sha256: 文件实际SHA256
```

一次调用至少提供一个 criterion；ID 唯一，requirement/basis/observation 非空。`modules` 与 `dimension` 均为可选描述，不限制取值。旧版四维记录仍可读取。

`pass` 需要存在且 hash 匹配的证据文件；`not_applicable` 通过 observation 描述原因。`fail`、`pending`、丢失或过期证据使这次检查返回错误。输出 quality-report.json/md 的 `evidence_complete` 只表示所提交记录通过这些完整性检查，不是作品质量评分，也不代表用户任务已完成。

不需要留档时，可以直接观察成果、测量所关心的内容或使用其他检查方法。无需为未采用本检查器另写解释。
