import json
import os
import re
import sys
import urllib.parse
from typing import Any
from urllib.request import urlopen, Request

import requests
import instaloader
from pytube import YouTube


def XitterDownload(source_url, target_location):
    script_dir = os.path.dirname(os.path.realpath(__file__))
    request_details_file = f"{script_dir}{os.sep}request_details.json"
    request_details = json.load(open(request_details_file, "r"))  # test
    features, variables = request_details["features"], request_details["variables"]

    def get_tokens(tweet_url):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0",
            "Accept": "*/*",
            "Accept-Language": "de,en-US;q=0.7,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "TE": "trailers",
        }

        html = requests.get(tweet_url, headers=headers)

        assert (
                html.status_code == 200
        ), f"Failed to get tweet page.  If you are using the correct Twitter URL this suggests a bug in the script.  Please open a GitHub issue and copy and paste this message.  Status code: {html.status_code}.  Tweet url: {tweet_url}"

        mainjs_url = re.findall(
            r"https://abs.twimg.com/responsive-web/client-web-legacy/main.[^\.]+.js",
            html.text,
        )

        assert (
                mainjs_url is not None and len(mainjs_url) > 0
        ), f"Failed to find main.js file.  If you are using the correct Twitter URL this suggests a bug in the script.  Please open a GitHub issue and copy and paste this message.  Tweet url: {tweet_url}"

        mainjs_url = mainjs_url[0]
        mainjs = requests.get(mainjs_url)

        assert (
                mainjs.status_code == 200
        ), f"Failed to get main.js file.  If you are using the correct Twitter URL this suggests a bug in the script.  Please open a GitHub issue and copy and paste this message.  Status code: {mainjs.status_code}.  Tweet url: {tweet_url}"

        bearer_token = re.findall(r'AAAAAAAAA[^"]+', mainjs.text)

        assert (
                bearer_token is not None and len(bearer_token) > 0
        ), f"Failed to find bearer token.  If you are using the correct Twitter URL this suggests a bug in the script.  Please open a GitHub issue and copy and paste this message.  Tweet url: {tweet_url}, main.js url: {mainjs_url}"

        bearer_token = bearer_token[0]

        # get the guest token
        with requests.Session() as s:
            s.headers.update(
                {
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0",
                    "accept": "*/*",
                    "accept-language": "de,en-US;q=0.7,en;q=0.3",
                    "accept-encoding": "gzip, deflate, br",
                    "te": "trailers",
                }
            )

            s.headers.update({"authorization": f"Bearer {bearer_token}"})

            # activate bearer token and get guest token
            guest_token = s.post("https://api.twitter.com/1.1/guest/activate.json").json()[
                "guest_token"
            ]

        assert (
                guest_token is not None
        ), f"Failed to find guest token.  If you are using the correct Twitter URL this suggests a bug in the script.  Please open a GitHub issue and copy and paste this message.  Tweet url: {tweet_url}, main.js url: {mainjs_url}"

        return bearer_token, guest_token

    def get_details_url(tweet_id, features, variables):
        # create a copy of variables - we don't want to modify the original
        variables = {**variables}
        variables["tweetId"] = tweet_id

        return f"https://twitter.com/i/api/graphql/0hWvDhmW8YQ-S_ib3azIrw/TweetResultByRestId?variables={urllib.parse.quote(json.dumps(variables))}&features={urllib.parse.quote(json.dumps(features))}"
        # return f"https://api.twitter.com/graphql/ncDeACNGIApPMaqGVuF_rw/TweetResultByRestId?variables={urllib.parse.quote(json.dumps(variables))}&features={urllib.parse.quote(json.dumps(features))}"

    def get_tweet_details(tweet_url, guest_token, bearer_token):
        tweet_id = re.findall(r"(?<=status/)\d+", tweet_url)

        assert (
                tweet_id is not None and len(tweet_id) == 1
        ), f"Could not parse tweet id from your url.  Make sure you are using the correct url.  If you are, then file a GitHub issue and copy and paste this message.  Tweet url: {tweet_url}"

        tweet_id = tweet_id[0]

        # the url needs a url encoded version of variables and features as a query string
        url = get_details_url(tweet_id, features, variables)

        details = requests.get(
            url,
            headers={
                "authorization": f"Bearer {bearer_token}",
                "x-guest-token": guest_token,
            },
        )

        max_retries = 10
        cur_retry = 0
        while details.status_code == 400 and cur_retry < max_retries:
            try:
                error_json = json.loads(details.text)
            except json.JSONDecodeError:
                assert (
                    False
                ), f"Failed to parse json from details error. details text: {details.text}  If you are using the correct Twitter URL this suggests a bug in the script.  Please open a GitHub issue and copy and paste this message.  Status code: {details.status_code}.  Tweet url: {tweet_url}"

            assert (
                    "errors" in error_json
            ), f"Failed to find errors in details error json.  If you are using the correct Twitter URL this suggests a bug in the script.  Please open a GitHub issue and copy and paste this message.  Status code: {details.status_code}.  Tweet url: {tweet_url}"

            needed_variable_pattern = re.compile(r"Variable '([^']+)'")
            needed_features_pattern = re.compile(
                r'The following features cannot be null: ([^"]+)'
            )

            for error in error_json["errors"]:
                needed_vars = needed_variable_pattern.findall(error["message"])
                for needed_var in needed_vars:
                    variables[needed_var] = True

                needed_features = needed_features_pattern.findall(error["message"])
                for nf in needed_features:
                    for feature in nf.split(","):
                        features[feature.strip()] = True

            url = get_details_url(tweet_id, features, variables)

            details = requests.get(
                url,
                headers={
                    "authorization": f"Bearer {bearer_token}",
                    "x-guest-token": guest_token,
                },
            )

            cur_retry += 1

            if details.status_code == 200:
                # save new variables
                request_details["variables"] = variables
                request_details["features"] = features

                with open(request_details_file, "w") as f:
                    json.dump(request_details, f, indent=4)

        assert (
                details.status_code == 200
        ), f"Failed to get tweet details.  If you are using the correct Twitter URL this suggests a bug in the script.  Please open a GitHub issue and copy and paste this message.  Status code: {details.status_code}.  Tweet url: {tweet_url}"

        return details

    def get_tweet_status_id(tweet_url):
        sid_patern = r'https://(?:x\.com|twitter\.com)/[^/]+/status/(\d+)'
        if tweet_url[len(tweet_url) - 1] != "/":
            tweet_url = tweet_url + "/"

        match = re.findall(sid_patern, tweet_url)
        if len(match) == 0:
            print("error, could not get status id from this tweet url :", tweet_url)
            exit()
        status_id = match[0]
        return status_id

    def get_associated_media_id(j, tweet_url):
        sid = get_tweet_status_id(tweet_url)
        pattern = (
                r'"expanded_url"\s*:\s*"https://x\.com/[^/]+/status/'
                + sid
                + r'/[^"]+",\s*"id_str"\s*:\s*"\d+",'
        )
        matches = re.findall(pattern, j)
        if len(matches) > 0:
            target = matches[0]
            target = target[0: len(target) - 1]  # remove the coma at the end
            return json.loads("{" + target + "}")["id_str"]
        return None

    def extract_mp4s(j, tweet_url, target_all_mp4s=False):
        # pattern looks like https://video.twimg.com/amplify_video/1638969830442237953/vid/1080x1920/lXSFa54mAVp7KHim.mp4?tag=16 or https://video.twimg.com/ext_tw_video/1451958820348080133/pu/vid/720x1280/GddnMJ7KszCQQFvA.mp4?tag=12
        amplitude_pattern = re.compile(
            r"(https://video.twimg.com/amplify_video/(\d+)/vid/(\d+x\d+)/[^.]+.mp4\?tag=\d+)"
        )
        ext_tw_pattern = re.compile(
            r"(https://video.twimg.com/ext_tw_video/(\d+)/pu/vid/(avc1/)?(\d+x\d+)/[^.]+.mp4\?tag=\d+)"
        )
        # format - https://video.twimg.com/tweet_video/Fvh6brqWAAQhU9p.mp4
        tweet_video_pattern = re.compile(r'https://video.twimg.com/tweet_video/[^"]+')

        # https://video.twimg.com/ext_tw_video/1451958820348080133/pu/pl/b-CiC-gZClIwXgDz.m3u8?tag=12&container=fmp4
        container_pattern = re.compile(r'https://video.twimg.com/[^"]*container=fmp4')
        media_id = get_associated_media_id(j, tweet_url)
        # find all the matches
        matches = amplitude_pattern.findall(j)
        matches += ext_tw_pattern.findall(j)
        container_matches = container_pattern.findall(j)

        tweet_video_matches = tweet_video_pattern.findall(j)

        if len(matches) == 0 and len(tweet_video_matches) > 0:
            return tweet_video_matches

        results = {}

        for match in matches:
            url, tweet_id, _, resolution = match
            if tweet_id not in results:
                results[tweet_id] = {"resolution": resolution, "url": url}
            else:
                # if we already have a higher resolution video, then don't overwrite it
                my_dims = [int(x) for x in resolution.split("x")]
                their_dims = [int(x) for x in results[tweet_id]["resolution"].split("x")]

                if my_dims[0] * my_dims[1] > their_dims[0] * their_dims[1]:
                    results[tweet_id] = {"resolution": resolution, "url": url}

        if media_id:
            all_urls = []
            for twid in results:
                all_urls.append(results[twid]["url"])
            all_urls += container_matches

            url_with_media_id = []
            for url in all_urls:
                if url.__contains__(media_id):
                    url_with_media_id.append(url)

            if len(url_with_media_id) > 0:
                return url_with_media_id

        if len(container_matches) > 0 and not target_all_mp4s:
            return container_matches

        if target_all_mp4s:
            urls = [x["url"] for x in results.values()]
            urls += container_matches
            return urls
        return [x["url"] for x in results.values()]

    def extract_mp4_fmp4(j):
        """
        Extract the URL of the MP4 video from the detailed information of the tweet.
        Returns a list of URLs, tweet IDs, and resolution information (dictionary type)
        and a list of tweet IDs as return values.
        """

        # Empty list to store tweet IDs
        tweet_id_list = []
        mp4_info_dict_list = []
        amplitude_pattern = re.compile(
            r"(https://video.twimg.com/amplify_video/(\d+)/vid/(avc1/)(\d+x\d+)/[^.]+.mp4\?tag=\d+)"
        )
        ext_tw_pattern = re.compile(
            r"(https://video.twimg.com/ext_tw_video/(\d+)/pu/vid/(avc1/)?(\d+x\d+)/[^.]+.mp4\?tag=\d+)"
        )
        tweet_video_pattern = re.compile(r'https://video.twimg.com/tweet_video/[^"]+')
        container_pattern = re.compile(r'https://video.twimg.com/[^"]*container=fmp4')

        matches = amplitude_pattern.findall(j)
        matches += ext_tw_pattern.findall(j)
        container_matches = container_pattern.findall(j)
        tweet_video_url_list = tweet_video_pattern.findall(j)

        for match in matches:
            url, tweet_id, _, resolution = match
            tweet_id_list.append(int(tweet_id))
            mp4_info_dict_list.append({"resolution": resolution, "url": url})

        tweet_id_list = list(dict.fromkeys(tweet_id_list))

        if len(container_matches) > 0:
            for url in container_matches:
                mp4_info_dict_list.append({"url": url})

        return tweet_id_list, mp4_info_dict_list, tweet_video_url_list

    def download_parts(url, output_filename):
        resp = requests.get(url, stream=True)
        pattern = re.compile(r"(/[^\n]*/(\d+x\d+)/[^\n]*container=fmp4)")
        matches = pattern.findall(resp.text)
        max_res = 0
        max_res_url = None

        for match in matches:
            url, resolution = match
            width, height = resolution.split("x")
            res = int(width) * int(height)
            if res > max_res:
                max_res = res
                max_res_url = url

        assert (
                max_res_url is not None
        ), f"Could not find a url to download from.  Make sure you are using the correct url.  If you are, then file a GitHub issue and copy and paste this message.  Tweet url: {url}"

        video_part_prefix = "https://video.twimg.com"

        resp = requests.get(video_part_prefix + max_res_url, stream=True)

        mp4_pattern = re.compile(r"(/[^\n]*\.mp4)")
        mp4_parts = mp4_pattern.findall(resp.text)

        assert (
                len(mp4_parts) == 1
        ), f"There should be exactly 1 mp4 container at this point.  Instead, found {len(mp4_parts)}.  Please open a GitHub issue and copy and paste this message into it.  Tweet url: {url}"

        mp4_url = video_part_prefix + mp4_parts[0]

        m4s_part_pattern = re.compile(r"(/[^\n]*\.m4s)")
        m4s_parts = m4s_part_pattern.findall(resp.text)

        with open(output_filename, "wb") as f:
            r = requests.get(mp4_url, stream=True)
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                    f.flush()

            for part in m4s_parts:
                part_url = video_part_prefix + part
                r = requests.get(part_url, stream=True)
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                        f.flush()

        return True

    def repost_check(j, exclude_replies=True):
        try:
            reply_index = j.index('"conversationthread-')
        except ValueError:
            reply_index = len(j)
        if exclude_replies:
            j = j[0:reply_index]

        # We use this regular expression to extract the source status
        source_status_pattern = r'"source_status_id_str"\s*:\s*"\d+"'
        matches = re.findall(source_status_pattern, j)

        if len(matches) > 0 and exclude_replies:
            # We extract the source status id (ssid)
            ssid = json.loads("{" + matches[0] + "}")["source_status_id_str"]
            # We plug it in this regular expression to find expanded_url (the original tweet url)
            expanded_url_pattern = (
                    r'"expanded_url"\s*:\s*"https://x\.com/[^/]+/status/' + ssid + '[^"]+"'
            )
            matches2 = re.findall(expanded_url_pattern, j)

            if len(matches2) > 0:
                # We extract the url and return it
                status_url = json.loads("{" + matches2[0] + "}")["expanded_url"]
                return status_url

        if not exclude_replies:
            # If we include replies we'll have to get all ssids and remove duplicates
            ssids = []
            for match in matches:
                ssids.append(json.loads("{" + match + "}")["source_status_id_str"])
            # we remove duplicates (this line is messy but it's the easiest way to do it)
            ssids = list(set(ssids))
            if len(ssids) > 0:
                for ssid in ssids:
                    expanded_url_pattern = (
                            r'"expanded_url"\s*:\s*"https://x\.com/[^/]+/status/'
                            + ssid
                            + '[^"]+"'
                    )
                    matches2 = re.findall(expanded_url_pattern, j)
                    if len(matches2) > 0:
                        status_urls = []
                        for match in matches2:
                            status_urls.append(
                                json.loads("{" + match + "}")["expanded_url"]
                            )
                        # We remove duplicates another time
                        status_urls = list(set(status_urls))
                        return status_urls

        # If we don't find source_status_id_str, the tweet doesn't feature a reposted video
        return None

    def download_video_from_x(tweet_url, output_file, target_all_videos=False):
        bearer_token, guest_token = get_tokens(tweet_url)
        resp = get_tweet_details(tweet_url, guest_token, bearer_token)
        mp4s = extract_mp4s(resp.text, tweet_url, target_all_videos)

        if target_all_videos:
            video_counter = 1
            original_urls = repost_check(resp.text, exclude_replies=False)

            if len(original_urls) > 0:
                for url in original_urls:
                    download_video_from_x(
                        url, output_file.replace(".mp4", f"_{video_counter}.mp4")
                    )
                    video_counter += 1
                if len(mp4s) > 0:
                    for mp4 in mp4s:
                        output_file = output_file.replace(".mp4", f"_{video_counter}.mp4")
                        if "container" in mp4:
                            download_parts(mp4, output_file)

                        else:
                            # use a stream to download the file
                            r = requests.get(mp4, stream=True)
                            with open(output_file, "wb") as f:
                                for chunk in r.iter_content(chunk_size=1024):
                                    if chunk:
                                        f.write(chunk)
                                        f.flush()
                        video_counter += 1
        else:
            original_url = repost_check(resp.text)

            if original_url:
                download_video_from_x(original_url, output_file)
            else:
                assert (
                        len(mp4s) > 0
                ), f"Could not find any mp4s to download.  Make sure you are using the correct url.  If you are, then file a GitHub issue and copy and paste this message.  Tweet url: {tweet_url}"

                mp4 = mp4s[0]
                if "container" in mp4:
                    download_parts(mp4, output_file)
                else:
                    # use a stream to download the file
                    r = requests.get(mp4, stream=True)
                    with open(output_file, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024):
                            if chunk:
                                f.write(chunk)
                                f.flush()
        return target_location

    return download_video_from_x(source_url, target_location)


