import json
import datetime as datetime
import os
import random
from types import NoneType

import emoji
import requests
from nostr_sdk import Tag, PublicKey, EventId, Keys
from pyupload.uploader import CatboxUploader

import pandas

from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nip98_utils import generate_nip98_header

'''
Post process results to either given output format or a Nostr readable plain text.
'''


class PostProcessFunctionType:
    NONE = 0
    LIST_TO_USERS = 1
    LIST_TO_EVENTS = 2


def post_process_result(anno, original_event):
    print("Post-processing...")
    if isinstance(anno, pandas.DataFrame):  # if input is an anno we parse it to required output format
        print("Pandas Dataframe...")
        has_output_tag = False
        output_format = "text/plain"

        for tag in original_event.tags():
            if tag.as_vec()[0] == "output":
                output_format = tag.as_vec()[1]
                has_output_tag = True
                print("requested output is " + str(output_format) + "...")

        if has_output_tag:
            print("Output Tag found: " + output_format)
            try:
                if output_format == "text/plain":
                    result = pandas_to_plaintext(anno)
                    result = replace_broken_words(
                        str(result).replace("\"", "").replace('[', "").replace(']',
                                                                               "").lstrip(None))
                    return result

                elif output_format == "text/vtt":
                    print(str(anno))
                    result = "WEBVTT\n\n"
                    for element in anno:
                        name = element["name"]  # name
                        start = float(element["from"])
                        convertstart = str(datetime.timedelta(seconds=start))
                        end = float(element["to"])
                        convertend = str(datetime.timedelta(seconds=end))
                        print(str(convertstart) + " --> " + str(convertend))
                        cleared_name = str(name).lstrip("\'").rstrip("\'")
                        result = result + str(convertstart) + " --> " + str(
                            convertend) + "\n" + cleared_name + "\n\n"
                    result = replace_broken_words(
                        str(result).replace("\"", "").replace('[', "").replace(']',
                                                                               "").lstrip(None))
                    return result

                elif output_format == "text/json" or output_format == "json":
                    # result = json.dumps(json.loads(anno.data.to_json(orient="records")))
                    result = replace_broken_words(json.dumps(anno.data.tolist()))
                    return result
                # TODO add more
                else:
                    print("Pandas Dataframe but output tag not supported.. falling back to default..")
                    result = pandas_to_plaintext(anno)
                    print(result)
                    result = str(result).replace("\"", "").replace('[', "").replace(']',
                                                                                    "").lstrip(None)
                    return result

            except Exception as e:
                print(e)
                result = replace_broken_words(str(anno.data))
                return result

        else:
            print("Pandas Dataframe but no output tag set.. falling back to default..")
            result = pandas_to_plaintext(anno)
            print(result)
            result = str(result).replace("\"", "").replace('[', "").replace(']',
                                                                            "").lstrip(None)
            return result
    elif isinstance(anno, NoneType):
        return "An error occurred"
    else:
        result = replace_broken_words(anno)  # TODO
        return result


def post_process_list_to_events(result):
    result_list = json.loads(result)
    result_str = ""
    if len(result_list) == 0:
        return "No results found"
    for tag in result_list:
        e_tag = Tag.parse(tag)
        result_str = result_str + "nostr:" + EventId.from_hex(
            e_tag.as_vec()[1]).to_bech32() + "\n"
    return result_str


def post_process_list_to_users(result):
    result_list = json.loads(result)
    result_str = ""
    if len(result_list) == 0:
        return "No results found"
    for tag in result_list:
        p_tag = Tag.parse(tag)
        result_str = result_str + "nostr:" + PublicKey.parse(
            p_tag.as_vec()[1]).to_bech32() + "\n"
    return result_str


def pandas_to_plaintext(anno):
    result = ""
    for each_row in anno['name']:
        if each_row is not None:
            for i in str(each_row).split('\n'):
                result = result + i + "\n"
    return result


'''
Convenience function to replace words like Noster with Nostr
'''


