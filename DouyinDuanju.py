# encoding:utf-8
import json
import requests
import re
import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from plugins import *

@plugins.register(
    name="DouyinDuanju",
    desire_priority=0,
    desc="抖音短剧资源查询插件，支持以下功能：\n1. 抖音短剧 [剧名] - 搜索短剧\n2. 抖音短剧 [book_id] - 获取1-5集播放链接\n3. 抖音短剧 [book_id] 第n集 - 获取n集开始的5集播放链接",
    version="2.4",
    author="Lingyuzhou",
)
class DouyinDuanju(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        self.base_url = "https://www.hhlqilongzhu.cn/api/duanju_fanqie.php"
        self.max_results = 5  # 修改为显示5条结果
        logger.info("[DouyinDuanju] inited.")

    def on_handle_context(self, e_context: EventContext):
        content = e_context["context"].content
        if not content.startswith("抖音短剧 "):
            return
        
        # 提取查询关键词
        query = content.replace("抖音短剧 ", "").strip()
        
        # 处理带集数的查询：抖音短剧 book_id 第n集
        episode_match = re.match(r'^(\d+)\s*第(\d+)集$', query)
        if episode_match:
            book_id, start_episode = episode_match.groups()
            logger.info(f"[DouyinDuanju] Matched episode query - book_id: {book_id}, episode: {start_episode}")
            reply_content = self._get_episode_list(book_id, int(start_episode))
        # 处理普通book_id查询
        elif query.isdigit() and len(query) > 15:
            reply_content = self._get_episode_list(query, 1)  # 默认从第1集开始
        # 处理剧名搜索
        else:
            reply_content = self._search_drama(query)

        reply = Reply()
        reply.type = ReplyType.TEXT
        reply.content = reply_content
        e_context["reply"] = reply
        e_context.action = EventAction.BREAK_PASS

    def _search_drama(self, keyword):
        """搜索短剧，返回前5条结果的基本信息"""
        try:
            response = requests.get(f"{self.base_url}?name={keyword}")
            data = response.json()
            
            if data["code"] != 200 or not data["data"]:
                return "未找到相关短剧资源。"
            
            reply_content = f"🎬 为您找到以下短剧：\n\n"
            
            # 显示前5个结果
            for idx, item in enumerate(data["data"][:self.max_results], 1):
                reply_content += f"{idx}. {item['title']}\n"
                reply_content += f"类型：{item['type']}\n"
                reply_content += f"剧集ID：{item['book_id']}\n"
                reply_content += f"封面：{item['cover']}\n"
                reply_content += "------------------------\n"
            
            reply_content += "\n💡 获取播放链接，请发送：\n"
            reply_content += "1. 抖音短剧 剧集ID（获取1-5集）\n"
            reply_content += "2. 抖音短剧 剧集ID 第n集（获取n~n+4集）"
            return reply_content
        except Exception as e:
            logger.error(f"[DouyinDuanju] Search drama error: {str(e)}")
            return "搜索出错，请稍后重试。"

    def _get_episode_list(self, book_id, start_episode=1):
        """获取剧集列表，返回从指定集数开始的5集播放链接"""
        try:
            response = requests.get(f"{self.base_url}?book_id={book_id}")
            data = response.json()
            
            if data["code"] != 200:
                return "获取剧集列表失败，请检查剧集ID是否正确。"
            
            total_episodes = len(data['data'])
            if total_episodes == 0:
                return "该短剧暂无剧集。"

            # 检查起始集数是否有效
            if start_episode < 1 or start_episode > total_episodes:
                return f"集数无效。该短剧共{total_episodes}集，请输入1-{total_episodes}之间的数字。"

            reply_content = f"📺 {data['book_name']} (共{total_episodes}集)\n"
            reply_content += f"👤 作者：{data['author']}\n\n"
            
            # 计算实际显示的集数范围
            end_episode = min(start_episode + 4, total_episodes)  # 修改为显示5集（n到n+4）
            
            # 显示指定范围的剧集
            for i in range(start_episode - 1, end_episode):
                episode = data['data'][i]
                episode_num = i + 1
                reply_content += f"第{episode_num}/{total_episodes}集\n"
                reply_content += f"▶️ {episode['url_mp4']}\n"
                reply_content += "------------------------\n"
            
            # 添加提示信息
            if end_episode < total_episodes:
                next_start = end_episode + 1
                reply_content += f"\n💡 继续观看请发送：抖音短剧 {book_id} 第{next_start}集"
            
            return reply_content
        except Exception as e:
            logger.error(f"[DouyinDuanju] Get episode list error: {str(e)}")
            return "获取剧集列表出错，请稍后重试。"

    def get_help_text(self, **kwargs):
        help_text = "抖音短剧资源查询插件使用说明：\n\n"
        help_text += "1. 搜索短剧：抖音短剧 [剧名]\n"
        help_text += "2. 获取1-5集：抖音短剧 [剧集ID]\n"
        help_text += "3. 获取指定集数：抖音短剧 [剧集ID] 第n集\n"
        help_text += "\n💡 示例：\n"
        help_text += "- 搜索：抖音短剧 总裁\n"
        help_text += "- 获取1-5集：抖音短剧 7416545333695499326\n"
        help_text += "- 获取6-10集：抖音短剧 7416545333695499326 第6集\n"
        return help_text
