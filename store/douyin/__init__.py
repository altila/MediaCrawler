# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/douyin/__init__.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/1/14 18:46
# @Desc    :
import json
from typing import List

import config
from media_platform.douyin.media import extract_cover_url, extract_image_urls, extract_video_urls
from var import source_keyword_var
from tools.user_hash import anonymize_user_id, mask_nickname

from ._store_impl import *


class DouyinStoreFactory:
    STORES = {
        "csv": DouyinCsvStoreImplement,
        "db": DouyinDbStoreImplement,
        "postgres": DouyinDbStoreImplement,
        "json": DouyinJsonStoreImplement,
        "jsonl": DouyinJsonlStoreImplement,
        "sqlite": DouyinSqliteStoreImplement,
        "mongodb": DouyinMongoStoreImplement,
        "excel": DouyinExcelStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = DouyinStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError("[DouyinStoreFactory.create_store] Invalid save option only supported csv or db or json or sqlite or mongodb or excel ...")
        return store_class()


def _extract_comment_image_list(comment_item: Dict) -> List[str]:
    """
    Extract comment image list

    Args:
        comment_item (Dict): Douyin comment

    Returns:
        List[str]: Comment image list
    """
    images_res: List[str] = []
    image_list: List[Dict] = comment_item.get("image_list", [])

    if not image_list:
        return []

    for image in image_list:
        image_url_list = image.get("origin_url", {}).get("url_list", [])
        if image_url_list and len(image_url_list) > 1:
            images_res.append(image_url_list[1])

    return images_res


def _extract_music_download_url(aweme_detail: Dict) -> str:
    """
    Extract music download URL

    Args:
        aweme_detail (Dict): Douyin video

    Returns:
        str: Music download URL
    """
    music_item = aweme_detail.get("music", {})
    play_url = music_item.get("play_url", {})
    music_url = play_url.get("uri", "")
    return music_url


async def update_douyin_aweme(aweme_item: Dict):
    aweme_id = aweme_item.get("aweme_id")
    user_info = aweme_item.get("author", {})
    interact_info = aweme_item.get("statistics", {})
    save_content_item = {
        "aweme_id": aweme_id,
        "aweme_type": str(aweme_item.get("aweme_type")),
        "title": aweme_item.get("desc", ""),
        "desc": aweme_item.get("desc", ""),
        "uid": anonymize_user_id(user_info.get("uid")),  # 创作者匿名哈希(不存原始 uid)
        "nickname": mask_nickname(user_info.get("nickname")),  # 用户昵称(已脱敏)
        "liked_count": str(interact_info.get("digg_count")),
        "collected_count": str(interact_info.get("collect_count")),
        "comment_count": str(interact_info.get("comment_count")),
        "share_count": str(interact_info.get("share_count")),
        "create_time": aweme_item.get("create_time"),
        "last_modify_ts": utils.get_current_timestamp(),
        "aweme_url": f"https://www.douyin.com/video/{aweme_id}",
        "cover_url": extract_cover_url(aweme_item),
        "video_download_url": (extract_video_urls(aweme_item) or [""])[0],
        "music_download_url": _extract_music_download_url(aweme_item),
        "note_download_url": ",".join(extract_image_urls(aweme_item)),
        "source_keyword": source_keyword_var.get(),
    }
    utils.logger.info(f"[store.douyin.update_douyin_aweme] douyin aweme id:{aweme_id}, title:{save_content_item.get('title')}")
    await DouyinStoreFactory.create_store().store_content(content_item=save_content_item)


async def batch_update_dy_aweme_comments(aweme_id: str, comments: List[Dict]):
    if not comments:
        return
    for comment_item in comments:
        await update_dy_aweme_comment(aweme_id, comment_item)


async def update_dy_aweme_comment(aweme_id: str, comment_item: Dict):
    comment_aweme_id = comment_item.get("aweme_id")
    if aweme_id != comment_aweme_id:
        utils.logger.error(f"[store.douyin.update_dy_aweme_comment] comment_aweme_id: {comment_aweme_id} != aweme_id: {aweme_id}")
        return
    user_info = comment_item.get("user", {})
    comment_id = comment_item.get("cid")
    parent_comment_id = comment_item.get("reply_id", "0")
    save_comment_item = {
        "comment_id": comment_id,
        "aweme_id": aweme_id,
        "content": comment_item.get("text"),
        "sec_uid": anonymize_user_id(user_info.get("sec_uid")),  # 创作者匿名哈希(不存原始 uid)
        "uid": anonymize_user_id(user_info.get("uid")),  # 创作者匿名哈希(不存原始 uid)
        "nickname": mask_nickname(user_info.get("nickname")),  # 用户昵称(已脱敏)
        "ip_label": comment_item.get("ip_label"),
        "sub_comment_count": str(comment_item.get("reply_comment_total", 0)),
        "like_count": (comment_item.get("digg_count") if comment_item.get("digg_count") else 0),
        "create_time": comment_item.get("create_time"),
        "last_modify_ts": utils.get_current_timestamp(),
        "parent_comment_id": parent_comment_id,
        "pictures": ",".join(_extract_comment_image_list(comment_item)),
    }
    utils.logger.info(f"[store.douyin.update_dy_aweme_comment] douyin aweme comment: {comment_id}, content: {save_comment_item.get('content')}")

    await DouyinStoreFactory.create_store().store_comment(comment_item=save_comment_item)


async def save_creator(user_id: str, creator: Dict):
    user_info = creator.get("user") or {}
    if not user_info:
        # 说明响应里没有用户对象(键名变化/被风控)，打印顶层键便于定位
        utils.logger.warning(
            f"[store.douyin.save_creator] user_info is empty, response top-level keys: {list(creator.keys())}"
        )
    save_creator_item = {
        "sec_uid": anonymize_user_id(user_info.get("sec_uid")),  # 创作者匿名哈希(不存原始 uid)
        "uid": anonymize_user_id(user_info.get("uid")),  # 创作者匿名哈希(不存原始 uid)
        "unique_id": anonymize_user_id(user_info.get("unique_id")),  # 创作者匿名哈希(不存原始 uid)
        "short_id": anonymize_user_id(user_info.get("short_id")),  # 创作者匿名哈希(不存原始 uid)
        "nickname": mask_nickname(user_info.get("nickname")),  # 用户昵称(已脱敏)
        "ip_location": user_info.get("ip_location"),
        "iso_country_code": user_info.get("iso_country_code"),
        "store_region": user_info.get("store_region"),
        "country": user_info.get("country"),
        "province": user_info.get("province"),
        "city": user_info.get("city"),
        "district": user_info.get("district"),
        "gender": user_info.get("gender"),
        "user_age": user_info.get("user_age"),
        "signature": user_info.get("signature"),
        "aweme_count": user_info.get("aweme_count"),
        "follower_count": user_info.get("follower_count"),
        "following_count": user_info.get("following_count"),
        "total_favorited": user_info.get("total_favorited"),
    }
    utils.logger.info(f"[store.douyin.save_creator] douyin creator: {save_creator_item.get('nickname')}")
    await DouyinStoreFactory.create_store().store_creator(save_creator_item)
