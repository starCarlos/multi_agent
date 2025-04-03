# 企业智能机器人

基于LangGraph构建的企业智能机器人系统，实现多Agent协同工作流。

## 功能特点

1. **混合数据架构**
   - ChromaDB向量引擎：处理非结构化文档（需求文档/会议纪要）
   - SQLite关系型存储：用户交互记录/报价历史/项目跟踪

2. **五维Agent协同网络**
   - 入口Agent：推理问题解决步骤，调用不同agent，也算意图识别分类
   - 需求分析师Agent：文档解析与需求拆解
   - 成本测算Agent：工时模型+报价矩阵
   - 企业智库Agent：公司知识图谱查询
   - 通用对话Agent：GPT-4级自然交互

3. **智能路由网关**
   - 动态决策树实现毫秒级任务分发

## 工作流逻辑

```
graph TD
    A[用户输入] --> B{入口意图分类器}
    B -->|需求相关| C[ChromaDB语义检索]
    B -->|报价测算| D[历史项目数据库]
    B -->|公司咨询| E[企业知识库]
    B -->|通用对话| F[LLM生成]
    C --> G[需求拆解引擎]
    D --> H[成本计算模型]
    E --> I[精准知识检索]
    G & H & I --> J[结构化输出组装]
```

## 安装与配置

1. 克隆仓库

```bash
git clone <repository-url>
cd multi_agent
```

2. 安装依赖

```bash
pip install -r requirements.txt
```

3. 配置环境变量

```bash
cp .env.example .env
# 编辑.env文件，填入必要的配置信息
```

4. 运行应用

```bash
python main.py
```

## 项目结构

```
.
├── data/               # 数据存储目录
│   ├── chroma/        # ChromaDB向量数据
│   └── enterprise.db  # SQLite数据库
├── agents/            # Agent实现
│   ├── classifier.py  # 分类Agent
│   ├── analyzer.py    # 需求分析Agent
│   ├── estimator.py   # 成本测算Agent
│   ├── knowledge.py   # 企业智库Agent
│   └── general.py     # 通用对话Agent
├── workflows/         # 工作流定义
│   ├── router.py      # 智能路由网关
│   └── graph.py       # 工作流图定义
├── models/            # 数据模型
│   ├── schema.py      # 数据模型定义
│   └── database.py    # 数据库操作
├── api/               # API接口
│   ├── routes.py      # 路由定义
│   └── server.py      # 服务器配置
├── utils/             # 工具函数
│   ├── logger.py      # 日志工具
│   └── helpers.py     # 辅助函数
|── docs/              # 知识库文档存放目录
├── config.py          # 配置文件
├── main.py            # 主程序入口
├── .env.example       # 环境变量示例
└── requirements.txt   # 依赖列表
```

## 使用示例

```python
from api.server import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 许可证

MIT
