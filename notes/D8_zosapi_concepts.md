Python 控制 Zemax 的最小连接流程

[打开 Zemax OpticStudio]
        ↓
[选择 Programming → Interactive Extension]
        ↓
[Zemax 等待外部 Python 连接]
        ↓
[运行 Python ZOS-API 连接脚本]
        ↓
[Python 获取 TheApplication]
        ↓
[Python 获取 TheSystem]
        ↓
[通过 TheSystem.LDE 访问 Lens Data Editor]
        ↓
[读取表面数量、曲率、厚度、材料等参数]
        ↓
[后续可继续修改参数 / 运行分析 / 导出结果]

# D8 ZOS-API / Python 概念入门

## 今日目标
理解 Python 与 Zemax ZOS-API 的连接方式，区分 Interactive Extension 和 Standalone，理解 TheSystem 与 LDE 的作用。

## 关键概念
- ZOS-API：
- Interactive Extension：
- Standalone：
- TheApplication：
- TheSystem：
- LDE：

## 最小连接流程
见下方流程图：

[打开 Zemax] -> [启动 Interactive Extension] -> [运行 Python 脚本] -> [获取 TheSystem] -> [访问 LDE]

## 今日疑问
1.
2.

## 明天 D9 要做
跑通一个官方 Python 示例脚本。


## ZOS-API 是什么                                                                                                                                                                    
ZOS-API 是 Zemax OpticStudio 的自动化接口。
Python 可以通过 ZOS-API 控制 OpticStudio，例如：
- 打开镜头文件
- 读取 LDE 表面参数
- 修改厚度、曲率、材料
- 运行 MTF、Spot Diagram 等分析
- 导出结果数据或图片


## Interactive Extension 和 Standalone 的区别
Interactive Extension：
先打开 Zemax，再让 Python 连接当前打开的软件。
优点是界面可见，适合学习和调试。
Standalone：
Python 自己启动 Zemax，在后台跑。
优点是适合自动化、批量扫描和无人值守运行。
我现在优先学 Interactive Extension，后面参数扫描再学 Standalone。

## ZOS-API 最小对象关系
TheConnection：负责连接 Zemax。
TheApplication：代表 OpticStudio 软件。
TheSystem：代表当前打开的光学系统。
TheSystem.LDE：代表 Lens Data Editor，可以读取和修改表面参数。