# 函数调用图生成器使用说明

## 环境要求

1. Python 3.8+
   - 安装依赖：`pip install -r requirements.txt`

2. Node.js 14+
   - 安装依赖：`cd agents && npm install`
   - 编译TypeScript：`cd agents && npm run build`

3. Frida
   - 安装Frida工具：`pip install frida-tools`
   - 在目标设备上安装Frida服务器

## 快速开始

1. 配置目标应用
   编辑 `configs/target_apps.yaml`：
   ```yaml
   apps:
     - name: "示例应用"
       package_name: "com.example.app"
       platform: "android"
       hooks:
         - module: "libc"
           functions:
             - "malloc"
             - "free"
   ```

2. 运行追踪器
   ```bash
   python main.py --config configs/target_apps.yaml --package com.example.app
   ```

3. 查看结果
   - 调用图将保存在 `outputs/graphs/` 目录下
   - 支持JSON和GraphML格式
   - 可以使用工具如Gephi可视化GraphML文件

## 命令行参数

- `--config`, `-c`: 配置文件路径（必需）
- `--device`, `-d`: 设备ID（可选，默认使用第一个可用设备）
- `--package`, `-p`: 目标应用包名（可选，如果配置文件中只有一个应用）
- `--output`, `-o`: 输出目录（默认：outputs）
- `--log-level`, `-l`: 日志级别（默认：INFO）

## 配置文件说明

### 目标应用配置 (target_apps.yaml)

```yaml
apps:
  - name: "应用名称"
    package_name: "应用包名"
    platform: "android"  # 或 "ios"
    hooks:
      - module: "模块名"
        functions:
          - "函数名1"
          - "函数名2"
    filters:
      include:
        - "包含模式"
      exclude:
        - "排除模式"
```

### 过滤规则配置 (filter_rules.json)

```json
{
  "global_filters": {
    "include_patterns": ["^[a-zA-Z_][a-zA-Z0-9_]*$"],
    "exclude_patterns": ["^_", "^\\$"]
  },
  "module_specific_filters": {
    "libc": {
      "include": ["malloc", "free"],
      "exclude": ["_*"]
    }
  },
  "call_depth_limit": 10,
  "min_call_count": 1,
  "max_call_count": 1000
}
```

## 输出文件说明

### JSON格式

```json
{
  "nodes": [
    {
      "id": "模块名!函数名",
      "name": "函数名",
      "module": "模块名",
      "call_count": 调用次数,
      "total_duration": 总耗时,
      "avg_duration": 平均耗时
    }
  ],
  "edges": [
    {
      "source": "调用者ID",
      "target": "被调用者ID",
      "call_count": 调用次数,
      "total_duration": 总耗时,
      "avg_duration": 平均耗时
    }
  ],
  "metadata": {
    "total_calls": 总调用次数,
    "start_time": "开始时间",
    "end_time": "结束时间",
    "duration": 持续时间
  }
}
```

### GraphML格式

- 可以使用Gephi等工具打开
- 包含完整的节点和边属性
- 支持可视化分析

## 常见问题

1. 设备连接问题
   - 确保设备已通过USB连接
   - 检查ADB设备列表：`adb devices`
   - 验证Frida服务器是否运行：`frida-ps -U`

2. 应用启动问题
   - 确保包名正确
   - 检查应用是否已安装
   - 尝试手动启动应用

3. 性能问题
   - 使用过滤规则减少追踪范围
   - 调整调用深度限制
   - 设置最小调用次数阈值

## 开发说明

1. 添加新的Hook
   - 在 `agents/src/custom-hooks/` 下创建新的Hook文件
   - 实现Hook逻辑
   - 在配置文件中引用

2. 扩展功能
   - 修改 `core/processor.py` 添加新的处理逻辑
   - 更新 `main.py` 添加新的命令行参数
   - 在 `docs/` 下更新文档

## 注意事项

1. 性能影响
   - 追踪会显著影响应用性能
   - 建议在测试环境中使用
   - 适当设置过滤规则

2. 数据安全
   - 注意保护敏感信息
   - 及时清理输出文件
   - 遵守相关法律法规

3. 兼容性
   - 不同Android版本可能需要不同的Hook方式
   - iOS设备需要越狱
   - 某些应用可能有反调试保护 