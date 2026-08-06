"""岛屿每日互动任务模块。

处理岛屿低频互动任务的自动化执行，包括摸猫、JUU 速运、商区外送服务和每周照相。
结合开发计划任务列表区域检测，按顺序执行所有已启用的互动任务。
"""
from datetime import timedelta

from module.config.time_source import now as current_time

from module.base.timer import Timer
from module.island.island import Island
from module.island.assets import *
from module.island_daily_interact.assets import *
from module.base.utils import crop
from module.handler.assets import STORY_SKIP_3
from module.logger import logger
from module.ui.assets import ISLAND_PHONE_CHECK, ISLAND_CHECK
from module.ui.page import page_island, page_island_map, page_island_phone


DEVELOPMENT_PLAN_TASK_LIST_AREA = (179, 124, 280, 690)
INTERACT_BLUE_RING_HSV_LOWER = np.array([85, 45, 95])
INTERACT_BLUE_RING_HSV_UPPER = np.array([145, 190, 255])
INTERACT_WHITE_ICON_HSV_LOWER = np.array([0, 0, 155])
INTERACT_WHITE_ICON_HSV_UPPER = np.array([179, 100, 255])
INTERACT_BLUE_RING_RADIUS = 30
INTERACT_BLUE_RING_SIZE = INTERACT_BLUE_RING_RADIUS * 2
INTERACT_BLUE_RING_HOUGH_MIN_RADIUS = 28
INTERACT_BLUE_RING_HOUGH_MAX_RADIUS = 38
INTERACT_BLUE_RING_CONTOUR_MIN_SIZE = 52
INTERACT_BLUE_RING_CONTOUR_MAX_SIZE = 78
INTERACT_BLUE_RING_BLUE_RATIO_THRESHOLD = 0.64
INTERACT_BLUE_RING_WHITE_RATIO_MIN = 0.12
INTERACT_BLUE_RING_WHITE_RATIO_MAX = 0.85
NURSERY_GREETING_ACTION_MATCH_THRESHOLD = 0.86
NURSERY_GREETING_ACTION_MATCH_MARGIN = 0.06
NURSERY_GREETING_BUBBLE_CLASSIFY_THRESHOLD = 0.68
NURSERY_GREETING_BUBBLE_CLASSIFY_MARGIN = 0.045
NURSERY_GREETING_BUBBLE_BLUE_SCORE_MIN = 0.45
NURSERY_GREETING_BUBBLE_BLUE_WEIGHT = 0.12
NURSERY_GREETING_ACTION_MAX_SCROLL = 5
NURSERY_GREETING_ICON_SIZE = 64
NURSERY_GREETING_OPTION_ICON_WIDTH = 90
NURSERY_GREETING_OPTION_ICON_HEIGHT = 92
NURSERY_GREETING_ACTION_TEMPLATE_COMMON_RATIO = 0.42
NURSERY_GREETING_ACTION_TEMPLATE_DETAIL_WEIGHT = 0.65
NURSERY_GREETING_ACTION_TEMPLATE_MIN_DETAIL_PIXELS = 12
NURSERY_GREETING_ACTION_TEMPLATE_LABELS = (
    '害怕', '伸懒腰', '打坐', '踩脚', '英雄登场', '羞躬',
    '展示肌肉', '胜利起跳', '挠头', '擦汗', '打哈欠', '拒绝',
    '飞吻', '投篮', '自夸', '抱拳', '叉腰', '跳舞',
    '赞美太阳', '打招呼', '道别', '点头', '摇头', '拍手',
)
GREET_NURSERY_JUU_1_BUBBLE_AREA = Button(
    area=(620, 176, 1182, 325),
    color=(),
    button=(620, 176, 1182, 325),
    name='GREET_NURSERY_JUU_1_BUBBLE_AREA',
)
GREET_NURSERY_JUU_2_BUBBLE_AREA = Button(
    area=(89, 176, 650, 367),
    color=(),
    button=(89, 176, 650, 367),
    name='GREET_NURSERY_JUU_2_BUBBLE_AREA',
)
GREET_NURSERY_JUU_3_BUBBLE_AREA = Button(
    area=(89, 118, 650, 275),
    color=(),
    button=(89, 118, 650, 275),
    name='GREET_NURSERY_JUU_3_BUBBLE_AREA',
)
GREET_NURSERY_ACTION_LIST_AREA = Button(
    area=(914, 15, 1127, 683),
    color=(),
    button=(914, 15, 1127, 683),
    name='GREET_NURSERY_ACTION_LIST_AREA',
)
GREET_NURSERY_ACTION_OPTION_SCROLL = Button(
    area=(1106, 58, 1127, 671),
    color=(),
    button=(1106, 58, 1127, 671),
    name='GREET_NURSERY_ACTION_OPTION_SCROLL',
)
GREET_NURSERY_ACTION_SCROLL_SAFE_AREA = GREET_NURSERY_ACTION_OPTION_SCROLL