def replace_broken_words(text):
    result = (text.replace("Noster", "Nostr").replace("Nostra", "Nostr").replace("no stir", "Nostr").
              replace("Nostro", "Nostr").replace("Impub", "npub").replace("sets", "Sats"))
    return result


'''
Function to upload to Nostr.build and if it fails to Nostrfiles.dev
Larger files than these hosters allow and fallback is catbox currently.
Will probably need to switch to another system in the future.
'''


async def upload_media_to_hoster(filepath: str, dvm_config=None, usealternativeforlargefiles=True):

    if dvm_config is None:
        dvm_config = DVMConfig()
        dvm_config.NIP89.PK = Keys.parse(os.getenv("NOSTR_BUILD_ACCOUNT_PK")).secret_key().to_hex()

    print("Uploading image: " + filepath)
    try:
        files = {'file': open(filepath, 'rb')}
        file_stats = os.stat(filepath)
        sizeinmb = file_stats.st_size / (1024 * 1024)
        print("Filesize of Uploaded media: " + str(sizeinmb) + " Mb.")
        if sizeinmb > 25 and usealternativeforlargefiles:
            print("Filesize over Nostr.build limited, using catbox")
            uploader = CatboxUploader(filepath)
            result = uploader.execute()
            return result
        else:
            url = 'https://nostr.build/api/v2/upload/files'
            auth = await generate_nip98_header(filepath, dvm_config)
            headers = {'authorization': auth}

            response = requests.post(url, files=files, headers=headers)
            print(response.text)
            json_object = json.loads(response.text)
            result = json_object["data"][0]["url"]
            return result
    except Exception as e:
        print(e)
        try:
            uploader = CatboxUploader(filepath)
            result = uploader.execute()
            print(result)
            return result
        except:
            raise Exception("Upload not possible, all hosters didn't work or couldn't generate output")


def build_status_reaction(status, task, amount, content, dvm_config):
    alt_description = "This is a reaction to a NIP90 DVM AI task. "

    if status == "processing":
        if content is not None:
            if isinstance(content, list) or isinstance(content, dict):
                message = random.choice(content)
            else:
                message = content
            alt_description = message
            reaction = alt_description

        else:
            alt_description = "NIP90 DVM task " + task + " started processing. "
            reaction = alt_description + emoji.emojize(":thumbs_up:")
    elif status == "success":
        alt_description = "NIP90 DVM task " + task + " finished successfully. "
        reaction = alt_description + emoji.emojize(":call_me_hand:")
    elif status == "chain-scheduled":
        alt_description = "NIP90 DVM task " + task + " Chain Task scheduled"
        reaction = alt_description + emoji.emojize(":thumbs_up:")
    elif status == "error":
        alt_description = "NIP90 DVM task " + task + " had an error. "
        if content is None:
            reaction = alt_description + emoji.emojize(":thumbs_down:")
        else:
            reaction = alt_description + emoji.emojize(":thumbs_down:") + " " + content

    elif status == "payment-required":
        alt_description = "NIP90 DVM task " + task + " requires payment of min " + str(
            amount) + " Sats. "
        reaction = alt_description + emoji.emojize(":orange_heart:")

    elif status == "subscription-required":
        if content is not None and content != "":
            alt_description = content
            reaction = alt_description

        else:
            alt_description = "NIP90 DVM task " + task + " requires payment for subscription"
            reaction = alt_description + emoji.emojize(":orange_heart:")



    elif status == "payment-rejected":
        alt_description = "NIP90 DVM task " + task + " payment is below required amount of " + str(
            amount) + " Sats. "
        reaction = alt_description + emoji.emojize(":thumbs_down:")
    elif status == "user-blocked-from-service":
        alt_description = "NIP90 DVM task " + task + " can't be performed. User has been blocked from Service. "
        reaction = alt_description + emoji.emojize(":thumbs_down:")
    else:
        reaction = emoji.emojize(":thumbs_down:")

    return alt_description, reaction
