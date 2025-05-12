import time
import requests
import os
import json
import sys
import mimetypes

from tqdm import tqdm
from urllib.parse import urlparse
from loguru import logger as log

log.remove()
log.add(sys.stderr, level="INFO")


class Downloader:
    def __init__(
        self,
        url: str,  # 用户主页的url
        platform: str,  # 平台名称kemono/coomer

        coomer_base_api_url="https://coomer.su/api/v1",
        coomer_image_api_url="https://img.coomer.su/thumbnail/data",
        coomer_file1_api_url="https://n1.coomer.su/data",
        coomer_file2_api_url="https://n2.coomer.su/data",
        coomer_file3_api_url="https://n3.coomer.su/data",
        coomer_file4_api_url="https://n4.coomer.su/data",

        kemono_base_api_url="https://kemono.su/api/v1",
        kemono_image_api_url="https://img.kemono.su/thumbnail/data",
        kemono_file1_api_url="https://n1.kemono.su/data",
        kemono_file2_api_url="https://n2.kemono.su/data",
        kemono_file3_api_url="https://n3.kemono.su/data",
        kemono_file4_api_url="https://n4.kemono.su/data",
    ):
        # 解析URL，提取路径部分并分割，过滤掉空字符串
        url_parsed_list = list(filter(None, urlparse(url).path.split("/")))
        self.service = url_parsed_list[0]
        self.user_id = url_parsed_list[2]

        # 选择api
        if platform == "coomer":
            self.base_api_url = coomer_base_api_url
            self.image_api_url = coomer_image_api_url
            self.file1_api_url = coomer_file1_api_url
            self.file2_api_url = coomer_file2_api_url
            self.file3_api_url = coomer_file3_api_url
            self.file4_api_url = coomer_file4_api_url
        elif platform == "kemono":
            self.base_api_url = kemono_base_api_url
            self.image_api_url = kemono_image_api_url
            self.file1_api_url = kemono_file1_api_url
            self.file2_api_url = kemono_file2_api_url
            self.file3_api_url = kemono_file3_api_url
            self.file4_api_url = kemono_file4_api_url
        

    def get_file_type(self, filename) -> str:
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            if mime_type.startswith("image/"):
                return "image"
            else:
                return "other"

    def download_file(self, url, output_path):
        res = requests.get(url=url, stream=True)
        if res.status_code == 200:
            with open(output_path, "wb") as f:
                for chunk in res.iter_content(chunk_size=8192):
                    f.write(chunk)
        else:
            raise Exception(f"服务器响应码错误 code:{res.status_code}")

    def download_image(self, url_path, output_path):
        self.download_file(self.image_api_url + url_path, output_path)

    def download_other(self, url_path, output_path):
        video_urls = [
            self.file1_api_url,
            self.file2_api_url,
            self.file3_api_url,
            self.file4_api_url,
        ]
        for video_url in video_urls:
            try:
                self.download_file(video_url + url_path, output_path)
                return  # 成功则直接返回
            except:
                continue  # 失败则尝试下一个

        # 如果所有URL都尝试失败，抛出异常
        raise Exception("下载失败，请检查网络连接或稍后再试")

    def downloader(self, url_path, file_name, output_path):
        file_type = self.get_file_type(file_name)
        file_output_path = os.path.join(output_path, file_name)
        if file_type == "image":
            self.download_image(url_path, file_output_path)
        if file_type == "other":
            self.download_other(url_path, file_output_path)

    def get_post_info(self, req_interval=0.1) -> list[dict]:
        """获取用户帖子列表"""
        page_num = 0
        res_list = []
        while True:
            res = requests.get(
                url=f"{self.base_api_url}/{self.service}/user/{self.user_id}",
                params={"o": page_num},
            ).json()
            page_num += 50
            # if len(res) <= 50:
            if len(res) == 0:
                break
            else:
                log.info(f"⌛查询第 {int(page_num/50)} 页")
            res_list += res
            time.sleep(req_interval)

        log.success(f"🚀 查询完成，该用户总帖子数量为：{len(res_list)}个")
        return res_list

    def download_post(
        self, post_dict: list, output_dir_path: str, download_interval=0.1
    ):
        """下载单个帖子"""
        # 检查下载存放目录是否存在
        if not os.path.exists(output_dir_path):
            os.mkdir(output_dir_path)

        # 创建帖子存放文件夹
        post_storage_dir = os.path.join(output_dir_path, post_dict["id"])
        if not os.path.exists(post_storage_dir):
            os.mkdir(post_storage_dir)
        else:
            log.info(f"文件夹：{output_dir_path} 已存在")
            return

        # 写入帖子文本内容
        if post_dict["content"]:
            log.info(f"📄 写入帖子文本：{post_dict["title"]}")
            content_html_path = os.path.join(post_storage_dir, "content.html")
            with open(content_html_path, "w", encoding="utf-8") as f:
                f.write(post_dict["title"] + "\n" + post_dict["content"])

        # 下载文件
        if post_dict["file"]:
            log.info(f"⌛ 下载文件：{post_dict['file']['name']}")
            self.downloader(
                post_dict["file"]["path"], post_dict["file"]["name"], post_storage_dir
            )
            time.sleep(download_interval)

        # 下载附件
        if post_dict["attachments"]:
            log.info(f"⌛ 下载附件：共 {len(post_dict['attachments'])} 个")
            attachment_num = 1
            for attachment in post_dict["attachments"]:
                self.downloader(
                    attachment["path"], attachment["name"], post_storage_dir
                )
                time.sleep(download_interval)
                log.info(
                    f"📦 下载附件：{attachment['name']} | {attachment_num}/{len(post_dict['attachments'])}"
                )
                attachment_num += 1

        log.info("✅ 帖子下载完成")

    def download_posts(
        self,
        post_list: list,
        output_dir_path: str,
        error_output_dir_path="./error.json",
        download_interval=0.1,
    ):
        error_list = []
        for post in tqdm(post_list):
            try:
                self.download_post(post, output_dir_path, download_interval)
                time.sleep(download_interval)
            except Exception as e:
                log.error(f"❌ 帖子下载失败 帖子ID：{post['id']}")
                print(e)
                error_list.append(post)
        log.success(
            f"🚀 下载完毕 | 下载成功：{len(post_list)-len(error_list)}/{len(post_list)}"
        )
        if error_list != []:
            with open(error_output_dir_path, "w", encoding="utf-8") as f:
                json.dump(error_list, f, indent=4, ensure_ascii=False)

        return error_list

if __name__ == "__main__":
    kd = Downloader("https://kemono.su/patreon/user/58531325", "kemono")
    # post_list = kd.get_post_info()
    # with open("temp/user_info.json", "w", encoding="utf-8") as f:
    #     json.dump(post_list, f, indent=4, ensure_ascii=False)

    # with open("temp/user_info.json", "r", encoding="utf-8") as f:
    #     post_list = json.load(f)
    # # download_fail_list = kd.download_post(post_list[10], r"./temp")
    # download_fail_list = kd.download_posts(post_list, r"./temp")