class IslandDailyInteract(Island):
    """每日与每周互动任务：摸猫、JUU速运、商区外送服务、苗圃打招呼、每周照相。"""

    def run(self):
        """执行启用的岛屿低频互动任务。"""
        logger.hr('岛屿每日互动运行', level=1)
        self.ui_ensure(page_island)

        all_done = True
        self.pet_cat()
        all_done = self.juu_express() and all_done
        all_done = self.business_delivery() and all_done
        if self.config.IslandDailyInteract_NurseryGreeting:
            all_done = self.greet_nursery_juus() and all_done
        if self.config.IslandDailyInteract_WeeklyPhoto:
            all_done = self.weekly_photo() and all_done

        self._delay_to_next_day()
        if all_done:
            self._delay_to_next_day()
            logger.info('[岛屿-每日周任务] 岛屿每日互动执行完成')
        else:
            logger.warning('[岛屿-每日周任务] 岛屿每日互动部分任务失败，60分钟后重试')
            self.config.task_delay(minute=60)

    def pet_cat(self):
        """
        执行晨露农场摸猫。

        Pages:
            in: 任意页面
            out: page_island 或奖励关闭后的当前页面
        """
        from module.island_daily_interact.assets import PET_CAT_FARM_INTERACT

        logger.hr('撸猫', level=2)
        if not self.island_map_goto('farm'):
            logger.warning('[岛屿-每日周任务] 前往晨露农场失败，跳过摸猫任务')
            return False
        self.move_for_morningdew_farm()

        if self._click_optional_interact(PET_CAT_FARM_INTERACT, '摸猫互动'):
            self._handle_island_reward_optional()
        else:
            logger.info('[岛屿-每日周任务] 未检测到摸猫互动按钮，跳过')

        self._clear_island_reward_popups()

    def juu_express(self):
        """
        执行 JUU 速运任务。

        Pages:
            in: 任意页面
            out: page_island
        """
        from module.island_daily_interact.assets import (
            DEVELOPMENT_PLAN_DAILY_TAB,
            DEVELOPMENT_PLAN_DAILY_TAB_CHECK,
            TEMPLATE_JUU_EXPRESS_TASK_ICON,
        )

        logger.hr('JUU快递', level=2)
        if not self._detect_development_plan_template_task(
                task_template=TEMPLATE_JUU_EXPRESS_TASK_ICON,
                tab_button=DEVELOPMENT_PLAN_DAILY_TAB,
                tab_check=DEVELOPMENT_PLAN_DAILY_TAB_CHECK,
                tab_label='每日计划',
                label='JUU速运'):
            logger.info('[岛屿-每日周任务] 未检测到或已完成 JUU 速运任务，跳过')
            self._back_to_island_phone_from_development_plan()
            return True
        if not self._back_to_island_phone_from_development_plan():
            return False

        completed = True
        for name, destination, move_method, interact_button, complete_button in self._juu_express_steps():
            if not self.juu_express_location_flow(
                    name=name,
                    destination=destination,
                    move_method=move_method,
                    interact_button=interact_button,
                    complete_button=complete_button):
                logger.warning(f'[岛屿-每日周任务] JUU速运地点交互失败，终止后续流程: {name}')
                completed = False
                break

        self._handle_island_reward_optional()
        self._clear_island_reward_popups()
        self.ui_goto(page_island, get_ship=False)
        return completed

    def business_delivery(self):
        """
        执行商区外送服务任务。

        Pages:
            in: 任意页面
            out: page_island
        """
        from module.island_daily_interact.assets import (
            DEVELOPMENT_PLAN_DAILY_TAB,
            DEVELOPMENT_PLAN_DAILY_TAB_CHECK,
            TEMPLATE_BUSINESS_DELIVERY_TASK_ICON,
        )

        logger.hr('商业配送', level=2)
        if not self._detect_development_plan_template_task(
                task_template=TEMPLATE_BUSINESS_DELIVERY_TASK_ICON,
                tab_button=DEVELOPMENT_PLAN_DAILY_TAB,
                tab_check=DEVELOPMENT_PLAN_DAILY_TAB_CHECK,
                tab_label='每日计划',
                label='商区外送服务'):
            logger.info('[岛屿-每日周任务] 未检测到或已完成商区外送服务任务，跳过')
            self._back_to_island_phone_from_development_plan()
            return True
        if not self._back_to_island_phone_from_development_plan():
            return False

        completed = True
        for name, destination, move_method, interact_button, complete_button in self._business_delivery_steps():
            if not self.delivery_location_flow(
                    task_label='商区外送服务',
                    name=name,
                    destination=destination,
                    move_method=move_method,
                    interact_button=interact_button,
                    complete_button=complete_button):
                logger.warning(f'[岛屿-每日周任务] 商区外送服务地点交互失败，终止后续流程: {name}')
                completed = False
                break

        self._handle_island_reward_optional()
        self._clear_island_reward_popups()
        self.ui_goto(page_island, get_ship=False)
        return completed

    def weekly_photo(self):
        """
        执行每周照相任务，直到开发计划中不再出现任务图标。

        Pages:
            in: 任意页面
            out: page_island_phone 或 page_island
        """
        from module.island_daily_interact.assets import (
            DEVELOPMENT_PLAN_WEEKLY_TAB,
            DEVELOPMENT_PLAN_WEEKLY_TAB_CHECK,
            TEMPLATE_WEEKLY_PHOTO_TASK_ICON,
            WEEKLY_PHOTO_TASK_CHECK,
        )

        logger.hr('每周拍照', level=2)
        completed = True
        for _ in range(10):
            if not self._start_development_plan_template_task(
                    task_template=TEMPLATE_WEEKLY_PHOTO_TASK_ICON,
                    task_check=WEEKLY_PHOTO_TASK_CHECK,
                    tab_button=DEVELOPMENT_PLAN_WEEKLY_TAB,
                    tab_check=DEVELOPMENT_PLAN_WEEKLY_TAB_CHECK,
                    tab_label='每周计划',
                    label='每周照相任务'):
                logger.info('[岛屿-每日周任务] 未检测到或已完成每周照相任务，结束循环')
                self._back_to_island_phone_from_development_plan()
                break

            if not self._run_weekly_photo_once():
                logger.warning('[岛屿-每日周任务] 每周照相任务单轮流程未完整完成，结束循环')
                completed = False
                break

            if not self._back_to_island_phone():
                completed = False
                break
        else:
            logger.warning('每周照相任务循环次数达到上限，60分钟后重试')
            completed = False

        return completed

    def greet_nursery_juus(self):
        """
        依次执行苗圃三个小人的打招呼互动。

        Pages:
            in: 任意页面
            out: page_island
        """
        logger.hr('Nursery Greeting', level=2)
        completed = True
        for index, move_method, bubble_area in self._nursery_greeting_steps():
            max_attempt = 6 if index == 3 else 3
            for attempt in range(max_attempt):
                logger.info(f'苗圃第{index}个小人打招呼尝试: {attempt + 1}/{max_attempt}')
                if self.greet_nursery_juu(index, move_method, bubble_area):
                    break
                if attempt < max_attempt - 1:
                    logger.warning(f'苗圃第{index}个小人打招呼失败，准备重试')
                    self._close_nursery_greeting_action_menu_before_retry()
                    continue
            else:
                logger.warning(f'苗圃第{index}个小人打招呼失败，继续尝试后续小人')
                self._close_nursery_greeting_action_menu_before_retry()
                completed = False
                continue

        self._clear_island_reward_popups()
        self.ui_goto(page_island, get_ship=False)
        return completed

    def greet_nursery_juu(self, index, move_method, bubble_area):
        """
        单个苗圃小人的打招呼流程。

        Args:
            index: 小人序号，仅用于日志。
            move_method: 从苗圃传送点前往该小人的移动路线。
            bubble_area: 小人头顶互动气泡检测区域。

        Returns:
            bool: 是否完成或跳过该小人的打招呼流程。
        """
        logger.hr(f'Nursery Greeting - JUU {index}', level=3)
        target_icon = None
        if not self.island_map_goto('nursery'):
            logger.warning(f'前往苗圃失败，无法执行第{index}个小人打招呼')
            return False

        move_method()
        bubble_found = False
        for _ in self.loop(timeout=8, skip_first=False):
            if self._appear_nursery_greeting_bubble(bubble_area):
                bubble_found = True
                target_icon = self._extract_nursery_greeting_action_icon(bubble_area)
                break
            if self._handle_island_reward_once():
                continue
        if not bubble_found:
            logger.warning(f'苗圃第{index}个小人未匹配到打招呼蓝圈')
            return False

        if target_icon is None:
            logger.warning(f'苗圃第{index}个小人动作图标提取失败')
            return False
        target_index = self._classify_nursery_greeting_action_icon(target_icon)
        if target_index is None:
            logger.warning(f'苗圃第{index}个小人动作图标未能可靠归类')
            return False
        if not self._open_nursery_greeting_action_menu():
            return False
        if not self._select_nursery_greeting_action(target_index):
            return False

        self.device.sleep(6)
        if not self._handle_island_reward_optional():
            logger.warning(f'苗圃第{index}个小人打招呼后未检测到奖励')
            return False
        return self._exit_nursery_greeting_action_menu()

    def _close_nursery_greeting_action_menu_before_retry(self):
        """重试前点击安全区域，关闭可能残留的动作界面。"""
        logger.info('苗圃打招呼重试前点击安全区域关闭动作界面')
        self.device.click(ISLAND_CLICK_SAFE_AREA)

    def delivery_location_flow(self, task_label, name, destination, move_method, interact_button, complete_button):
        """
        单个外送类任务地点的通用交付流程。

        Args:
            task_label: 日志中的任务名称。
            name: 日志中的地点名称。
            destination: island_map_goto() 的目的地。
            move_method: 目的地内移动路线函数。
            interact_button: 当前地点交互按钮。
            complete_button: 当前地点已完成图标。

        Returns:
            bool: 是否完成该地点交付。
        """
        logger.hr(f'{task_label} - {name}', level=3)
        for attempt in range(2):
            logger.info(f'[岛屿-每日周任务] 前往{name}，第{attempt + 1}次尝试')
            if not self.island_map_goto(destination):
                logger.warning(f'[岛屿-每日周任务] 前往{name}失败')
                continue
            move_method()

            interact_status = self._click_optional_interact_or_complete(
                    interact_button=interact_button,
                    complete_button=complete_button,
                    label=f'{name}交付互动')
            if interact_status == 'clicked':
                self.handle_island_story_skip_safely()
                self.device.sleep(2)
                self._handle_island_reward_optional()
                return True
            if interact_status == 'complete':
                return True

            logger.warning(f'[岛屿-每日周任务] 未检测到{name}交付互动按钮')

        return False

    def juu_express_location_flow(self, name, destination, move_method, interact_button, complete_button):
        """单个 JUU 速运地点的通用交付流程。"""
        return self.delivery_location_flow(
            task_label='JUU速运',
            name=name,
            destination=destination,
            move_method=move_method,
            interact_button=interact_button,
            complete_button=complete_button,
        )

    def move_for_lakeniya(self):
        """繁荫农圃拉科尼娅移动路线。"""
        self.island_up(2000)
        self.island_right(1800)
        self.island_up(500)

    def move_for_luxi(self):
        """繁荫农圃露西移动路线。"""
        self.island_left(800)
        self.island_up(5500)
        self.island_left(1000)
        self.island_up(3700)

    def move_for_aobulaien(self):
        """栖风原野奥布莱恩移动路线。"""
        self.island_right(4600)
        self.island_up(5100)
        self.island_right(1100)

    def move_for_qiaoan(self):
        """栖风原野乔安移动路线。"""
        self.island_right(6000)
        self.island_down(3000)
        self.island_right(2300)

    def move_for_morningdew_farm(self):
        """晨露农场摸猫移动路线。"""
        self.island_left(500)
        self.island_down(200)

    def move_for_hemo(self):
        """晨露农场赫莫移动路线。"""
        self.island_left(600)
        self.island_up(2000)
        self.island_left(800)

    def move_for_meili(self):
        """晨露农场梅莉移动路线。"""
        self.island_right(1800)
        self.island_down(600)

    def move_for_aolipike(self):
        """晨露农场奥利匹克移动路线。"""
        self.island_left(500)
        self.island_down(1500)
        self.island_left(1700)
        self.island_down(1900)

    def move_for_amoma(self):
        """港口商区阿莫玛移动路线。"""
        self.island_up(1500)
        self.island_left(400)

    def move_for_pateli(self):
        """港口帕特莉移动路线。"""
        self.island_left(2200)
        self.device.click(ISLAND_JUMP)
        self.island_left(1200)
        self.island_up(500)

    def move_for_bulaimei(self):
        """港口布莱梅移动路线（需跳转到啾咖啡餐厅）。"""
        self.island_up(2600)
        self.device.click(ROUTE_TWO_OPTION_COMPLETE)
        for _ in self.loop(timeout=12, skip_first=False):
            self.device.sleep(2)
            if self.appear(ISLAND_CHECK):
                break
        self.island_left(600)

    def move_for_lisha(self):
        """集会岛莉莎移动路线。"""
        self.island_up(3000)
        self.island_left(2000)
        self.island_up(5500)
        self.island_right(300)
        self.island_up(2200)
        self.island_left(1100)

    def handle_island_story_skip_safely(self):
        """
        安全处理岛屿互动后的剧情跳过。

        Returns:
            bool: 是否检测到返回状态或执行过跳过处理。
        """
        handled = False
        for _ in self.loop(timeout=20, skip_first=False):
            if self._appear_story_skip_luma(interval=2):
                self.device.click(AIR_DROP_SKIP)
                handled = True
                continue

            in_island = self.ui_page_appear(page_island)
            in_island_map = self.ui_page_appear(page_island_map)
            if in_island or in_island_map:
                return handled

            if self.appear(ISLAND_PHONE_CHECK):
                logger.warning('[岛屿-每日周任务] 跳过期间检测到岛屿手机页面，停止继续点击跳过')
                self.ui_goto(page_island, get_ship=False)
                return handled

            if self._handle_island_reward_once():
                handled = True
                continue

        logger.warning('[岛屿-每日周任务] 剧情跳过等待超时')
        return handled

    def _appear_story_skip_luma(self, interval=0):
        """岛屿对话左上角菜单易受场景光照染色，使用亮度匹配复用 STORY_SKIP_3。"""
        self.device.stuck_record_add(STORY_SKIP_3)
        if interval:
            timer = self.interval_timer.get(STORY_SKIP_3.name)
            if timer is None or timer.limit != interval:
                self.interval_timer[STORY_SKIP_3.name] = Timer(interval)
                timer = self.interval_timer[STORY_SKIP_3.name]
            if not timer.reached():
                return False

        appear = STORY_SKIP_3.match_luma(self.device.image, offset=(20, 20), similarity=0.85)
        if appear and interval:
            timer.reset()
        return appear

    def _juu_express_steps(self):
        return [
            ('港口的帕特莉', 'port', self.move_for_pateli, JUU_EXPRESS_PATELI_INTERACT, ROUTE_TWO_OPTION_COMPLETE),
            ('栖风原野的奥布莱恩', 'mine_forest', self.move_for_aobulaien, JUU_EXPRESS_AOBULAIEN_INTERACT, ROUTE_TWO_OPTION_COMPLETE),
            ('晨露农场的梅莉', 'farm', self.move_for_meili, JUU_EXPRESS_MEILI_INTERACT, ROUTE_TWO_OPTION_COMPLETE),
            ('集会岛的莉莎', 'assembly', self.move_for_lisha, JUU_EXPRESS_LISHA_INTERACT, ROUTE_TWO_OPTION_COMPLETE),
            ('繁荫农圃的拉科尼娅', 'nursery', self.move_for_lakeniya, JUU_EXPRESS_LAKENIYA_INTERACT, ROUTE_THREE_OPTION_COMPLETE),
            ('栖风原野的乔安', 'mine_forest', self.move_for_qiaoan, JUU_EXPRESS_QIAOAN_INTERACT, ROUTE_TWO_OPTION_COMPLETE),
            ('晨露农场的奥利匹克', 'farm', self.move_for_aolipike, JUU_EXPRESS_AOLIPIKE_INTERACT, ROUTE_TWO_OPTION_COMPLETE),
            ('港口商区的阿莫玛', 'port_business', self.move_for_amoma, JUU_EXPRESS_AMOMA_INTERACT, ROUTE_THREE_OPTION_COMPLETE),
            ('繁荫农圃的露西', 'nursery', self.move_for_luxi, JUU_EXPRESS_LUXI_INTERACT, ROUTE_THREE_OPTION_COMPLETE),
        ]

    def _business_delivery_steps(self):
        return [
            ('港口商区的阿莫玛', 'port_business', self.move_for_amoma, BUSINESS_DELIVERY_AMOMA_INTERACT, ROUTE_THREE_OPTION_COMPLETE),
            ('栖风原野的奥布莱恩', 'mine_forest', self.move_for_aobulaien, BUSINESS_DELIVERY_TWO_OPTION_INTERACT, ROUTE_TWO_OPTION_COMPLETE),
            ('集会岛的莉莎', 'assembly', self.move_for_lisha, BUSINESS_DELIVERY_TWO_OPTION_INTERACT, ROUTE_TWO_OPTION_COMPLETE),
            ('繁荫农圃的拉科尼娅', 'nursery', self.move_for_lakeniya, BUSINESS_DELIVERY_THREE_OPTION_INTERACT, ROUTE_THREE_OPTION_COMPLETE),
            ('繁荫农圃的露西', 'nursery', self.move_for_luxi, BUSINESS_DELIVERY_THREE_OPTION_INTERACT, ROUTE_THREE_OPTION_COMPLETE),
            ('港口的帕特莉', 'port', self.move_for_pateli, BUSINESS_DELIVERY_TWO_OPTION_INTERACT, ROUTE_TWO_OPTION_COMPLETE),
            ('啾咖啡餐厅的布莱梅', 'port', self.move_for_bulaimei, BUSINESS_DELIVERY_THREE_OPTION_INTERACT, ROUTE_THREE_OPTION_COMPLETE),
            ('晨露农场的赫莫', 'farm', self.move_for_hemo, BUSINESS_DELIVERY_THREE_OPTION_INTERACT, ROUTE_THREE_OPTION_COMPLETE),
        ]

    def _nursery_greeting_steps(self):
        return [
            (1, self.move_for_nursery_greet_1, GREET_NURSERY_JUU_1_BUBBLE_AREA),
            (2, self.move_for_nursery_greet_2, GREET_NURSERY_JUU_2_BUBBLE_AREA),
            (3, self.move_for_nursery_greet_3, GREET_NURSERY_JUU_3_BUBBLE_AREA),
        ]

    def _enter_development_plan(self):
        """
        从岛屿手机页面进入开发计划页面。

        Pages:
            in: page_island_phone
            out: ISLAND_DEVELOPMENT_PLAN_CHECK
        """
        from module.island_daily_interact.assets import ISLAND_DEVELOPMENT_PLAN_CHECK, ISLAND_PHONE_DEVELOPMENT_PLAN

        self.ui_goto(page_island_phone, get_ship=False)
        for _ in self.loop(timeout=15):
            if self.appear(ISLAND_DEVELOPMENT_PLAN_CHECK):
                return True
            if self.appear_then_click(ISLAND_PHONE_DEVELOPMENT_PLAN, interval=2):
                continue
            if self._handle_island_reward_once():
                continue

        logger.warning('[岛屿-每日周任务] 进入开发计划页面超时')
        return False

    def _start_development_plan_template_task(self, task_template, task_check, tab_button, tab_check, tab_label, label):
        """
        进入开发计划页面后先切换到目标页签，再通过模板搜索启动指定任务。

        Args:
            task_template: 开发计划任务列表中的任务图标模板。
            task_check: 点击任务图标后的确认按钮。
            tab_button: 目标页签的切换按钮。
            tab_check: 目标页签切换后的激活检测按钮。
            tab_label: 目标页签日志名称。
            label: 日志名称。

        Returns:
            bool: 是否需要继续执行任务流程。
        """
        if not self._enter_development_plan():
            return False

        if not self._switch_development_plan_tab(tab_button=tab_button, tab_check=tab_check, label=tab_label):
            return False

        self.device.screenshot()
        task_button = self._match_development_plan_task_template(task_template)
        if task_button is None:
            return False

        logger.info(f'[岛屿-每日周任务] 检测到{label}，点击任务图标')
        self.device.click(task_button)
        for _ in self.loop(timeout=8):
            if self.appear_then_click(task_check, offset=(20, 20), interval=2):
                logger.info(f'[岛屿-每日周任务] {label}确认成功')
                return True
            if self._handle_island_reward_once():
                continue

        logger.warning(f'[岛屿-每日周任务] {label}确认按钮等待超时')
        return False

    def _detect_development_plan_template_task(self, task_template, tab_button, tab_check, tab_label, label):
        """
        进入开发计划页面后只检测指定任务图标，不点击任务确认按钮。

        Args:
            task_template: 开发计划任务列表中的任务图标模板。
            tab_button: 目标页签的切换按钮。
            tab_check: 目标页签切换后的激活检测按钮。
            tab_label: 目标页签日志名称。
            label: 日志名称。

        Returns:
            bool: 是否检测到目标任务图标。
        """
        if not self._enter_development_plan():
            return False

        if not self._switch_development_plan_tab(tab_button=tab_button, tab_check=tab_check, label=tab_label):
            return False

        self.device.screenshot()
        if self._match_development_plan_task_template(task_template) is None:
            return False

        logger.info(f'[岛屿-每日周任务] 检测到{label}任务图标')
        return True

    def _switch_development_plan_tab(self, tab_button, tab_check, label):
        """切换到开发计划目标页签，并确认页签已激活。"""
        logger.info(f'[岛屿-每日周任务] 切换到{label}页签')
        for _ in self.loop(timeout=12):
            if self.appear(tab_check):
                logger.info(f'[岛屿-每日周任务] {label}页签已激活')
                return True
            if self.appear_then_click(tab_button, interval=2):
                continue
            if self._handle_island_reward_once():
                continue

        logger.warning(f'[岛屿-每日周任务] 切换到{label}页签超时')
        return False

    def _match_development_plan_task_template(self, task_template):
        """在开发计划任务列表区域内匹配任务图标模板。"""
        region = crop(self.device.image, DEVELOPMENT_PLAN_TASK_LIST_AREA, copy=False)
        matches = task_template.match_multi(
            region,
            similarity=0.85,
            threshold=5,
            name='DEVELOPMENT_PLAN_TASK_TEMPLATE',
        )
        if not matches:
            return None

        matches.sort(key=lambda button: (button.area[1], button.area[0]))
        return matches[0].move(DEVELOPMENT_PLAN_TASK_LIST_AREA[:2])

    def _run_weekly_photo_once(self):
        from module.island_daily_interact.assets import (
            WEEKLY_PHOTO_CAMERA,
            WEEKLY_PHOTO_IDLE,
        )

        for index in range(3):
            logger.info(f'[岛屿-每日周任务] 每周照相第{index + 1}轮')
            self._click_weekly_photo_button(WEEKLY_PHOTO_CAMERA, '照相按钮')
            self._click_weekly_photo_button(WEEKLY_PHOTO_IDLE, '空闲按钮')

        for _ in self.loop(timeout=12):
            if self._handle_island_reward_once():
                continue
            if self.appear_then_click(ISLAND_BACK, interval=2):
                return True

        logger.warning('[岛屿-每日周任务] 每周照相通用奖励或返回按钮等待超时')
        return False

    def _click_weekly_photo_button(self, button, label):
        """每周照相页面按钮位置固定，直接点击，不做出现检测。"""
        self.device.screenshot()
        logger.info(f'[岛屿-每日周任务] 点击{label}')
        self.device.click(button)

    def _click_optional_interact(self, button, label, timeout=8):
        for _ in self.loop(timeout=timeout):
            if self.appear_then_click(button, interval=2):
                logger.info(f'[岛屿-每日周任务] 点击{label}')
                return True
            if self._handle_island_reward_once():
                continue

        return False

    def _click_optional_interact_or_complete(self, interact_button, complete_button, label, timeout=8):
        for _ in self.loop(timeout=timeout):
            if self.appear_then_click(interact_button, interval=2):
                logger.info(f'[岛屿-每日周任务] 点击{label}')
                return 'clicked'
            if self.appear(complete_button, offset=(20, 20)):
                logger.info(f'[岛屿-每日周任务] {label}已完成，进入下一步')
                return 'complete'
            if self._handle_island_reward_once():
                continue

        return 'missing'

    def appear_interact_blue_ring(self, area, show_log=False):
        """
        检测指定区域内是否存在蓝色互动圈。

        互动圈内部动作图标会随机变化，因此这里只识别外层蓝色高亮圈。
        """
        return self._find_interact_blue_ring(area, show_log=show_log) is not None

    def _appear_nursery_greeting_bubble(self, bubble_area):
        """检测苗圃小人头顶打招呼互动气泡。"""
        return self._find_interact_blue_ring(bubble_area, show_log=True) is not None

    def _find_interact_blue_ring_legacy(self, area, show_log=False):
        """在指定区域内寻找最可信的蓝色互动圈。"""
        button_area = area.area if isinstance(area, Button) else area
        image = crop(self.device.image, button_area, copy=False)
        if image.size <= 0:
            return None

        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        blue_mask = cv2.inRange(hsv, INTERACT_BLUE_RING_HSV_LOWER, INTERACT_BLUE_RING_HSV_UPPER)
        white_mask = cv2.inRange(hsv, INTERACT_WHITE_ICON_HSV_LOWER, INTERACT_WHITE_ICON_HSV_UPPER)
        blue_mask = cv2.morphologyEx(
            blue_mask,
            cv2.MORPH_CLOSE,
            np.ones((3, 3), dtype=np.uint8),
            iterations=1,
        )

        best_rect = None
        best = {
            'area': 0,
            'width': 0,
            'height': 0,
            'aspect': 0,
            'extent': 0,
        }
        contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            contour_area = cv2.contourArea(contour)
            if contour_area < 300:
                continue

            x, y, width, height = cv2.boundingRect(contour)
            if width < 24 or height < 24:
                continue
            aspect = width / max(height, 1)
            if not 0.7 <= aspect <= 1.45:
                continue

            extent = contour_area / max(width * height, 1)
            if extent < 0.35:
                continue

            center_white = white_mask[y:y + height, x:x + width]
            yy, xx = np.ogrid[:height, :width]
            cx = (width - 1) / 2
            cy = (height - 1) / 2
            rx = max(width / 2, 1)
            ry = max(height / 2, 1)
            center_mask = (((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 0.55 ** 2).astype('uint8') * 255
            white_total = cv2.countNonZero(center_mask)
            white_ratio = (
                cv2.countNonZero(cv2.bitwise_and(center_white, center_mask)) / white_total
                if white_total
                else 0
            )
            if white_ratio < 0.12:
                continue

            if contour_area > best['area']:
                best = {
                    'area': contour_area,
                    'width': width,
                    'height': height,
                    'aspect': aspect,
                    'extent': extent,
                    'white': white_ratio,
                }
                best_rect = (x, y, width, height)

        if show_log:
            logger.attr(
                'InteractBlueRing',
                (
                    f"area={best['area']:.1f}, size={best['width']}x{best['height']}, "
                    f"aspect={best['aspect']:.2f}, extent={best['extent']:.2f}, "
                    f"white={best.get('white', 0):.2f}, appear={best_rect is not None}"
                ),
        )
        return best_rect

    def _find_interact_blue_ring(self, area, show_log=False):
        """在指定区域内寻找固定大小的蓝色互动气泡。"""
        button_area = area.area if isinstance(area, Button) else area
        image = crop(self.device.image, button_area, copy=False)
        if image.size <= 0:
            return None

        blue_mask, white_mask = self._interact_blue_ring_masks(image)
        contour_rect, contour = self._find_interact_blue_ring_by_contour(blue_mask, white_mask)
        best_rect = None
        best = contour or {
            'method': 'none',
            'area': 0,
            'width': 0,
            'height': 0,
            'aspect': 0,
            'extent': 0,
            'blue': 0,
            'white': 0,
            'tail': 0,
            'score': 0,
        }

        if self._is_normal_interact_blue_ring_contour(contour):
            best_rect = contour_rect
            best = contour
        else:
            hough_rect, hough = self._find_interact_blue_ring_by_hough(blue_mask, white_mask)
            if hough_rect is not None:
                best_rect = hough_rect
                best = hough

        if show_log:
            logger.attr(
                'InteractBlueRing',
                (
                    f"method={best.get('method', 'none')}, score={best.get('score', 0):.2f}, "
                    f"area={best.get('area', 0):.1f}, size={best.get('width', 0)}x{best.get('height', 0)}, "
                    f"aspect={best.get('aspect', 0):.2f}, extent={best.get('extent', 0):.2f}, "
                    f"blue={best.get('blue', 0):.2f}, white={best.get('white', 0):.2f}, "
                    f"tail={best.get('tail', 0):.2f}, appear={best_rect is not None}"
                ),
            )
        return best_rect

    def _interact_blue_ring_masks(self, image):
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        blue_mask = cv2.inRange(hsv, INTERACT_BLUE_RING_HSV_LOWER, INTERACT_BLUE_RING_HSV_UPPER)
        white_mask = cv2.inRange(hsv, INTERACT_WHITE_ICON_HSV_LOWER, INTERACT_WHITE_ICON_HSV_UPPER)
        blue_mask = cv2.morphologyEx(
            blue_mask,
            cv2.MORPH_CLOSE,
            np.ones((3, 3), dtype=np.uint8),
            iterations=1,
        )
        return blue_mask, white_mask

    def _find_interact_blue_ring_by_contour(self, blue_mask, white_mask):
        best_rect = None
        best = None
        contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            contour_area = cv2.contourArea(contour)
            if contour_area < 300:
                continue

            x, y, width, height = cv2.boundingRect(contour)
            if width < 24 or height < 24:
                continue
            aspect = width / max(height, 1)
            if not 0.7 <= aspect <= 1.45:
                continue

            extent = contour_area / max(width * height, 1)
            if extent < 0.35:
                continue

            white_ratio = self._interact_blue_ring_center_white_ratio(white_mask, x, y, width, height)
            if white_ratio < INTERACT_BLUE_RING_WHITE_RATIO_MIN:
                continue

            center_x = x + width // 2
            center_y = y + height // 2
            fixed_rect = self._fixed_interact_blue_ring_rect(center_x, center_y, blue_mask.shape)
            if fixed_rect is None:
                continue

            blue_ratio, fixed_white_ratio, tail_ratio = self._interact_blue_ring_fixed_metrics(
                blue_mask,
                white_mask,
                center_x,
                center_y,
            )
            score = self._interact_blue_ring_score(blue_ratio, fixed_white_ratio, tail_ratio)
            if best is None or contour_area > best['area']:
                best = {
                    'method': 'contour',
                    'rect': (x, y, width, height),
                    'area': contour_area,
                    'width': width,
                    'height': height,
                    'aspect': aspect,
                    'extent': extent,
                    'blue': blue_ratio,
                    'white': fixed_white_ratio,
                    'tail': tail_ratio,
                    'score': score,
                }
                best_rect = fixed_rect

        return best_rect, best

    def _find_interact_blue_ring_by_hough(self, blue_mask, white_mask):
        work = cv2.medianBlur(blue_mask, 5)
        circles = cv2.HoughCircles(
            work,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=28,
            param1=80,
            param2=8,
            minRadius=INTERACT_BLUE_RING_HOUGH_MIN_RADIUS,
            maxRadius=INTERACT_BLUE_RING_HOUGH_MAX_RADIUS,
        )
        if circles is None:
            return None, None

        best_rect = None
        best = None
        for center_x, center_y, _ in np.round(circles[0]).astype(int):
            fixed_rect = self._fixed_interact_blue_ring_rect(center_x, center_y, blue_mask.shape)
            if fixed_rect is None:
                continue

            blue_ratio, white_ratio, tail_ratio = self._interact_blue_ring_fixed_metrics(
                blue_mask,
                white_mask,
                center_x,
                center_y,
            )
            if blue_ratio < INTERACT_BLUE_RING_BLUE_RATIO_THRESHOLD:
                continue
            if not INTERACT_BLUE_RING_WHITE_RATIO_MIN <= white_ratio <= INTERACT_BLUE_RING_WHITE_RATIO_MAX:
                continue

            score = self._interact_blue_ring_score(blue_ratio, white_ratio, tail_ratio)
            if best is None or score > best['score']:
                best = {
                    'method': 'hough',
                    'area': 0,
                    'width': INTERACT_BLUE_RING_SIZE,
                    'height': INTERACT_BLUE_RING_SIZE,
                    'aspect': 1,
                    'extent': 0,
                    'blue': blue_ratio,
                    'white': white_ratio,
                    'tail': tail_ratio,
                    'score': score,
                }
                best_rect = fixed_rect

        return best_rect, best

    def _fixed_interact_blue_ring_rect(self, center_x, center_y, shape):
        height, width = shape[:2]
        radius = INTERACT_BLUE_RING_RADIUS
        x = int(round(center_x - radius))
        y = int(round(center_y - radius))
        if x < 0 or y < 0 or x + INTERACT_BLUE_RING_SIZE > width or y + INTERACT_BLUE_RING_SIZE > height:
            return None
        return (x, y, INTERACT_BLUE_RING_SIZE, INTERACT_BLUE_RING_SIZE)

    def _is_normal_interact_blue_ring_contour(self, contour):
        if not contour:
            return False
        width = contour['width']
        height = contour['height']
        return (
                INTERACT_BLUE_RING_CONTOUR_MIN_SIZE <= width <= INTERACT_BLUE_RING_CONTOUR_MAX_SIZE
                and INTERACT_BLUE_RING_CONTOUR_MIN_SIZE <= height <= INTERACT_BLUE_RING_CONTOUR_MAX_SIZE
                and contour['blue'] >= INTERACT_BLUE_RING_BLUE_RATIO_THRESHOLD
                and contour['white'] >= INTERACT_BLUE_RING_WHITE_RATIO_MIN
        )

    def _interact_blue_ring_center_white_ratio(self, white_mask, x, y, width, height):
        center_white = white_mask[y:y + height, x:x + width]
        yy, xx = np.ogrid[:height, :width]
        cx = (width - 1) / 2
        cy = (height - 1) / 2
        rx = max(width / 2, 1)
        ry = max(height / 2, 1)
        center_mask = (((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 0.55 ** 2).astype('uint8') * 255
        white_total = cv2.countNonZero(center_mask)
        return (
            cv2.countNonZero(cv2.bitwise_and(center_white, center_mask)) / white_total
            if white_total
            else 0
        )

    def _interact_blue_ring_fixed_metrics(self, blue_mask, white_mask, center_x, center_y):
        radius = INTERACT_BLUE_RING_RADIUS
        height, width = blue_mask.shape[:2]
        yy, xx = np.ogrid[:height, :width]
        distance = np.sqrt((xx - center_x) ** 2 + (yy - center_y) ** 2)
        angle = (np.degrees(np.arctan2(yy - center_y, xx - center_x)) + 360) % 360
        ring_mask = ((distance >= radius * 0.62) & (distance <= radius * 1.08)).astype('uint8') * 255
        inner_mask = (distance <= radius * 0.55).astype('uint8') * 255
        right_tail_mask = (
                (distance >= radius * 1.02)
                & (distance <= radius * 1.55)
                & (angle >= 30)
                & (angle <= 85)
        ).astype('uint8') * 255
        left_tail_mask = (
                (distance >= radius * 1.02)
                & (distance <= radius * 1.55)
                & (angle >= 95)
                & (angle <= 150)
        ).astype('uint8') * 255

        blue_ratio = cv2.countNonZero(cv2.bitwise_and(blue_mask, ring_mask)) / max(cv2.countNonZero(ring_mask), 1)
        white_ratio = cv2.countNonZero(cv2.bitwise_and(white_mask, inner_mask)) / max(cv2.countNonZero(inner_mask), 1)
        right_tail_ratio = cv2.countNonZero(cv2.bitwise_and(blue_mask, right_tail_mask)) / max(cv2.countNonZero(right_tail_mask), 1)
        left_tail_ratio = cv2.countNonZero(cv2.bitwise_and(blue_mask, left_tail_mask)) / max(cv2.countNonZero(left_tail_mask), 1)
        tail_ratio = max(right_tail_ratio, left_tail_ratio)
        return blue_ratio, white_ratio, tail_ratio

    def _interact_blue_ring_score(self, blue_ratio, white_ratio, tail_ratio):
        return blue_ratio * 0.55 + white_ratio * 0.30 + tail_ratio * 0.15

    def _extract_nursery_greeting_action_icon(self, bubble_area):
        """从互动气泡中心提取动作图标和蓝圈特征，用于归类目标动作。"""
        button_area = bubble_area.area if isinstance(bubble_area, Button) else bubble_area
        ring_rect = self._find_interact_blue_ring(bubble_area)
        if ring_rect is None:
            return None

        image = crop(self.device.image, button_area, copy=False)
        x, y, width, height = ring_rect
        bubble_image = image[y:y + height, x:x + width]
        white_mask, blue_mask = self._nursery_greeting_bubble_features(bubble_image)
        if cv2.countNonZero(white_mask) < 20:
            logger.warning('互动气泡内白色动作图标像素过少')
            return None
        if cv2.countNonZero(blue_mask) < 20:
            logger.warning('互动气泡蓝圈像素过少')
            return None
        return white_mask, blue_mask

    def _nursery_greeting_bubble_features(self, bubble_image):
        """从带蓝圈的气泡图中提取动作白色 mask 和蓝圈 mask。"""
        if bubble_image.size <= 0:
            empty = np.zeros((NURSERY_GREETING_ICON_SIZE, NURSERY_GREETING_ICON_SIZE), dtype=np.uint8)
            return empty, empty

        inner_image = self._mask_blue_ring_inner_icon(bubble_image)
        white_mask = self._normalize_icon_mask(self._white_icon_mask(inner_image))
        blue_mask = self._fixed_size_icon_mask(self._blue_ring_mask(bubble_image))
        return white_mask, blue_mask

    def _mask_blue_ring_inner_icon(self, icon_image):
        """用椭圆遮罩保留蓝色互动圈内侧动作图标。"""
        if icon_image.size <= 0:
            return icon_image

        height, width = icon_image.shape[:2]
        yy, xx = np.ogrid[:height, :width]
        cx = (width - 1) / 2
        cy = (height - 1) / 2
        rx = max(width / 2, 1)
        ry = max(height / 2, 1)
        ellipse_mask = (((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 0.78 ** 2)
        return np.where(ellipse_mask[..., None], icon_image, 0).astype(icon_image.dtype)

    def _blue_ring_mask(self, image):
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        mask = cv2.inRange(hsv, INTERACT_BLUE_RING_HSV_LOWER, INTERACT_BLUE_RING_HSV_UPPER)
        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_CLOSE,
            np.ones((3, 3), dtype=np.uint8),
            iterations=1,
        )
        return cv2.bitwise_and(mask, self._blue_ring_circle_mask(mask.shape))

    def _blue_ring_circle_mask(self, shape):
        """只保留蓝圈圆环区域，忽略气泡尖角方向。"""
        height, width = shape[:2]
        yy, xx = np.ogrid[:height, :width]
        cx = (width - 1) / 2
        cy = (height - 1) / 2
        radius = min(width, height) / 2
        distance = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        angle = (np.degrees(np.arctan2(yy - cy, xx - cx)) + 360) % 360
        ring_mask = (
                (distance >= radius * 0.62)
                & (distance <= radius * 1.08)
        )
        bubble_tail_gap = (
                ((angle >= 30) & (angle <= 85))
                | ((angle >= 95) & (angle <= 150))
        )
        ring_mask &= ~bubble_tail_gap
        return np.where(ring_mask, 255, 0).astype(np.uint8)

    def _nursery_greeting_bubble_template_features(self, template_image):
        """从黑底白气泡模板中拆分动作图标和稳定蓝圈区域。"""
        if len(template_image.shape) == 3:
            gray = cv2.cvtColor(template_image, cv2.COLOR_RGB2GRAY)
        else:
            gray = template_image
        _, mask = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY)

        height, width = mask.shape[:2]
        if width == height * 2:
            half_width = width // 2
            white_mask = mask[:, :half_width].copy()
            blue_mask = mask[:, half_width:].copy()
            return self._normalize_icon_mask(white_mask), self._fixed_size_icon_mask(blue_mask)

        mask = self._fixed_size_icon_mask(mask)
        ring_mask = self._blue_ring_circle_mask(mask.shape)
        blue_mask = cv2.bitwise_and(mask, ring_mask)
        icon_mask = cv2.bitwise_and(mask, cv2.bitwise_not(ring_mask))
        white_mask = self._normalize_icon_mask(icon_mask)
        return white_mask, blue_mask

    def _white_icon_mask(self, image):
        """将动作图标裁剪图转换为白色像素 mask。"""
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        mask = cv2.inRange(hsv, INTERACT_WHITE_ICON_HSV_LOWER, INTERACT_WHITE_ICON_HSV_UPPER)
        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_OPEN,
            np.ones((2, 2), dtype=np.uint8),
            iterations=1,
        )
        return mask

    def _fixed_size_icon_mask(self, mask):
        """将固定外框 mask 缩放到统一尺寸，不重新裁剪中心位置。"""
        if mask.shape[:2] != (NURSERY_GREETING_ICON_SIZE, NURSERY_GREETING_ICON_SIZE):
            mask = cv2.resize(
                mask,
                (NURSERY_GREETING_ICON_SIZE, NURSERY_GREETING_ICON_SIZE),
                interpolation=cv2.INTER_AREA,
            )
            _, mask = cv2.threshold(mask, 80, 255, cv2.THRESH_BINARY)
        return mask.astype(np.uint8)

    def _normalize_icon_mask(self, mask):
        """将不同大小的动作图标 mask 居中归一化，便于相似度比较。"""
        ys, xs = np.where(mask > 0)
        if not len(xs):
            return np.zeros(
                (NURSERY_GREETING_ICON_SIZE, NURSERY_GREETING_ICON_SIZE),
                dtype=np.uint8,
            )

        mask = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        height, width = mask.shape
        target_size = NURSERY_GREETING_ICON_SIZE - 8
        scale = min(target_size / max(width, 1), target_size / max(height, 1))
        resized_width = max(int(round(width * scale)), 1)
        resized_height = max(int(round(height * scale)), 1)
        resized = cv2.resize(
            mask,
            (resized_width, resized_height),
            interpolation=cv2.INTER_AREA,
        )
        _, resized = cv2.threshold(resized, 80, 255, cv2.THRESH_BINARY)

        normalized = np.zeros(
            (NURSERY_GREETING_ICON_SIZE, NURSERY_GREETING_ICON_SIZE),
            dtype=np.uint8,
        )
        x = (NURSERY_GREETING_ICON_SIZE - resized_width) // 2
        y = (NURSERY_GREETING_ICON_SIZE - resized_height) // 2
        normalized[y:y + resized_height, x:x + resized_width] = resized
        return normalized

    def _open_nursery_greeting_action_menu(self):
        """点击右侧动作互动按钮，并等待动作选项列表打开。"""
        from module.island_daily_interact.assets import (
            GREET_NURSERY_ACTION_MENU,
            GREET_NURSERY_ACTION_MENU_CHECK,
        )

        for _ in self.loop(timeout=10, skip_first=False):
            if self.appear(GREET_NURSERY_ACTION_MENU_CHECK, offset=(20, 20)):
                logger.info('苗圃打招呼动作列表已打开')
                return True
            if self.appear_then_click(GREET_NURSERY_ACTION_MENU, interval=2):
                logger.info('点击苗圃打招呼动作互动按钮')
                continue
            if self._handle_island_reward_once():
                continue

        logger.warning('苗圃打招呼动作列表打开超时')
        return False

    def _select_nursery_greeting_action(self, target_index):
        """在动作列表中匹配目标动作图标并点击对应选项。"""
        target_label = NURSERY_GREETING_ACTION_TEMPLATE_LABELS[target_index]
        for scroll_index in range(NURSERY_GREETING_ACTION_MAX_SCROLL + 1):
            match_state = 'empty'
            for _ in self.loop(timeout=4, skip_first=False):
                match_button, match_state = self._match_nursery_greeting_action(
                    target_index,
                    GREET_NURSERY_ACTION_LIST_AREA,
                )
                if match_button is not None:
                    self.device.click(match_button)
                    logger.info(f'点击苗圃动作选项: {target_label}')
                    return True
                if match_state == 'empty':
                    continue
                break

            if scroll_index >= NURSERY_GREETING_ACTION_MAX_SCROLL:
                break

            logger.info(f'当前动作列表未命中{target_label}动作，向上滑动列表: {scroll_index + 1}')
            self.device.swipe_vector(
                vector=(0, -240),
                box=GREET_NURSERY_ACTION_OPTION_SCROLL.button,
                name='NurseryGreetingActionSwipe',
            )
            self.device.sleep(0.3)
            self.device.long_click(GREET_NURSERY_ACTION_SCROLL_SAFE_AREA)

        logger.warning(f'苗圃动作列表未匹配到目标动作: {target_label}')
        return False

    def _match_nursery_greeting_action(self, target_index, list_area):
        """在当前动作列表可见区域内寻找指定静态动作模板。"""
        candidates = self._detect_nursery_greeting_action_candidates(list_area)
        if not candidates:
            return None, 'empty'

        target_mask = self._nursery_greeting_action_template_masks[target_index]
        target_detail = self._nursery_greeting_action_template_detail_masks[target_index]
        scored = []
        for center, icon_mask in candidates:
            score, full_score, detail_score = self._nursery_greeting_action_template_score(
                target_mask=target_mask,
                target_detail=target_detail,
                candidate_mask=icon_mask,
            )
            scored.append((score, center, full_score, detail_score))
        scored.sort(key=lambda item: item[0], reverse=True)

        best_score, best_center, best_full, best_detail = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else 0
        target_label = NURSERY_GREETING_ACTION_TEMPLATE_LABELS[target_index]
        logger.attr(
            'NurseryGreetingActionMatch',
            (
                f'target={target_label}, best={best_score:.3f}, second={second_score:.3f}, '
                f'full={best_full:.3f}, detail={best_detail:.3f}, count={len(scored)}'
            ),
        )
        if (
                best_score >= NURSERY_GREETING_ACTION_MATCH_THRESHOLD
                and best_score - second_score >= NURSERY_GREETING_ACTION_MATCH_MARGIN
        ):
            x, y = best_center
            button = Button(
                area=(),
                color=(),
                button=(x - 16, y - 16, x + 16, y + 16),
                name='GREET_NURSERY_ACTION_OPTION',
            )
            return button, 'matched'
        return None, 'ambiguous'

    def _classify_nursery_greeting_action_icon(self, target_icon):
        """将气泡动作图标归类到 24 个气泡动作模板之一。"""
        target_white, target_blue = target_icon
        scored = []
        for index, template_features in enumerate(self._nursery_greeting_bubble_action_template_features):
            score, white_score, detail_score, blue_score = self._nursery_greeting_bubble_template_score(
                target_white=target_white,
                target_blue=target_blue,
                template_white=template_features[0],
                template_detail=self._nursery_greeting_bubble_action_template_detail_masks[index],
                template_blue=template_features[1],
            )
            scored.append((score, index, white_score, detail_score, blue_score))
        scored.sort(key=lambda item: item[0], reverse=True)

        best_score, best_index, best_white, best_detail, best_blue = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else 0
        best_label = NURSERY_GREETING_ACTION_TEMPLATE_LABELS[best_index]
        logger.attr(
            'NurseryGreetingActionClassify',
            (
                f'target={best_label}, best={best_score:.3f}, second={second_score:.3f}, '
                f'white={best_white:.3f}, detail={best_detail:.3f}, blue={best_blue:.3f}'
            ),
        )
        if (
                best_score >= NURSERY_GREETING_BUBBLE_CLASSIFY_THRESHOLD
                and best_score - second_score >= NURSERY_GREETING_BUBBLE_CLASSIFY_MARGIN
                and best_blue >= NURSERY_GREETING_BUBBLE_BLUE_SCORE_MIN
        ):
            return best_index
        return None

    def _detect_nursery_greeting_action_candidates(self, list_area):
        """检测动作列表当前可见的白色动作图标候选。"""
        button_area = list_area.area if isinstance(list_area, Button) else list_area
        image = crop(self.device.image, button_area, copy=False)
        if image.size <= 0:
            return []

        raw_white_mask = self._white_icon_mask(image)
        body_mask = cv2.morphologyEx(
            raw_white_mask,
            cv2.MORPH_CLOSE,
            np.ones((3, 3), dtype=np.uint8),
            iterations=1,
        )
        count, labels, stats, centroids = cv2.connectedComponentsWithStats(body_mask, connectivity=8)

        candidates = []
        for index in range(1, count):
            x, y, width, height, area = stats[index]
            if area < 700:
                continue
            if width < 25 or height < 40:
                continue
            aspect = width / max(height, 1)
            if not 0.35 <= aspect <= 1.35:
                continue

            center_x = int(round(centroids[index][0]))
            center_y = int(round(centroids[index][1]))
            x1 = max(center_x - NURSERY_GREETING_OPTION_ICON_WIDTH // 2, 0)
            y1 = max(center_y - NURSERY_GREETING_OPTION_ICON_HEIGHT // 2, 0)
            x2 = min(center_x + NURSERY_GREETING_OPTION_ICON_WIDTH // 2, raw_white_mask.shape[1])
            y2 = min(center_y + NURSERY_GREETING_OPTION_ICON_HEIGHT // 2, raw_white_mask.shape[0])

            icon_mask = raw_white_mask[y1:y2, x1:x2]
            icon_mask = self._normalize_icon_mask(icon_mask)
            center = (
                button_area[0] + center_x,
                button_area[1] + center_y,
            )
            candidates.append((center, icon_mask))

        candidates.sort(key=lambda item: (item[0][1], item[0][0]))
        return candidates

    @cached_property
    def _nursery_greeting_bubble_action_templates(self):
        from module.island_daily_interact.assets import (
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_AFRAID,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_STRETCH,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_MEDITATE,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_STOMP,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_HERO,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_BOW_SHY,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_FLEX,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_VICTORY_JUMP,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_SCRATCH_HEAD,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_WIPE_SWEAT,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_YAWN,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_REFUSE,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_BLOW_KISS,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_SHOOT_BALL,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_SELF_PRAISE,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_FIST_SALUTE,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_AKIMBO,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_DANCE,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_PRAISE_SUN,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_GREETING,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_FAREWELL,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_NOD,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_SHAKE_HEAD,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_CLAP,
        )

        return (
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_AFRAID,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_STRETCH,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_MEDITATE,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_STOMP,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_HERO,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_BOW_SHY,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_FLEX,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_VICTORY_JUMP,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_SCRATCH_HEAD,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_WIPE_SWEAT,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_YAWN,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_REFUSE,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_BLOW_KISS,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_SHOOT_BALL,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_SELF_PRAISE,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_FIST_SALUTE,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_AKIMBO,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_DANCE,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_PRAISE_SUN,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_GREETING,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_FAREWELL,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_NOD,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_SHAKE_HEAD,
            TEMPLATE_GREET_NURSERY_BUBBLE_ACTION_CLAP,
        )

    @cached_property
    def _nursery_greeting_bubble_action_template_features(self):
        features = []
        for index, template in enumerate(self._nursery_greeting_bubble_action_templates):
            white_mask, blue_mask = self._nursery_greeting_bubble_template_features(template.image)
            if cv2.countNonZero(white_mask) < 20:
                logger.warning(f'苗圃气泡动作模板白色像素过少: {NURSERY_GREETING_ACTION_TEMPLATE_LABELS[index]}')
            if cv2.countNonZero(blue_mask) < 20:
                logger.warning(f'苗圃气泡动作模板蓝圈像素过少: {NURSERY_GREETING_ACTION_TEMPLATE_LABELS[index]}')
            features.append((white_mask, blue_mask))
        return tuple(features)

    @cached_property
    def _nursery_greeting_bubble_action_detail_keep_mask(self):
        templates = np.stack([
            features[0] > 0
            for features in self._nursery_greeting_bubble_action_template_features
        ])
        frequency = templates.mean(axis=0)
        return frequency <= NURSERY_GREETING_ACTION_TEMPLATE_COMMON_RATIO

    @cached_property
    def _nursery_greeting_bubble_action_template_detail_masks(self):
        return tuple(
            self._nursery_greeting_bubble_action_detail_mask(features[0])
            for features in self._nursery_greeting_bubble_action_template_features
        )

    def _nursery_greeting_bubble_action_detail_mask(self, icon_mask):
        detail = (icon_mask > 0) & self._nursery_greeting_bubble_action_detail_keep_mask
        return np.where(detail, 255, 0).astype(np.uint8)

    def _nursery_greeting_bubble_template_score(
            self,
            target_white,
            target_blue,
            template_white,
            template_detail,
            template_blue,
    ):
        white_full = self._icon_mask_similarity(template_white, target_white)
        target_detail = self._nursery_greeting_bubble_action_detail_mask(target_white)
        if (
                cv2.countNonZero(template_detail) < NURSERY_GREETING_ACTION_TEMPLATE_MIN_DETAIL_PIXELS
                or cv2.countNonZero(target_detail) < NURSERY_GREETING_ACTION_TEMPLATE_MIN_DETAIL_PIXELS
        ):
            white_score = white_full
            detail_score = 0
        else:
            detail_score = self._icon_mask_similarity(template_detail, target_detail)
            white_score = (
                white_full * (1 - NURSERY_GREETING_ACTION_TEMPLATE_DETAIL_WEIGHT)
                + detail_score * NURSERY_GREETING_ACTION_TEMPLATE_DETAIL_WEIGHT
            )

        blue_score = self._icon_mask_similarity(template_blue, target_blue)
        score = (
            white_score * (1 - NURSERY_GREETING_BUBBLE_BLUE_WEIGHT)
            + blue_score * NURSERY_GREETING_BUBBLE_BLUE_WEIGHT
        )
        return score, white_score, detail_score, blue_score

    @cached_property
    def _nursery_greeting_action_templates(self):
        from module.island_daily_interact.assets import (
            TEMPLATE_GREET_NURSERY_ACTION_AFRAID,
            TEMPLATE_GREET_NURSERY_ACTION_STRETCH,
            TEMPLATE_GREET_NURSERY_ACTION_MEDITATE,
            TEMPLATE_GREET_NURSERY_ACTION_STOMP,
            TEMPLATE_GREET_NURSERY_ACTION_HERO,
            TEMPLATE_GREET_NURSERY_ACTION_BOW_SHY,
            TEMPLATE_GREET_NURSERY_ACTION_FLEX,
            TEMPLATE_GREET_NURSERY_ACTION_VICTORY_JUMP,
            TEMPLATE_GREET_NURSERY_ACTION_SCRATCH_HEAD,
            TEMPLATE_GREET_NURSERY_ACTION_WIPE_SWEAT,
            TEMPLATE_GREET_NURSERY_ACTION_YAWN,
            TEMPLATE_GREET_NURSERY_ACTION_REFUSE,
            TEMPLATE_GREET_NURSERY_ACTION_BLOW_KISS,
            TEMPLATE_GREET_NURSERY_ACTION_SHOOT_BALL,
            TEMPLATE_GREET_NURSERY_ACTION_SELF_PRAISE,
            TEMPLATE_GREET_NURSERY_ACTION_FIST_SALUTE,
            TEMPLATE_GREET_NURSERY_ACTION_AKIMBO,
            TEMPLATE_GREET_NURSERY_ACTION_DANCE,
            TEMPLATE_GREET_NURSERY_ACTION_PRAISE_SUN,
            TEMPLATE_GREET_NURSERY_ACTION_GREETING,
            TEMPLATE_GREET_NURSERY_ACTION_FAREWELL,
            TEMPLATE_GREET_NURSERY_ACTION_NOD,
            TEMPLATE_GREET_NURSERY_ACTION_SHAKE_HEAD,
            TEMPLATE_GREET_NURSERY_ACTION_CLAP,
        )

        return (
            TEMPLATE_GREET_NURSERY_ACTION_AFRAID,
            TEMPLATE_GREET_NURSERY_ACTION_STRETCH,
            TEMPLATE_GREET_NURSERY_ACTION_MEDITATE,
            TEMPLATE_GREET_NURSERY_ACTION_STOMP,
            TEMPLATE_GREET_NURSERY_ACTION_HERO,
            TEMPLATE_GREET_NURSERY_ACTION_BOW_SHY,
            TEMPLATE_GREET_NURSERY_ACTION_FLEX,
            TEMPLATE_GREET_NURSERY_ACTION_VICTORY_JUMP,
            TEMPLATE_GREET_NURSERY_ACTION_SCRATCH_HEAD,
            TEMPLATE_GREET_NURSERY_ACTION_WIPE_SWEAT,
            TEMPLATE_GREET_NURSERY_ACTION_YAWN,
            TEMPLATE_GREET_NURSERY_ACTION_REFUSE,
            TEMPLATE_GREET_NURSERY_ACTION_BLOW_KISS,
            TEMPLATE_GREET_NURSERY_ACTION_SHOOT_BALL,
            TEMPLATE_GREET_NURSERY_ACTION_SELF_PRAISE,
            TEMPLATE_GREET_NURSERY_ACTION_FIST_SALUTE,
            TEMPLATE_GREET_NURSERY_ACTION_AKIMBO,
            TEMPLATE_GREET_NURSERY_ACTION_DANCE,
            TEMPLATE_GREET_NURSERY_ACTION_PRAISE_SUN,
            TEMPLATE_GREET_NURSERY_ACTION_GREETING,
            TEMPLATE_GREET_NURSERY_ACTION_FAREWELL,
            TEMPLATE_GREET_NURSERY_ACTION_NOD,
            TEMPLATE_GREET_NURSERY_ACTION_SHAKE_HEAD,
            TEMPLATE_GREET_NURSERY_ACTION_CLAP,
        )

    @cached_property
    def _nursery_greeting_action_template_masks(self):
        """读取 24 个右侧动作面板模板，并转换为归一化动作 mask。"""
        masks = []
        for index, template in enumerate(self._nursery_greeting_action_templates):
            image = template.image
            if len(image.shape) == 3:
                image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            _, mask = cv2.threshold(image, 80, 255, cv2.THRESH_BINARY)
            mask = mask.astype(np.uint8)
            if mask.shape[:2] != (NURSERY_GREETING_ICON_SIZE, NURSERY_GREETING_ICON_SIZE):
                logger.warning(f'苗圃动作模板尺寸异常: {NURSERY_GREETING_ACTION_TEMPLATE_LABELS[index]}')
                mask = self._normalize_icon_mask(mask)
            masks.append(mask)
        return tuple(masks)

    @cached_property
    def _nursery_greeting_action_template_detail_keep_mask(self):
        """去掉 24 个动作中反复出现的小人主体公共像素，只保留区分动作的细节区域。"""
        templates = np.stack([mask > 0 for mask in self._nursery_greeting_action_template_masks])
        frequency = templates.mean(axis=0)
        return frequency <= NURSERY_GREETING_ACTION_TEMPLATE_COMMON_RATIO

    @cached_property
    def _nursery_greeting_action_template_detail_masks(self):
        return tuple(
            self._nursery_greeting_action_detail_mask(mask)
            for mask in self._nursery_greeting_action_template_masks
        )

    def _nursery_greeting_action_detail_mask(self, icon_mask):
        detail = (icon_mask > 0) & self._nursery_greeting_action_template_detail_keep_mask
        return np.where(detail, 255, 0).astype(np.uint8)

    def _nursery_greeting_action_template_score(self, target_mask, target_detail, candidate_mask):
        full_score = self._icon_mask_similarity(target_mask, candidate_mask)
        candidate_detail = self._nursery_greeting_action_detail_mask(candidate_mask)
        if (
                cv2.countNonZero(target_detail) < NURSERY_GREETING_ACTION_TEMPLATE_MIN_DETAIL_PIXELS
                or cv2.countNonZero(candidate_detail) < NURSERY_GREETING_ACTION_TEMPLATE_MIN_DETAIL_PIXELS
        ):
            return full_score, full_score, 0

        detail_score = self._icon_mask_similarity(target_detail, candidate_detail)
        score = (
            full_score * (1 - NURSERY_GREETING_ACTION_TEMPLATE_DETAIL_WEIGHT)
            + detail_score * NURSERY_GREETING_ACTION_TEMPLATE_DETAIL_WEIGHT
        )
        return score, full_score, detail_score

    def _icon_mask_similarity(self, target_icon, candidate_icon):
        """计算两个白色动作图标 mask 的 Dice 相似度。"""
        target = target_icon > 0
        candidate = candidate_icon > 0
        intersection = np.logical_and(target, candidate).sum()
        total = target.sum() + candidate.sum()
        if total <= 0:
            return 0
        return 2 * intersection / total

    def _handle_island_reward_optional(self, timeout=6):
        handled = False
        for _ in self.loop(timeout=timeout):
            if self._handle_island_reward_once():
                handled = True
                continue
        return handled

    def _handle_island_reward_once(self):
        if self.appear(GET_ITEMS_ISLAND, offset=(20, 20)):
            logger.info('[岛屿-每日周任务] 检测到岛屿奖励页面，点击安全区域关闭')
            self.device.click(ISLAND_CLICK_SAFE_AREA)
            return True
        if self.appear(ISLAND_GET, offset=(20, 20)):
            logger.info('[岛屿-每日周任务] 检测到岛屿领取页面，点击安全区域关闭')
            self.device.click(ISLAND_CLICK_SAFE_AREA)
            return True
        return False

    def _exit_nursery_greeting_action_menu(self, timeout=10):
        from module.island_daily_interact.assets import GREET_NURSERY_ACTION_MENU_CHECK

        logger.info('苗圃打招呼奖励处理完成，退出动作界面')
        click_interval = Timer(1)
        for _ in self.loop(timeout=timeout, skip_first=False):
            if self._handle_island_reward_once():
                continue
            if (
                    self.ui_page_appear(page_island)
                    and not self.appear(GREET_NURSERY_ACTION_MENU_CHECK, offset=(20, 20))
            ):
                logger.info('已回到岛屿主界面')
                return True
            if click_interval.reached():
                logger.info('未回到岛屿主界面，点击安全区域关闭动作界面')
                self.device.click(ISLAND_CLICK_SAFE_AREA)
                click_interval.reset()
                continue

        logger.warning('退出苗圃打招呼动作界面超时')
        return False

    def _clear_island_reward_popups(self, timeout=4):
        for _ in self.loop(timeout=timeout, skip_first=False):
            if self._handle_island_reward_once():
                continue
            return True
        logger.warning('清理岛屿奖励浮层超时')
        return False

    def _back_to_island_phone_from_development_plan(self):
        logger.info('[岛屿-每日周任务] 退出开发计划页面')
        for _ in self.loop(timeout=8):
            if self.appear(ISLAND_PHONE_CHECK):
                return True
            if self.appear_then_click(ISLAND_BACK, interval=2):
                continue
            if self._handle_island_reward_once():
                continue
        logger.warning('[岛屿-每日周任务] 退出开发计划页面超时')
        return False

    def _back_to_island_phone(self):
        logger.info('[岛屿-每日周任务] 返回岛屿手机页面')
        for _ in self.loop(timeout=20):
            if self.appear(ISLAND_PHONE_CHECK):
                return True
            if self.appear_then_click(ISLAND_BACK, interval=2):
                continue
            if self._handle_island_reward_once():
                continue
        logger.warning('[岛屿-每日周任务] 返回岛屿手机页面超时')
        return False

    def _delay_to_next_day(self):
        target = current_time().replace(hour=3, minute=0, second=0, microsecond=0)
        if target <= current_time():
            target += timedelta(days=1)
        self.config.task_delay(target=target)
        logger.info(f'[岛屿-每日周任务] 下次岛屿每日互动运行时间: {target}')
