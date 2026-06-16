# 岛屿功能扩展设计文档

> 本文档记录岛屿模块新增功能的详细设计方案。

---

## 实现进度 TODO

- [ ] **功能1**: 摸猫/JUU速运/每周照相任务 — 每日与每周互动任务
- [ ] 配置系统：更新 [`argument.yaml`](module/config/argument/argument.yaml) 和 [`task.yaml`](module/config/argument/task.yaml)
- [ ] i18n：更新翻译文件
- [ ] 运行配置生成器

---

## 目录

1. [功能1: 摸猫/JUU速运/每周照相任务](#功能1-摸猫juu速运每周照相任务)
2. [配置变更总览](#配置变更总览)
3. [任务调度集成](#任务调度集成)

---

## 功能1: 摸猫/JUU速运/每周照相任务

### 目标

在岛屿上执行每日与每周互动：

1. **摸猫**: 点击岛上出现的猫，获得好感度和随机奖励
2. **JUU速运**: 从开发计划页面检测 JUU 速运任务，按指定地点完成多段交付互动
3. **每周照相任务**: 从开发计划页面检测每周照相任务，执行三轮照相与空闲选择，领取奖励后循环清空

### 设计方案

**新文件**: [`module/island/island_daily_interact.py`](module/island/island_daily_interact.py)

#### 核心类: `IslandDailyInteract`

```python
class IslandDailyInteract(Island):
    """每日与每周互动任务：摸猫、JUU速运、每周照相"""
    
    def run(self):
        """执行每日与每周互动"""
        if self.config.IslandDailyInteract_PetCat:
            self.pet_cat()
        if self.config.IslandDailyInteract_JuuExpress:
            self.juu_express()
        if self.config.IslandDailyInteract_WeeklyPhoto:
            self.weekly_photo()
    
    def pet_cat(self):
        """
        摸猫流程：
        1. 通过地图传送到晨露农场
        2. 执行晨露农场移动方法，当前先置空，等待实测补充路线
        3. 移动结束后识别摸猫互动按钮，识别到则点击
        4. 点击后尝试识别奖励领取界面，识别到则点击安全区域关闭
        5. 奖励界面可能不存在，未识别到不视为失败
        """
    
    def juu_express(self):
        """
        JUU速运流程：
        1. 进入开发计划页面
        2. 识别 JUU 速运任务特征图标，存在则点击
        3. 识别点击后的 check 图标，若通过则点击 check
           - check 必须使用单独 Button 资源，修正点击范围
        4. 点击 check 后会传送到港口地图
        5. 依次执行港口、港口商区、栖风原野、繁荫农圃四段交付
        6. 每段交付都使用统一流程：
           a. 通过地图传送到目标地点
           b. 执行目标地点移动方法，当前先置空，等待实测补充路线
           c. 移动结束后识别交互按钮
           d. 识别到则点击；未识别到则重新从地图传送到该地点并重试一次
           e. 点击成功后识别跳过按钮并点击
           f. 跳过处理必须模仿每日订单/好友补给的保护逻辑，避免多点后误打开手机界面
        7. 四段交付完成后尝试识别奖励领取界面
        8. 奖励界面识别不到也可以接受，最后点击两次岛屿安全区域结束流程
        """

    def weekly_photo(self):
        """
        每周照相任务流程：
        1. 进入手机界面并打开开发计划页面
        2. 识别每周照相任务特征图标，存在则点击
        3. 识别点击后的 check 图标，若通过则点击 check
           - check 同样使用单独 Button 资源，修正点击范围
        4. 点击 check 后进入任务执行页面
        5. 执行三轮：
           a. 识别照相按钮并点击
           b. 识别空闲按钮并点击
        6. 三轮完成后识别奖励领取按钮，识别到则点击领取
        7. 如果奖励领取按钮识别不到，可以识别 `ISLAND_BACK` 直接退出
        8. 退出后重新进入手机界面和开发计划页面
        9. 重复上述流程，直到开发计划页面识别不到每周照相任务特征图标
        """

    def juu_express_location_flow(self, destination, move_method, interact_button):
        """
        单个 JUU 速运地点的通用交付流程。

        destination:
            island_map_goto() 的目标地点，例如 port、assembly、farm、nursery。
            后续若新增近似任务，只需要替换地点序列、移动方法和交互按钮。
        move_method:
            当前全部置空，不做实际移动；实测后补入每个地点自己的移动路线。
        interact_button:
            目标地点交互按钮。识别到点击，识别不到则重新传送到同地点并重试一次。
        """

    def move_for_juu_port(self):
        """JUU速运：港口移动路线，待实测后补充。"""

    def move_for_juu_port_business(self):
        """JUU速运：港口商区移动路线，待实测后补充。"""

    def move_for_juu_plain(self):
        """JUU速运：栖风原野移动路线，待实测后补充。"""

    def move_for_juu_nursery(self):
        """JUU速运：繁荫农圃移动路线，待实测后补充。"""

    def move_for_pet_cat_farm(self):
        """摸猫：晨露农场移动路线，待实测后补充。"""
```

#### 摸猫检测

- 摸猫不再全屏扫描随机猫模板，改为固定通过地图前往晨露农场
- 晨露农场移动路线暂时置空，等待实测补充
- 移动结束后识别摸猫互动按钮并点击
- 点击后只尝试处理奖励领取界面；奖励可能不存在，未出现不阻断任务

#### JUU速运检测

- 入口不从岛屿场景寻找，改为从开发计划页面识别 JUU 速运任务特征图标
- 点击任务图标后必须二次识别 check 图标，只有 check 通过才点击
- check 图标需要单独生成 Button 资源，用于修正点击范围，避免直接复用任务特征图标的点击区域
- 点击 check 后进入港口地图，再开始地点交付流程
- 地点交付顺序：
  1. 港口
  2. 港口商区
  3. 栖风原野
  4. 繁荫农圃
- 每个地点都采用“地图传送 → 空移动 → 识别交互按钮 → 未识别则重传送重试一次 → 点击后跳过”的统一模板
- 跳过按钮处理需要先判断当前仍在剧情/对话跳过界面，再点击跳过；点击后等待返回岛屿场景或地图相关 check，防止多次点击误打开手机界面
- 还有一个任务与 JUU 速运流程几乎一致，仅地点序列和移动方法不同；实现时应将“地点流程”抽为可配置列表，等待后续刷到任务后补充具体配置

#### 通用流程抽象

```python
JUU_EXPRESS_STEPS = [
    {
        "name": "港口",
        "destination": "port",
        "move": move_for_juu_port,
        "button": JUU_EXPRESS_PORT_INTERACT,
    },
    {
        "name": "港口商区",
        "destination": "port_business",
        "move": move_for_juu_port_business,
        "button": JUU_EXPRESS_PORT_BUSINESS_INTERACT,
    },
    {
        "name": "栖风原野",
        "destination": "plain",
        "move": move_for_juu_plain,
        "button": JUU_EXPRESS_PLAIN_INTERACT,
    },
    {
        "name": "繁荫农圃",
        "destination": "nursery",
        "move": move_for_juu_nursery,
        "button": JUU_EXPRESS_NURSERY_INTERACT,
    },
]
```

- `port_business` 需要新增地图按钮资源，并补进 `island_map_goto()` 的目的地映射
- `plain` 直接复用现成的 `ISLAND_MAP_MINE_FOREST` 作为栖风原野入口，不再新增独立地图按钮
- 所有 `move_for_*` 方法先保留空实现，不做点击、不做滑动、不加临时坐标
- 与 JUU 类似的新任务不要复制整段流程，应新增步骤列表复用 `juu_express_location_flow()`

#### 每周照相任务

- 每周照相任务由 `IslandDailyInteract_WeeklyPhoto` 配置开关控制，用户可选择是否启用
- 每周照相任务前半段与 JUU 速运一致：
  1. 进入手机界面
  2. 点击开发计划页面
  3. 识别任务特征图标
  4. 点击任务特征图标
  5. 识别并点击独立的 check 图标
- 点击 check 后不进入 JUU 的地图交付流程，而是进入照相流程
- 照相流程固定往复三次：点击照相按钮 → 点击空闲按钮
- 三次完成后优先识别奖励领取按钮并点击；如果识别不到奖励领取按钮，则识别 `ISLAND_BACK` 并直接退出
- 退出后必须重新进入手机界面和开发计划页面，再次检测每周照相任务；直到任务特征图标识别不到才结束
- 每次重新进入开发计划页面后都重新截图检测，不复用旧截图状态

#### 跳过与奖励处理

- 跳过按钮点击必须设置点击间隔，并在循环中优先检测返回状态
- 跳过期间如果检测到 `ISLAND_PHONE_CHECK`，说明可能误入手机页面，应立即停止继续点击跳过并返回岛屿主场景
- 每段交互完成后的剧情跳过都使用同一方法，例如 `handle_island_story_skip_safely()`
- 奖励领取界面统一使用岛屿奖励检测逻辑，例如 `GET_ITEMS_ISLAND` / `ISLAND_GET`
- JUU 速运最终奖励界面可能不出现；流程末尾固定点击两次 `ISLAND_CLICK_SAFE_AREA` 后结束
- 摸猫奖励界面同样可能不出现；未识别到奖励时直接结束摸猫流程

#### 待生成资源

- 任务独有的特征图标、check 图标、交互按钮统一放在 `assets/cn/island_daily_interact/`，不放入通用 `assets/cn/island/`
- 只有岛屿通用按钮（如 `ISLAND_BACK`、`ISLAND_CLICK_SAFE_AREA`、`GET_ITEMS_ISLAND`、已有地图按钮等）继续放在 `assets/cn/island/`

| 资源名称 | 类型 | 用途 | 资源文件夹 |
|----------|------|------|------------|
| `ISLAND_MAP_PORT_BUSINESS` | Button | 港口商区地图目的地按钮 | `assets/cn/island/` |
| `ISLAND_MAP_PORT_BUSINESS_CHECK` | Button | 港口商区地图目的地确认按钮 | `assets/cn/island/` |
| `JUU_EXPRESS_NURSERY_INTERACT` | Button | 繁荫农圃交付点交互按钮 | `assets/cn/island_daily_interact/` |
| `JUU_EXPRESS_PLAIN_INTERACT` | Button | 栖风原野交付点交互按钮 | `assets/cn/island_daily_interact/` |
| `JUU_EXPRESS_PORT_BUSINESS_INTERACT` | Button | 港口商区交付点交互按钮 | `assets/cn/island_daily_interact/` |
| `JUU_EXPRESS_PORT_INTERACT` | Button | 港口交付点交互按钮 | `assets/cn/island_daily_interact/` |
| `JUU_EXPRESS_SKIP` | Button | JUU 速运剧情/对话跳过按钮，需带防误触手机页面逻辑 | `assets/cn/island_daily_interact/` |
| `JUU_EXPRESS_TASK_CHECK` | Button | 点击任务特征图标后的 check 图标，单独修正点击范围 | `assets/cn/island_daily_interact/` |
| `JUU_EXPRESS_TASK_ICON` | Button | 开发计划页面中 JUU 速运任务特征图标 | `assets/cn/island_daily_interact/` |
| `PET_CAT_FARM_INTERACT` | Button | 晨露农场摸猫互动按钮 | `assets/cn/island_daily_interact/` |
| `WEEKLY_PHOTO_CAMERA` | Button | 每周照相任务中的照相按钮 | `assets/cn/island_daily_interact/` |
| `WEEKLY_PHOTO_IDLE` | Button | 每周照相任务中的空闲按钮 | `assets/cn/island_daily_interact/` |
| `WEEKLY_PHOTO_REWARD` | Button | 每周照相任务完成后的奖励领取按钮 | `assets/cn/island_daily_interact/` |
| `WEEKLY_PHOTO_TASK_CHECK` | Button | 点击每周照相任务特征图标后的 check 图标，单独修正点击范围 | `assets/cn/island_daily_interact/` |
| `WEEKLY_PHOTO_TASK_ICON` | Button | 开发计划页面中每周照相任务特征图标 | `assets/cn/island_daily_interact/` |

#### 配置项

```yaml
IslandDailyInteract:
  PetCat: true               # 启用摸猫
  JuuExpress: true           # 启用JUU速运
  WeeklyPhoto: true          # 启用每周照相任务
```

## 配置变更总览

### [`argument.yaml`](module/config/argument/argument.yaml) 新增配置

```yaml
IslandDailyInteract:
  PetCat: true
  JuuExpress: true
  WeeklyPhoto: true
```

---

## 任务调度集成

各岛屿任务作为 `Island` 组下的独立任务，由 [`alas.py`](alas.py) 调度器按标准流程运行。
关键在于各任务模块内部自行处理运行频率和状态判断，调度器仅负责按配置触发。

### 优先级参考

```
低频率（按条件触发）：
  摸猫/速运（每日一次）
  每周照相（每周任务刷新后循环清空）
```

---

## 文件结构变化

```
module/island/
├── island.py                    # 已有 - 核心类
├── island_daily_interact.py     # 新增 - 摸猫/速运/每周照相
├── assets.py                    # 已有 - 通用按钮资源
├── ...
```

---

## i18n 新增 Key

在 [`zh-CN.json`](module/config/i18n/zh-CN.json) 等翻译文件中新增：

```json
{
  "Island.IslandDailyInteract.PetCat": "摸猫",
  "Island.IslandDailyInteract.JuuExpress": "JUU速运",
  "Island.IslandDailyInteract.WeeklyPhoto": "每周照相任务"
}
```

---

## 实现优先级

| 优先级 | 功能 | 预计工作量 |
|--------|------|-----------|
| P2 | 摸猫/JUU速运/每周照相 | 中（需截图资源） |

> **注意**: 摸猫、JUU速运、每周照相等功能需要游戏内截图资源（Button/Template），需先通过 `dev_tools/button_extract.py` 从截图中提取按钮定义才能实现。
