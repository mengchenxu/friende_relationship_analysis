# Friend Relationship Analysis

分析一对一聊天记录，量化并理解人际关系的本地桌面工具。

## Language

### 数据层

**Contact**（联系人）:
一个参与聊天的个体。同一真实人物可拥有多个 Contact（如微信版本和 QQ 版本），通过跨平台合并关联。
_Avoid_: 用户、好友、人员、Person

**Conversation**（对话）:
两个 Contact 之间全部聊天消息的容器。一条 Conversation 仅属于一对一私聊，不包含群聊。
_Avoid_: 聊天、会话、Session、Chat

**Message**（消息）:
Conversation 中的一条发言。包含发送者、文本内容、时间戳和消息类型。
_Avoid_: 发言、记录、文本、Record

### 导入层

**Adapter**（适配器）:
负责将特定平台的聊天记录导出格式转换为内部数据模型（Contact、Conversation、Message）的模块。每个平台对应一个 Adapter。
_Avoid_: 导入器、解析器、转换器、Importer

**Test Data**（测试数据）:
人工构造的、用于开发和验证分析引擎的模拟聊天记录。不来自任何真实平台。
_Avoid_: 假数据、Mock 数据

### 分析层

**Interaction Frequency**（互动频率）:
衡量对话活跃度的统计指标集合，包括消息总数、时间跨度、日均消息数、消息密度趋势、沉默期识别。纯统计算法，不依赖 NLP 或大模型。
_Avoid_: 聊天频率、活跃度

**Reciprocity**（关系对等度）:
衡量对话双方投入程度是否均衡的指标集合，包括发起对话次数比、回复速度比、消息长度比。纯统计算法。
_Avoid_: 公平度、对称性、Balance

**Profile**（画像）:
从聊天记录中推断出的对方特征，包括性格特征、话题态度倾向和观点摘录。通过大模型（脱敏后）批量分析生成。
_Avoid_: 人物画像、用户画像、Persona、Character

**Relationship Stage**（关系阶段）:
对话双方当前所处的关系阶段判定（如活跃期、稳定期、冷却期）。MVP 阶段基于互动频率和对等度指标判定，预留大模型定性分析接口。
_Avoid_: 关系状态、亲密度等级

### 隐私层

**Sanitization**（脱敏）:
在聊天内容离开本地环境（发送至大模型 API）之前，移除或替换可识别个人身份的信息。MVP 阶段仅做人名替换，敏感信息过滤留待后续。
_Avoid_: 去标识化、匿名化、混淆

## References

所有分析指标的学术依据存放于 `references/` 目录，按模块组织。v1 阶段留空，后续由用户填入。
