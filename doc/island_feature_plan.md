# 岛屿功能扩展设计文档

> 本文档记录岛屿模块新增功能的详细设计方案。

---

## 实现进度 TODO

- [ ] **功能1**: 摸猫/JUU速运任务 — 每日互动任务
- [ ] **功能2**: 自动清空开发季商店 — 花光开发季 PT 买空商店
- [ ] **功能3**: 给三个小人打招呼 — NPC 互动
- [ ] 配置系统：更新 [`argument.yaml`](module/config/argument/argument.yaml) 和 [`task.yaml`](module/config/argument/task.yaml)
- [ ] i18n：更新翻译文件
- [ ] 运行配置生成器

---

## 目录

1. [功能1: 摸猫/JUU速运任务](#功能1-摸猫juu速运任务)
2. [功能2: 自动清空开发季商店](#功能2-自动清空开发季商店)
3. [功能3: 给三个小人打招呼](#功能3-给三个小人打招呼)
4. [配置变更总览](#配置变更总览)
5. [任务调度集成](#任务调度集成)

---

## 功能1: 摸猫/JUU速运任务

### 目标

每日在岛屿上执行两个小互动：

1. **摸猫**: 点击岛上出现的猫，获得好感度和随机奖励
2. **JUU速运**: 在岛屿场景中找到并点击啾啾速运的NPC/建筑物，领取或提交速运任务

### 设计方案

**新文件**: [`module/island/island_daily_interact.py`](module/island/island_daily_interact.py)

#### 核心类: `IslandDailyInteract`

```python
class IslandDailyInteract(Island):
    """每日互动任务：摸猫、JUU速运"""
    
    def run(self):
        """执行每日互动"""
        self.goto_island()
        self.pet_cat()
        self.juu_express()
    
    def pet_cat(self):
        """
        摸猫流程：
        1. 在岛屿主场景中寻找猫
        2. 猫会随机出现在岛屿各个位置
        3. 通过模板匹配检测猫
        4. 点击猫 → 出现互动弹窗
        5. 点击"抚摸"按钮
        6. 关闭奖励弹窗
        """
    
    def juu_express(self):
        """
        JUU速运流程：
        1. 在岛屿场景中寻找JUU速运点
        2. 通常在地图固定位置
        3. 点击进入速运界面
        4. 领取已完成速运的奖励
        5. 如果有可用速运，接受
        """
```

#### 摸猫检测

- 猫的图像模板存储在 [`assets/`](assets/) 中
- 猫可能出现在多个位置，使用模板匹配扫描全屏
- 如果没有检测到猫，说明已经被摸过了或不在场景中

#### JUU速运检测

- JUU速运在岛屿地图上有固定位置的建筑物/NPC
- 需要先进入岛屿场景，然后寻找速运入口
- 速运界面有：领取奖励、查看速运列表

#### 配置项

```yaml
IslandDailyInteract:
  PetCat: true               # 启用摸猫
  JuuExpress: true           # 启用JUU速运
```

---

## 功能2: 自动清空开发季商店

### 目标

开发季活动期间，自动进入开发季商店，用金币买空商店中有价值的物品（如"开发核心""繁荣之基""发展支柱"等）。

### 设计方案

**新文件**: [`module/island/island_dev_shop.py`](module/island/island_dev_shop.py)

#### 核心类: `IslandDevShop`

```python
class IslandDevShop(Island):
    """自动清空开发季商店"""

    # 购买优先级：稀有物品优先
    PURCHASE_PRIORITY = [
        'development_core',      # 开发核心（高价值）
        'prosperity_foundation', # 繁荣之基
        'development_pillar',    # 发展支柱
        # ... 其他物品按价值降序
    ]

    def run(self):
        """检查金币 → 进入开发季商店 → 按优先级购买 → 花光金币"""
```

#### 流程

```
run()
  ├── goto_island_shop()
  ├── switch_to_dev_shop_tab()         # 切换到开发季商店页签
  ├── detect_gold()                    # OCR 当前持有金币数量
  ├── if gold == 0: return             # 没钱就跳过
  │
  ├── scan_shop_items()                # 扫描商店中所有可购买物品
  │     ├── 模板匹配识别物品图标
  │     └── OCR 物品价格（金币数）
  │
  ├── generate_purchase_plan()         # 按优先级生成购买计划
  │     ├── 优先购买稀有物品（开发核心等）
  │     ├── 剩余金币购买常规资源
  │     └── 金币不够买高优物品时跳过
  │
  └── execute_purchase_plan()          # 执行购买
        ├── click_item()
        ├── confirm_purchase()
        └── repeat until gold runs out
```

#### 金币检测

```python
def detect_gold(self):
    """OCR 检测当前持有金币数量（在商店页面顶部显示）"""
    ocr = Digit(OCR_GOLD, letter=(255, 255, 255), threshold=200)
    return ocr.ocr(self.device.image)
```

#### 购买优先级配置

```yaml
IslandDevShop:
  Enabled: true                # 启用自动清空
  ReserveGold: 0               # 保留金币数量（不花光）
```

#### 物品识别

- 使用模板匹配识别开发季商店中的各个物品
- 物品图标需要从游戏中截图后通过 [`button_extract.py`](dev_tools/button_extract.py) 提取

#### 配置项

```yaml
IslandDevShop:
  Enabled: true
  ReserveGold: 0
```

---

## 功能3: 给三个小人打招呼

### 目标

岛屿场景中会出现三个可互动的小人（NPC/游客），点击给他们打招呼可以获得友好度或小奖励。

### 设计方案

在 [`module/island/island_daily_interact.py`](module/island/island_daily_interact.py) 中扩展。

#### 核心逻辑

```python
def greet_npcs(self):
    """
    给三个小人打招呼流程：
    1. 进入岛屿主场景
    2. 扫描场景中出现的 NPC 小人
    3. 小人有三种类型/位置
    4. 依次点击每个小人
    5. 点击"打招呼"按钮
    6. 关闭弹窗
    """
    
    NPC_TEMPLATES = [
        TEMPLATE_NPC_1,   # 小人1的模板
        TEMPLATE_NPC_2,   # 小人2的模板
        TEMPLATE_NPC_3,   # 小人3的模板
    ]
```

#### NPC 检测

- 三个小人在岛屿场景中的固定或半固定位置
- 使用模板匹配检测
- 可能出现在不同区域，需要扫描
- 如果已被打过招呼，小人可能消失或变为不同状态

#### 挑战与注意事项

1. 小人可能不在当前屏幕视口中，需要滑动地图寻找
2. 小人出现有随机性，不是每天都会出现
3. 点击后的弹窗需要处理

#### 配置项

```yaml
IslandDailyInteract:
  GreetNpcs: true            # 启用打招呼
  GreetNpcCount: 3           # 打招呼数量
```

---

## 配置变更总览

### [`argument.yaml`](module/config/argument/argument.yaml) 新增配置

```yaml
# ==================== Island 新增配置 ====================

IslandDevShop:
  Enabled: true
  ReserveGold: 0

IslandDailyInteract:
  PetCat: true
  JuuExpress: true
  GreetNpcs: true
  GreetNpcCount: 3
```

---

## 任务调度集成

各岛屿任务作为 `Island` 组下的独立任务，由 [`alas.py`](alas.py) 调度器按标准流程运行。
关键在于各任务模块内部自行处理运行频率和状态判断，调度器仅负责按配置触发。

### 优先级参考

```
低频率（按条件触发）：
  摸猫/速运/打招呼（每日一次）
  每日采集（每日一次）
  开发季商店清空（开发季活动期间）
```

---

## 文件结构变化

```
module/island/
├── island.py                    # 已有 - 核心类
├── island_dev_shop.py           # 新增 - 开发季商店清空
├── island_daily_interact.py     # 新增 - 摸猫/速运/打招呼
├── assets.py                    # 已有 - 通用按钮资源
├── ...
```

---

## i18n 新增 Key

在 [`zh-CN.json`](module/config/i18n/zh-CN.json) 等翻译文件中新增：

```json
{
  "Island.IslandDevShop.Enabled": "启用开发季商店清空",
  "Island.IslandDevShop.ReserveGold": "保留金币数量",
  "Island.IslandDailyInteract.PetCat": "摸猫",
  "Island.IslandDailyInteract.JuuExpress": "JUU速运",
  "Island.IslandDailyInteract.GreetNpcs": "打招呼"
}
```

---

## 实现优先级

| 优先级 | 功能 | 预计工作量 |
|--------|------|-----------|
| P2 | 摸猫/JUU速运 | 中（需截图资源） |
| P2 | 开发季商店清空 | 中（需截图） |
| P3 | 打招呼 | 中（需截图资源） |

> **注意**: 摸猫、JUU速运、给小人打招呼等功能需要游戏内截图资源（Button/Template），需先通过 `dev_tools/button_extract.py` 从截图中提取按钮定义才能实现。
