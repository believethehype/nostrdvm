import json
import datetime as datetime
from types import NoneType

import pandas


def post_process_result(anno, original_event):
    print("post-processing...")
    if isinstance(anno, pandas.DataFrame):  # if input is an anno we parse it to required output format
        for tag in original_event.tags():
            print(tag.as_vec()[0])
            if tag.as_vec()[0] == "output":
                print("HAS OUTPUT TAG")
                output_format = tag.as_vec()[1]
                print("requested output is " + str(tag.as_vec()[1]) + "...")
                try:
                    if output_format == "text/plain":
                        result = ""
                        for each_row in anno['name']:
                            if each_row is not None:
                                for i in str(each_row).split('\n'):
                                    result = result + i + "\n"
                        result = replace_broken_words(
                            str(result).replace("\"", "").replace('[', "").replace(']', "").lstrip(None))
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
                            str(result).replace("\"", "").replace('[', "").replace(']', "").lstrip(None))
                        return result

                    elif output_format == "text/json" or output_format == "json":
                        # result = json.dumps(json.loads(anno.data.to_json(orient="records")))
                        result = replace_broken_words(json.dumps(anno.data.tolist()))
                        return result
                    # TODO add more
                    else:
                        result = ""
                        for element in anno.data:
                            element["name"] = str(element["name"]).lstrip()
                            element["from"] = (format(float(element["from"]), '.2f')).lstrip()  # name
                            element["to"] = (format(float(element["to"]), '.2f')).lstrip()  # name
                            result = result + "(" + str(element["from"]) + "," + str(element["to"]) + ")" + " " + str(
                                element["name"]) + "\n"

                        print(result)
                        result = replace_broken_words(result)
                        return result

                except Exception as e:
                    print(e)
                    result = replace_broken_words(str(anno.data))
                    return result

        else:
            result = ""
            for element in anno.data:
                element["name"] = str(element["name"]).lstrip()
                element["from"] = (format(float(element["from"]), '.2f')).lstrip()  # name
                element["to"] = (format(float(element["to"]), '.2f')).lstrip()  # name
                result = result + "(" + str(element["from"]) + "," + str(element["to"]) + ")" + " " + str(
                    element["name"]) + "\n"

            print(result)
            result = replace_broken_words(result)
            return result
    elif isinstance(anno, NoneType):
        return "An error occurred"
    else:
        result = replace_broken_words(anno) #TODO
        return result


def replace_broken_words(text):
    result = (text.replace("Noster", "Nostr").replace("Nostra", "Nostr").replace("no stir", "Nostr").
              replace("Nostro", "Nostr").replace("Impub", "npub").replace("sets", "Sats"))
    return result
