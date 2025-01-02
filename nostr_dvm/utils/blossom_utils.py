import base64
import hashlib
import json
import mimetypes
import os

import aiohttp
from nostr_sdk import Keys, Tag, EventBuilder, Kind, Timestamp


def sha256(file):
        h = hashlib.sha256()
        h.update(file)
        return h.digest().hex()

async def check(url, sha256, key):
    async with aiohttp.ClientSession(url) as sess:
        b64_auth = await generate_blossom_header(key, sha256, "get")
        headers = {
            "Authorization": b64_auth
        }

        async with sess.get(f"{sha256}",   headers=headers) as resp:
            return resp.status == 200


async def generate_blossom_header(key, hash, method):

    keys = Keys.parse(key)
    t_tag = Tag.parse(["t", method])
    x_tag = Tag.parse(["x", hash])
    expiration_tag = Tag.parse(["expiration", str(Timestamp.now().as_secs() + 300)])
    tags = [x_tag, t_tag, expiration_tag]

    eb = EventBuilder(Kind(24242), "Uploading blob with SHA-256 hash").tags(tags)
    event  = eb.sign_with_keys(keys)

    encoded_nip98_event = base64.b64encode(event.as_json().encode('utf-8')).decode('utf-8')
    return "Nostr " + encoded_nip98_event


def upload_image_to_blossom(file_path, url):
    """Uploads an image to a Blossom server via a PUT request."""


async def upload_blossom(filepath, pkey, url):

    with open(filepath, "rb") as f:
        mtime = int(os.fstat(f.fileno()).st_mtime)

        file = f.read()
        hash = sha256(file)
        b64_auth = await generate_blossom_header(pkey, hash, "upload")

        file_stats = os.stat(filepath)
        sizeinmb = file_stats.st_size / (1024 * 1024)
        print("Filesize of Uploaded media: " + str(sizeinmb) + " Mb.")

        if await check(url, hash, pkey):
            print(f"Blob {hash} is up to date for [{filepath}].")
        else:
            print(f"Storing file [{hash}] on blossom.")


            content_type = mimetypes.guess_type(filepath)[0] or 'application/octet-stream'

            # Upload object to blossom.
            async with aiohttp.ClientSession() as sess:
                async with sess.put(
                        url = url.rstrip('/') + '/upload',
                        data=file,
                        headers={
                            "Authorization": b64_auth,
                            "Content-Type": content_type
                        }) as resp:


                    if resp.status == 413:
                        print("Can't upload on Blossom Server")
                        return "Can't upload on Blossom Server"

                    elif resp.status != 200:
                        txt = await resp.text()
                        print(txt)
                    else:
                        res = await resp.text()
                        resjson = json.loads(res)
                        print(resjson["url"])
                        return resjson["url"]

