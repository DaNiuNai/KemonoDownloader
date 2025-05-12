import os
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup


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
