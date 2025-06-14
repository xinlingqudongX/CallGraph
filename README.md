### 项目需求
- 创建一个使用frida配合ts的方式追踪应用函数调用并生成关系图的项目

### 项目结构
frida-call-graph/
├── agents/                  # Frida脚本模块
│   ├── src/                 # TypeScript源码
│   │   ├── core-tracer.ts   # 核心追踪逻辑
│   │   ├── module-loader.ts # 动态加载模块
│   │   └── custom-hooks/    # 特定库的Hook脚本
│   │       ├── android.ts
│   │       ├── libc.ts
│   │       └── react-native.ts
│   ├── dist/                # 编译后的JavaScript
│   ├── types/               # 类型定义
│   │   ├── frida.d.ts       # Frida API类型定义
│   │   └── custom.d.ts      # 自定义类型
│   ├── tsconfig.json        # TypeScript配置
│   └── package.json         # 依赖管理
├── core/                    # Python核心处理逻辑
│   ├── tracer.py            # Frida设备管理&脚本注入
│   ├── processor.py         # 原始数据处理
│   ├── graph_builder.py     # 调用图生成
│   └── visualizer.py        # 可视化输出
├── outputs/                 # 生成文件存储
│   ├── graphs/              # 可视化图表
│   └── logs/                # 原始数据记录
├── configs/                 # 配置文件
│   ├── target_apps.yaml     # 目标应用配置
│   └── filter_rules.json    # 函数过滤规则
├── utils/                   # 工具脚本
│   ├── adb_helper.py        # ADB设备管理
│   ├── report_generator.py  # PDF报告生成
│   └── symbol_resolver.py   # 符号反混淆
├── tests/                   # 测试目录
│   ├── agent_tests/         # Frida脚本测试
│   └── core_tests/          # Python核心逻辑测试
├── scripts/                 # 构建和开发脚本
│   ├── build.sh             # 构建脚本
│   └── dev.sh               # 开发环境脚本
├── main.py                  # 主入口脚本
├── requirements.txt         # Python依赖
└── README.md                # 项目文档