# TIKTOK/INSTA
def getDict() -> dict:
    response = requests.get('https://ttdownloader.com/')
    point = response.text.find('<input type="hidden" id="token" name="token" value="') + \
            len('<input type="hidden" id="token" name="token" value="')
    token = response.text[point:point + 64]
    TTDict = {
        'token': token,
    }

    for i in response.cookies:
        TTDict[str(i).split()[1].split('=')[0].strip()] = str(
            i).split()[1].split('=')[1].strip()
    return TTDict


def createHeader(parseDict) -> tuple[dict[str, Any], dict[str | Any, str | Any], dict[str, str | Any]]:
    cookies = {
        'PHPSESSID': parseDict['PHPSESSID'],
        # 'popCookie': parseDict['popCookie'],
    }
    headers = {
        'authority': 'ttdownloader.com',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://ttdownloader.com',
        'referer': 'https://ttdownloader.com/',
        'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/108.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }
    data = {
        'url': '',
        'format': '',
        'token': parseDict['token'],
    }
    return cookies, headers, data


def TikTokDownload(cookies, headers, data, name, path) -> str:
    response = requests.post('https://ttdownloader.com/search/',
                             cookies=cookies, headers=headers, data=data)
    parsed_link = [i for i in str(response.text).split()
                   if i.startswith("href=")][0]

    response = requests.get(parsed_link[6:-10])
    with open(path + "\\" + name + ".mp4", "wb") as f:
        f.write(response.content)
    return path + "\\" + name + ".mp4"


def TiktokDownloadAll(linkList, path) -> str:
    parseDict = getDict()
    cookies, headers, data = createHeader(parseDict)
    # linkList = getLinkDict()['tiktok']
    for i in linkList:
        try:
            data['url'] = i
            result = TikTokDownload(cookies, headers, data, "tiktok", path)  # str(linkList.index(i))
            return result
        except IndexError:
            parseDict = getDict()
            cookies, headers, data = createHeader(parseDict)
        except Exception as err:
            print(err)
            exit(1)


def InstagramDownload(url, name, path) -> str:
    obj = instaloader.Instaloader()
    post = instaloader.Post.from_shortcode(obj.context, url.split("/")[-2])
    photo_url = post.url
    video_url = post.video_url
    print(video_url)
    if video_url:
        response = requests.get(video_url)
        with open(path + "\\" + name + ".mp4", "wb") as f:
            f.write(response.content)
            return path + "\\" + name + ".mp4"
    elif photo_url:
        response = requests.get(photo_url)
        with open(path + "\\" + name + ".jpg", "wb") as f:
            f.write(response.content)
            return path + "\\" + name + ".jpg"


def InstagramDownloadAll(linklist, path) -> str:
    for i in linklist:
        try:
            print(str(linklist.index(i)))
            print(str(linklist[i]))
            result = InstagramDownload(i, str(linklist.index(i)), path)
            return result
        except Exception as err:
            print(err)
            exit(1)


# YOUTUBE
def YouTubeDownload(link, path, audio_only=True):
    youtubeObject = YouTube(link)
    if audio_only:
        youtubeObject = youtubeObject.streams.get_audio_only()
        youtubeObject.download(path, "yt.mp3")
        print("Download is completed successfully")
        return path + "yt.mp3"
    else:
        youtubeObject = youtubeObject.streams.get_highest_resolution()
        youtubeObject.download(path, "yt.mp4")
        print("Download is completed successfully")
        return path + "yt.mp4"


def checkYoutubeLinkValid(link):
    try:
        # TODO find a way to test without fully downloading the file
        youtubeObject = YouTube(link)
        youtubeObject = youtubeObject.streams.get_audio_only()
        youtubeObject.download(".", "yt.mp3")
        os.remove("yt.mp3")
        return True

    except Exception as e:
        print(str(e))
        return False


# OVERCAST
def OvercastDownload(source_url, target_location):
    def get_title(html_str):
        """Get the title from the meta tags"""

        title = re.findall(r"<meta name=\"og:title\" content=\"(.+)\"", html_str)
        if len(title) == 1:
            return title[0].replace("&mdash;", "-")
        return None

    def get_description(html_str):
        """Get the description from the Meta tag"""

        desc_re = r"<meta name=\"og:description\" content=\"(.+)\""
        description = re.findall(desc_re, html_str)
        if len(description) == 1:
            return description[0]
        return None

    def get_url(html_string):
        """Find the URL from the <audio><source>.... tag"""

        url = re.findall(r"<source src=\"(.+?)\"", html_string)
        if len(url) == 1:
            # strip off the last 4 characters to cater for the #t=0 in the URL
            # which urlretrieve flags as invalid
            return url[0][:-4]
        return None

    """Given a Overcast source URL fetch the file it points to"""
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
                      "AppleWebKit/537.11 (KHTML, like Gecko) "
                      "Chrome/23.0.1271.64 Safari/537.11",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
        "Accept-Encoding": "none",
        "Accept-Language": "en-US,en;q=0.8",
        "Connection": "keep-alive",
    }
    req = Request(source_url, None, headers)
    source_data = urlopen(req).read().decode('utf-8')
    title = get_title(source_data)
    url = get_url(source_data)

    if url is None or title is None:
        sys.exit("Could not find parse URL")
    if not os.path.exists(target_location):
        req = requests.get(url)
        file = open(target_location, 'wb')
        for chunk in req.iter_content(100000):
            file.write(chunk)
        file.close()
