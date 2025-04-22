import time
import requests
import os
import json
import sys
import mimetypes

from tqdm import tqdm
from urllib.parse import urlparse
from loguru import logger as log
from bs4 import BeautifulSoup

log.remove()
log.add(sys.stderr, level="INFO")


class KemonoDownloader:
    def __init__(
        self,
        url: str,  # 用户主页的url
        api_url="https://kemono.su/api/v1",
        image_api_url="https://img.kemono.su/thumbnail/data",
        video_api_url="https://n2.kemono.su/data",
        file_api_url="https://n4.kemono.su/data",
        # attachments_api_url="https://n1.kemono.su/data",
        # file_api_url="https://n4.kemono.su/data,
    ):
        self.api_url = api_url
        self.image_api_url = image_api_url
        self.file_api_url = file_api_url
        self.video_api_url = video_api_url

        # 解析URL，提取路径部分并分割，过滤掉空字符串
        url_parsed_list = list(filter(None, urlparse(url).path.split("/")))
        self.service = url_parsed_list[0]
        self.user_id = url_parsed_list[2]

    def get_file_type(self, filename) -> str:
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            if mime_type.startswith("image/"):
                return "image"
            if mime_type.startswith("video/"):
                return "video"

    def download(self, url, output_path):
        res = requests.get(url=url, stream=True)
        if res.status_code == 200:
            with open(output_path, "wb") as f:
                for chunk in res.iter_content(chunk_size=8192):
                    f.write(chunk)
        else:
            log.error(res.status_code)
            raise Exception

    def get_post_info(self, req_interval=0.1) -> list[dict]:
        """获取用户帖子列表"""
        page_num = 0
        res_list = []
        while True:
            res = requests.get(
                url=f"{self.api_url}/{self.service}/user/{self.user_id}",
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

        log.info(f"✅查询完成，该用户总帖子数量为：{len(res_list)}个")
        return res_list

    def download_post(
        self, post_dict: list, output_dir_path: str, download_interval=0.1
    ):
        # 检查下载存放目录是否存在
        if not os.path.exists(output_dir_path):
            os.mkdir(output_dir_path)

        # 创建帖子存放文件夹
        post_storage_dir = os.path.join(output_dir_path, post_dict["id"])
        if not os.path.exists(post_storage_dir):
            os.mkdir(post_storage_dir)

        # 写入帖子文本内容
        if post_dict["content"]:
            log.info(f"⌛写入帖子文本：{post_dict["title"]}")
            content_html_path = os.path.join(post_storage_dir, "content.html")
            with open(content_html_path, "w", encoding="utf-8") as f:
                f.write(post_dict["title"] + "\n" + post_dict["content"])

        # 下载文件
        if post_dict["file"]:
            log.info(f"⌛下载文件：{post_dict['file']['name']}")
            file_type = self.get_file_type(post_dict["file"]["name"])
            file_output_path = os.path.join(post_storage_dir, post_dict["file"]["name"])
            if file_type == "image":
                self.download(
                    self.image_api_url + post_dict["file"]["path"], file_output_path
                )
                time.sleep(download_interval)
            if file_type == "video":
                self.download(
                    self.video_api_url + post_dict["file"]["path"], file_output_path
                )
                time.sleep(download_interval)

        # 下载附件
        if post_dict["attachments"]:
            log.info(f"⌛下载附件：共 {len(post_dict['attachments'])} 个")
            for attachment in post_dict["attachments"]:
                file_type = self.get_file_type(attachment["name"])
                attachment_output_path = os.path.join(
                    post_storage_dir, attachment["name"]
                )
                if file_type == "image":
                    self.download(
                        self.image_api_url + attachment["path"], attachment_output_path
                    )
                elif file_type == "video":
                    self.download(
                        self.video_api_url + attachment["path"], attachment_output_path
                    )
                time.sleep(download_interval)
                log.info(f"📦下载附件：{attachment['name']}")

        log.info("✅帖子下载完成")

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
            except Exception:
                log.error(f"❌帖子下载失败：{post['id']}")
                error_list.append(post)
        log.success(f"🚀下载完毕")
        if error_list != []:
            with open(error_output_dir_path, "w", encoding="utf-8") as f:
                json.dump(error_list, f, indent=4, ensure_ascii=False)

    def analysis_html_content(self, html: str) -> list[dict]:
        # 分析html
        soup = BeautifulSoup(html, "html.parser")
        # 查找所有img标签
        img_tags = soup.find_all("img")
        # 提取data-media-id和src属性
        results = []
        for img in img_tags:
            media_id = img.get("data-media-id")
            src = img.get("src")
            results.append({"id": media_id, "src": self.base_url + src})
        return results

    def download_html_content_batch(self, dir_path) -> list[dict]:

        html_file_list = []  # 存储所有找到的content.html路径
        download_fail_list = []  # 下载失败列表
        # 递归遍历目录
        for dirpath, dirnames, filenames in os.walk(dir_path):
            # 检查当前目录是否存在content.html
            if "content.html" in filenames:
                # 获取文件的绝对路径
                full_path = os.path.abspath(os.path.join(dirpath, "content.html"))
                html_file_list.append(full_path)

        print(f"找到{len(html_file_list)}个html文件")
        for html_file in html_file_list:
            html_file_parent_dir = os.path.dirname(html_file)
            with open(html_file, "r", encoding="utf-8") as f:
                html = f.read()
            download_url_list = self.analysis_html_content(html)
            now_html_download_progress = 1
            print(f"即将下载{len(download_url_list)}个文件")
            for url_dict in download_url_list:
                print(
                    "下载"
                    + url_dict["src"]
                    + " | "
                    + f"{html_file_parent_dir}/{os.path.basename(urlparse(url_dict['src']).path.rstrip('/'))}"
                    + " | "
                    + f"{now_html_download_progress}/{len(download_url_list)}"
                )
                try:
                    res = requests.get(url_dict["src"])
                    if res.status_code == 200:
                        with open(
                            f"{html_file_parent_dir}/{os.path.basename(urlparse(url_dict['src']).path.rstrip('/'))}",
                            "wb",
                        ) as f:
                            for chunk in res.iter_content(chunk_size=8192):
                                f.write(chunk)
                except:
                    download_fail_list.append(
                        {
                            "type": "html_content",
                            "url": url_dict["src"],
                            "name": os.path.basename(
                                urlparse(url_dict["src"]).path.rstrip("/")
                            ),
                            "storage_dir": f"{html_file_parent_dir}/{os.path.basename(urlparse(url_dict['src']).path.rstrip('/'))}",
                        }
                    )
                    print("下载失败：" + url_dict["src"])
                finally:
                    now_html_download_progress += 1
        return download_fail_list


if __name__ == "__main__":
    kd = KemonoDownloader("https://kemono.su/fanbox/user/13881589")
    # post_list = kd.get_post_info()
    # with open("temp/user_info.json", "w", encoding="utf-8") as f:
    #     json.dump(post_list, f, indent=4, ensure_ascii=False)

    # with open("temp/user_info.json", "r", encoding="utf-8") as f:
    # post_list = json.load(f)
    # download_fail_list = kd.download_post(post_list[10], r"./temp")
    # download_fail_list = kd.download_posts(post_list, r"./temp")
