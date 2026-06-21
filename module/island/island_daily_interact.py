from datetime import datetime, timedelta

import cv2
import numpy as np

from module.island.island import Island
from module.island.assets import *
from module.base.button import Button
from module.base.timer import Timer
from module.base.utils import crop
from module.handler.assets import STORY_SKIP_3
from module.logger import logger
from module.ui.assets import ISLAND_PHONE_CHECK
from module.ui.page import page_island, page_island_map, page_island_phone


DEVELOPMENT_PLAN_TASK_LIST_AREA = (179, 124, 280, 690)
INTERACT_BLUE_RING_HSV_LOWER = np.array([85, 45, 95])
INTERACT_BLUE_RING_HSV_UPPER = np.array([145, 190, 255])
INTERACT_WHITE_ICON_HSV_LOWER = np.array([0, 0, 155])
INTERACT_WHITE_ICON_HSV_UPPER = np.array([179, 100, 255])
NURSERY_GREETING_ACTION_MATCH_THRESHOLD = 0.58
NURSERY_GREETING_ACTION_MATCH_MARGIN = 0.08
NURSERY_GREETING_ACTION_MAX_SCROLL = 5
NURSERY_GREETING_ICON_SIZE = 64
NURSERY_GREETING_OPTION_ICON_WIDTH = 90
NURSERY_GREETING_OPTION_ICON_HEIGHT = 92
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
        logger.hr('Island Daily Interact Run', level=1)

        all_done = True
        self.pet_cat()
        all_done = self.juu_express() and all_done
        all_done = self.business_delivery() and all_done
        if self.config.IslandDailyInteract_NurseryGreeting:
            all_done = self.greet_nursery_juus() and all_done
        if self.config.IslandDailyInteract_WeeklyPhoto:
            all_done = self.weekly_photo() and all_done

        if all_done:
            self._delay_to_next_day()
            logger.info('岛屿每日互动执行完成')
        else:
            logger.warning('岛屿每日互动部分任务失败，60分钟后重试')
            self.config.task_delay(minute=60)

    def pet_cat(self):
        """
        执行晨露农场摸猫。

        Pages:
            in: 任意页面
            out: page_island 或奖励关闭后的当前页面
        """
        from module.island_daily_interact.assets import PET_CAT_FARM_INTERACT

        logger.hr('Pet Cat', level=2)
        if not self.island_map_goto('farm'):
            logger.warning('前往晨露农场失败，跳过摸猫任务')
            return False
        self.move_for_pet_cat_farm()

        if self._click_optional_interact(PET_CAT_FARM_INTERACT, '摸猫互动'):
            self._handle_island_reward_optional()
        else:
            logger.info('未检测到摸猫互动按钮，跳过')

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

        logger.hr('JUU Express', level=2)
        if not self._detect_development_plan_template_task(
                task_template=TEMPLATE_JUU_EXPRESS_TASK_ICON,
                tab_button=DEVELOPMENT_PLAN_DAILY_TAB,
                tab_check=DEVELOPMENT_PLAN_DAILY_TAB_CHECK,
                tab_label='每日计划',
                label='JUU速运'):
            logger.info('未检测到或已完成 JUU 速运任务，跳过')
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
                logger.warning(f'JUU速运地点交互失败，终止后续流程: {name}')
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

        logger.hr('Business Delivery', level=2)
        if not self._detect_development_plan_template_task(
                task_template=TEMPLATE_BUSINESS_DELIVERY_TASK_ICON,
                tab_button=DEVELOPMENT_PLAN_DAILY_TAB,
                tab_check=DEVELOPMENT_PLAN_DAILY_TAB_CHECK,
                tab_label='每日计划',
                label='商区外送服务'):
            logger.info('未检测到或已完成商区外送服务任务，跳过')
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
                logger.warning(f'商区外送服务地点交互失败，终止后续流程: {name}')
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

        logger.hr('Weekly Photo', level=2)
        completed = True
        for _ in range(10):
            if not self._start_development_plan_template_task(
                    task_template=TEMPLATE_WEEKLY_PHOTO_TASK_ICON,
                    task_check=WEEKLY_PHOTO_TASK_CHECK,
                    tab_button=DEVELOPMENT_PLAN_WEEKLY_TAB,
                    tab_check=DEVELOPMENT_PLAN_WEEKLY_TAB_CHECK,
                    tab_label='每周计划',
                    label='每周照相任务'):
                logger.info('未检测到或已完成每周照相任务，结束循环')
                self._back_to_island_phone_from_development_plan()
                break

            if not self._run_weekly_photo_once():
                logger.warning('每周照相任务单轮流程未完整完成，结束循环')
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
            if not self.greet_nursery_juu(index, move_method, bubble_area):
                logger.warning(f'苗圃第{index}个小人打招呼失败，终止后续流程')
                completed = False
                break

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
        max_attempt = 2 if index == 3 else 1
        target_icon = None
        for attempt in range(max_attempt):
            if max_attempt > 1:
                logger.info(f'苗圃第{index}个小人打招呼路线尝试: {attempt + 1}/{max_attempt}')

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
            if bubble_found:
                break
            if attempt < max_attempt - 1:
                logger.info(f'苗圃第{index}个小人未检测到打招呼气泡，重新尝试一次')
                continue

            logger.info(f'苗圃第{index}个小人未检测到打招呼气泡，视为已完成')
            return True

        if target_icon is None:
            logger.warning(f'苗圃第{index}个小人动作图标提取失败')
            return False
        if not self._open_nursery_greeting_action_menu():
            return False
        if not self._select_nursery_greeting_action(target_icon):
            return False

        self.device.sleep(6)
        self._handle_island_reward_optional()
        return self._exit_nursery_greeting_action_menu()

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
            logger.info(f'前往{name}，第{attempt + 1}次尝试')
            if not self.island_map_goto(destination):
                logger.warning(f'前往{name}失败')
                continue
            move_method()

            interact_status = self._click_optional_interact_or_complete(
                    interact_button=interact_button,
                    complete_button=complete_button,
                    label=f'{name}交付互动')
            if interact_status == 'clicked':
                self.handle_island_story_skip_safely()
                return True
            if interact_status == 'complete':
                return True

            logger.warning(f'未检测到{name}交付互动按钮')

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

    def move_for_juu_port(self):
        """JUU速运：港口移动路线。"""
        self.island_left(2200)
        self.device.click(ISLAND_JUMP)
        self.island_left(1200)
        self.island_up(500)

    def move_for_juu_port_business(self):
        """JUU速运：港口商区移动路线。"""
        self.island_up(1500)
        self.island_left(400)

    def move_for_juu_plain(self):
        """JUU速运：栖风原野移动路线。"""
        self.island_right(6000)
        self.island_down(3000)
        self.island_right(2300)

    def move_for_juu_nursery(self):
        """JUU速运：繁荫农圃移动路线。"""
        self.island_left(800)
        self.island_up(5500)
        self.island_left(1000)
        self.island_up(3700)

    def move_for_business_delivery_assembly(self):
        """商区外送服务：集会岛移动路线。"""
        self.island_up(3000)
        self.island_left(2000)
        self.island_up(5500)
        self.island_right(300)
        self.island_up(2200)
        self.island_left(1100)

    def move_for_business_delivery_nursery(self):
        """商区外送服务：繁荫农圃移动路线。"""
        self.island_up(2000)
        self.island_right(1800)
        self.island_up(500)

    def move_for_pet_cat_farm(self):
        """摸猫：晨露农场移动路线。"""
        self.island_left(500)
        self.island_down(200)

    def move_for_nursery_greet_1(self):
        """苗圃打招呼：第一个小人移动路线。"""
        self.island_up(500)
        self.island_right(600)

    def move_for_nursery_greet_2(self):
        """苗圃打招呼：第二个小人移动路线。"""
        self.island_left(800)
        self.island_up(5500)
        self.island_left(1000)
        self.island_up(800)
        self.island_left(100)
        self.island_up(100)

    def move_for_nursery_greet_3(self):
        """苗圃打招呼：第三个小人移动路线。"""
        self.island_down(1500)
        self.island_left(1500)
        self.island_down(1000)
        self.island_left(1000)
        self.island_down(800)
        self.island_left(1800)

    def handle_island_story_skip_safely(self):
        """
        安全处理岛屿互动后的剧情跳过。

        Returns:
            bool: 是否检测到返回状态或执行过跳过处理。
        """
        handled = False
        for _ in self.loop(timeout=20, skip_first=False):
            if self.appear(STORY_SKIP_3, offset=(20, 20), interval=2):
                self.device.click(AIR_DROP_SKIP)
                handled = True
                continue

            in_island = self.ui_page_appear(page_island)
            in_island_map = self.ui_page_appear(page_island_map)
            if in_island or in_island_map:
                return handled

            if self.appear(ISLAND_PHONE_CHECK):
                logger.warning('跳过期间检测到岛屿手机页面，停止继续点击跳过')
                self.ui_goto(page_island, get_ship=False)
                return handled

            if self._handle_island_reward_once():
                handled = True
                continue

        logger.warning('剧情跳过等待超时')
        return handled

    def _juu_express_steps(self):
        from module.island_daily_interact.assets import (
            JUU_EXPRESS_NURSERY_INTERACT,
            JUU_EXPRESS_PLAIN_INTERACT,
            JUU_EXPRESS_PORT_BUSINESS_INTERACT,
            JUU_EXPRESS_PORT_INTERACT,
            ROUTE_JUU_NURSERY_COMPLETE,
            ROUTE_PLAIN_COMPLETE,
            ROUTE_PORT_BUSINESS_COMPLETE,
            ROUTE_PORT_COMPLETE,
        )

        return [
            ('港口', 'port', self.move_for_juu_port, JUU_EXPRESS_PORT_INTERACT, ROUTE_PORT_COMPLETE),
            ('港口商区', 'port_business', self.move_for_juu_port_business, JUU_EXPRESS_PORT_BUSINESS_INTERACT, ROUTE_PORT_BUSINESS_COMPLETE),
            ('栖风原野', 'mine_forest', self.move_for_juu_plain, JUU_EXPRESS_PLAIN_INTERACT, ROUTE_PLAIN_COMPLETE),
            ('繁荫农圃', 'nursery', self.move_for_juu_nursery, JUU_EXPRESS_NURSERY_INTERACT, ROUTE_JUU_NURSERY_COMPLETE),
        ]

    def _business_delivery_steps(self):
        from module.island_daily_interact.assets import (
            BUSINESS_DELIVERY_ASSEMBLY_INTERACT,
            BUSINESS_DELIVERY_NURSERY_INTERACT,
            BUSINESS_DELIVERY_PORT_BUSINESS_INTERACT,
            BUSINESS_DELIVERY_PORT_INTERACT,
            ROUTE_ASSEMBLY_COMPLETE,
            ROUTE_BUSINESS_NURSERY_COMPLETE,
            ROUTE_PORT_BUSINESS_COMPLETE,
            ROUTE_PORT_COMPLETE,
        )

        return [
            ('港口商区', 'port_business', self.move_for_juu_port_business, BUSINESS_DELIVERY_PORT_BUSINESS_INTERACT, ROUTE_PORT_BUSINESS_COMPLETE),
            ('繁荫农圃', 'nursery', self.move_for_business_delivery_nursery, BUSINESS_DELIVERY_NURSERY_INTERACT, ROUTE_BUSINESS_NURSERY_COMPLETE),
            ('港口', 'port', self.move_for_juu_port, BUSINESS_DELIVERY_PORT_INTERACT, ROUTE_PORT_COMPLETE),
            ('集会岛', 'assembly', self.move_for_business_delivery_assembly, BUSINESS_DELIVERY_ASSEMBLY_INTERACT, ROUTE_ASSEMBLY_COMPLETE),
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

        logger.warning('进入开发计划页面超时')
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

        logger.info(f'检测到{label}，点击任务图标')
        self.device.click(task_button)
        for _ in self.loop(timeout=8):
            if self.appear_then_click(task_check, offset=(20, 20), interval=2):
                logger.info(f'{label}确认成功')
                return True
            if self._handle_island_reward_once():
                continue

        logger.warning(f'{label}确认按钮等待超时')
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

        logger.info(f'检测到{label}任务图标')
        return True

    def _switch_development_plan_tab(self, tab_button, tab_check, label):
        """切换到开发计划目标页签，并确认页签已激活。"""
        logger.info(f'切换到{label}页签')
        for _ in self.loop(timeout=12):
            if self.appear(tab_check):
                logger.info(f'{label}页签已激活')
                return True
            if self.appear_then_click(tab_button, interval=2):
                continue
            if self._handle_island_reward_once():
                continue

        logger.warning(f'切换到{label}页签超时')
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
            logger.info(f'每周照相第{index + 1}轮')
            self._click_weekly_photo_button(WEEKLY_PHOTO_CAMERA, '照相按钮')
            self._click_weekly_photo_button(WEEKLY_PHOTO_IDLE, '空闲按钮')

        for _ in self.loop(timeout=12):
            if self._handle_island_reward_once():
                continue
            if self.appear_then_click(ISLAND_BACK, interval=2):
                return True

        logger.warning('每周照相通用奖励或返回按钮等待超时')
        return False

    def _click_weekly_photo_button(self, button, label):
        """每周照相页面按钮位置固定，直接点击，不做出现检测。"""
        self.device.screenshot()
        logger.info(f'点击{label}')
        self.device.click(button)

    def _click_optional_interact(self, button, label, timeout=8):
        for _ in self.loop(timeout=timeout):
            if self.appear_then_click(button, interval=2):
                logger.info(f'点击{label}')
                return True
            if self._handle_island_reward_once():
                continue

        return False

    def _click_optional_interact_or_complete(self, interact_button, complete_button, label, timeout=8):
        for _ in self.loop(timeout=timeout):
            if self.appear_then_click(interact_button, interval=2):
                logger.info(f'点击{label}')
                return 'clicked'
            if self.appear(complete_button, offset=(20, 20)):
                logger.info(f'{label}已完成，进入下一步')
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

    def _find_interact_blue_ring(self, area, show_log=False):
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

    def _extract_nursery_greeting_action_icon(self, bubble_area):
        """从互动气泡中心提取白色动作图标 mask。"""
        button_area = bubble_area.area if isinstance(bubble_area, Button) else bubble_area
        ring_rect = self._find_interact_blue_ring(bubble_area)
        if ring_rect is None:
            return None

        image = crop(self.device.image, button_area, copy=False)
        x, y, width, height = ring_rect
        icon_image = self._crop_blue_ring_inner_icon(image, x, y, width, height)
        icon_mask = self._white_icon_mask(icon_image)
        if cv2.countNonZero(icon_mask) < 20:
            logger.warning('互动气泡内白色动作图标像素过少')
            return None
        return self._normalize_icon_mask(icon_mask)

    def _crop_blue_ring_inner_icon(self, image, x, y, width, height):
        """裁剪蓝色互动圈，并用椭圆遮罩保留内侧动作图标。"""
        icon_image = image[y:y + height, x:x + width]
        if icon_image.size <= 0:
            return icon_image

        yy, xx = np.ogrid[:height, :width]
        cx = (width - 1) / 2
        cy = (height - 1) / 2
        rx = max(width / 2, 1)
        ry = max(height / 2, 1)
        ellipse_mask = (((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 0.78 ** 2)
        return np.where(ellipse_mask[..., None], icon_image, 0).astype(icon_image.dtype)

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

    def _select_nursery_greeting_action(self, target_icon):
        """在动作列表中匹配目标动作图标并点击对应选项。"""
        for scroll_index in range(NURSERY_GREETING_ACTION_MAX_SCROLL + 1):
            match_state = 'empty'
            for _ in self.loop(timeout=4, skip_first=False):
                match_button, match_state = self._match_nursery_greeting_action(target_icon, GREET_NURSERY_ACTION_LIST_AREA)
                if match_button is not None:
                    self.device.click(match_button)
                    logger.info('点击苗圃打招呼动作选项')
                    return True
                if match_state == 'empty':
                    continue
                break

            if scroll_index >= NURSERY_GREETING_ACTION_MAX_SCROLL:
                break

            logger.info(f'当前动作列表未命中目标动作，向上滑动列表: {scroll_index + 1}')
            self.device.swipe_vector(
                vector=(0, -240),
                box=GREET_NURSERY_ACTION_OPTION_SCROLL.button,
                name='NurseryGreetingActionSwipe',
            )
            self.device.sleep(0.3)
            self.device.long_click(GREET_NURSERY_ACTION_SCROLL_SAFE_AREA)

        logger.warning('苗圃打招呼动作列表未匹配到目标动作')
        return False

    def _match_nursery_greeting_action(self, target_icon, list_area):
        """在当前动作列表可见区域内寻找最相似的动作图标。"""
        candidates = self._detect_nursery_greeting_action_candidates(list_area)
        if not candidates:
            return None, 'empty'

        target_symbol = self._nursery_greeting_symbol_mask(target_icon)
        target_symbol_pixels = cv2.countNonZero(target_symbol)
        use_symbol = 20 <= target_symbol_pixels <= 220
        scored = []
        for center, icon_mask, symbol_mask in candidates:
            full_score = self._icon_mask_similarity(target_icon, icon_mask)
            if use_symbol:
                symbol_score = self._icon_mask_similarity(target_symbol, symbol_mask)
                score = full_score * 0.55 + symbol_score * 0.45
            else:
                symbol_score = 0
                score = full_score
            scored.append((score, center, full_score, symbol_score))
        scored.sort(key=lambda item: item[0], reverse=True)

        best_score, best_center, best_full, best_symbol = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else 0
        logger.attr(
            'NurseryGreetingActionMatch',
            (
                f'best={best_score:.3f}, second={second_score:.3f}, '
                f'full={best_full:.3f}, symbol={best_symbol:.3f}, count={len(scored)}'
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
            symbol_mask = self._nursery_greeting_symbol_mask(icon_mask)
            center = (
                button_area[0] + center_x,
                button_area[1] + center_y,
            )
            candidates.append((center, icon_mask, symbol_mask))

        candidates.sort(key=lambda item: (item[0][1], item[0][0]))
        return candidates

    def _nursery_greeting_symbol_mask(self, icon_mask):
        """提取动作图标中区别于小人主体的小符号、手势和道具。"""
        count, labels, stats, centroids = cv2.connectedComponentsWithStats(icon_mask, connectivity=8)
        symbol_mask = np.zeros_like(icon_mask)
        if count <= 1:
            return symbol_mask

        largest = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        height, _ = icon_mask.shape
        for index in range(1, count):
            if index == largest:
                continue

            area = stats[index, cv2.CC_STAT_AREA]
            if area < 6 or area > 350:
                continue
            if centroids[index][1] > height * 0.72:
                continue

            symbol_mask[labels == index] = 255
        return symbol_mask

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
            logger.info('检测到岛屿奖励页面，点击安全区域关闭')
            self.device.click(ISLAND_CLICK_SAFE_AREA)
            return True
        if self.appear(ISLAND_GET, offset=(20, 20)):
            logger.info('检测到岛屿领取页面，点击安全区域关闭')
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
        logger.info('退出开发计划页面')
        for _ in self.loop(timeout=8):
            if self.appear(ISLAND_PHONE_CHECK):
                return True
            if self.appear_then_click(ISLAND_BACK, interval=2):
                continue
            if self._handle_island_reward_once():
                continue
        logger.warning('退出开发计划页面超时')
        return False

    def _back_to_island_phone(self):
        logger.info('返回岛屿手机页面')
        for _ in self.loop(timeout=20):
            if self.appear(ISLAND_PHONE_CHECK):
                return True
            if self.appear_then_click(ISLAND_BACK, interval=2):
                continue
            if self._handle_island_reward_once():
                continue
        logger.warning('返回岛屿手机页面超时')
        return False

    def _delay_to_next_day(self):
        target = datetime.now().replace(hour=3, minute=0, second=0, microsecond=0)
        if target <= datetime.now():
            target += timedelta(days=1)
        self.config.task_delay(target=target)
        logger.info(f'下次岛屿每日互动运行时间: {target}')
